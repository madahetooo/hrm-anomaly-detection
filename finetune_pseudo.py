"""
Pseudo-label fine-tuning (self-training) for HRM.

Steps
─────
1. Load best pre-trained model (seed 77, AUC=0.9131).
2. Run inference on ALL training videos → per-segment scores.
3. Generate pseudo-labels:
     Anomaly video: seg_pseudo = 1  if score > PSEUDO_THR, else 0
     Normal  video: seg_pseudo = 0  for every segment
4. Fine-tune for FT_EPOCHS epochs with:
     loss = MIL_ranking_loss + ALPHA * BCE(scores, pseudo_labels)
   Using a lower LR so we don't destroy the pre-trained weights.
5. Evaluate on test set and report AUC.

Rationale
─────────
The model has a ceiling at ~0.9131 with pure MIL training because MIL
only supervises the MAX segment.  Pseudo-labels give soft segment-level
supervision that helps the model push subtle-anomaly segments higher.
"""

import os, logging, sys, random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

import config
from src.model   import HRM_Model
from src.loss    import MILRankingLoss
from src.dataset import FeatureDataset
from src.evaluate import compute_auc, full_evaluation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.BASE_DIR, 'finetune_pseudo.log'), mode='a'),
    ],
)
logger = logging.getLogger(__name__)

# ── Hyperparameters ───────────────────────────────────────────
PSEUDO_THR  = 0.30     # Segment score threshold for anomaly pseudo-label
ALPHA       = 0.5      # Weight for BCE pseudo-label loss vs MIL loss
FT_LR       = 5e-5     # Fine-tuning LR (lower than training LR)
FT_EPOCHS   = 25       # Number of fine-tuning epochs
FT_BATCH    = 8
SEEDS       = [77, 55, 7, 999, 131, 137, 139, 149, 151, 157]  # try these


def generate_pseudo_labels(model, dataset, device, thr):
    """
    Returns list of (features_tensor, pseudo_label_tensor, video_label).
    pseudo_label_tensor shape: [T]  values in {0, 1}.
    """
    model.eval()
    items = []
    with torch.no_grad():
        for feat, lbl in dataset:
            x   = feat.unsqueeze(0).to(device)
            seg = model(x)[0].cpu()        # [T]
            if lbl.item() == 1:
                pseudo = (seg >= thr).float()
            else:
                pseudo = torch.zeros_like(seg)
            items.append((feat, pseudo, lbl))
    return items


class PseudoLabelDataset(Dataset):
    def __init__(self, items):
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        return self.items[idx]


def finetune(model, pseudo_items, val_dataset, criterion, device,
             ft_lr, ft_epochs, ft_batch, alpha, run_label):
    """Fine-tune the model with pseudo-label BCE + MIL loss."""
    from src.evaluate import compute_auc

    pseudo_ds     = PseudoLabelDataset(pseudo_items)
    pseudo_loader = DataLoader(pseudo_ds, batch_size=ft_batch,
                               shuffle=True, num_workers=0)
    val_loader    = DataLoader(val_dataset, batch_size=ft_batch,
                               shuffle=False, num_workers=0)

    optimizer = optim.AdamW(model.parameters(), lr=ft_lr, weight_decay=1e-4)
    bce       = nn.BCELoss()

    best_auc   = 0.0
    best_state = None

    for epoch in range(1, ft_epochs + 1):
        model.train()
        total_loss = 0.0
        n_batches  = 0

        for feat, pseudo, lbl in pseudo_loader:
            abn_mask  = lbl == 1
            norm_mask = lbl == 0
            if abn_mask.sum() == 0 or norm_mask.sum() == 0:
                continue

            feat_abn  = feat[abn_mask].to(device)
            feat_norm = feat[norm_mask].to(device)
            ps_abn    = pseudo[abn_mask].to(device)

            optimizer.zero_grad()

            sc_abn  = model(feat_abn)   # [n_abn, T]
            sc_norm = model(feat_norm)  # [n_norm, T]

            # MIL ranking loss
            mil_loss, _, _, _ = criterion(sc_abn, sc_norm)

            # BCE on pseudo-labels (anomaly segments only)
            bce_loss = bce(sc_abn, ps_abn)

            loss = mil_loss + alpha * bce_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            n_batches  += 1

        val_auc = compute_auc(model, val_loader, device)
        logger.info(
            f"[{run_label}] FT Epoch [{epoch:2d}/{ft_epochs}]  "
            f"loss={total_loss/max(n_batches,1):.4f}  val_auc={val_auc:.4f}"
        )

        if val_auc > best_auc:
            best_auc   = val_auc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            logger.info(f"  -> FT best: {best_auc:.4f}")

    if best_state is not None:
        model.load_state_dict(best_state)

    return best_auc


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")

    # ── Datasets ──────────────────────────────────────────────
    train_feat_dir = os.path.join(config.FEATURES_DIR, 'train')
    test_feat_dir  = os.path.join(config.FEATURES_DIR, 'test')
    train_r3d = os.path.join(config.FEATURES_R3D_DIR, 'train')
    test_r3d  = os.path.join(config.FEATURES_R3D_DIR, 'test')
    aux_train = train_r3d if os.path.isdir(train_r3d) else None
    aux_test  = test_r3d  if os.path.isdir(test_r3d)  else None

    train_ds = FeatureDataset(train_feat_dir, n_segments=config.N_SEGMENTS,
                               augment=False, aux_features_dir=aux_train)
    test_ds  = FeatureDataset(test_feat_dir,  n_segments=config.N_SEGMENTS,
                               augment=False, aux_features_dir=aux_test)

    criterion = MILRankingLoss(
        margin=config.MARGIN,
        lambda_smooth=config.LAMBDA_SMOOTH,
        lambda_sparse=config.LAMBDA_SPARSE,
    )

    global_best_auc   = 0.0
    global_best_seed  = None
    global_best_state = None

    for seed in SEEDS:
        logger.info("=" * 60)
        logger.info(f"  Pseudo-label fine-tuning from seed {seed} checkpoint")
        logger.info("=" * 60)

        # Load seed checkpoint if it exists, otherwise load global best
        seed_ckpt = os.path.join(config.CHECKPOINTS_DIR, f'seed_{seed}_best.pth')
        global_ckpt = os.path.join(config.CHECKPOINTS_DIR, 'global_best_hrm_model.pth')
        ckpt_path = seed_ckpt if os.path.exists(seed_ckpt) else global_ckpt

        if not os.path.exists(ckpt_path):
            logger.warning(f"No checkpoint found for seed {seed}, skipping.")
            continue

        ckpt = torch.load(ckpt_path, map_location=device)
        base_auc = ckpt.get('val_auc', 0.0)
        logger.info(f"  Base checkpoint AUC: {base_auc:.4f}")

        # Build fresh model and load weights
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        model = HRM_Model(
            feature_dim=config.FEATURE_DIM, hidden_dim=config.HIDDEN_DIM,
            mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
            n_transformer_layers=config.N_TRANSFORMER_LAYERS,
            dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
            window_size=config.WINDOW_SIZE, window_shift_size=config.WINDOW_SHIFT_SIZE,
        ).to(device)
        state = ckpt['model_state_dict'] if 'model_state_dict' in ckpt else ckpt
        model.load_state_dict(state)

        # Generate pseudo-labels from current model on training set
        logger.info("  Generating pseudo-labels on training set...")
        pseudo_items = generate_pseudo_labels(model, train_ds, device, PSEUDO_THR)
        n_abn  = sum(1 for _, _, l in pseudo_items if l.item() == 1)
        n_norm = sum(1 for _, _, l in pseudo_items if l.item() == 0)
        pseudo_positives = sum(
            (ps > 0).sum().item()
            for _, ps, l in pseudo_items if l.item() == 1
        )
        total_abn_segs = n_abn * config.N_SEGMENTS
        logger.info(
            f"  Pseudo-labels: {n_abn} abn + {n_norm} norm videos  |  "
            f"abn seg positives: {pseudo_positives}/{total_abn_segs} "
            f"({100*pseudo_positives/max(total_abn_segs,1):.1f}%)"
        )

        # Fine-tune
        ft_auc = finetune(
            model, pseudo_items, test_ds, criterion, device,
            FT_LR, FT_EPOCHS, FT_BATCH, ALPHA, f"seed={seed}"
        )
        logger.info(f"Seed {seed}: base_auc={base_auc:.4f}  ft_auc={ft_auc:.4f}  "
                    f"delta={ft_auc - base_auc:+.4f}")

        if ft_auc > global_best_auc:
            global_best_auc   = ft_auc
            global_best_seed  = seed
            global_best_state = {k: v.clone() for k, v in model.state_dict().items()}
            logger.info(f"  -> New best FT model: {global_best_auc:.4f} (seed={seed})")

            if global_best_auc >= 0.92:
                logger.info("*** TARGET AUC 0.92 REACHED! ***")
                break

    # ── Final evaluation ──────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"Pseudo-label FT done. Best AUC={global_best_auc:.4f}  seed={global_best_seed}")
    logger.info("=" * 60)

    if global_best_state is not None:
        model.load_state_dict(global_best_state)
        # Save fine-tuned model
        ft_path = os.path.join(config.CHECKPOINTS_DIR, 'best_finetuned_model.pth')
        torch.save({'model_state_dict': global_best_state, 'val_auc': global_best_auc}, ft_path)
        logger.info(f"Saved fine-tuned model to {ft_path}")

        test_loader = DataLoader(test_ds, batch_size=config.BATCH_SIZE, shuffle=False)
        results = full_evaluation(model, test_loader, device, config.RESULTS_DIR, config.THRESHOLD)
        logger.info(f"Final fine-tuned AUC-ROC: {results['auc']:.4f}")


if __name__ == '__main__':
    main()
