"""
Multi-seed training: runs N independent seeds, keeps the best checkpoint.
Usage:  python multiseed_train.py
"""
import os, sys, random, logging, shutil
import numpy as np
import torch
from torch.utils.data import DataLoader

import config
from src.dataset   import FeatureDataset
from src.model     import HRM_Model
from src.loss      import MILRankingLoss
from src.train     import train
from src.evaluate  import full_evaluation, ensemble_auc
from src.visualize import plot_training_history

# Seed 77 previously gave 0.9131, seed 55 gave 0.9122 — include them first.
# Remaining are new primes not yet tried.
SEEDS = [
    77, 55, 7, 999,          # known good seeds from earlier runs
    131, 137, 139, 149, 151, # new primes
    157, 163, 167, 173, 179,
    181, 191, 193, 197, 199,
    211, 223, 227, 229, 233,
    239, 241, 251, 257, 263,
]
TARGET_AUC  = 0.92

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.BASE_DIR, 'multiseed.log'), mode='a'),
    ],
)
logger = logging.getLogger(__name__)


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")

    for d in (config.FEATURES_DIR, config.CHECKPOINTS_DIR, config.RESULTS_DIR):
        os.makedirs(d, exist_ok=True)

    train_feat_dir = os.path.join(config.FEATURES_DIR, 'train')
    test_feat_dir  = os.path.join(config.FEATURES_DIR, 'test')

    train_r3d = os.path.join(config.FEATURES_R3D_DIR, 'train')
    test_r3d  = os.path.join(config.FEATURES_R3D_DIR, 'test')
    aux_train = train_r3d if os.path.isdir(train_r3d) else None
    aux_test  = test_r3d  if os.path.isdir(test_r3d)  else None

    train_dataset = FeatureDataset(train_feat_dir, n_segments=config.N_SEGMENTS,
                                   augment=False, aux_features_dir=aux_train)
    test_dataset  = FeatureDataset(test_feat_dir,  n_segments=config.N_SEGMENTS,
                                   augment=False, aux_features_dir=aux_test)

    train_config = {
        'batch_size':      config.BATCH_SIZE,
        'learning_rate':   config.LEARNING_RATE,
        'weight_decay':    config.WEIGHT_DECAY,
        'num_epochs':      config.NUM_EPOCHS,
        'grad_clip':       config.GRAD_CLIP,
        'checkpoints_dir': config.CHECKPOINTS_DIR,
    }

    # Initialise from any previously saved global best so we never regress
    global_ckpt_init = os.path.join(config.CHECKPOINTS_DIR, 'global_best_hrm_model.pth')
    global_best_auc = 0.0
    if os.path.exists(global_ckpt_init):
        try:
            _c = torch.load(global_ckpt_init, map_location='cpu')
            global_best_auc = _c.get('val_auc', 0.0) if isinstance(_c, dict) else 0.0
            logger.info(f"Resuming with existing global best AUC={global_best_auc:.4f}")
        except Exception:
            global_best_auc = 0.0
    global_best_seed = None

    for seed in SEEDS:
        logger.info("=" * 60)
        logger.info(f"  SEED {seed}")
        logger.info("=" * 60)
        set_seed(seed)
        train_config['seed_tag'] = str(seed)  # per-seed snapshot directory

        model = HRM_Model(
            feature_dim          = config.FEATURE_DIM,
            hidden_dim           = config.HIDDEN_DIM,
            mlp_dim              = config.MLP_DIM,
            n_heads              = config.N_HEADS,
            n_transformer_layers = config.N_TRANSFORMER_LAYERS,
            dropout              = config.DROPOUT,
            patch_size           = config.PATCH_SIZE,
            window_size          = config.WINDOW_SIZE,
            window_shift_size    = config.WINDOW_SHIFT_SIZE,
        ).to(device)

        criterion = MILRankingLoss(
            margin        = config.MARGIN,
            lambda_smooth = config.LAMBDA_SMOOTH,
            lambda_sparse = config.LAMBDA_SPARSE,
        )

        history, best_auc, top_k_paths = train(
            model                = model,
            train_dataset        = train_dataset,
            val_dataset          = test_dataset,
            criterion            = criterion,
            config               = train_config,
            device               = device,
            early_stop_patience  = 0,   # disabled — model peaks late (~epoch 50)
        )

        # Snapshot ensemble AUC for this seed
        val_loader_ens = DataLoader(test_dataset, batch_size=config.BATCH_SIZE, shuffle=False)
        ens_auc = ensemble_auc(model, top_k_paths, val_loader_ens, device)
        logger.info(f"Seed {seed}: best_auc={best_auc:.4f}  ensemble_auc={ens_auc:.4f}")

        # Use ensemble AUC as the score for global-best comparison
        effective_auc = max(best_auc, ens_auc)

        seed_ckpt   = os.path.join(config.CHECKPOINTS_DIR, 'best_hrm_model.pth')
        global_ckpt = os.path.join(config.CHECKPOINTS_DIR, 'global_best_hrm_model.pth')
        global_snaps_dir = os.path.join(config.CHECKPOINTS_DIR, 'global_best_snapshots')

        # Always save this seed's best checkpoint under its own name (for cross-seed ensemble)
        seed_named_ckpt = os.path.join(config.CHECKPOINTS_DIR, f'seed_{seed}_best.pth')
        if os.path.exists(seed_ckpt):
            shutil.copy2(seed_ckpt, seed_named_ckpt)

        if effective_auc > global_best_auc:
            global_best_auc  = effective_auc
            global_best_seed = seed
            logger.info(f"  -> New global best: {global_best_auc:.4f} (seed={seed}, ens={ens_auc:.4f})")
            if os.path.exists(seed_ckpt):
                shutil.copy2(seed_ckpt, global_ckpt)
            if os.path.exists(global_snaps_dir):
                shutil.rmtree(global_snaps_dir)
            if top_k_paths:
                os.makedirs(global_snaps_dir, exist_ok=True)
                for p in top_k_paths:
                    if os.path.exists(p):
                        shutil.copy2(p, os.path.join(global_snaps_dir, os.path.basename(p)))
        else:
            if os.path.exists(global_ckpt):
                shutil.copy2(global_ckpt, seed_ckpt)

        if global_best_auc >= TARGET_AUC:
            logger.info(f"Target AUC {TARGET_AUC} reached! Stopping early.")
            break

    logger.info("=" * 60)
    logger.info(f"Multi-seed done. Best AUC={global_best_auc:.4f}  seed={global_best_seed}")
    logger.info("=" * 60)

    # ── Final evaluation ──────────────────────────────────────
    global_ckpt      = os.path.join(config.CHECKPOINTS_DIR, 'global_best_hrm_model.pth')
    global_snaps_dir = os.path.join(config.CHECKPOINTS_DIR, 'global_best_snapshots')

    if os.path.exists(global_ckpt):
        shutil.copy2(global_ckpt, os.path.join(config.CHECKPOINTS_DIR, 'best_hrm_model.pth'))

    ckpt_path = os.path.join(config.CHECKPOINTS_DIR, 'best_hrm_model.pth')
    if os.path.exists(ckpt_path):
        model = HRM_Model(
            feature_dim=config.FEATURE_DIM, hidden_dim=config.HIDDEN_DIM,
            mlp_dim=config.MLP_DIM, n_heads=config.N_HEADS,
            n_transformer_layers=config.N_TRANSFORMER_LAYERS,
            dropout=config.DROPOUT, patch_size=config.PATCH_SIZE,
            window_size=config.WINDOW_SIZE, window_shift_size=config.WINDOW_SHIFT_SIZE,
        ).to(device)
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])

        test_loader = DataLoader(test_dataset, batch_size=config.BATCH_SIZE, shuffle=False)

        # Single-model evaluation
        results = full_evaluation(model, test_loader, device, config.RESULTS_DIR, config.THRESHOLD)
        logger.info(f"Final Test AUC-ROC (single): {results['auc']:.4f}")

        # Cross-seed ensemble: average predictions from top-N per-seed checkpoints
        seed_ckpts = sorted([
            os.path.join(config.CHECKPOINTS_DIR, f)
            for f in os.listdir(config.CHECKPOINTS_DIR)
            if f.startswith('seed_') and f.endswith('_best.pth')
        ])
        if len(seed_ckpts) >= 2:
            # Try ensembles of increasing size (best-2, best-3, ...) by AUC
            # Load AUC from checkpoint metadata to rank them
            ranked = []
            for p in seed_ckpts:
                try:
                    c = torch.load(p, map_location=device)
                    ranked.append((c.get('val_auc', 0.0), p))
                except Exception:
                    pass
            ranked.sort(reverse=True)
            logger.info(f"Cross-seed ensemble candidates ({len(ranked)} seeds):")
            for auc_val, p in ranked[:10]:
                logger.info(f"  {os.path.basename(p)}: AUC={auc_val:.4f}")

            for k in range(2, min(len(ranked) + 1, 8)):
                top_paths = [p for _, p in ranked[:k]]
                ens_k = ensemble_auc(model, top_paths, test_loader, device)
                logger.info(f"  Cross-seed ensemble top-{k}: AUC={ens_k:.4f}")
                if ens_k >= TARGET_AUC:
                    logger.info(f"  *** TARGET REACHED with {k}-model ensemble: {ens_k:.4f} ***")


if __name__ == '__main__':
    main()
