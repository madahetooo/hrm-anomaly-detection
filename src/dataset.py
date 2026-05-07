"""
Dataset utilities for HRM Crime Detection.

The UCF-Crime frames follow the naming convention:
  {ClassName}{VideoNumber}_x264_{FrameNumber}.png
  e.g.  Abuse001_x264_0.png, Normal_Videos003_x264_500.png

Frames are grouped into videos using the video_id
(everything before the last underscore + number).
"""

import os
import re
import logging
from collections import defaultdict

import numpy as np
import torch
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def parse_frame_filename(filename: str):
    """
    Parse a UCF-Crime frame filename into (video_id, frame_number).

    Handles both:
      Abuse001_x264_1000.png         -> ('Abuse001_x264', 1000)
      Normal_Videos001_x264_500.png  -> ('Normal_Videos001_x264', 500)

    Returns (None, None) if the pattern does not match.
    """
    match = re.match(r'^(.+_x264)_(\d+)\.png$', filename)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


def scan_frames_directory(data_dir: str, crime_classes: list, normal_class: str) -> dict:
    """
    Walk data_dir and collect all frame paths grouped by video_id.

    Returns
    -------
    dict
        { video_id: { 'frames': [sorted_paths], 'label': 0|1, 'class': str } }
    """
    videos = {}

    all_class_dirs = [(c, 1) for c in crime_classes] + [(normal_class, 0)]

    for cls_name, label in all_class_dirs:
        cls_dir = os.path.join(data_dir, cls_name)
        if not os.path.isdir(cls_dir):
            logger.warning(f"Directory not found, skipping: {cls_dir}")
            continue

        # Group frames by video_id
        class_videos: dict = defaultdict(list)
        for fname in os.listdir(cls_dir):
            if not fname.lower().endswith('.png'):
                continue
            vid_id, frame_num = parse_frame_filename(fname)
            if vid_id is None:
                continue
            class_videos[vid_id].append((frame_num, os.path.join(cls_dir, fname)))

        for vid_id, frame_list in class_videos.items():
            # Sort by frame number so temporal order is correct
            frame_list.sort(key=lambda x: x[0])
            videos[vid_id] = {
                'frames': [fp for _, fp in frame_list],
                'label':  label,
                'class':  cls_name,
            }

    logger.info(f"Scanned {data_dir} -> {len(videos)} videos found")
    return videos


# ─────────────────────────────────────────────────────────────
# Feature-based Dataset  (used after feature extraction)
# ─────────────────────────────────────────────────────────────

class FeatureDataset(Dataset):
    """
    Loads pre-extracted feature files (.npy).

    Supports two modes:
      1. Single-source: loads from one features_dir (ResNet-50 or R3D-18)
      2. Dual-source:   loads from features_dir AND aux_features_dir and
                        concatenates along the feature dimension.
                        Useful for combining spatial + temporal features.

    Expected directory layout:
        features_dir/
            Normal/    {video_id}.npy   # shape [n_segments, feat_dim]
            Abnormal/  {video_id}.npy
    """

    def __init__(
        self,
        features_dir: str,
        n_segments: int = 20,
        augment: bool = False,
        aux_features_dir: str = None,   # optional second feature source
    ):
        self.n_segments      = n_segments
        self.augment         = augment
        self.aux_features_dir = aux_features_dir
        self.samples = []   # list of (path, label)

        for category, label in [('Abnormal', 1), ('Normal', 0)]:
            cat_dir = os.path.join(features_dir, category)
            if not os.path.isdir(cat_dir):
                logger.warning(f"Feature directory missing: {cat_dir}")
                continue
            for fname in sorted(os.listdir(cat_dir)):
                if fname.endswith('.npy'):
                    self.samples.append(
                        (os.path.join(cat_dir, fname), float(label))
                    )

        logger.info(
            f"FeatureDataset loaded {len(self.samples)} videos "
            f"from {features_dir}"
            + (f" + {aux_features_dir}" if aux_features_dir else "")
        )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        features = self._load_and_norm(path)

        # Optionally concatenate auxiliary features (e.g. R3D-18 temporal)
        if self.aux_features_dir is not None:
            fname    = os.path.basename(path)
            category = os.path.basename(os.path.dirname(path))
            aux_path = os.path.join(self.aux_features_dir, category, fname)
            if os.path.exists(aux_path):
                aux_feat = self._load_and_norm(aux_path)
                features = np.concatenate([features, aux_feat], axis=1)

        # Feature augmentation: small Gaussian noise + random temporal dropout
        if self.augment:
            # Additive noise on L2-normalised features (sigma chosen so SNR stays high)
            noise = np.random.normal(0.0, 0.02, features.shape).astype(np.float32)
            features = features + noise
            # Re-normalise so unit-norm invariant holds approximately
            norms = np.linalg.norm(features, axis=1, keepdims=True)
            features = features / np.maximum(norms, 1e-8)
            # Random segment dropout (zero out 1-2 segments) — acts like temporal masking
            n_drop = np.random.randint(0, 3)   # 0, 1, or 2 segments
            if n_drop > 0:
                drop_idx = np.random.choice(features.shape[0], n_drop, replace=False)
                features[drop_idx] = 0.0

        return (
            torch.from_numpy(features).float(),
            torch.tensor(label).float(),
        )

    def _load_and_norm(self, path: str) -> np.ndarray:
        """Load .npy, resample to n_segments, L2-normalise each vector."""
        features = np.load(path)
        if features.shape[0] != self.n_segments:
            features = self._temporal_resample(features, self.n_segments)
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        return (features / norms).astype(np.float32)

    # ── private ──────────────────────────────────────────────

    @staticmethod
    def _temporal_resample(features: np.ndarray, n: int) -> np.ndarray:
        """Uniformly resample feature array to exactly n segments."""
        t = features.shape[0]
        indices = np.linspace(0, t - 1, n, dtype=int)
        return features[indices]

    # ── utility ──────────────────────────────────────────────

    def class_counts(self):
        """Return (n_normal, n_abnormal)."""
        labels = [s[1] for s in self.samples]
        n_abn  = int(sum(labels))
        n_norm = len(labels) - n_abn
        return n_norm, n_abn
