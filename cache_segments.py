"""Cache per-model segment-level scores + labels for the UCF-Crime test set.
Output: results_093/cached_scores.npz  containing:
    segs_77 (N, T), segs_55 (N, T), segs_s (N, T), segs_t (N, T), labels (N,)
"""
import os, numpy as np, torch
from torch.utils.data import DataLoader

import config
from src.dataset import FeatureDataset
from src.model   import HRM_Model

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def load_model(dim, path):
    m = HRM_Model(feature_dim=dim, hidden_dim=config.HIDDEN_DIM,
        mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
        n_transformer_layers=config.N_TRANSFORMER_LAYERS,
        dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
        window_size=config.WINDOW_SIZE,
        window_shift_size=config.WINDOW_SHIFT_SIZE).to(DEVICE)
    ck = torch.load(path, map_location=DEVICE)
    sd = ck['model_state_dict'] if isinstance(ck, dict) else ck
    m.load_state_dict(sd, strict=False)
    m.eval()
    return m

def get_segs(model, loader):
    segs, lbls = [], []
    with torch.no_grad():
        for f, l in loader:
            segs.append(model(f.to(DEVICE)).cpu().numpy())
            lbls.extend(l.numpy())
    return np.concatenate(segs, axis=0), np.array(lbls)

test_feat = os.path.join(config.FEATURES_DIR, 'test')
test_r3d  = os.path.join(config.FEATURES_R3D_DIR, 'test')

ds_c = FeatureDataset(test_feat, n_segments=config.N_SEGMENTS,
                      augment=False, aux_features_dir=test_r3d)
ds_s = FeatureDataset(test_feat, n_segments=config.N_SEGMENTS,
                      augment=False, aux_features_dir=None)
ds_t = FeatureDataset(test_r3d,  n_segments=config.N_SEGMENTS,
                      augment=False, aux_features_dir=None)

ck = config.CHECKPOINTS_DIR
m77 = load_model(2560, f'{ck}/seed_77_best.pth');       print('loaded seed-77')
m55 = load_model(2560, f'{ck}/seed_55_best.pth');       print('loaded seed-55')
ms  = load_model(2048, f'{ck}/best_spatial_model.pth'); print('loaded spatial')
mt  = load_model(512,  f'{ck}/best_temporal_model.pth');print('loaded temporal')

segs_77, y = get_segs(m77, DataLoader(ds_c, batch_size=32, shuffle=False))
segs_55, _ = get_segs(m55, DataLoader(ds_c, batch_size=32, shuffle=False))
segs_s,  _ = get_segs(ms,  DataLoader(ds_s, batch_size=32, shuffle=False))
segs_t,  _ = get_segs(mt,  DataLoader(ds_t, batch_size=32, shuffle=False))

print(f'segs shapes: {segs_77.shape}, {segs_55.shape}, {segs_s.shape}, {segs_t.shape}')
print(f'labels: {y.shape}  (anomaly {y.sum()}, normal {(y==0).sum()})')

os.makedirs('results_093', exist_ok=True)
np.savez('results_093/cached_scores.npz',
         segs_77=segs_77, segs_55=segs_55, segs_s=segs_s, segs_t=segs_t,
         labels=y)
print('Saved: results_093/cached_scores.npz')
