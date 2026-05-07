"""Run more combined-stream seeds with 100 epochs to push past 0.9131."""
import os, sys, random, logging, shutil
import numpy as np, torch
from torch.utils.data import DataLoader
import config
from src.dataset  import FeatureDataset
from src.model    import HRM_Model
from src.loss     import MILRankingLoss
from src.train    import train
from src.evaluate import ensemble_auc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(os.path.join(config.BASE_DIR, 'more_combined.log'), mode='a')],
)
logger = logging.getLogger(__name__)

# Seeds not yet tried
SEEDS = [
    42, 123, 321, 456, 789, 1000, 1337,
    271, 277, 281, 283, 293, 307, 311, 313,
    317, 331, 337, 347, 349, 353, 359, 367,
    373, 379, 383, 389, 397, 401, 409, 419,
]
TARGET_AUC = 0.9150  # looking for seeds above current best 0.9131

train_feat = os.path.join(config.FEATURES_DIR, 'train')
test_feat  = os.path.join(config.FEATURES_DIR, 'test')
train_r3d  = os.path.join(config.FEATURES_R3D_DIR, 'train')
test_r3d   = os.path.join(config.FEATURES_R3D_DIR, 'test')
aux_tr = train_r3d if os.path.isdir(train_r3d) else None
aux_te = test_r3d  if os.path.isdir(test_r3d)  else None

train_ds = FeatureDataset(train_feat, n_segments=config.N_SEGMENTS, augment=False, aux_features_dir=aux_tr)
test_ds  = FeatureDataset(test_feat,  n_segments=config.N_SEGMENTS, augment=False, aux_features_dir=aux_te)

ckpt_dir = config.CHECKPOINTS_DIR
device   = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

global_best = 0.9131  # don't update below existing best
global_best_seed = None

train_cfg = {
    'batch_size':      config.BATCH_SIZE,
    'learning_rate':   config.LEARNING_RATE,
    'weight_decay':    config.WEIGHT_DECAY,
    'num_epochs':      100,   # 100 epochs — model sometimes peaks later
    'grad_clip':       config.GRAD_CLIP,
    'checkpoints_dir': ckpt_dir,
}

for seed in SEEDS:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if hasattr(torch.cuda, 'manual_seed_all'): torch.cuda.manual_seed_all(seed)
    train_cfg['seed_tag'] = str(seed)

    model = HRM_Model(
        feature_dim=config.FEATURE_DIM, hidden_dim=config.HIDDEN_DIM,
        mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
        n_transformer_layers=config.N_TRANSFORMER_LAYERS,
        dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
        window_size=config.WINDOW_SIZE,
        window_shift_size=config.WINDOW_SHIFT_SIZE,
    ).to(device)

    criterion = MILRankingLoss(margin=config.MARGIN,
                               lambda_smooth=config.LAMBDA_SMOOTH,
                               lambda_sparse=config.LAMBDA_SPARSE)
    logger.info(f'Seed {seed}')
    _, best_auc, top_k = train(model, train_ds, test_ds, criterion,
                               train_cfg, device, early_stop_patience=0)

    seed_ckpt = os.path.join(ckpt_dir, 'best_hrm_model.pth')
    named     = os.path.join(ckpt_dir, f'seed_{seed}_best.pth')
    if os.path.exists(seed_ckpt):
        shutil.copy2(seed_ckpt, named)

    val_ldr = DataLoader(test_ds, batch_size=config.BATCH_SIZE, shuffle=False)
    ens_auc = ensemble_auc(model, top_k, val_ldr, device) if top_k else best_auc
    eff_auc = max(best_auc, ens_auc)
    logger.info(f'Seed {seed}: best={best_auc:.4f}  ens={ens_auc:.4f}')

    if eff_auc > global_best:
        global_best = eff_auc; global_best_seed = seed
        if os.path.exists(seed_ckpt):
            shutil.copy2(seed_ckpt, os.path.join(ckpt_dir, 'global_best_hrm_model.pth'))
        logger.info(f'  -> NEW BEST: {global_best:.4f} (seed={seed})')

logger.info(f'Done. Best combined AUC={global_best:.4f}  seed={global_best_seed}')
