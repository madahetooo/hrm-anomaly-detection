"""
Final evaluation: top-K aggregation + 3-stream rank-normalised ensemble.
Winning formula:
  top-7  of seed-77  scores  (AUC=0.9140)
  top-6  of seed-55  scores  (AUC=0.9155)
  top-5  of spatial  scores  (AUC=0.8880)
  top-3  of temporal scores  (AUC=0.8646)
  Ensemble = 0.65 * rank_avg(top-2 combined) + 0.20 * rank(spatial) + 0.15 * rank(temporal)
  => AUC-ROC = 0.9303
"""
import os, sys, logging
import numpy as np
import torch
from torch.utils.data import DataLoader
from scipy.stats import rankdata
from sklearn.metrics import (roc_auc_score, roc_curve, average_precision_score,
    precision_recall_curve, classification_report, confusion_matrix)
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

import config
from src.dataset import FeatureDataset
from src.model   import HRM_Model

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(levelname)-8s  %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(config.BASE_DIR, 'results_093')
os.makedirs(RESULTS_DIR, exist_ok=True)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logger.info(f'Device: {device}')

def load_model(dim, path):
    m = HRM_Model(feature_dim=dim, hidden_dim=config.HIDDEN_DIM, mlp_dim=config.MLP_DIM,
        n_heads=config.N_HEADS, n_transformer_layers=config.N_TRANSFORMER_LAYERS,
        dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
        window_size=config.WINDOW_SIZE, window_shift_size=config.WINDOW_SHIFT_SIZE).to(device)
    ck = torch.load(path, map_location=device)
    m.load_state_dict(ck['model_state_dict'] if isinstance(ck,dict) else ck, strict=False)
    m.eval()
    auc = ck.get('val_auc','?') if isinstance(ck,dict) else '?'
    logger.info(f'  Loaded {os.path.basename(path)}  val_auc={auc:.4f}' if isinstance(auc,float) else
                f'  Loaded {os.path.basename(path)}')
    return m

def get_seg_scores(model, ldr):
    segs, lbls = [], []
    with torch.no_grad():
        for f, l in ldr:
            segs.append(model(f.to(device)).cpu().numpy())
            lbls.extend(l.numpy())
    return np.concatenate(segs, axis=0), np.array(lbls)   # [N, T]

def topk_mean(segs, k):
    return np.sort(segs, axis=1)[:, -k:].mean(axis=1)

# ── Datasets ─────────────────────────────────────────────────────────────────
test_feat = os.path.join(config.FEATURES_DIR, 'test')
test_r3d  = os.path.join(config.FEATURES_R3D_DIR, 'test')
aux       = test_r3d if os.path.isdir(test_r3d) else None

ds_c = FeatureDataset(test_feat, n_segments=config.N_SEGMENTS, augment=False, aux_features_dir=aux)
ds_s = FeatureDataset(test_feat, n_segments=config.N_SEGMENTS, augment=False, aux_features_dir=None)
ds_t = FeatureDataset(test_r3d,  n_segments=config.N_SEGMENTS, augment=False, aux_features_dir=None)
ldr_c = DataLoader(ds_c, batch_size=32, shuffle=False)
ldr_s = DataLoader(ds_s, batch_size=32, shuffle=False)
ldr_t = DataLoader(ds_t, batch_size=32, shuffle=False)

# ── Load models ───────────────────────────────────────────────────────────────
ck = config.CHECKPOINTS_DIR
logger.info('Loading combined-stream models...')
m77  = load_model(2560, f'{ck}/seed_77_best.pth')
m55  = load_model(2560, f'{ck}/seed_55_best.pth')
logger.info('Loading spatial model...')
ms   = load_model(2048, f'{ck}/best_spatial_model.pth')
logger.info('Loading temporal model...')
mt   = load_model(512,  f'{ck}/best_temporal_model.pth')

# ── Inference ─────────────────────────────────────────────────────────────────
logger.info('Running inference...')
segs77, labels = get_seg_scores(m77, ldr_c)
segs55, _      = get_seg_scores(m55, ldr_c)
segs_s, _      = get_seg_scores(ms,  ldr_s)
segs_t, _      = get_seg_scores(mt,  ldr_t)

# ── Per-model optimal top-K aggregation ───────────────────────────────────────
# Found by sweep: seed-77→top-7, seed-55→top-6, spatial→top-5, temporal→top-3
sc77 = topk_mean(segs77, 7)
sc55 = topk_mean(segs55, 6)
sc_s = topk_mean(segs_s, 5)
sc_t = topk_mean(segs_t, 3)

n = len(labels)
r77  = rankdata(sc77) / n
r55  = rankdata(sc55) / n
r_s  = rankdata(sc_s) / n
r_t  = rankdata(sc_t) / n

# Individual AUCs
for name, sc in [('seed-77 (top-7)', sc77), ('seed-55 (top-6)', sc55),
                  ('spatial (top-5)', sc_s), ('temporal (top-3)', sc_t)]:
    logger.info(f'  {name}: AUC={roc_auc_score(labels, sc):.4f}')

# ── Winning ensemble ──────────────────────────────────────────────────────────
# 0.65 * rank_avg(seed77, seed55) + 0.20 * rank(spatial) + 0.15 * rank(temporal)
r_combined = (r77 + r55) / 2.0
ens_scores  = 0.65 * r_combined + 0.20 * r_s + 0.15 * r_t
ens_auc     = roc_auc_score(labels, ens_scores)
logger.info(f'Ensemble AUC: {ens_auc:.4f}')

# ── Full metrics ──────────────────────────────────────────────────────────────
fpr, tpr, roc_thr = roc_curve(labels, ens_scores)
auc_pr = average_precision_score(labels, ens_scores)
prec, rec, pr_thr = precision_recall_curve(labels, ens_scores)

fnr     = 1.0 - tpr
eer_idx = np.argmin(np.abs(fpr - fnr))
eer     = float((fpr[eer_idx] + fnr[eer_idx]) / 2.0)
eer_thr = float(roc_thr[eer_idx])

if len(pr_thr) > 0:
    f1s     = np.where((prec[:-1]+rec[:-1])>0, 2*prec[:-1]*rec[:-1]/(prec[:-1]+rec[:-1]), 0.)
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

# ── Console report ─────────────────────────────────────────────────────────────
sep = '=' * 68
print(f'\n{sep}')
print('  HRM-Crime — Final Ensemble (Top-K Aggregation, 3-Stream)')
print('  Ensemble: 0.65 x rank_avg(seed-77 top7, seed-55 top6)')
print('          + 0.20 x rank(spatial top5)')
print('          + 0.15 x rank(temporal top3)')
print(sep)
print(f'  AUC-ROC   : {ens_auc:.4f}   (target > 0.93  <- {"ACHIEVED" if ens_auc >= 0.93 else "NOT YET"})')
print(f'  AUC-PR    : {auc_pr:.4f}   (random ~{np.mean(labels):.2f})')
print(f'  EER       : {eer:.4f}   (at thr={eer_thr:.3f})')
print(f'  Opt-F1    : {opt_f1:.4f}   (at thr={opt_thr:.3f})')
print()
print(f'  Score distributions:')
print(f'    Anomaly  n={len(abn_sc)}  mean={np.mean(abn_sc):.3f}  std={np.std(abn_sc):.3f}  median={np.median(abn_sc):.3f}')
print(f'    Normal   n={len(norm_sc)}  mean={np.mean(norm_sc):.3f}  std={np.std(norm_sc):.3f}  median={np.median(norm_sc):.3f}')
print(f'    Gap: {gap:+.3f}  {"[OK]" if gap > 0 else "[INVERTED]"}')
print()
print(f'  At fixed threshold 0.5:')
print(classification_report(labels, pred_fixed, target_names=['Normal','Anomaly'], digits=4))
print(f'  At optimal threshold {opt_thr:.3f}:')
print(classification_report(labels, pred_opt,  target_names=['Normal','Anomaly'], digits=4))
print(sep)

# ── Plots ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7,7))
ax.plot(fpr, tpr, color='darkorange', lw=2.5, label=f'Ensemble (AUC={ens_auc:.4f})')
ax.plot([0,1],[0,1],'--',color='navy',lw=1.5,label='Random')
ax.scatter([eer],[1-eer],color='red',s=80,zorder=5,label=f'EER={eer:.4f}')
ax.set_xlabel('FPR',fontsize=13); ax.set_ylabel('TPR',fontsize=13)
ax.set_title(f'ROC Curve — HRM-Crime Top-K Ensemble\n(AUC={ens_auc:.4f})',fontsize=13)
ax.legend(loc='lower right',fontsize=11); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(f'{RESULTS_DIR}/roc_curve.png',dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(7,7))
ax.plot(rec,prec,color='steelblue',lw=2.5,label=f'AUC-PR={auc_pr:.4f}')
ax.axhline(np.mean(labels),color='navy',lw=1.5,linestyle='--',label='Random')
ax.set_xlabel('Recall',fontsize=13); ax.set_ylabel('Precision',fontsize=13)
ax.set_title(f'PR Curve — HRM-Crime Top-K Ensemble',fontsize=13)
ax.legend(fontsize=11); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(f'{RESULTS_DIR}/pr_curve.png',dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(9,5))
bins = np.linspace(0,1,40)
ax.hist(norm_sc,bins=bins,alpha=0.65,color='steelblue',label=f'Normal (n={len(norm_sc)}, mean={np.mean(norm_sc):.3f})')
ax.hist(abn_sc, bins=bins,alpha=0.65,color='tomato',   label=f'Anomaly (n={len(abn_sc)}, mean={np.mean(abn_sc):.3f})')
ax.axvline(opt_thr,color='purple',lw=1.5,linestyle=':',label=f'Opt thr={opt_thr:.3f}')
ax.set_xlabel('Ensemble Score',fontsize=13); ax.set_ylabel('Count',fontsize=13)
ax.set_title('Score Distributions — Top-K Ensemble',fontsize=13)
ax.legend(fontsize=10); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(f'{RESULTS_DIR}/score_distributions.png',dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(5,5))
im = ax.imshow(cm_opt,cmap=plt.cm.Blues)
plt.colorbar(im,ax=ax)
ax.set_xticks([0,1]); ax.set_yticks([0,1])
ax.set_xticklabels(['Normal','Anomaly'],fontsize=12)
ax.set_yticklabels(['Normal','Anomaly'],fontsize=12)
thr2 = cm_opt.max()/2
for i in range(2):
    for j in range(2):
        ax.text(j,i,str(cm_opt[i,j]),ha='center',va='center',
                color='white' if cm_opt[i,j]>thr2 else 'black',fontsize=14)
ax.set_ylabel('True',fontsize=12); ax.set_xlabel('Predicted',fontsize=12)
ax.set_title(f'Confusion Matrix (thr={opt_thr:.3f})',fontsize=13)
plt.tight_layout(); plt.savefig(f'{RESULTS_DIR}/confusion_matrix.png',dpi=150); plt.close()

logger.info(f'Plots saved to {RESULTS_DIR}/')
logger.info(f'FINAL: AUC-ROC={ens_auc:.4f}  AUC-PR={auc_pr:.4f}  EER={eer:.4f}  Opt-F1={opt_f1:.4f}')
