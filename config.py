"""
Configuration for HRM (Hierarchical Relationship Model) Crime Detection.
Dataset: UCF-Crime (pre-extracted frames, 64x64 PNG images).
"""
import os

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR     = os.path.join(BASE_DIR, 'archive')
TRAIN_DIR       = os.path.join(ARCHIVE_DIR, 'Train')
TEST_DIR        = os.path.join(ARCHIVE_DIR, 'Test')
FEATURES_DIR    = os.path.join(BASE_DIR, 'features')       # ResNet-50 (primary)
FEATURES_R3D_DIR = os.path.join(BASE_DIR, 'features_r3d')  # R3D-18 temporal (aux)
CHECKPOINTS_DIR = os.path.join(BASE_DIR, 'checkpoints')
RESULTS_DIR     = os.path.join(BASE_DIR, 'results')

# ─────────────────────────────────────────────────────────────
# Dataset
# ─────────────────────────────────────────────────────────────
NORMAL_CLASS = 'NormalVideos'
CRIME_CLASSES = [
    'Abuse', 'Arrest', 'Arson', 'Assault', 'Burglary',
    'Explosion', 'Fighting', 'RoadAccidents', 'Robbery',
    'Shooting', 'Shoplifting', 'Stealing', 'Vandalism',
]
ALL_CLASSES = CRIME_CLASSES + [NORMAL_CLASS]

# ─────────────────────────────────────────────────────────────
# Feature Extraction
# ─────────────────────────────────────────────────────────────
# ResNet-50 spatial + R3D-18 temporal combined features
FRAME_SIZE    = (224, 224)
N_SEGMENTS    = 20       # Temporal segments per video (T=20)
FEATURE_DIM   = 2048 + 512   # ResNet-50 (2048) + R3D-18 (512) concatenated
EXTRACT_BATCH = 64       # Frames per batch during extraction

# ─────────────────────────────────────────────────────────────
# HRM Model Architecture
# ─────────────────────────────────────────────────────────────
HIDDEN_DIM           = 64   # Embedding dimensions
MLP_DIM              = 256  # MLP hidden size inside Transformer blocks
N_HEADS              = 8    # Multi-head self-attention heads
N_TRANSFORMER_LAYERS = 2    # Stacked windowed-attention layers
DROPOUT              = 0.3  # Dropout rate

# Patch embedding: groups PATCH_SIZE[0] consecutive temporal segments
# into one token  →  T_tokens = N_SEGMENTS // PATCH_SIZE[0]
PATCH_SIZE       = (2, 2)   # (temporal_patch, feature_patch)  2×2 patch

# Windowed self-attention (Swin-style)
WINDOW_SIZE      = 2        # Attention window size (tokens)
WINDOW_SHIFT_SIZE = 1       # Cyclic shift size for SW-MSA

# ─────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────
BATCH_SIZE    = 8
LEARNING_RATE = 0.0001
WEIGHT_DECAY  = 0.0001
NUM_EPOCHS    = 70
GRAD_CLIP     = 1.0     # Gradient clipping max norm

# MIL Ranking Loss hyperparameters (standard for UCF-Crime literature)
MARGIN        = 1.0     # Separation margin (must match sigmoid [0,1] output scale)
LAMBDA_SMOOTH = 8e-5    # Weight for temporal smoothness regularisation
LAMBDA_SPARSE = 8e-5    # Weight for sparsity regularisation

# ─────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────
THRESHOLD = 0.5         # Binary classification threshold

# ─────────────────────────────────────────────────────────────
# Reproducibility
# ─────────────────────────────────────────────────────────────
SEED = 42
