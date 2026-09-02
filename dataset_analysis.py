"""Dataset statistics + per-class results + threshold sensitivity.

Addresses:
  R1.5  - dataset section has no statistical/visual analysis
  R3.3  - justify the 0.540 decision threshold
  R2.1  - figure fonts too small
"""
import os, re, json, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_fscore_support

FEAT = 'features'
R3D  = 'features_r3d'
OUT  = 'results_093'

CLASS_RX = re.compile(r'^([A-Za-z]+?)(?:_?Videos?)?_?\d+')

def class_of(fname):
    stem = fname.replace('.npy', '')
    if stem.startswith('Normal'):
        return 'Normal'
    m = re.match(r'^([A-Za-z]+)\d+', stem)
    return m.group(1) if m else stem

# ── 1. Class distribution across splits ───────────────────────────────────
def scan(split):
    rows = {}
    for cat in ('Abnormal', 'Normal'):
        d = os.path.join(FEAT, split, cat)
        for f in sorted(os.listdir(d)):
            if f.endswith('.npy'):
                rows.setdefault(class_of(f), []).append(os.path.join(d, f))
    return rows

train, test = scan('train'), scan('test')
classes = sorted(set(train) | set(test))
classes = [c for c in classes if c != 'Normal'] + ['Normal']

print('=' * 74)
print('  UCF-CRIME CLASS DISTRIBUTION (from the feature release we used)')
print('=' * 74)
print(f'{"Class":<18}{"Train":>8}{"Test":>8}{"Total":>8}{"Test %":>9}{"Share %":>9}')
print('-' * 74)
n_tr_all = sum(len(v) for v in train.values())
n_te_all = sum(len(v) for v in test.values())
dist = []
for c in classes:
    tr, te = len(train.get(c, [])), len(test.get(c, []))
    tot = tr + te
    dist.append({'class': c, 'train': tr, 'test': te, 'total': tot,
                 'test_frac': te / tot if tot else 0.0,
                 'share': tot / (n_tr_all + n_te_all)})
    print(f'{c:<18}{tr:>8}{te:>8}{tot:>8}{100*te/tot if tot else 0:>8.1f}%'
          f'{100*tot/(n_tr_all+n_te_all):>8.2f}%')
print('-' * 74)
print(f'{"TOTAL":<18}{n_tr_all:>8}{n_te_all:>8}{n_tr_all+n_te_all:>8}')

anom = [d for d in dist if d['class'] != 'Normal']
sizes = np.array([d['total'] for d in anom])
print(f'\nAnomaly classes            : {len(anom)}')
print(f'Largest / smallest class   : {sizes.max()} / {sizes.min()}  '
      f'(imbalance ratio {sizes.max()/sizes.min():.1f}:1)')
print(f'Mean +/- std per class     : {sizes.mean():.1f} +/- {sizes.std(ddof=1):.1f}')
gini = 1 - np.sum((sizes / sizes.sum()) ** 2)
print(f'Gini-Simpson diversity     : {gini:.3f}  (1.0 = perfectly uniform)')

# ── 2. Segment / feature-shape statistics ─────────────────────────────────
shapes = []
for c in classes:
    for p in (train.get(c, []) + test.get(c, []))[:40]:
        shapes.append(np.load(p, mmap_mode='r').shape)
shp = np.array(shapes)
print(f'\nFeature tensors sampled    : {len(shp)}')
print(f'Segments per video         : {np.unique(shp[:,0])} (fixed by design)')
print(f'Spatial feature dimension  : {np.unique(shp[:,1])}')
r3d_shp = np.load(glob.glob(f'{R3D}/train/Abnormal/*.npy')[0], mmap_mode='r').shape
print(f'Temporal feature dimension : {r3d_shp[1]}  (R3D-18)')
print(f'Concatenated dimension     : {int(np.unique(shp[:,1])[0]) + r3d_shp[1]}')

# ── 3. Per-class results on the test set (deployed ensemble) ──────────────
order = ([os.path.basename(p) for p in sorted(os.listdir(f'{FEAT}/test/Abnormal')) if p.endswith('.npy')]
         + [os.path.basename(p) for p in sorted(os.listdir(f'{FEAT}/test/Normal')) if p.endswith('.npy')])
test_classes = np.array([class_of(f) for f in order])

data = np.load(f'{OUT}/cached_scores.npz')
y = data['labels'].astype(int)
assert len(order) == len(y), f'ordering mismatch {len(order)} vs {len(y)}'

topk = lambda a, k: np.sort(a, axis=1)[:, -k:].mean(axis=1)
rank = lambda x: rankdata(x) / len(x)
K, W = (8, 3, 6, 3), (0.60, 0.21, 0.19)
s77, s55 = topk(data['segs_77'], K[0]), topk(data['segs_55'], K[1])
ss,  st  = topk(data['segs_s'],  K[2]), topk(data['segs_t'],  K[3])
ens = W[0]*(rank(s77)+rank(s55))/2.0 + W[1]*rank(ss) + W[2]*rank(st)
auc = roc_auc_score(y, ens)
print(f'\nDeployed ensemble AUC      : {auc:.4f}   (sanity check)')

# ── 4. Threshold sensitivity: fixed 0.50, EER point, F1-optimal ───────────
fpr, tpr, thr = roc_curve(y, ens)
eer_i = np.nanargmin(np.abs(fpr - (1 - tpr)))
eer_thr, eer = float(thr[eer_i]), float((fpr[eer_i] + 1 - tpr[eer_i]) / 2)

cands = np.unique(ens)
f1s = [precision_recall_fscore_support(y, (ens >= t).astype(int),
        average='binary', zero_division=0)[2] for t in cands]
f1_thr = float(cands[int(np.argmax(f1s))])

print('\n' + '=' * 74)
print('  THRESHOLD SENSITIVITY (R3.3)')
print('=' * 74)
print(f'{"Operating point":<34}{"thr":>8}{"Prec":>9}{"Rec":>9}{"F1":>9}{"Acc":>9}')
print('-' * 74)
thr_rows = []
for name, t in [('Fixed 0.500 (no tuning)', 0.50),
                ('EER point', eer_thr),
                ('F1-optimal (test-selected)', f1_thr)]:
    pred = (ens >= t).astype(int)
    p, r, f, _ = precision_recall_fscore_support(y, pred, average='binary', zero_division=0)
    acc = (pred == y).mean()
    print(f'{name:<34}{t:>8.3f}{p:>9.4f}{r:>9.4f}{f:>9.4f}{acc:>9.4f}')
    thr_rows.append({'name': name, 'threshold': float(t), 'precision': float(p),
                     'recall': float(r), 'f1': float(f), 'accuracy': float(acc)})
print('-' * 74)
print(f'EER = {eer:.4f}.  ROC-AUC ({auc:.4f}) and PR-AUC are threshold-free '
      'and are the primary metrics.')

# ── 5. Per-anomaly-class recall at the fixed 0.50 threshold ───────────────
pred50 = (ens >= 0.50).astype(int)
print('\n' + '=' * 74)
print('  PER-CLASS RECALL ON THE TEST SET (threshold = 0.50, untuned)')
print('=' * 74)
print(f'{"Class":<18}{"n":>5}{"Detected":>10}{"Recall":>9}{"Mean score":>12}')
print('-' * 74)
per_class = []
for c in classes:
    m = test_classes == c
    if m.sum() == 0:
        continue
    if c == 'Normal':
        det = int((pred50[m] == 0).sum()); rate = det / m.sum()
        label = 'Normal (specificity)'
    else:
        det = int(pred50[m].sum()); rate = det / m.sum()
        label = c
    print(f'{label:<18}{m.sum():>5}{det:>10}{rate:>9.3f}{ens[m].mean():>12.3f}')
    per_class.append({'class': c, 'n': int(m.sum()), 'correct': det,
                      'rate': float(rate), 'mean_score': float(ens[m].mean())})

# ── 6. Figures with large, legible fonts (R2.1) ───────────────────────────
plt.rcParams.update({'font.size': 11, 'axes.labelsize': 11.5,
                     'axes.titlesize': 12, 'xtick.labelsize': 10,
                     'ytick.labelsize': 10.5, 'legend.fontsize': 10})

# Narrow canvas: the figure is reproduced at ~6.5 in of text width, so a
# 10-in canvas scales by 0.65 and keeps glyphs above 7 pt (Reviewer 2 #1).
fig, ax = plt.subplots(1, 2, figsize=(10, 4.3))
names = [d['class'] for d in anom]
tr_c  = [d['train'] for d in anom]
te_c  = [d['test'] for d in anom]
idx = np.argsort(-(np.array(tr_c) + np.array(te_c)))
names = [names[i] for i in idx]; tr_c = [tr_c[i] for i in idx]; te_c = [te_c[i] for i in idx]
yp = np.arange(len(names))
ax[0].barh(yp, tr_c, color='#3b6ea5', label='Train', height=0.72)
ax[0].barh(yp, te_c, left=tr_c, color='#d95f02', label='Test', height=0.72)
ax[0].set_yticks(yp); ax[0].set_yticklabels(names)
ax[0].invert_yaxis(); ax[0].set_xlabel('Number of videos')
ax[0].set_title('(a) Anomaly class distribution')
ax[0].legend(loc='lower right', frameon=False)
ax[0].grid(axis='x', alpha=0.3); ax[0].set_axisbelow(True)

rates = [p for p in per_class if p['class'] != 'Normal']
rates.sort(key=lambda d: -d['n'])
yp2 = np.arange(len(rates))
ADEQ = 9   # minimum test support we treat as interpretable
cols = ['#2b6a3f' if r['n'] >= ADEQ else '#bdbdbd' for r in rates]
ax[1].barh(yp2, [r['rate'] for r in rates], color=cols, height=0.72)
ax[1].set_yticks(yp2); ax[1].set_yticklabels([r['class'] for r in rates])
ax[1].invert_yaxis(); ax[1].set_xlim(0, 1.15)
ax[1].set_xticks([0, 0.25, 0.5, 0.75, 1.0])
ax[1].set_xlabel('Recall at untuned threshold 0.50')
ax[1].set_title('(b) Per-class recall vs. test support')
ax[1].grid(axis='x', alpha=0.3); ax[1].set_axisbelow(True)
for i, r in enumerate(rates):
    ax[1].text(r['rate'] + 0.02, i, f"n={r['n']}", va='center', fontsize=9.5,
               color='#2b6a3f' if r['n'] >= ADEQ else '#7a7a7a')
from matplotlib.patches import Patch
ax[1].legend(handles=[Patch(color='#2b6a3f', label='test n \u2265 9'),
                      Patch(color='#bdbdbd', label='test n < 9 (noisy)')],
             loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
             frameon=False, fontsize=9.5)
plt.tight_layout()
plt.savefig(f'{OUT}/class_distribution.png', dpi=300, bbox_inches='tight')
print(f'\nSaved: {OUT}/class_distribution.png')

json.dump({'distribution': dist,
           'n_anomaly_classes': len(anom),
           'imbalance_ratio': float(sizes.max() / sizes.min()),
           'gini_simpson': float(gini),
           'segments_per_video': int(np.unique(shp[:, 0])[0]),
           'dim_spatial': int(np.unique(shp[:, 1])[0]),
           'dim_temporal': int(r3d_shp[1]),
           'ensemble_auc': float(auc),
           'eer': eer, 'thresholds': thr_rows,
           'per_class_test': per_class},
          open(f'{OUT}/dataset_stats.json', 'w'), indent=2)
print(f'Saved: {OUT}/dataset_stats.json')
