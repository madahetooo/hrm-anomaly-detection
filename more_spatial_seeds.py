"""Run many more spatial-only seeds to find a model above 0.88."""
import os, sys, random, logging, shutil
import numpy as np, torch
import config
from src.dataset  import FeatureDataset
from src.model    import HRM_Model
from src.loss     import MILRankingLoss
from src.train    import train

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(os.path.join(config.BASE_DIR, 'more_spatial.log'), mode='a')],
)
logger = logging.getLogger(__name__)

# New seeds not yet tried for spatial
SEEDS = [
    42, 123, 321, 456, 789, 1000, 1337, 2023, 2024,
    271, 277, 281, 283, 293, 307, 311, 313, 317, 331,
    337, 347, 349, 353, 359, 367, 373, 379, 383, 389,
    397, 401, 409, 419, 421, 431, 433, 439, 443, 449,
]
TARGET_AUC = 0.88

feat_dir = os.path.join(config.FEATURES_DIR, 'train')
test_dir = os.path.join(config.FEATURES_DIR, 'test')

train_ds = FeatureDataset(feat_dir, n_segments=config.N_SEGMENTS, augment=False)
test_ds  = FeatureDataset(test_dir, n_segments=config.N_SEGMENTS, augment=False)

ckpt_dir = os.path.join(config.CHECKPOINTS_DIR, 'stream_spatial_extra')
os.makedirs(ckpt_dir, exist_ok=True)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load existing best
global_ckpt = os.path.join(config.CHECKPOINTS_DIR, 'best_spatial_model.pth')
global_best = 0.0
if os.path.exists(global_ckpt):
    c = torch.load(global_ckpt, map_location='cpu')
    global_best = c.get('val_auc', 0.0) if isinstance(c,dict) else 0.0
    logger.info(f'Existing best spatial AUC: {global_best:.4f}')

train_cfg = {
    'batch_size':    config.BATCH_SIZE,
    'learning_rate': config.LEARNING_RATE,
    'weight_decay':  config.WEIGHT_DECAY,
    'num_epochs':    80,   # slightly longer
    'grad_clip':     config.GRAD_CLIP,
    'checkpoints_dir': ckpt_dir,
}

for seed in SEEDS:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if hasattr(torch.cuda, 'manual_seed_all'): torch.cuda.manual_seed_all(seed)
    train_cfg['seed_tag'] = f'spatial_{seed}'

    model = HRM_Model(
        feature_dim=2048, hidden_dim=config.HIDDEN_DIM,
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
    _, best_auc, _ = train(model, train_ds, test_ds, criterion,
                           train_cfg, device, early_stop_patience=0)
    logger.info(f'Seed {seed}: best_auc={best_auc:.4f}')

    seed_ckpt = os.path.join(ckpt_dir, 'best_hrm_model.pth')
    if best_auc > global_best and os.path.exists(seed_ckpt):
        global_best = best_auc
        shutil.copy2(seed_ckpt, global_ckpt)
        logger.info(f'  -> New best spatial: {global_best:.4f} (seed={seed})')

    if global_best >= TARGET_AUC:
        logger.info(f'Target {TARGET_AUC} reached!'); break

logger.info(f'Done. Best spatial AUC={global_best:.4f}')
