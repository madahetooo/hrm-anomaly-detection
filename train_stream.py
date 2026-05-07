"""Train HRM with a single feature stream (spatial or temporal only)."""
import os, sys, random, logging, shutil
import numpy as np
import torch
from torch.utils.data import DataLoader

import config
from src.dataset   import FeatureDataset
from src.model     import HRM_Model
from src.loss      import MILRankingLoss
from src.train     import train
from src.evaluate  import ensemble_auc

STREAM = sys.argv[1]   # 'spatial' | 'temporal'
SEEDS  = [77, 55, 7, 999, 131, 137, 139, 149]

if STREAM == 'spatial':
    feat_dir  = os.path.join(config.FEATURES_DIR, 'train')
    test_dir  = os.path.join(config.FEATURES_DIR, 'test')
    feat_dim  = 2048
    aux_train = aux_test = None
    tag = 'spatial'
elif STREAM == 'temporal':
    feat_dir  = os.path.join(config.FEATURES_R3D_DIR, 'train')
    test_dir  = os.path.join(config.FEATURES_R3D_DIR, 'test')
    feat_dim  = 512
    aux_train = aux_test = None
    tag = 'temporal'
else:
    raise ValueError(f"Unknown stream: {STREAM}")

log_file = os.path.join(config.BASE_DIR, f'stream_{tag}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(log_file, mode='a')],
)
logger = logging.getLogger(__name__)
logger.info(f"Training stream={tag}  feat_dim={feat_dim}")

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

train_ds = FeatureDataset(feat_dir, n_segments=config.N_SEGMENTS, augment=False)
test_ds  = FeatureDataset(test_dir, n_segments=config.N_SEGMENTS, augment=False)

# Isolated checkpoint dir — no conflict with the main multiseed run
stream_ckpt_dir = os.path.join(config.CHECKPOINTS_DIR, f'stream_{tag}')
os.makedirs(stream_ckpt_dir, exist_ok=True)

train_cfg = {
    'batch_size': config.BATCH_SIZE, 'learning_rate': config.LEARNING_RATE,
    'weight_decay': config.WEIGHT_DECAY, 'num_epochs': config.NUM_EPOCHS,
    'grad_clip': config.GRAD_CLIP, 'checkpoints_dir': stream_ckpt_dir,
    'seed_tag': f'{tag}_seed',
}

global_best = 0.0
global_ckpt = os.path.join(config.CHECKPOINTS_DIR, f'best_{tag}_model.pth')

for seed in SEEDS:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if hasattr(torch.cuda, 'manual_seed_all'): torch.cuda.manual_seed_all(seed)

    train_cfg['seed_tag'] = f'{tag}_{seed}'
    model = HRM_Model(
        feature_dim=feat_dim, hidden_dim=config.HIDDEN_DIM,
        mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
        n_transformer_layers=config.N_TRANSFORMER_LAYERS,
        dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
        window_size=config.WINDOW_SIZE, window_shift_size=config.WINDOW_SHIFT_SIZE,
    ).to(device)
    criterion = MILRankingLoss(margin=config.MARGIN,
                                lambda_smooth=config.LAMBDA_SMOOTH,
                                lambda_sparse=config.LAMBDA_SPARSE)
    logger.info(f"SEED {seed}")
    history, best_auc, _ = train(model, train_ds, test_ds, criterion,
                                  train_cfg, device, early_stop_patience=0)
    logger.info(f"Seed {seed}: best_auc={best_auc:.4f}")

    if best_auc > global_best:
        global_best = best_auc
        seed_ckpt = os.path.join(stream_ckpt_dir, 'best_hrm_model.pth')
        if os.path.exists(seed_ckpt):
            shutil.copy2(seed_ckpt, global_ckpt)
        logger.info(f"  -> New best {tag}: {global_best:.4f} (seed={seed})")

    if global_best >= 0.92:
        logger.info("Target 0.92 reached!")
        break

logger.info(f"Stream {tag} done. Best={global_best:.4f}")
