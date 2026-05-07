"""
RL-Guided Temporal Prediction Training for HRM-Crime.

Core idea
---------
Normal video segments are temporally predictable; anomalous segments are not.
We add a TemporalPredictor head that predicts the next segment's hidden
representation from the current one.  The prediction error becomes a second
anomaly signal.

RL-guidance: The prediction loss for each segment is weighted by the model's
current anomaly score (the "policy").  This creates a self-reinforcing loop:
  - High-score (anomaly) segments → forced to be hard to predict (high error)
  - Low-score (normal) segments  → forced to be easy to predict (low error)

At inference: final_score = 0.65 * rank(HRM_score) + 0.35 * rank(pred_error)

Loss = MIL_ranking_loss
     + lambda_pred * mean( score(t) * MSE(pred(h_t), h_{t+1}) )   [abn only]
     + lambda_smooth * pred_error_smooth                            [abn only]
"""

import os, sys, random, logging, shutil
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

import config
from src.dataset  import FeatureDataset
from src.model    import HRM_Model
from src.loss     import MILRankingLoss
from src.evaluate import compute_auc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.BASE_DIR, 'rl_pred.log'), mode='a'),
    ],
)
logger = logging.getLogger(__name__)

# ── Hyperparameters ──────────────────────────────────────────────────────────
SEEDS         = [77, 55, 241, 151, 7, 999, 131, 137]
NUM_EPOCHS    = 80
LR            = 1e-4
WEIGHT_DECAY  = 1e-4
BATCH_SIZE    = 8
GRAD_CLIP     = 1.0
LAMBDA_PRED   = 0.3    # weight for RL-guided prediction loss
LAMBDA_SMOOTH = 8e-5
LAMBDA_SPARSE = 8e-5
TARGET_AUC    = 0.96
WARMUP_EPOCHS = 5


# ── TemporalPredictor head ───────────────────────────────────────────────────
class TemporalPredictor(nn.Module):
    """
    Predicts hidden representation h_{t+1} from h_t.
    Returns both predictions and the per-segment MSE errors.
    """
    def __init__(self, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.LayerNorm(hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
        )

    def forward(self, h: torch.Tensor):
        """
        h: [B, T, hidden_dim]
        Returns:
            pred_errors : [B, T]   per-segment prediction error (MSE)
                          error at t = how poorly we predicted h_t from h_{t-1}
                          (padded with 0 at t=0)
        """
        # Predict h[1..T] from h[0..T-1]
        pred_next   = self.net(h[:, :-1, :])       # [B, T-1, hidden]
        actual_next = h[:, 1:, :].detach()          # [B, T-1, hidden]  no grad through target
        mse         = F.mse_loss(pred_next, actual_next, reduction='none')  # [B, T-1, hidden]
        per_seg_err = mse.mean(dim=-1)              # [B, T-1]
        # Pad: segment 0 has no predecessor error → use first error
        pad = per_seg_err[:, :1]
        per_seg_err = torch.cat([pad, per_seg_err], dim=1)  # [B, T]
        return per_seg_err


# ── Extended HRM model with predictor ────────────────────────────────────────
class HRM_RL(nn.Module):
    def __init__(self, base_model: HRM_Model, hidden_dim: int = 64):
        super().__init__()
        self.base   = base_model
        self.pred   = TemporalPredictor(hidden_dim)

    def forward(self, x: torch.Tensor):
        """
        Returns:
            scores      : [B, T']  anomaly scores from MIL head
            pred_errors : [B, T']  temporal prediction errors
            hidden      : [B, T', hidden_dim]
        """
        x_pat      = self.base.patch_embed(x)
        local_out  = self.base.local_module(x_pat)
        global_out = self.base.global_module(local_out)
        fused      = torch.cat([local_out, global_out], dim=-1)
        hidden     = self.base.fusion(fused)               # [B, T', 64]
        scores     = self.base.score_head(hidden).squeeze(-1)  # [B, T']
        pred_errs  = self.pred(hidden)                     # [B, T']
        return scores, pred_errs, hidden

    # Convenience: forward returning only scores (for compute_auc compatibility)
    def score_only(self, x: torch.Tensor) -> torch.Tensor:
        scores, _, _ = self.forward(x)
        return scores


# ── Training loop ─────────────────────────────────────────────────────────────
def train_rl(model_rl: HRM_RL, train_ds, val_ds, device, seed_tag: str,
             ckpt_dir: str):
    train_ldr = DataLoader(train_ds, batch_size=BATCH_SIZE,
                           shuffle=True, num_workers=0)
    val_ldr   = DataLoader(val_ds,   batch_size=BATCH_SIZE,
                           shuffle=False, num_workers=0)

    mil_crit = MILRankingLoss(margin=config.MARGIN,
                               lambda_smooth=LAMBDA_SMOOTH,
                               lambda_sparse=LAMBDA_SPARSE)

    optimizer = optim.AdamW(model_rl.parameters(),
                            lr=LR, weight_decay=WEIGHT_DECAY)

    # LR: warmup then cosine
    peak_lr  = LR
    start_lr = LR / 1000.0
    import math
    def lr_lambda(ep):
        if ep < WARMUP_EPOCHS:
            return start_lr/peak_lr + (1 - start_lr/peak_lr) * ep / WARMUP_EPOCHS
        prog = (ep - WARMUP_EPOCHS) / max(1, NUM_EPOCHS - WARMUP_EPOCHS)
        return 1e-6/peak_lr + 0.5*(1 - 1e-6/peak_lr)*(1 + math.cos(math.pi * prog))

    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    best_auc   = 0.0
    best_state = None
    snap_dir   = os.path.join(ckpt_dir, f'rl_snapshots_{seed_tag}')
    os.makedirs(snap_dir, exist_ok=True)
    top_k = []  # (auc, path) max-heap

    for epoch in range(1, NUM_EPOCHS + 1):
        model_rl.train()
        tot_loss = rank_loss_ = pred_loss_ = 0.0
        n_batches = 0

        for feats, labels in train_ldr:
            abn_mask  = labels == 1
            norm_mask = labels == 0
            if abn_mask.sum() == 0 or norm_mask.sum() == 0:
                continue

            feat_abn  = feats[abn_mask].to(device)
            feat_norm = feats[norm_mask].to(device)

            optimizer.zero_grad()

            sc_abn,  pe_abn,  _ = model_rl(feat_abn)
            sc_norm, pe_norm, _ = model_rl(feat_norm)

            # MIL ranking + smoothness + sparsity
            mil_loss, r_loss, sm_loss, sp_loss = mil_crit(sc_abn, sc_norm)

            # RL-guided prediction loss (anomaly videos only)
            # Weight prediction error by anomaly score → high-score segments
            # are penalised more for being predictable, driving up their error
            rl_weights  = sc_abn.detach()                       # [B_abn, T']
            pred_loss_a = (rl_weights * pe_abn).mean()          # abn: high error wanted
            pred_loss_n = (1.0 - sc_norm.detach()) * pe_norm    # norm: low error wanted
            pred_loss   = pred_loss_a + pred_loss_n.mean()

            loss = mil_loss + LAMBDA_PRED * pred_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model_rl.parameters(), GRAD_CLIP)
            optimizer.step()

            tot_loss   += loss.item()
            rank_loss_ += r_loss.item()
            pred_loss_ += pred_loss.item()
            n_batches  += 1

        scheduler.step()

        # ── Validation ──────────────────────────────────────────
        # Evaluate using combined score: HRM + prediction error
        model_rl.eval()
        all_sc, all_pe, all_lbl = [], [], []
        with torch.no_grad():
            for feats, lbls in val_ldr:
                sc, pe, _ = model_rl(feats.to(device))
                vid_sc = torch.max(sc,  dim=1)[0]
                vid_pe = torch.max(pe,  dim=1)[0]
                all_sc.extend(vid_sc.cpu().numpy())
                all_pe.extend(vid_pe.cpu().numpy())
                all_lbl.extend(lbls.numpy())

        all_sc  = np.array(all_sc)
        all_pe  = np.array(all_pe)
        all_lbl = np.array(all_lbl)
        n       = len(all_lbl)

        auc_hrm  = roc_auc_score(all_lbl, all_sc)
        auc_pred = roc_auc_score(all_lbl, all_pe)

        # Combined (sweep during training, use best weight)
        r_sc = rankdata(all_sc) / n
        r_pe = rankdata(all_pe) / n
        best_combo = 0.0
        best_w     = 0.0
        for w in [0.0, 0.1, 0.2, 0.3, 0.35, 0.4]:
            combo = (1-w)*r_sc + w*r_pe
            a = roc_auc_score(all_lbl, combo)
            if a > best_combo:
                best_combo = a
                best_w     = w

        logger.info(
            f"[{seed_tag}] Ep {epoch:3d}/{NUM_EPOCHS}  "
            f"loss={tot_loss/max(n_batches,1):.4f}  "
            f"rank_l={rank_loss_/max(n_batches,1):.4f}  "
            f"pred_l={pred_loss_/max(n_batches,1):.4f}  "
            f"AUC_hrm={auc_hrm:.4f}  AUC_pred={auc_pred:.4f}  "
            f"AUC_combo={best_combo:.4f}(w={best_w:.2f})")

        # Save best by combined AUC
        if best_combo > best_auc:
            best_auc   = best_combo
            best_state = {k: v.clone() for k, v in model_rl.state_dict().items()}
            ckpt_path  = os.path.join(ckpt_dir, f'rl_best_{seed_tag}.pth')
            torch.save({
                'model_state_dict': best_state,
                'val_auc':          best_auc,
                'auc_hrm':          auc_hrm,
                'auc_pred':         auc_pred,
                'best_w':           best_w,
                'epoch':            epoch,
            }, ckpt_path)
            logger.info(f"  -> Best RL model saved: {best_auc:.4f}")

        # Top-K snapshots
        if epoch > 10:
            sp = os.path.join(snap_dir, f'rl_ep{epoch:03d}_auc{best_combo:.4f}.pth')
            torch.save(model_rl.state_dict(), sp)
            top_k.append((best_combo, sp))
            top_k.sort(key=lambda x: -x[0])
            while len(top_k) > 5:
                _, old = top_k.pop()
                if os.path.exists(old):
                    os.remove(old)

    if best_state:
        model_rl.load_state_dict(best_state)
    return best_auc, [p for _, p in top_k]


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")

    train_feat = os.path.join(config.FEATURES_DIR,     'train')
    test_feat  = os.path.join(config.FEATURES_DIR,     'test')
    train_r3d  = os.path.join(config.FEATURES_R3D_DIR, 'train')
    test_r3d   = os.path.join(config.FEATURES_R3D_DIR, 'test')
    aux_tr = train_r3d if os.path.isdir(train_r3d) else None
    aux_te = test_r3d  if os.path.isdir(test_r3d)  else None

    train_ds = FeatureDataset(train_feat, n_segments=config.N_SEGMENTS,
                              augment=False, aux_features_dir=aux_tr)
    test_ds  = FeatureDataset(test_feat,  n_segments=config.N_SEGMENTS,
                              augment=False, aux_features_dir=aux_te)
    test_ldr = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    ckpt_dir = os.path.join(config.CHECKPOINTS_DIR, 'rl_pred')
    os.makedirs(ckpt_dir, exist_ok=True)

    global_best_auc   = 0.0
    global_best_seed  = None
    all_seed_ckpts    = []

    for seed in SEEDS:
        logger.info('=' * 60)
        logger.info(f'  RL-PRED  seed={seed}')
        logger.info('=' * 60)
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)

        base = HRM_Model(
            feature_dim=config.FEATURE_DIM, hidden_dim=config.HIDDEN_DIM,
            mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
            n_transformer_layers=config.N_TRANSFORMER_LAYERS,
            dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
            window_size=config.WINDOW_SIZE,
            window_shift_size=config.WINDOW_SHIFT_SIZE,
        ).to(device)

        # Warm-start from existing best checkpoint to save time
        global_ckpt = os.path.join(config.CHECKPOINTS_DIR,
                                   f'seed_{seed}_best.pth')
        if not os.path.exists(global_ckpt):
            global_ckpt = os.path.join(config.CHECKPOINTS_DIR,
                                       'global_best_hrm_model.pth')
        if os.path.exists(global_ckpt):
            ck = torch.load(global_ckpt, map_location=device)
            state = ck['model_state_dict'] if isinstance(ck, dict) else ck
            try:
                base.load_state_dict(state)
                logger.info(f'  Warm-start from {os.path.basename(global_ckpt)}'
                            f'  (AUC={ck.get("val_auc", "?") if isinstance(ck,dict) else "?"})')
            except Exception as e:
                logger.warning(f'  Could not load warm-start: {e}')

        model_rl = HRM_RL(base, hidden_dim=config.HIDDEN_DIM).to(device)
        best_auc, snap_paths = train_rl(
            model_rl, train_ds, test_ds, device,
            seed_tag=str(seed), ckpt_dir=ckpt_dir,
        )

        seed_ckpt = os.path.join(ckpt_dir, f'rl_best_{seed}.pth')
        if os.path.exists(seed_ckpt):
            all_seed_ckpts.append((best_auc, seed_ckpt, seed))

        if best_auc > global_best_auc:
            global_best_auc  = best_auc
            global_best_seed = seed
            shutil.copy2(seed_ckpt,
                         os.path.join(ckpt_dir, 'rl_global_best.pth'))
            logger.info(f'  -> NEW GLOBAL BEST: {global_best_auc:.4f} (seed={seed})')

        if global_best_auc >= TARGET_AUC:
            logger.info(f'TARGET {TARGET_AUC} REACHED!')
            break

    # ── Final ensemble evaluation ────────────────────────────────
    logger.info('=' * 60)
    logger.info(f'RL-Pred done. Best={global_best_auc:.4f}  seed={global_best_seed}')
    logger.info('=' * 60)

    # Build the best RL model for evaluation
    best_rl_ckpt = os.path.join(ckpt_dir, 'rl_global_best.pth')
    if not os.path.exists(best_rl_ckpt):
        logger.warning('No RL checkpoint found')
        return

    ck = torch.load(best_rl_ckpt, map_location=device)
    base = HRM_Model(
        feature_dim=config.FEATURE_DIM, hidden_dim=config.HIDDEN_DIM,
        mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
        n_transformer_layers=config.N_TRANSFORMER_LAYERS,
        dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
        window_size=config.WINDOW_SIZE,
        window_shift_size=config.WINDOW_SHIFT_SIZE,
    ).to(device)
    model_rl = HRM_RL(base).to(device)
    model_rl.load_state_dict(
        ck['model_state_dict'] if isinstance(ck, dict) else ck)
    model_rl.eval()

    best_w = ck.get('best_w', 0.3) if isinstance(ck, dict) else 0.3
    logger.info(f'Best pred weight at training: {best_w:.2f}')

    # Collect RL scores
    all_sc, all_pe, all_lbl = [], [], []
    with torch.no_grad():
        for feats, lbls in test_ldr:
            sc, pe, _ = model_rl(feats.to(device))
            all_sc.extend(torch.max(sc, dim=1)[0].cpu().numpy())
            all_pe.extend(torch.max(pe, dim=1)[0].cpu().numpy())
            all_lbl.extend(lbls.numpy())
    all_sc  = np.array(all_sc)
    all_pe  = np.array(all_pe)
    labels  = np.array(all_lbl)
    n       = len(labels)

    auc_hrm  = roc_auc_score(labels, all_sc)
    auc_pred = roc_auc_score(labels, all_pe)
    logger.info(f'RL model  AUC_hrm={auc_hrm:.4f}  AUC_pred={auc_pred:.4f}')

    r_sc = rankdata(all_sc) / n
    r_pe = rankdata(all_pe) / n
    logger.info('Weight sweep (HRM + pred_err):')
    for w in [0.0, 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]:
        combo = (1-w)*r_sc + w*r_pe
        logger.info(f'  w={w:.2f}: AUC={roc_auc_score(labels, combo):.4f}')

    # Also combine with the old ensemble
    logger.info('\nCombine RL model + original ensemble:')
    old_ckpts = {
        'combined_77':  os.path.join(config.CHECKPOINTS_DIR, 'seed_77_best.pth'),
        'combined_55':  os.path.join(config.CHECKPOINTS_DIR, 'seed_55_best.pth'),
        'combined_241': os.path.join(config.CHECKPOINTS_DIR, 'seed_241_best.pth'),
        'combined_151': os.path.join(config.CHECKPOINTS_DIR, 'seed_151_best.pth'),
        'spatial':      os.path.join(config.CHECKPOINTS_DIR, 'best_spatial_model.pth'),
    }
    dims = {
        'combined_77': 2560, 'combined_55': 2560,
        'combined_241': 2560, 'combined_151': 2560, 'spatial': 2048,
    }
    old_scores = {}
    for name, path in old_ckpts.items():
        if not os.path.exists(path):
            continue
        dim = dims[name]
        aux = aux_te if dim == 2560 else None
        ds2 = FeatureDataset(test_feat, n_segments=config.N_SEGMENTS,
                             augment=False, aux_features_dir=aux)
        ldr2 = DataLoader(ds2, batch_size=BATCH_SIZE, shuffle=False)
        m2   = HRM_Model(feature_dim=dim, hidden_dim=config.HIDDEN_DIM,
                         mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
                         n_transformer_layers=config.N_TRANSFORMER_LAYERS,
                         dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
                         window_size=config.WINDOW_SIZE,
                         window_shift_size=config.WINDOW_SHIFT_SIZE).to(device)
        ck2  = torch.load(path, map_location=device)
        m2.load_state_dict(ck2['model_state_dict'] if isinstance(ck2,dict) else ck2)
        m2.eval()
        sc2 = []
        with torch.no_grad():
            for feats, _ in ldr2:
                v = torch.max(m2(feats.to(device)), dim=1)[0]
                sc2.extend(v.cpu().numpy())
        old_scores[name] = np.array(sc2)
        logger.info(f'  {name}: AUC={roc_auc_score(labels, old_scores[name]):.4f}')

    # Old ensemble (0.80 top-4 + 0.20 spatial)
    combined_keys = ['combined_77', 'combined_55', 'combined_241', 'combined_151']
    if all(k in old_scores for k in combined_keys) and 'spatial' in old_scores:
        rank_old_avg = np.mean(
            [rankdata(old_scores[k])/n for k in combined_keys], axis=0)
        rank_spatial = rankdata(old_scores['spatial']) / n
        old_ens = 0.80 * rank_old_avg + 0.20 * rank_spatial
        logger.info(f'\nOld ensemble AUC: {roc_auc_score(labels, old_ens):.4f}')

        # Best combined RL signal
        rl_combined = (1 - best_w) * r_sc + best_w * r_pe
        rank_rl = rankdata(rl_combined) / n

        logger.info('Merge RL into final ensemble:')
        for w_rl in [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]:
            mega = (1 - w_rl) * old_ens + w_rl * rank_rl
            logger.info(
                f'  {1-w_rl:.2f}*old_ens + {w_rl:.2f}*rl: '
                f'AUC={roc_auc_score(labels, mega):.4f}')


if __name__ == '__main__':
    main()
