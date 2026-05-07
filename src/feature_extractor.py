"""
Feature Extraction for HRM Crime Detection.

Converts UCF-Crime frames (64×64 PNG) into R3D-18 clip-based temporal features.

R3D-18 is a 3D ResNet pretrained on Kinetics-400 (video action recognition).
It processes short clips of 16 frames at once, capturing temporal dynamics
(motion, action patterns) that ResNet-50 spatial features completely miss.

Each video → N_SEGMENTS=20 clips → [20, 512] feature matrix saved as .npy.
"""

import os
import re
import logging
from collections import defaultdict
from typing import List, Tuple

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from torchvision.models.video import r3d_18, R3D_18_Weights

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Frame filename parser
# ─────────────────────────────────────────────────────────────

def parse_frame_filename(filename: str) -> Tuple[str, int]:
    match = re.match(r'^(.+_x264)_(\d+)\.png$', filename)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


# ─────────────────────────────────────────────────────────────
# R3D-18 backbone wrapper (temporal clip features)
# ─────────────────────────────────────────────────────────────

class R3D18Extractor:
    """
    Wraps pretrained R3D-18 as a 512-dim temporal feature extractor.

    Input : list of PIL images (one clip = CLIP_LENGTH consecutive frames)
    Output: np.ndarray  [1, 512]  per clip

    R3D-18 expects clips shaped [B, 3, T, H, W] with T=16, H=W=112.
    Pretrained on Kinetics-400 — captures motion and temporal patterns.
    """

    CLIP_LENGTH = 16   # frames per clip
    CLIP_SIZE   = (112, 112)

    def __init__(self, device: torch.device):
        self.device = device

        backbone = r3d_18(weights=R3D_18_Weights.KINETICS400_V1)
        # Remove final FC → output: [B, 512, 1, 1, 1] after AdaptiveAvgPool
        import torch.nn as nn
        self.model = nn.Sequential(*list(backbone.children())[:-1])
        self.model.to(device)
        self.model.eval()

        # R3D-18 Kinetics normalisation
        self.transform = transforms.Compose([
            transforms.Resize(self.CLIP_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.43216, 0.394666, 0.37645],
                std =[0.22803, 0.22145, 0.216989],
            ),
        ])

    @torch.no_grad()
    def extract_clip(self, pil_frames: List[Image.Image]) -> np.ndarray:
        """
        Extract a 512-dim feature from a list of PIL frames.

        Parameters
        ----------
        pil_frames : List[PIL.Image]  length = CLIP_LENGTH (16 frames)

        Returns
        -------
        np.ndarray  shape [512]
        """
        # Pad or truncate to exactly CLIP_LENGTH frames
        frames = list(pil_frames)
        while len(frames) < self.CLIP_LENGTH:
            frames.append(frames[-1])   # repeat last frame
        frames = frames[:self.CLIP_LENGTH]

        # [T, 3, H, W]
        tensors = torch.stack([self.transform(f) for f in frames])
        # [3, T, H, W]
        clip = tensors.permute(1, 0, 2, 3).unsqueeze(0).to(self.device)  # [1,3,T,H,W]

        feat = self.model(clip)          # [1, 512, 1, 1, 1]
        feat = feat.view(1, -1)          # [1, 512]
        return feat.cpu().numpy()        # [1, 512]


# ─────────────────────────────────────────────────────────────
# Per-video extraction
# ─────────────────────────────────────────────────────────────

def extract_video_features(
    frame_paths: List[str],
    extractor: R3D18Extractor,
    n_segments: int = 20,
    batch_size: int = 8,
) -> np.ndarray:
    """
    Extract n_segments clip-level features from a video's frames.

    Strategy
    --------
    Divide the video into n_segments equal-length windows.
    For each window, sample CLIP_LENGTH evenly-spaced frames and
    extract a single R3D-18 clip feature.

    Returns
    -------
    np.ndarray  shape [n_segments, 512]
    """
    n_frames = len(frame_paths)
    if n_frames == 0:
        raise ValueError("Video has no frames.")

    clip_len = extractor.CLIP_LENGTH
    features = []

    for seg_i in range(n_segments):
        # Window boundaries for this segment
        start = int(seg_i       * n_frames / n_segments)
        end   = int((seg_i + 1) * n_frames / n_segments)
        end   = max(end, start + 1)

        # Sample clip_len frames from this window
        window_size = end - start
        if window_size >= clip_len:
            idxs = np.linspace(start, end - 1, clip_len, dtype=int)
        else:
            # Window smaller than clip — sample with replacement by repeating
            base_idxs = np.linspace(start, end - 1, window_size, dtype=int)
            rep = (clip_len // window_size) + 1
            idxs = np.tile(base_idxs, rep)[:clip_len]

        frames = [Image.open(frame_paths[i]).convert('RGB') for i in idxs]
        feat   = extractor.extract_clip(frames)  # [1, 512]
        features.append(feat[0])                 # [512]

    return np.stack(features)   # [n_segments, 512]


# ─────────────────────────────────────────────────────────────
# Full dataset extraction
# ─────────────────────────────────────────────────────────────

def extract_all_features(
    data_dir: str,
    output_dir: str,
    crime_classes: List[str],
    normal_class: str,
    n_segments: int = 20,
    frame_size: Tuple[int, int] = (112, 112),   # kept for API compat, not used
    batch_size: int = 8,
    device: torch.device = None,
):
    """
    Extract R3D-18 clip features for every video and save .npy files.

    Output layout:
        output_dir/
            Normal/    {video_id}.npy   # shape [n_segments, 512]
            Abnormal/  {video_id}.npy
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    logger.info(
        f"R3D-18 feature extraction | device={device} | segments={n_segments}"
    )

    for cat in ('Normal', 'Abnormal'):
        os.makedirs(os.path.join(output_dir, cat), exist_ok=True)

    extractor = R3D18Extractor(device)

    all_class_defs = (
        [(c, 'Abnormal') for c in crime_classes]
        + [(normal_class, 'Normal')]
    )

    total_done = total_skip = total_err = 0

    for cls_name, category in all_class_defs:
        cls_dir = os.path.join(data_dir, cls_name)
        if not os.path.isdir(cls_dir):
            logger.warning(f"Skipping missing directory: {cls_dir}")
            continue

        video_frames: dict = defaultdict(list)
        for fname in os.listdir(cls_dir):
            if not fname.lower().endswith('.png'):
                continue
            vid_id, frame_num = parse_frame_filename(fname)
            if vid_id is not None:
                video_frames[vid_id].append(
                    (frame_num, os.path.join(cls_dir, fname))
                )

        logger.info(f"  [{cls_name}] {len(video_frames)} videos -> {category}/")

        for vid_id, frames in video_frames.items():
            save_path = os.path.join(output_dir, category, f"{vid_id}.npy")
            if os.path.exists(save_path):
                total_skip += 1
                continue

            frames.sort(key=lambda x: x[0])
            frame_paths = [fp for _, fp in frames]

            try:
                feats = extract_video_features(
                    frame_paths, extractor, n_segments, batch_size
                )
                np.save(save_path, feats)
                total_done += 1
                if total_done % 50 == 0:
                    logger.info(
                        f"    ... {total_done} done "
                        f"(skipped={total_skip}, errors={total_err})"
                    )
            except Exception as exc:
                logger.error(f"    ERROR on {vid_id}: {exc}")
                total_err += 1

    logger.info(
        f"Extraction complete: done={total_done}, "
        f"skipped={total_skip}, errors={total_err}"
    )
