"""
Visualisation utilities for the HRM Crime Detection model.

Produces two kinds of plots:

1. Anomaly Profile  (per-video)
   Shows the HRM's per-segment anomaly score over the video timeline.
   A good model "spikes" only when a crime actually occurs.

2. Training History
   Side-by-side: Training Loss and Validation AUC-ROC per epoch.
"""

import os
import logging
from typing import Dict, List, Optional

import numpy as np
import torch
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. Per-video anomaly profile
# ─────────────────────────────────────────────────────────────

def visualize_anomaly_profile(
    model,
    features: np.ndarray,
    video_name: str,
    results_dir: str,
    threshold: float = 0.5,
    device: torch.device = None,
    true_label: Optional[int] = None,
) -> np.ndarray:
    """
    Run model inference on one video and plot the anomaly score timeline.

    Parameters
    ----------
    model       : trained HRM_Model
    features    : np.ndarray  [T, feature_dim]  pre-extracted features
    video_name  : str   used as plot title and output filename stem
    results_dir : str   directory where the PNG will be saved
    threshold   : float binary detection threshold (default 0.5)
    device      : torch.device (defaults to cpu)
    true_label  : 0 (Normal) or 1 (Anomaly), used to annotate the plot

    Returns
    -------
    scores : np.ndarray  [T]  per-segment anomaly scores
    """
    if device is None:
        device = torch.device('cpu')

    model.eval()
    feat_tensor = torch.from_numpy(features).float().unsqueeze(0).to(device)

    with torch.no_grad():
        scores = model(feat_tensor).cpu().numpy().flatten()   # [T]

    T = len(scores)
    t_axis = np.arange(T)

    # ── Figure ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 5))

    # Shaded area under the score curve
    ax.fill_between(t_axis, scores, alpha=0.25, color='steelblue')
    ax.plot(t_axis, scores, color='steelblue', lw=2,
            label='Anomaly Score', marker='o', markersize=3)

    # Threshold line
    ax.axhline(y=threshold, color='red', linestyle='--', lw=1.5,
               label=f'Threshold = {threshold}')

    # Highlight segments above threshold
    for i in t_axis:
        if scores[i] >= threshold:
            ax.axvspan(i - 0.5, i + 0.5, alpha=0.18, color='red', zorder=0)

    # ── Labels & decoration ───────────────────────────────────
    gt_text = ''
    if true_label is not None:
        gt_text = f'  [Ground Truth: {"Anomaly" if true_label else "Normal"}]'
    ax.set_title(f'HRM Anomaly Profile — {video_name}{gt_text}', fontsize=13)
    ax.set_xlabel('Temporal Segment  (video timeline →)', fontsize=11)
    ax.set_ylabel('Anomaly Score', fontsize=11)
    ax.set_xlim(-0.5, T - 0.5)
    ax.set_ylim(-0.05, 1.10)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    # Annotations
    peak_idx = int(np.argmax(scores))
    ax.annotate(
        f'Peak: {scores[peak_idx]:.2f}',
        xy=(peak_idx, scores[peak_idx]),
        xytext=(peak_idx + 1, scores[peak_idx] + 0.08),
        arrowprops=dict(arrowstyle='->', color='black'),
        fontsize=9,
    )

    os.makedirs(results_dir, exist_ok=True)
    save_path = os.path.join(results_dir, f'{video_name}_anomaly_profile.png')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info(f"Anomaly profile saved: {save_path}")

    return scores


# ─────────────────────────────────────────────────────────────
# 2. Training history
# ─────────────────────────────────────────────────────────────

def plot_training_history(history: Dict[str, List], results_dir: str):
    """
    Plot training loss components and validation AUC-ROC over epochs.

    Parameters
    ----------
    history     : dict returned by  src.train.train()
                  keys: train_loss, rank_loss, smooth_loss, sparse_loss, val_auc
    results_dir : str  output directory
    """
    os.makedirs(results_dir, exist_ok=True)

    epochs = list(range(1, len(history['train_loss']) + 1))

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))

    # ── Left: Loss curves ─────────────────────────────────────
    ax = axes[0]
    ax.plot(epochs, history['train_loss'],  lw=2, label='Total loss', color='royalblue')
    ax.plot(epochs, history['rank_loss'],   lw=1.5, linestyle='--',
            label='Ranking loss', color='darkorange')
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('Loss', fontsize=12)
    ax.set_title('Training Loss Components', fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    # ── Right: Validation AUC ──────────────────────────────────
    ax = axes[1]
    ax.plot(epochs, history['val_auc'], lw=2, color='seagreen',
            label='Val AUC-ROC')
    ax.axhline(y=0.82, color='red', linestyle='--', lw=1.5,
               label='Target AUC = 0.82')
    best_auc   = max(history['val_auc'])
    best_epoch = epochs[history['val_auc'].index(best_auc)]
    ax.axvline(x=best_epoch, color='purple', linestyle=':', lw=1.2,
               label=f'Best epoch {best_epoch} ({best_auc:.4f})')
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('AUC-ROC', fontsize=12)
    ax.set_title('Validation AUC-ROC', fontsize=13)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    plt.suptitle('HRM Model — Training History', fontsize=14, y=1.02)
    plt.tight_layout()

    path = os.path.join(results_dir, 'training_history.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Training history saved: {path}")


# ─────────────────────────────────────────────────────────────
# 3. Score distribution comparison
# ─────────────────────────────────────────────────────────────

def plot_score_distribution(
    eval_results: Dict,
    results_dir: str,
    threshold: float = 0.5,
):
    """
    Plot the distribution of anomaly scores for Normal vs Anomaly videos.

    Parameters
    ----------
    eval_results : dict returned by  src.evaluate.full_evaluation()
    results_dir  : output directory
    threshold    : float
    """
    scores = eval_results['scores']
    labels = eval_results['labels']

    normal_scores  = scores[labels == 0]
    anomaly_scores = scores[labels == 1]

    fig, ax = plt.subplots(figsize=(10, 5))

    bins = np.linspace(0, 1, 50)
    ax.hist(normal_scores,  bins=bins, alpha=0.6, color='steelblue',
            label=f'Normal  (n={len(normal_scores)})')
    ax.hist(anomaly_scores, bins=bins, alpha=0.6, color='tomato',
            label=f'Anomaly (n={len(anomaly_scores)})')
    ax.axvline(x=threshold, color='black', linestyle='--', lw=1.5,
               label=f'Threshold = {threshold}')

    ax.set_xlabel('Video Anomaly Score', fontsize=12)
    ax.set_ylabel('Number of Videos', fontsize=12)
    ax.set_title(f'Score Distribution — HRM Model  (AUC={eval_results["auc"]:.4f})',
                 fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(results_dir, 'score_distribution.png')
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"Score distribution saved: {path}")
