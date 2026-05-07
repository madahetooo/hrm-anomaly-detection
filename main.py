"""
main.py  —  HRM Crime Detection Pipeline
=========================================
UCF-Crime dataset (pre-extracted 64×64 PNG frames)

Phases
──────
  1. Feature Extraction
       ResNet-50 backbone converts each video's frames into a
       [32, 2048] feature matrix saved as a .npy file.
       ~380 K PNG frames  →  ~150 MB of .npy files.

  2. Dataset Construction
       FeatureDataset wraps the .npy files for Train and Test splits.

  3. Model Initialisation
       Two-level HRM:
         Level 1  Transformer self-attention (local relationships)
         Level 2  Dilated 1-D convolutions   (global temporal reasoning)

  4. Training
       MIL Ranking Loss  +  Smoothness  +  Sparsity regularisers.
       Best model (highest val AUC) saved to checkpoints/.

  5. Evaluation
       AUC-ROC, classification report, confusion matrix, ROC curve plot.

  6. Visualisation
       Per-video anomaly profile plots for sample test videos.

Usage
─────
  # Full pipeline (extract + train + evaluate)
  python main.py

  # Skip feature extraction (already done)
  python main.py --skip-extract

  # Skip training (use saved checkpoint for evaluation only)
  python main.py --skip-extract --skip-train
"""

import argparse
import logging
import os
import random
import sys

import numpy as np
import torch

# ── Project modules ───────────────────────────────────────────
import config
from src.dataset          import FeatureDataset
from src.feature_extractor import extract_all_features
from src.model            import HRM_Model
from src.loss             import MILRankingLoss
from src.train            import train
from src.evaluate         import full_evaluation
from src.visualize        import (
    visualize_anomaly_profile,
    plot_training_history,
    plot_score_distribution,
)


# ─────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────

def _setup_logging():
    fmt = '%(asctime)s  %(levelname)-8s  %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                os.path.join(config.BASE_DIR, 'hrm_run.log'), mode='a'
            ),
        ],
    )


# ─────────────────────────────────────────────────────────────
# Reproducibility
# ─────────────────────────────────────────────────────────────

def _set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    # ── CLI arguments ─────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description='HRM Crime Detection — UCF-Crime Dataset'
    )
    parser.add_argument(
        '--skip-extract', action='store_true',
        help='Skip feature extraction (reuse existing .npy files)',
    )
    parser.add_argument(
        '--skip-train', action='store_true',
        help='Skip training (load best_hrm_model.pth for evaluation)',
    )
    args = parser.parse_args()

    # ── Setup ─────────────────────────────────────────────────
    _setup_logging()
    _set_seed(config.SEED)
    logger = logging.getLogger(__name__)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")
    if device.type == 'cuda':
        logger.info(f"GPU   : {torch.cuda.get_device_name(0)}")

    # Create output directories
    for d in (config.FEATURES_DIR, config.CHECKPOINTS_DIR, config.RESULTS_DIR):
        os.makedirs(d, exist_ok=True)

    train_feat_dir = os.path.join(config.FEATURES_DIR, 'train')
    test_feat_dir  = os.path.join(config.FEATURES_DIR, 'test')

    # ─────────────────────────────────────────────────────────
    # Phase 1 — Feature Extraction
    # ─────────────────────────────────────────────────────────
    if not args.skip_extract:
        logger.info("=" * 60)
        logger.info("Phase 1: Feature Extraction  (ResNet-50)")
        logger.info("=" * 60)

        for split, src_dir, out_dir in [
            ('Train', config.TRAIN_DIR, train_feat_dir),
            ('Test',  config.TEST_DIR,  test_feat_dir),
        ]:
            logger.info(f"  Extracting {split} features ...")
            extract_all_features(
                data_dir     = src_dir,
                output_dir   = out_dir,
                crime_classes= config.CRIME_CLASSES,
                normal_class = config.NORMAL_CLASS,
                n_segments   = config.N_SEGMENTS,
                frame_size   = config.FRAME_SIZE,
                batch_size   = config.EXTRACT_BATCH,
                device       = device,
            )
    else:
        logger.info("Phase 1 skipped (--skip-extract).")

    # ─────────────────────────────────────────────────────────
    # Phase 2 — Build Datasets
    # ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Phase 2: Building Datasets")
    logger.info("=" * 60)

    train_r3d_dir = os.path.join(config.FEATURES_R3D_DIR, 'train')
    test_r3d_dir  = os.path.join(config.FEATURES_R3D_DIR, 'test')
    aux_train = train_r3d_dir if os.path.isdir(train_r3d_dir) else None
    aux_test  = test_r3d_dir  if os.path.isdir(test_r3d_dir)  else None

    train_dataset = FeatureDataset(train_feat_dir, n_segments=config.N_SEGMENTS,
                                   augment=False, aux_features_dir=aux_train)
    test_dataset  = FeatureDataset(test_feat_dir,  n_segments=config.N_SEGMENTS,
                                   augment=False, aux_features_dir=aux_test)

    n_norm_tr, n_abn_tr = train_dataset.class_counts()
    n_norm_te, n_abn_te = test_dataset.class_counts()
    logger.info(
        f"  Train: {len(train_dataset)} videos  "
        f"(normal={n_norm_tr}, anomaly={n_abn_tr})"
    )
    logger.info(
        f"  Test : {len(test_dataset)}  videos  "
        f"(normal={n_norm_te}, anomaly={n_abn_te})"
    )

    if len(train_dataset) == 0:
        logger.error(
            "No training features found. "
            "Run without --skip-extract first to extract features."
        )
        sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # Phase 3 — Initialise HRM Model
    # ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Phase 3: Initialising HRM Model")
    logger.info("=" * 60)

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

    patch_t  = config.PATCH_SIZE[0]
    n_tokens = config.N_SEGMENTS // patch_t
    logger.info(f"  Trainable parameters: {model.count_parameters():,}")
    logger.info(f"  Architecture summary:")
    logger.info(f"    Patch Embed : {config.FEATURE_DIM}×{patch_t} -> {config.HIDDEN_DIM}"
                f"  (patch_size={config.PATCH_SIZE})")
    logger.info(f"    Tokens      : {n_tokens}  (from T={config.N_SEGMENTS} segments)")
    logger.info(f"    Local  (L1) : Windowed-Attn x{config.N_TRANSFORMER_LAYERS}"
                f"  heads={config.N_HEADS}"
                f"  window={config.WINDOW_SIZE}  shift={config.WINDOW_SHIFT_SIZE}"
                f"  mlp_dim={config.MLP_DIM}")
    logger.info(f"    Global (L2) : Dilated Conv1D  [dilation 1,2,4]")

    # ─────────────────────────────────────────────────────────
    # Phase 4 — Training
    # ─────────────────────────────────────────────────────────
    history = None
    best_ckpt = os.path.join(config.CHECKPOINTS_DIR, 'best_hrm_model.pth')

    if not args.skip_train:
        logger.info("=" * 60)
        logger.info("Phase 4: Training HRM Model")
        logger.info("=" * 60)

        train_config = {
            'batch_size':    config.BATCH_SIZE,
            'learning_rate': config.LEARNING_RATE,
            'weight_decay':  config.WEIGHT_DECAY,
            'num_epochs':    config.NUM_EPOCHS,
            'grad_clip':     config.GRAD_CLIP,
            'checkpoints_dir': config.CHECKPOINTS_DIR,
        }

        history, best_auc = train(
            model         = model,
            train_dataset = train_dataset,
            val_dataset   = test_dataset,
            criterion     = criterion,
            config        = train_config,
            device        = device,
            resume_from   = None,
        )

        logger.info(f"Training done.  Best Val AUC = {best_auc:.4f}")
        plot_training_history(history, config.RESULTS_DIR)

    else:
        logger.info("Phase 4 skipped (--skip-train).")

    # ── Load best checkpoint ──────────────────────────────────
    if os.path.exists(best_ckpt):
        ckpt = torch.load(best_ckpt, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        logger.info(
            f"Loaded best model  "
            f"(epoch {ckpt.get('epoch','?')},  "
            f"val AUC={ckpt.get('val_auc', '?'):.4f})"
        )
    else:
        logger.warning(
            "No saved checkpoint found — evaluating with current (untrained) weights."
        )

    # ─────────────────────────────────────────────────────────
    # Phase 5 — Evaluation on Test Set
    # ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Phase 5: Evaluating on Test Set")
    logger.info("=" * 60)

    from torch.utils.data import DataLoader
    test_loader = DataLoader(
        test_dataset,
        batch_size  = config.BATCH_SIZE,
        shuffle     = False,
        num_workers = min(4, os.cpu_count() or 1),
    )

    eval_results = full_evaluation(
        model       = model,
        dataloader  = test_loader,
        device      = device,
        results_dir = config.RESULTS_DIR,
        threshold   = config.THRESHOLD,
    )

    plot_score_distribution(eval_results, config.RESULTS_DIR, config.THRESHOLD)

    # ─────────────────────────────────────────────────────────
    # Phase 6 — Anomaly Profile Visualisation
    # ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Phase 6: Anomaly Profile Visualisation")
    logger.info("=" * 60)

    _visualize_samples(
        model        = model,
        test_feat_dir= test_feat_dir,
        results_dir  = config.RESULTS_DIR,
        threshold    = config.THRESHOLD,
        device       = device,
        n_samples    = 3,   # visualise 3 abnormal + 3 normal
    )

    # ─────────────────────────────────────────────────────────
    # Final summary
    # ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Pipeline complete!")
    logger.info(f"  Test AUC-ROC : {eval_results['auc']:.4f}")
    logger.info(f"  Test AUC-PR  : {eval_results['auc_pr']:.4f}")
    logger.info(f"  Test EER     : {eval_results['eer']:.4f}")
    logger.info(f"  Test Opt-F1  : {eval_results['opt_f1']:.4f}  (thr={eval_results['opt_threshold']:.3f})")
    logger.info(f"  Results dir  : {config.RESULTS_DIR}")
    logger.info(f"  Checkpoints  : {config.CHECKPOINTS_DIR}")
    logger.info("=" * 60)


# ─────────────────────────────────────────────────────────────
# Helper: visualise sample videos
# ─────────────────────────────────────────────────────────────

def _visualize_samples(model, test_feat_dir, results_dir, threshold,
                        device, n_samples=3):
    """Visualise n_samples from Abnormal and Normal test videos."""
    for category, label in [('Abnormal', 1), ('Normal', 0)]:
        cat_dir = os.path.join(test_feat_dir, category)
        if not os.path.isdir(cat_dir):
            continue

        npy_files = sorted(
            [f for f in os.listdir(cat_dir) if f.endswith('.npy')]
        )[:n_samples]

        for fname in npy_files:
            video_name = fname.replace('.npy', '')
            features   = np.load(os.path.join(cat_dir, fname))
            try:
                visualize_anomaly_profile(
                    model       = model,
                    features    = features,
                    video_name  = video_name,
                    results_dir = results_dir,
                    threshold   = threshold,
                    device      = device,
                    true_label  = label,
                )
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    f"Could not visualise {video_name}: {exc}"
                )


if __name__ == '__main__':
    main()
