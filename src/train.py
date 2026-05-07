"""
Training loop for the HRM Crime Detection model.

Strategy
────────
Each mini-batch is split into abnormal and normal samples.
The MIL Ranking Loss compares the peak anomaly score of abnormal videos
against the peak score of normal videos.

Schedule
────────
- Optimiser : AdamW (weight decay regularises the Transformer)
- LR Scheduler: CosineAnnealingLR decays LR smoothly to near zero
- Gradient clipping at max_norm=1.0 prevents exploding gradients
  (common with Transformer encoders)

Checkpointing
─────────────
- Best model (highest val AUC) saved as  checkpoints/best_hrm_model.pth
- Epoch snapshots saved every  CHECKPOINT_EVERY  epochs
"""

import os
import heapq
import logging
from typing import Dict, Tuple

import torch
import torch.optim as optim
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)

CHECKPOINT_EVERY = 10   # Save an epoch snapshot every N epochs
TOP_K_SNAPSHOTS  = 5    # Keep the top-K epoch checkpoints by val AUC for ensembling


# ─────────────────────────────────────────────────────────────
# Single epoch
# ─────────────────────────────────────────────────────────────

def _train_one_epoch(model, dataloader, criterion, optimizer, device, grad_clip):
    model.train()

    total_loss   = 0.0
    rank_loss_   = 0.0
    smooth_loss_ = 0.0
    sparse_loss_ = 0.0
    n_batches    = 0

    for features, labels in dataloader:
        abn_mask  = labels == 1
        norm_mask = labels == 0

        # Skip batch if it lacks either class
        if abn_mask.sum() == 0 or norm_mask.sum() == 0:
            continue

        abn_feat  = features[abn_mask].to(device)
        norm_feat = features[norm_mask].to(device)

        optimizer.zero_grad()

        scores_abn  = model(abn_feat)   # [n_abn, T]
        scores_norm = model(norm_feat)  # [n_norm, T]

        loss, r_loss, sm_loss, sp_loss = criterion(scores_abn, scores_norm)

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
        optimizer.step()

        total_loss   += loss.item()
        rank_loss_   += r_loss.item()
        smooth_loss_ += sm_loss.item()
        sparse_loss_ += sp_loss.item()
        n_batches    += 1

    if n_batches == 0:
        return 0.0, 0.0, 0.0, 0.0

    n = n_batches
    return (
        total_loss   / n,
        rank_loss_   / n,
        smooth_loss_ / n,
        sparse_loss_ / n,
    )


# ─────────────────────────────────────────────────────────────
# Main training function
# ─────────────────────────────────────────────────────────────

def train(
    model,
    train_dataset,
    val_dataset,
    criterion,
    config: Dict,
    device: torch.device,
    resume_from: str = None,
    early_stop_patience: int = 15,
) -> Tuple[Dict, float]:
    """
    Train the HRM model and return (history, best_val_auc).

    Parameters
    ----------
    model          : HRM_Model instance (already on device)
    train_dataset  : FeatureDataset for training split
    val_dataset    : FeatureDataset for validation / test split
    criterion      : MILRankingLoss instance
    config         : dict with keys:
                       batch_size, learning_rate, weight_decay,
                       num_epochs, checkpoints_dir, grad_clip
    device         : torch.device

    Returns
    -------
    history : dict  {'train_loss', 'val_auc', 'rank_loss',
                     'smooth_loss', 'sparse_loss'}
    best_auc : float
    """
    # Lazy import to avoid circular dependency
    from src.evaluate import compute_auc

    os.makedirs(config['checkpoints_dir'], exist_ok=True)

    # ── Data loaders ─────────────────────────────────────────
    train_loader = DataLoader(
        train_dataset,
        batch_size  = config['batch_size'],
        shuffle     = True,
        num_workers = 0,
        pin_memory  = device.type == 'cuda',
        drop_last   = False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size  = config['batch_size'],
        shuffle     = False,
        num_workers = 0,
        pin_memory  = device.type == 'cuda',
    )

    # ── Optimiser & scheduler ─────────────────────────────────
    optimizer = optim.AdamW(
        model.parameters(),
        lr           = config['learning_rate'],
        weight_decay = config['weight_decay'],
    )

    # Linear warmup for WARMUP_EPOCHS epochs, then cosine annealing.
    WARMUP_EPOCHS = 5
    peak_lr  = config['learning_rate']
    start_lr = peak_lr / 1000.0

    def _lr_lambda(epoch_0indexed: int) -> float:
        if epoch_0indexed < WARMUP_EPOCHS:
            return (start_lr / peak_lr) + (1.0 - start_lr / peak_lr) * \
                   epoch_0indexed / WARMUP_EPOCHS
        eta_min  = 1e-6
        progress = (epoch_0indexed - WARMUP_EPOCHS) / \
                   max(1, config['num_epochs'] - WARMUP_EPOCHS)
        return eta_min / peak_lr + \
               0.5 * (1.0 - eta_min / peak_lr) * \
               (1 + __import__('math').cos(__import__('math').pi * progress))

    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=_lr_lambda)

    # ── Resume from checkpoint ────────────────────────────────
    start_epoch = 1
    best_auc    = 0.0
    if resume_from and os.path.exists(resume_from):
        ckpt = torch.load(resume_from, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        start_epoch = ckpt.get('epoch', 0) + 1
        best_auc    = ckpt.get('val_auc', 0.0)
        # Fast-forward scheduler to match resumed epoch
        for _ in range(start_epoch - 1):
            scheduler.step()
        logger.info(
            f"Resumed from {resume_from}  "
            f"(epoch {start_epoch-1}, best_auc={best_auc:.4f})"
        )

    # ── Training history ──────────────────────────────────────
    history = {
        'train_loss':  [],
        'rank_loss':   [],
        'smooth_loss': [],
        'sparse_loss': [],
        'val_auc':     [],
    }
    grad_clip      = config.get('grad_clip', 1.0)
    no_improve_cnt = 0   # early stopping counter
    # min-heap of (auc, path) — we keep the top-K by evicting the lowest
    top_k_heap: list = []
    seed_tag = config.get('seed_tag', 'unknown')
    snap_dir = os.path.join(config['checkpoints_dir'], f'snapshots_seed_{seed_tag}')
    os.makedirs(snap_dir, exist_ok=True)

    logger.info(
        f"Training starts | "
        f"epochs={config['num_epochs']} | "
        f"batch={config['batch_size']} | "
        f"lr={config['learning_rate']}"
    )

    for epoch in range(start_epoch, config['num_epochs'] + 1):

        # ── Train ──────────────────────────────────────────────
        t_loss, r_loss, sm_loss, sp_loss = _train_one_epoch(
            model, train_loader, criterion, optimizer, device, grad_clip
        )
        scheduler.step()

        # ── Validate ───────────────────────────────────────────
        val_auc = compute_auc(model, val_loader, device)

        # ── Log ────────────────────────────────────────────────
        history['train_loss'].append(t_loss)
        history['rank_loss'].append(r_loss)
        history['smooth_loss'].append(sm_loss)
        history['sparse_loss'].append(sp_loss)
        history['val_auc'].append(val_auc)

        lr_now = scheduler.get_last_lr()[0]
        logger.info(
            f"Epoch [{epoch:3d}/{config['num_epochs']}]  "
            f"Loss={t_loss:.4f} (rank={r_loss:.4f} sm={sm_loss:.6f} sp={sp_loss:.4f})  "
            f"Val AUC={val_auc:.4f}  lr={lr_now:.2e}"
        )

        # ── Save best model ────────────────────────────────────
        if val_auc > best_auc:
            best_auc       = val_auc
            no_improve_cnt = 0
            ckpt_path = os.path.join(
                config['checkpoints_dir'], 'best_hrm_model.pth'
            )
            torch.save(
                {
                    'epoch':               epoch,
                    'model_state_dict':    model.state_dict(),
                    'optimizer_state_dict':optimizer.state_dict(),
                    'val_auc':             val_auc,
                    'config':              config,
                },
                ckpt_path,
            )
            logger.info(f"  -> Best model saved  AUC={best_auc:.4f}")
        else:
            no_improve_cnt += 1

        # ── Epoch snapshot ─────────────────────────────────────
        if epoch % CHECKPOINT_EVERY == 0:
            snap_path = os.path.join(
                config['checkpoints_dir'], f'hrm_epoch_{epoch:03d}.pth'
            )
            torch.save(model.state_dict(), snap_path)
            logger.info(f"  -> Epoch snapshot saved: {snap_path}")

        # ── Top-K snapshot for ensemble ────────────────────────
        # Only start collecting after warmup (epoch > 10) to skip noisy early epochs
        if epoch > 10:
            snap_path = os.path.join(snap_dir, f'snap_epoch_{epoch:03d}_auc_{val_auc:.4f}.pth')
            torch.save(model.state_dict(), snap_path)
            heapq.heappush(top_k_heap, (val_auc, snap_path))
            if len(top_k_heap) > TOP_K_SNAPSHOTS:
                evicted_auc, evicted_path = heapq.heappop(top_k_heap)
                if os.path.exists(evicted_path):
                    os.remove(evicted_path)

        # ── Early stopping ─────────────────────────────────────
        if early_stop_patience > 0 and no_improve_cnt >= early_stop_patience:
            logger.info(
                f"  -> Early stopping at epoch {epoch} "
                f"(no improvement for {early_stop_patience} epochs). "
                f"Best AUC={best_auc:.4f}"
            )
            break

    # Persist the top-K snapshot paths so multiseed can retrieve them
    top_k_paths = [path for _, path in sorted(top_k_heap, reverse=True)]
    logger.info(
        f"Training complete.  Best Val AUC: {best_auc:.4f}  "
        f"Top-{len(top_k_paths)} snapshots kept for ensemble."
    )
    return history, best_auc, top_k_paths
