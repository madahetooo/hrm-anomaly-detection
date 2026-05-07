"""
Final ensemble evaluation: rank-normalized combined + spatial.
Winning formula: 0.7 * rank(combined) + 0.3 * rank(spatial) = 0.9200 AUC
"""
import os, sys, logging
import numpy as np
import torch
from torch.utils.data import DataLoader
from scipy.stats import rankdata
from sklearn.metrics import (
    roc_auc_score, roc_curve, average_precision_score,
    precision_recall_curve, classification_report, confusion_matrix, f1_score,
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

RESULTS_DIR = os.path.join(config.BASE_DIR, 'results_ensemble')
os.makedirs(RESULTS_DIR, exist_ok=True)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logger.info(f"Device: {device}")

# ── Load combined model (2560-dim) ───────────────────────────────
combined_ckpt = os.path.join(config.CHECKPOINTS_DIR, 'global_best_hrm_model.pth')
combined_model = HRM_Model(
    feature_dim=config.FEATURE_DIM, hidden_dim=config.HIDDEN_DIM,
    mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
    n_transformer_layers=config.N_TRANSFORMER_LAYERS,
    dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
    window_size=config.WINDOW_SIZE, window_shift_size=config.WINDOW_SHIFT_SIZE,
).to(device)
ck = torch.load(combined_ckpt, map_location=device)
combined_model.load_state_dict(ck['model_state_dict'])
combined_model.eval()
logger.info(f"Combined model loaded (AUC={ck.get('val_auc', '?'):.4f})")

# ── Load spatial model (2048-dim) ────────────────────────────────
spatial_ckpt = os.path.join(config.CHECKPOINTS_DIR, 'best_spatial_model.pth')
spatial_model = HRM_Model(
    feature_dim=2048, hidden_dim=config.HIDDEN_DIM,
    mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
    n_transformer_layers=config.N_TRANSFORMER_LAYERS,
    dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
    window_size=config.WINDOW_SIZE, window_shift_size=config.WINDOW_SHIFT_SIZE,
).to(device)
sk = torch.load(spatial_ckpt, map_location=device)
spatial_model.load_state_dict(sk['model_state_dict'])
spatial_model.eval()
logger.info(f"Spatial model loaded (AUC={sk.get('val_auc', '?'):.4f})")

# ── Test dataset ─────────────────────────────────────────────────
test_feat_dir = os.path.join(config.FEATURES_DIR, 'test')
test_r3d      = os.path.join(config.FEATURES_R3D_DIR, 'test')
aux_test      = test_r3d if os.path.isdir(test_r3d) else None

# Combined test dataset (spatial+temporal features)
test_combined = FeatureDataset(test_feat_dir, n_segments=config.N_SEGMENTS,
                               augment=False, aux_features_dir=aux_test)
# Spatial-only test dataset
test_spatial  = FeatureDataset(test_feat_dir, n_segments=config.N_SEGMENTS,
                               augment=False, aux_features_dir=None)

loader_combined = DataLoader(test_combined, batch_size=config.BATCH_SIZE, shuffle=False)
loader_spatial  = DataLoader(test_spatial,  batch_size=config.BATCH_SIZE, shuffle=False)

# ── Inference ────────────────────────────────────────────────────
def get_scores(model, loader, dev):
    scores, labels = [], []
    with torch.no_grad():
        for feats, lbls in loader:
            seg = model(feats.to(dev))          # [B, T]
            vid = torch.max(seg, dim=1)[0]       # [B]
            scores.extend(vid.cpu().numpy())
            labels.extend(lbls.numpy())
    return np.array(scores), np.array(labels)

logger.info("Running combined model inference…")
sc_combined, labels = get_scores(combined_model, loader_combined, device)
logger.info("Running spatial model inference…")
sc_spatial, _       = get_scores(spatial_model,  loader_spatial,  device)

auc_c = roc_auc_score(labels, sc_combined)
auc_s = roc_auc_score(labels, sc_spatial)
logger.info(f"Single-model AUCs — combined: {auc_c:.4f}  spatial: {auc_s:.4f}")

# ── Rank-normalised ensemble (winning formula) ───────────────────
n = len(labels)
r_c = rankdata(sc_combined) / n
r_s = rankdata(sc_spatial)  / n
ens_scores = 0.7 * r_c + 0.3 * r_s
ens_auc = roc_auc_score(labels, ens_scores)
logger.info(f"Ensemble AUC (rank 0.7c+0.3s): {ens_auc:.4f}")

# ── Full metric suite ────────────────────────────────────────────
fpr, tpr, roc_thr = roc_curve(labels, ens_scores)
auc_pr = average_precision_score(labels, ens_scores)
prec, rec, pr_thr = precision_recall_curve(labels, ens_scores)

# EER
fnr = 1.0 - tpr
eer_idx = np.argmin(np.abs(fpr - fnr))
eer     = float((fpr[eer_idx] + fnr[eer_idx]) / 2.0)
eer_thr = float(roc_thr[eer_idx])

# Optimal F1
if len(pr_thr) > 0:
    f1s = np.where((prec[:-1]+rec[:-1]) > 0,
                   2*prec[:-1]*rec[:-1]/(prec[:-1]+rec[:-1]), 0.0)
    bi = int(np.argmax(f1s))
    opt_thr = float(pr_thr[bi])
    opt_f1  = float(f1s[bi])
else:
    opt_thr, opt_f1 = 0.5, 0.0

abn_sc  = ens_scores[labels == 1]
norm_sc = ens_scores[labels == 0]
gap     = float(np.mean(abn_sc) - np.mean(norm_sc))

# Fixed-threshold 0.5 report
pred_fixed = (ens_scores >= 0.5).astype(int)
cm_fixed   = confusion_matrix(labels, pred_fixed)
# Opt-threshold report
pred_opt = (ens_scores >= opt_thr).astype(int)
cm_opt   = confusion_matrix(labels, pred_opt)

# ── Console ──────────────────────────────────────────────────────
sep = "=" * 65
print(f"\n{sep}")
print("  HRM Ensemble — Feature-Diversity (Combined + Spatial)")
print("  Rank-normalised: 0.70 × rank(combined) + 0.30 × rank(spatial)")
print(sep)
print(f"  AUC-ROC          : {ens_auc:.4f}   (target > 0.92)")
print(f"  AUC-PR           : {auc_pr:.4f}   (random≈{np.mean(labels):.2f})")
print(f"  EER              : {eer:.4f}   (at thr={eer_thr:.3f})")
print(f"  Opt-F1           : {opt_f1:.4f}   (at thr={opt_thr:.3f})")
print()
print(f"  Score distributions (after rank-norm):")
print(f"    Anomaly  n={len(abn_sc)}  mean={np.mean(abn_sc):.3f}  std={np.std(abn_sc):.3f}  median={np.median(abn_sc):.3f}")
print(f"    Normal   n={len(norm_sc)}  mean={np.mean(norm_sc):.3f}  std={np.std(norm_sc):.3f}  median={np.median(norm_sc):.3f}")
print(f"    Gap (abn-norm mean): {gap:+.3f}  {'[OK]' if gap>0 else '[WARNING inverted]'}")
print()
print(f"  --- At fixed threshold 0.5 ---")
print(classification_report(labels, pred_fixed, target_names=['Normal','Anomaly'], digits=4))
print(f"  Confusion Matrix (thr=0.5):")
print(f"                Pred Normal  Pred Anomaly")
for i, row in enumerate(cm_fixed):
    print(f"  True {'Normal ' if i==0 else 'Anomaly'}  {row[0]:10d}  {row[1]:10d}")
print()
print(f"  --- At optimal threshold {opt_thr:.3f} (max-F1) ---")
print(classification_report(labels, pred_opt, target_names=['Normal','Anomaly'], digits=4))
print(f"  Confusion Matrix (thr={opt_thr:.3f}):")
print(f"                Pred Normal  Pred Anomaly")
for i, row in enumerate(cm_opt):
    print(f"  True {'Normal ' if i==0 else 'Anomaly'}  {row[0]:10d}  {row[1]:10d}")
print(sep)

# ── Plots ────────────────────────────────────────────────────────
# ROC
fig, ax = plt.subplots(figsize=(7,7))
ax.plot(fpr, tpr, color='darkorange', lw=2,
        label=f'Ensemble (AUC-ROC = {ens_auc:.4f})')
ax.plot([0,1],[0,1],'--', color='navy', lw=1.5, label='Random')
ax.scatter([eer],[1-eer], color='red', s=60, zorder=5,
           label=f'EER={eer:.4f} (thr={eer_thr:.3f})')
ax.set_xlabel('FPR', fontsize=13); ax.set_ylabel('TPR', fontsize=13)
ax.set_title('ROC Curve — Feature-Diversity Ensemble\n(Combined + Spatial, rank-norm 70/30)', fontsize=13)
ax.legend(loc='lower right', fontsize=11); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR,'roc_curve.png'), dpi=150)
plt.close()

# PR
fig, ax = plt.subplots(figsize=(7,7))
ax.plot(rec, prec, color='steelblue', lw=2,
        label=f'Ensemble (AUC-PR = {auc_pr:.4f})')
ax.axhline(y=np.mean(labels), color='navy', lw=1.5, linestyle='--', label='Random baseline')
ax.set_xlabel('Recall', fontsize=13); ax.set_ylabel('Precision', fontsize=13)
ax.set_title(f'PR Curve — Ensemble\nOpt-F1={opt_f1:.4f} at thr={opt_thr:.3f}', fontsize=13)
ax.legend(loc='upper right', fontsize=11); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR,'pr_curve.png'), dpi=150)
plt.close()

# Score distributions
fig, ax = plt.subplots(figsize=(9,5))
bins = np.linspace(0, 1, 40)
ax.hist(norm_sc, bins=bins, alpha=0.6, color='steelblue',
        label=f'Normal  (n={len(norm_sc)}, mean={np.mean(norm_sc):.3f})')
ax.hist(abn_sc,  bins=bins, alpha=0.6, color='tomato',
        label=f'Anomaly (n={len(abn_sc)}, mean={np.mean(abn_sc):.3f})')
ax.axvline(0.5,     color='black',  lw=1.5, linestyle='--', label='Fixed thr=0.5')
ax.axvline(opt_thr, color='purple', lw=1.5, linestyle=':',  label=f'Opt thr={opt_thr:.3f}')
ax.set_xlabel('Ensemble Score (rank-norm)', fontsize=13)
ax.set_ylabel('Count', fontsize=13)
ax.set_title('Score Distributions — Rank-Normalised Ensemble', fontsize=13)
ax.legend(fontsize=10); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR,'score_distributions.png'), dpi=150)
plt.close()

# Confusion matrix (optimal threshold)
fig, ax = plt.subplots(figsize=(5,5))
im = ax.imshow(cm_opt, cmap=plt.cm.Blues)
plt.colorbar(im, ax=ax)
ax.set_xticks([0,1]); ax.set_yticks([0,1])
ax.set_xticklabels(['Normal','Anomaly'], fontsize=12)
ax.set_yticklabels(['Normal','Anomaly'], fontsize=12)
thresh = cm_opt.max() / 2.0
for i in range(2):
    for j in range(2):
        ax.text(j, i, str(cm_opt[i,j]), ha='center', va='center',
                color='white' if cm_opt[i,j]>thresh else 'black', fontsize=14)
ax.set_ylabel('True label', fontsize=12)
ax.set_xlabel('Predicted label', fontsize=12)
ax.set_title(f'Confusion Matrix (thr={opt_thr:.3f})', fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR,'confusion_matrix.png'), dpi=150)
plt.close()

logger.info(f"All plots saved to {RESULTS_DIR}")
logger.info(f"FINAL: AUC-ROC={ens_auc:.4f}  AUC-PR={auc_pr:.4f}  EER={eer:.4f}  OptF1={opt_f1:.4f}")
print(f"\n{'='*65}")
print(f"  TARGET {'ACHIEVED' if ens_auc >= 0.92 else 'NOT YET REACHED'}: AUC = {ens_auc:.4f}")
print(f"{'='*65}\n")
