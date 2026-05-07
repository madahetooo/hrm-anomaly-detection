"""
Final formal evaluation of the winning ensemble.
Formula: rank_avg(top-4 cross-seed combined models) * 0.80
        + rank(spatial model)                        * 0.20
AUC-ROC = 0.9267
"""
import os, sys, logging
import numpy as np
import torch
from torch.utils.data import DataLoader
from scipy.stats import rankdata
from sklearn.metrics import (
    roc_auc_score, roc_curve, average_precision_score,
    precision_recall_curve, classification_report, confusion_matrix,
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import config
from src.dataset import FeatureDataset
from src.model   import HRM_Model

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(levelname)-8s  %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(config.BASE_DIR, 'results_final')
os.makedirs(RESULTS_DIR, exist_ok=True)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logger.info(f"Device: {device}")


def load_model(dim, ckpt_path):
    m = HRM_Model(
        feature_dim=dim, hidden_dim=config.HIDDEN_DIM, mlp_dim=config.MLP_DIM,
        n_heads=config.N_HEADS, n_transformer_layers=config.N_TRANSFORMER_LAYERS,
        dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
        window_size=config.WINDOW_SIZE, window_shift_size=config.WINDOW_SHIFT_SIZE,
    ).to(device)
    ck = torch.load(ckpt_path, map_location=device)
    state = ck['model_state_dict'] if isinstance(ck, dict) and 'model_state_dict' in ck else ck
    m.load_state_dict(state)
    m.eval()
    auc = ck.get('val_auc', 0.0) if isinstance(ck, dict) else 0.0
    return m, auc


@torch.no_grad()
def get_scores(model, loader):
    scores, labels = [], []
    for feats, lbls in loader:
        seg = model(feats.to(device))
        vid = torch.max(seg, dim=1)[0]
        scores.extend(vid.cpu().numpy())
        labels.extend(lbls.numpy())
    return np.array(scores), np.array(labels)


# ── Datasets ──────────────────────────────────────────────────────
test_feat = os.path.join(config.FEATURES_DIR, 'test')
test_r3d  = os.path.join(config.FEATURES_R3D_DIR, 'test')
aux       = test_r3d if os.path.isdir(test_r3d) else None

ds_combined = FeatureDataset(test_feat, n_segments=config.N_SEGMENTS, augment=False, aux_features_dir=aux)
ds_spatial  = FeatureDataset(test_feat, n_segments=config.N_SEGMENTS, augment=False, aux_features_dir=None)
ldr_c = DataLoader(ds_combined, batch_size=32, shuffle=False)
ldr_s = DataLoader(ds_spatial,  batch_size=32, shuffle=False)

# ── Top-4 cross-seed combined models ────────────────────────────
# Seeds ranked by their validation AUC (from multiseed run):
#   seed 77: 0.9131, seed 55: 0.9122, seed 241: 0.9055, seed 151: 0.9051
top4_seeds = [
    ('seed_77_best.pth',  'checkpoints/seed_77_best.pth'),
    ('seed_55_best.pth',  'checkpoints/seed_55_best.pth'),
    ('seed_241_best.pth', 'checkpoints/seed_241_best.pth'),
    ('seed_151_best.pth', 'checkpoints/seed_151_best.pth'),
]

logger.info("Loading and scoring top-4 combined-stream models…")
seed_scores = []
labels_ref  = None
for name, path in top4_seeds:
    if not os.path.exists(path):
        logger.warning(f"Missing {path}, skipping")
        continue
    m, auc_val = load_model(2560, path)
    sc, lbls = get_scores(m, ldr_c)
    logger.info(f"  {name}: val_auc={auc_val:.4f}  inference done")
    seed_scores.append(sc)
    if labels_ref is None:
        labels_ref = lbls

# ── Spatial model ────────────────────────────────────────────────
logger.info("Loading spatial-only model…")
ms, auc_s = load_model(2048, 'checkpoints/best_spatial_model.pth')
sc_spatial, _ = get_scores(ms, ldr_s)
logger.info(f"  best_spatial_model.pth: val_auc={auc_s:.4f}")

labels = labels_ref
n      = len(labels)

# ── Rank-based ensemble ──────────────────────────────────────────
ranked_seeds = np.mean([rankdata(s)/n for s in seed_scores], axis=0)
rank_spatial  = rankdata(sc_spatial) / n

ens_scores = 0.80 * ranked_seeds + 0.20 * rank_spatial
ens_auc    = roc_auc_score(labels, ens_scores)
logger.info(f"Ensemble AUC (top-4 seeds 0.80 + spatial 0.20): {ens_auc:.4f}")

# Individual AUCs for context
for i, (name, _) in enumerate(top4_seeds[:len(seed_scores)]):
    a = roc_auc_score(labels, seed_scores[i])
    logger.info(f"  {name}: AUC={a:.4f}")
logger.info(f"  best_spatial_model.pth: AUC={roc_auc_score(labels, sc_spatial):.4f}")

# ── Full metrics ─────────────────────────────────────────────────
fpr, tpr, roc_thr = roc_curve(labels, ens_scores)
auc_pr = average_precision_score(labels, ens_scores)
prec, rec, pr_thr = precision_recall_curve(labels, ens_scores)

fnr     = 1.0 - tpr
eer_idx = np.argmin(np.abs(fpr - fnr))
eer     = float((fpr[eer_idx] + fnr[eer_idx]) / 2.0)
eer_thr = float(roc_thr[eer_idx])

if len(pr_thr) > 0:
    f1s     = np.where((prec[:-1]+rec[:-1]) > 0,
                       2*prec[:-1]*rec[:-1]/(prec[:-1]+rec[:-1]), 0.0)
    bi      = int(np.argmax(f1s))
    opt_thr = float(pr_thr[bi])
    opt_f1  = float(f1s[bi])
else:
    opt_thr, opt_f1 = 0.5, 0.0

abn_sc  = ens_scores[labels == 1]
norm_sc = ens_scores[labels == 0]
gap     = float(np.mean(abn_sc) - np.mean(norm_sc))

pred_fixed = (ens_scores >= 0.5).astype(int)
cm_fixed   = confusion_matrix(labels, pred_fixed)
pred_opt   = (ens_scores >= opt_thr).astype(int)
cm_opt     = confusion_matrix(labels, pred_opt)

# ── Console report ────────────────────────────────────────────────
sep = "=" * 68
print(f"\n{sep}")
print("  HRM Crime Detection — Final Ensemble Evaluation")
print("  UCF-Crime Test Set (290 videos: 140 anomaly, 150 normal)")
print()
print("  Ensemble: rank_avg(seed-77, seed-55, seed-241, seed-151) × 0.80")
print("          + rank(spatial-only model)                        × 0.20")
print(sep)
print(f"  AUC-ROC   : {ens_auc:.4f}   (target > 0.92  ← {'ACHIEVED' if ens_auc > 0.92 else 'NOT YET'})")
print(f"  AUC-PR    : {auc_pr:.4f}   (random≈{np.mean(labels):.2f}, prevalence)")
print(f"  EER       : {eer:.4f}   (at threshold {eer_thr:.3f}; lower is better)")
print(f"  Opt-F1    : {opt_f1:.4f}   (best achievable F1 at thr={opt_thr:.3f})")
print()
print("  Score distributions (rank-normalised, 0–1):")
print(f"    Anomaly  n={len(abn_sc):3d}  mean={np.mean(abn_sc):.3f}  std={np.std(abn_sc):.3f}  median={np.median(abn_sc):.3f}")
print(f"    Normal   n={len(norm_sc):3d}  mean={np.mean(norm_sc):.3f}  std={np.std(norm_sc):.3f}  median={np.median(norm_sc):.3f}")
print(f"    Separation gap (abn−norm mean): {gap:+.3f}  {'[correct direction]' if gap>0 else '[INVERTED!]'}")
print()
print(f"  ── At fixed threshold 0.5 ──────────────────────────────────")
print(classification_report(labels, pred_fixed, target_names=['Normal','Anomaly'], digits=4))
print(f"  Confusion Matrix (thr=0.50):")
print(f"                   Pred Normal  Pred Anomaly")
for i, row in enumerate(cm_fixed):
    print(f"  True {'Normal ' if i==0 else 'Anomaly'}       {row[0]:8d}  {row[1]:10d}")
print()
print(f"  ── At optimal threshold {opt_thr:.3f} (max-F1) ───────────────────")
print(classification_report(labels, pred_opt, target_names=['Normal','Anomaly'], digits=4))
print(f"  Confusion Matrix (thr={opt_thr:.3f}):")
print(f"                   Pred Normal  Pred Anomaly")
for i, row in enumerate(cm_opt):
    print(f"  True {'Normal ' if i==0 else 'Anomaly'}       {row[0]:8d}  {row[1]:10d}")
print(sep + "\n")

# ── Plots ─────────────────────────────────────────────────────────
# ROC curve
fig, ax = plt.subplots(figsize=(7, 7))
ax.plot(fpr, tpr, color='darkorange', lw=2.5,
        label=f'HRM Ensemble (AUC = {ens_auc:.4f})')
ax.plot([0,1],[0,1],'--', color='navy', lw=1.5, label='Random classifier')
ax.scatter([eer],[1-eer], color='red', s=80, zorder=5,
           label=f'EER = {eer:.4f}  (thr={eer_thr:.3f})')
ax.axvline(fpr[eer_idx], color='red', lw=1, linestyle=':')
ax.set_xlabel('False Positive Rate', fontsize=13)
ax.set_ylabel('True Positive Rate', fontsize=13)
ax.set_title('ROC Curve — HRM Ensemble\n(UCF-Crime, 4-seed + spatial rank-norm)', fontsize=13)
ax.legend(loc='lower right', fontsize=11)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, 'roc_curve.png'), dpi=150)
plt.close()

# PR curve
fig, ax = plt.subplots(figsize=(7, 7))
ax.plot(rec, prec, color='steelblue', lw=2.5,
        label=f'HRM Ensemble (AUC-PR = {auc_pr:.4f})')
ax.axhline(y=np.mean(labels), color='navy', lw=1.5, linestyle='--',
           label=f'Random baseline (≈{np.mean(labels):.2f})')
ax.scatter([rec[bi]], [prec[bi]], color='purple', s=80, zorder=5,
           label=f'Opt-F1 = {opt_f1:.4f}  (thr={opt_thr:.3f})')
ax.set_xlabel('Recall', fontsize=13)
ax.set_ylabel('Precision', fontsize=13)
ax.set_title('Precision-Recall Curve — HRM Ensemble', fontsize=13)
ax.legend(loc='upper right', fontsize=11)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, 'pr_curve.png'), dpi=150)
plt.close()

# Score distributions
fig, ax = plt.subplots(figsize=(9, 5))
bins = np.linspace(0, 1, 40)
ax.hist(norm_sc, bins=bins, alpha=0.65, color='steelblue',
        label=f'Normal  (n={len(norm_sc)}, mean={np.mean(norm_sc):.3f})')
ax.hist(abn_sc,  bins=bins, alpha=0.65, color='tomato',
        label=f'Anomaly (n={len(abn_sc)}, mean={np.mean(abn_sc):.3f})')
ax.axvline(0.5,     color='black',  lw=1.5, linestyle='--', label='Fixed thr=0.50')
ax.axvline(opt_thr, color='purple', lw=1.5, linestyle=':',  label=f'Opt thr={opt_thr:.3f}')
ax.set_xlabel('Ensemble Score (rank-normalised)', fontsize=13)
ax.set_ylabel('Count', fontsize=13)
ax.set_title('Score Distributions — Normal vs Anomaly (Ensemble)', fontsize=13)
ax.legend(fontsize=10); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, 'score_distributions.png'), dpi=150)
plt.close()

# Confusion matrix (at optimal threshold)
fig, ax = plt.subplots(figsize=(5, 5))
im = ax.imshow(cm_opt, cmap=plt.cm.Blues)
plt.colorbar(im, ax=ax)
ax.set_xticks([0,1]); ax.set_yticks([0,1])
ax.set_xticklabels(['Normal','Anomaly'], fontsize=12)
ax.set_yticklabels(['Normal','Anomaly'], fontsize=12)
thr2 = cm_opt.max() / 2.0
for i in range(2):
    for j in range(2):
        ax.text(j, i, str(cm_opt[i,j]), ha='center', va='center',
                color='white' if cm_opt[i,j] > thr2 else 'black', fontsize=14)
ax.set_ylabel('True label', fontsize=12)
ax.set_xlabel('Predicted label', fontsize=12)
ax.set_title(f'Confusion Matrix (thr={opt_thr:.3f}, max-F1)', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, 'confusion_matrix.png'), dpi=150)
plt.close()

logger.info(f"All results saved to {RESULTS_DIR}/")
logger.info(f"FINAL: AUC-ROC={ens_auc:.4f}  AUC-PR={auc_pr:.4f}  EER={eer:.4f}  OptF1={opt_f1:.4f}")
