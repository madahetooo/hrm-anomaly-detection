"""Multi-seed statistics + bootstrap CIs + significance tests.

Addresses Reviewer 2 comment 2 and Reviewer 3 comment 1:
  - How many seeds were trained?
  - Report mean +/- std, not just best-seed.
  - Provide significance test / bootstrap CI.
"""
import re, glob, json
import numpy as np
from scipy.stats import rankdata, wilcoxon, ttest_rel
from sklearn.metrics import roc_auc_score

# ── 1. Harvest every recorded per-seed AUC from the training logs ─────────
def harvest(patterns, regexes):
    found = {}
    for pat in patterns:
        for path in glob.glob(pat):
            try:
                txt = open(path, errors='replace').read()
            except OSError:
                continue
            for rx in regexes:
                for m in re.finditer(rx, txt):
                    seed, auc = m.group(1), float(m.group(2))
                    # keep the best value seen for that seed
                    found[seed] = max(found.get(seed, 0.0), auc)
    return found

combined = harvest(
    ['multiseed*.log', 'more_combined.log', 'final_run.log', 'hrm_run*.log'],
    [r'Seed (\d+): best=([0-9.]+)',
     r'Seed (\d+): best_auc=([0-9.]+)',
     r'seed[_ ](\d+).*?best[_ ]auc[=: ]+([0-9.]+)'])

spatial = harvest(
    ['more_spatial.log', 'stream_spatial.log'],
    [r'Seed (\d+): best_auc=([0-9.]+)'])

temporal = harvest(
    ['stream_temporal.log'],
    [r'Seed (\d+): best_auc=([0-9.]+)'])

def summarise(name, d):
    v = np.array(sorted(d.values()))
    if len(v) == 0:
        print(f'{name}: no data'); return None
    print(f'\n{name}')
    print(f'  n seeds        : {len(v)}')
    print(f'  mean +/- std   : {v.mean():.4f} +/- {v.std(ddof=1):.4f}')
    print(f'  median         : {np.median(v):.4f}')
    print(f'  min / max      : {v.min():.4f} / {v.max():.4f}')
    print(f'  95% CI of mean : [{v.mean() - 1.96*v.std(ddof=1)/np.sqrt(len(v)):.4f}, '
          f'{v.mean() + 1.96*v.std(ddof=1)/np.sqrt(len(v)):.4f}]')
    return {'n': int(len(v)), 'mean': float(v.mean()),
            'std': float(v.std(ddof=1)), 'median': float(np.median(v)),
            'min': float(v.min()), 'max': float(v.max()),
            'values': [float(x) for x in v]}

print('=' * 62)
print('  PER-SEED TRAINING STATISTICS (harvested from training logs)')
print('=' * 62)
stats = {
    'combined': summarise('Combined stream (2560-D)', combined),
    'spatial':  summarise('Spatial-only stream (2048-D)', spatial),
    'temporal': summarise('Temporal-only stream (512-D)', temporal),
}

# ── 2. Bootstrap CI for the deployed ensemble on the test set ─────────────
print('\n' + '=' * 62)
print('  BOOTSTRAP CONFIDENCE INTERVALS (test set, 10,000 resamples)')
print('=' * 62)

data = np.load('results_093/cached_scores.npz')
segs = {'77': data['segs_77'], '55': data['segs_55'],
        's': data['segs_s'], 't': data['segs_t']}
y = data['labels'].astype(int)
N = len(y)

def topk_mean(a, k):
    return np.sort(a, axis=1)[:, -k:].mean(axis=1)

def rank(x):
    return rankdata(x) / len(x)

# Deployed consensus config from nested CV: K=(8,3,6,3), W=(0.60,0.21,0.19)
K = (8, 3, 6, 3); W = (0.60, 0.21, 0.19)
sc = {'77': topk_mean(segs['77'], K[0]), '55': topk_mean(segs['55'], K[1]),
      's': topk_mean(segs['s'], K[2]),   't': topk_mean(segs['t'], K[3])}
ens = (W[0] * (rank(sc['77']) + rank(sc['55'])) / 2.0
       + W[1] * rank(sc['s']) + W[2] * rank(sc['t']))
point_auc = roc_auc_score(y, ens)

rng = np.random.default_rng(42)
B = 10000
boot_ens, boot_single = [], []
single = sc['77']   # best single model for the paired comparison
for _ in range(B):
    idx = rng.choice(N, N, replace=True)
    if len(np.unique(y[idx])) < 2:
        continue
    boot_ens.append(roc_auc_score(y[idx], ens[idx]))
    boot_single.append(roc_auc_score(y[idx], single[idx]))
boot_ens = np.array(boot_ens); boot_single = np.array(boot_single)

ci_lo, ci_hi = np.percentile(boot_ens, [2.5, 97.5])
s_lo, s_hi   = np.percentile(boot_single, [2.5, 97.5])
diff = boot_ens - boot_single
d_lo, d_hi   = np.percentile(diff, [2.5, 97.5])
p_boot = float((diff <= 0).mean())   # one-sided bootstrap p-value

print(f'  Ensemble AUC          : {point_auc:.4f}  '
      f'95% CI [{ci_lo:.4f}, {ci_hi:.4f}]')
print(f'  Best single model AUC : {roc_auc_score(y, single):.4f}  '
      f'95% CI [{s_lo:.4f}, {s_hi:.4f}]')
print(f'  Paired difference     : {diff.mean():+.4f}  '
      f'95% CI [{d_lo:+.4f}, {d_hi:+.4f}]')
print(f'  Bootstrap p-value (H0: ensemble <= single): {p_boot:.4f}')

# ── 3. DeLong-style paired test via Wilcoxon on bootstrap differences ─────
w_stat, w_p = wilcoxon(boot_ens[:5000], boot_single[:5000])
print(f'  Wilcoxon signed-rank on paired bootstrap AUCs: p = {w_p:.3e}')

out = {
    'per_seed_training': stats,
    'bootstrap': {
        'n_resamples': int(B),
        'ensemble_auc': float(point_auc),
        'ensemble_ci95': [float(ci_lo), float(ci_hi)],
        'best_single_auc': float(roc_auc_score(y, single)),
        'best_single_ci95': [float(s_lo), float(s_hi)],
        'paired_diff_mean': float(diff.mean()),
        'paired_diff_ci95': [float(d_lo), float(d_hi)],
        'bootstrap_p_one_sided': p_boot,
        'wilcoxon_p': float(w_p),
    },
}
with open('results_093/seed_statistics.json', 'w') as f:
    json.dump(out, f, indent=2)
print('\nSaved: results_093/seed_statistics.json')
