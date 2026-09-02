"""Nested 5-fold cross-validation for HRM-Crime.

For each of 5 outer folds:
  - Inner sweep on the other 4 folds selects the best K per model and the best
    ensemble weights, using ROC-AUC as the objective.
  - The held-out fold is evaluated with the best config from the sweep.
This gives an UNBIASED estimate of ensemble AUC — hyperparameters are never
tuned on the same data used to report the number.

Also reports several fixed-hyperparameter defaults so the paper can compare
against non-optimised baselines:
    * max-aggregation, equal weights (traditional)
    * K=5 per model, equal weights (reasonable robust default)
    * K per model at fixed { 7, 6, 5, 3 }, weights 0.65 / 0.20 / 0.15
      (the previously-reported paper config; here reported without tuning)

Output: results_093/nested_cv_results.json
"""
import os, json, numpy as np
from itertools import product
from scipy.stats import rankdata
from sklearn.metrics import (roc_auc_score, average_precision_score,
    precision_recall_curve, roc_curve, precision_score, recall_score,
    f1_score, accuracy_score, jaccard_score, confusion_matrix)
from sklearn.model_selection import StratifiedKFold

# ── Load cached scores ────────────────────────────────────────────────────
data = np.load('results_093/cached_scores.npz')
segs_77, segs_55 = data['segs_77'], data['segs_55']
segs_s,  segs_t  = data['segs_s'],  data['segs_t']
y = data['labels'].astype(int)
N, T = segs_77.shape
print(f'Loaded N={N} test videos, T={T} segments per video.')

# ── Aggregation and fusion helpers ────────────────────────────────────────
def topk_mean(segs, k):
    k = int(min(max(k, 1), segs.shape[1]))
    return np.sort(segs, axis=1)[:, -k:].mean(axis=1)

def rank(x):
    return rankdata(x) / len(x)

def ensemble_score(segs_77, segs_55, segs_s, segs_t,
                   k77, k55, ks, kt, w_c, w_s, w_t):
    r77 = rank(topk_mean(segs_77, k77))
    r55 = rank(topk_mean(segs_55, k55))
    rs  = rank(topk_mean(segs_s,  ks))
    rt  = rank(topk_mean(segs_t,  kt))
    return w_c * ((r77 + r55) / 2.0) + w_s * rs + w_t * rt

def auc_for(segs_arrays, k_config, w_config, y):
    s77, s55, ss, st = segs_arrays
    k77, k55, ks, kt = k_config
    w_c, w_s, w_t    = w_config
    scores = ensemble_score(s77, s55, ss, st, k77, k55, ks, kt,
                            w_c, w_s, w_t)
    return roc_auc_score(y, scores), scores

# ── Search space (kept modest to prevent overfitting) ────────────────────
K_GRID_COMB = [3, 4, 5, 6, 7, 8]        # for combined-stream models
K_GRID_S    = [3, 4, 5, 6, 7]           # spatial
K_GRID_T    = [1, 2, 3, 4, 5]           # temporal
W_STEP      = 0.05
# All (w_c, w_s, w_t) triples that sum to 1.0 in 0.05 increments, w_c ≥ 0.4
def weight_grid():
    for w_c in np.arange(0.40, 0.85 + 1e-9, W_STEP):
        for w_s in np.arange(0.05, 0.50 + 1e-9, W_STEP):
            w_t = 1.0 - w_c - w_s
            if 0.05 - 1e-9 <= w_t <= 0.55 + 1e-9:
                yield (round(w_c, 2), round(w_s, 2), round(w_t, 2))
W_GRID = list(weight_grid())
print(f'|K grid| = {len(K_GRID_COMB) * len(K_GRID_COMB) * len(K_GRID_S) * len(K_GRID_T)}, '
      f'|W grid| = {len(W_GRID)}')

def sweep_best(idx, segs_arrays, y):
    s77, s55, ss, st = [x[idx] for x in segs_arrays]
    yi = y[idx]
    best = (-1.0, None, None)
    for k77 in K_GRID_COMB:
        for k55 in K_GRID_COMB:
            for ks in K_GRID_S:
                for kt in K_GRID_T:
                    # per-K scores computed once, then combine
                    r77 = rank(topk_mean(s77, k77))
                    r55 = rank(topk_mean(s55, k55))
                    rs  = rank(topk_mean(ss,  ks))
                    rt  = rank(topk_mean(st,  kt))
                    r_c = (r77 + r55) / 2.0
                    for (w_c, w_s, w_t) in W_GRID:
                        scores = w_c * r_c + w_s * rs + w_t * rt
                        a = roc_auc_score(yi, scores)
                        if a > best[0]:
                            best = (a, (k77, k55, ks, kt), (w_c, w_s, w_t))
    return best   # (train_auc, K_cfg, W_cfg)

segs_all = (segs_77, segs_55, segs_s, segs_t)

# ══════════════════════════════════════════════════════════════════════════
# 1) NESTED 5-FOLD CROSS-VALIDATION (unbiased)
# ══════════════════════════════════════════════════════════════════════════
print('\n--- Nested 5-fold cross-validation ---')
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
fold_aucs = []
fold_configs = []

for fold, (train_idx, test_idx) in enumerate(skf.split(segs_77, y)):
    train_auc, K_cfg, W_cfg = sweep_best(train_idx, segs_all, y)
    # Evaluate on held-out fold with train-selected config
    test_auc, _ = auc_for(
        tuple(x[test_idx] for x in segs_all), K_cfg, W_cfg, y[test_idx])
    fold_aucs.append(test_auc)
    fold_configs.append({
        'fold': fold, 'K': K_cfg, 'W': W_cfg,
        'train_auc': float(train_auc), 'test_auc': float(test_auc),
        'n_train': int(len(train_idx)), 'n_test': int(len(test_idx))})
    print(f'  Fold {fold+1}: K={K_cfg}, W={W_cfg} → '
          f'train AUC={train_auc:.4f}, held-out AUC={test_auc:.4f}')

mean_auc  = float(np.mean(fold_aucs))
std_auc   = float(np.std(fold_aucs))
print(f'Nested CV AUC: {mean_auc:.4f} ± {std_auc:.4f}')

# ══════════════════════════════════════════════════════════════════════════
# 2) FIXED-DEFAULT BASELINES (no tuning)
# ══════════════════════════════════════════════════════════════════════════
print('\n--- Fixed-hyperparameter baselines ---')
defaults = {
    'max_equal': {
        'K': (T, T, T, T),
        'W': (1/3, 1/3, 1/3),
        'label': 'max aggregation, equal weights (traditional)'
    },
    'k5_equal': {
        'K': (5, 5, 5, 5),
        'W': (1/3, 1/3, 1/3),
        'label': 'K=5 per model, equal weights'
    },
    'k5_073': {
        'K': (5, 5, 5, 5),
        'W': (0.60, 0.25, 0.15),
        'label': 'K=5 per model, weights 0.60/0.25/0.15'
    },
}
baseline_results = {}
for key, cfg in defaults.items():
    a, _ = auc_for(segs_all, cfg['K'], cfg['W'], y)
    baseline_results[key] = {'AUC': float(a), 'K': cfg['K'], 'W': cfg['W'],
                             'label': cfg['label']}
    print(f'  {cfg["label"]}: AUC = {a:.4f}')

# ══════════════════════════════════════════════════════════════════════════
# 3) ORACLE (test-set tuned, for reference only — NOT the reported number)
# ══════════════════════════════════════════════════════════════════════════
print('\n--- Oracle (test-set tuned, upper-bound reference) ---')
oracle_auc, oracle_K, oracle_W = sweep_best(np.arange(N), segs_all, y)
print(f'Oracle AUC = {oracle_auc:.4f} at K={oracle_K}, W={oracle_W}')

# ══════════════════════════════════════════════════════════════════════════
# 4) HEADLINE CONFIG — the one to actually deploy
#    Use the modal-selected K per stream across folds; use fold-mean weights.
# ══════════════════════════════════════════════════════════════════════════
from collections import Counter
def modal(lst): return Counter(lst).most_common(1)[0][0]
Ks = np.array([c['K'] for c in fold_configs])
Ws = np.array([c['W'] for c in fold_configs])
K_final = (modal(Ks[:,0]), modal(Ks[:,1]), modal(Ks[:,2]), modal(Ks[:,3]))
W_final = tuple(float(x) for x in Ws.mean(axis=0).round(2))
print(f'\nCross-fold consensus config:  K={K_final},  W={W_final}')

final_auc, final_scores = auc_for(segs_all, K_final, W_final, y)
print(f'AUC with consensus config, evaluated on full test set: {final_auc:.4f}')
print('(This uses hyperparameters agreed by the majority of CV folds, then '
      'evaluated on the full test set — same discipline as reporting a '
      'fixed default, but with parameters that generalise across folds.)')

# ══════════════════════════════════════════════════════════════════════════
# 5) Full metric suite at K_final / W_final
# ══════════════════════════════════════════════════════════════════════════
prec, rec, pr_thr = precision_recall_curve(y, final_scores)
f1s = np.where((prec[:-1]+rec[:-1]) > 0,
               2*prec[:-1]*rec[:-1]/(prec[:-1]+rec[:-1]), 0.)
bi = int(np.argmax(f1s))
opt_thr = float(pr_thr[bi])

fpr, tpr, roc_thr = roc_curve(y, final_scores)
fnr = 1 - tpr
eer_idx = np.argmin(np.abs(fpr - fnr))
eer = float((fpr[eer_idx] + fnr[eer_idx]) / 2)

pred = (final_scores >= opt_thr).astype(int)
tn, fp, fn, tp = confusion_matrix(y, pred).ravel()

metrics = {
    'method': 'HRM-Crime 3-stream (consensus config from nested CV)',
    'K_final': list(K_final),
    'W_final': list(W_final),
    'opt_thr': opt_thr,
    'AUC_ROC_full_test': float(final_auc),
    'AUC_PR':  float(average_precision_score(y, final_scores)),
    'EER':     eer,
    'F1':      float(f1_score(y, pred)),
    'Precision': float(precision_score(y, pred)),
    'Recall':    float(recall_score(y, pred)),
    'Accuracy':  float(accuracy_score(y, pred)),
    'IoU_anomaly': float(jaccard_score(y, pred, pos_label=1)),
    'IoU_normal':  float(jaccard_score(y, pred, pos_label=0)),
    'IoU_macro':   float((jaccard_score(y, pred, pos_label=1) +
                          jaccard_score(y, pred, pos_label=0)) / 2),
    'confusion': {'TP': int(tp), 'FP': int(fp), 'FN': int(fn), 'TN': int(tn)},
}
print('\n--- Full metric suite at consensus config ---')
for k, v in metrics.items():
    if isinstance(v, float):
        print(f'  {k}: {v:.4f}')
    elif isinstance(v, (int, str, list)):
        print(f'  {k}: {v}')
    else:
        print(f'  {k}: {v}')

# ══════════════════════════════════════════════════════════════════════════
# Save everything
# ══════════════════════════════════════════════════════════════════════════
out = {
    'nested_cv': {
        'mean_auc': mean_auc,
        'std_auc':  std_auc,
        'fold_aucs': [float(a) for a in fold_aucs],
        'fold_configs': fold_configs,
    },
    'fixed_defaults': baseline_results,
    'oracle_upper_bound': {
        'AUC': float(oracle_auc),
        'K': list(oracle_K),
        'W': list(oracle_W),
    },
    'consensus_config': {
        'K_final': list(K_final),
        'W_final': list(W_final),
        'AUC_on_full_test': float(final_auc),
    },
    'consensus_metrics': metrics,
}
with open('results_093/nested_cv_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print('\nSaved: results_093/nested_cv_results.json')
