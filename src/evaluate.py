"""
Evaluation utilities for the HRM Crime Detection model.

Metrics
───────
AUC-ROC   Area Under the ROC Curve  (primary UCF-Crime metric)
AUC-PR    Area Under the Precision-Recall Curve
            More informative when classes are imbalanced or when
            the operating point matters.  Random baseline = prevalence.
EER       Equal Error Rate  — threshold where FPR == FNR
            Lower is better; good models reach <0.20.
Opt-F1    Threshold that maximises F1 on the test set
            Shows the *best possible* binary accuracy, not the
            arbitrary 0.5 default which may be misleading.
Score stats
            Mean / std / median of anomaly vs. normal score distributions
            — confirms the model separates the two classes.

Evaluation logic
────────────────
Because training uses weak (video-level) labels, we evaluate at the
video level: the anomaly score for a video is the maximum segment score.
  score_video = max(scores_t  for t in 1..T)
"""

import os
import logging
from typing import Dict

import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import (
    roc_auc_score,
    roc_curve,
    average_precision_score,
    precision_recall_curve,
    classification_report,
    confusion_matrix,
    f1_score,
)
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Snapshot ensemble AUC  (average predictions from top-K models)
# ─────────────────────────────────────────────────────────────

@torch.no_grad()
def ensemble_auc(model, snapshot_paths: list, dataloader: DataLoader,
                 device: torch.device) -> float:
    """
    Average the video-level anomaly scores from multiple saved snapshots
    and return the ensemble AUC-ROC.
    """
    all_labels = None
    sum_scores = None

    for path in snapshot_paths:
        raw = torch.load(path, map_location=device)
        state = raw['model_state_dict'] if isinstance(raw, dict) and 'model_state_dict' in raw else raw
        model.load_state_dict(state)
        model.eval()
        scores = []
        labels = []
        for features, lbls in dataloader:
            features = features.to(device)
            seg_scores   = model(features)
            video_scores = torch.max(seg_scores, dim=1)[0]
            scores.extend(video_scores.cpu().numpy())
            labels.extend(lbls.numpy())
        scores = np.array(scores)
        labels = np.array(labels)
        if sum_scores is None:
            sum_scores = scores.copy()
            all_labels = labels
        else:
            sum_scores += scores

    if sum_scores is None or len(np.unique(all_labels)) < 2:
        return 0.5

    avg_scores = sum_scores / len(snapshot_paths)
    return float(roc_auc_score(all_labels, avg_scores))


# ─────────────────────────────────────────────────────────────
# Fast AUC computation  (used during validation each epoch)
# ─────────────────────────────────────────────────────────────

@torch.no_grad()
def compute_auc(model, dataloader: DataLoader, device: torch.device) -> float:
    """
    Compute video-level AUC-ROC.
    Returns 0.5 if only one class is present.
    """
    model.eval()
    all_scores = []
    all_labels = []

    for features, labels in dataloader:
        features = features.to(device)
        seg_scores   = model(features)                       # [B, T]
        video_scores = torch.max(seg_scores, dim=1)[0]      # [B]

        all_scores.extend(video_scores.cpu().numpy())
        all_labels.extend(labels.numpy())

    all_labels = np.array(all_labels)
    all_scores = np.array(all_scores)

    if len(np.unique(all_labels)) < 2:
        return 0.5

    return float(roc_auc_score(all_labels, all_scores))


# ─────────────────────────────────────────────────────────────
# Full evaluation  (run once after training)
# ─────────────────────────────────────────────────────────────

@torch.no_grad()
def full_evaluation(
    model,
    dataloader: DataLoader,
    device: torch.device,
    results_dir: str,
    threshold: float = 0.5,
) -> Dict:
    """
    Run full evaluation on the test set.

    Saves
    ─────
    results_dir/roc_curve.png
    results_dir/pr_curve.png
    results_dir/confusion_matrix.png
    results_dir/score_distributions.png

    Returns
    -------
    dict with keys: auc, auc_pr, eer, opt_threshold, opt_f1,
                    fpr, tpr, predictions, scores, labels
    """
    os.makedirs(results_dir, exist_ok=True)
    model.eval()

    all_scores = []
    all_labels = []

    for features, labels in dataloader:
        features     = features.to(device)
        seg_scores   = model(features)                       # [B, T]
        video_scores = torch.max(seg_scores, dim=1)[0]      # [B]

        all_scores.extend(video_scores.cpu().numpy())
        all_labels.extend(labels.numpy())

    all_scores = np.array(all_scores)
    all_labels = np.array(all_labels)

    # ── AUC-ROC ───────────────────────────────────────────────
    auc = roc_auc_score(all_labels, all_scores)
    fpr, tpr, roc_thresholds = roc_curve(all_labels, all_scores)

    # ── AUC-PR (Average Precision) ────────────────────────────
    auc_pr = average_precision_score(all_labels, all_scores)
    prec, rec, pr_thresholds = precision_recall_curve(all_labels, all_scores)

    # ── Equal Error Rate (EER) ────────────────────────────────
    # EER is the threshold where FPR ≈ FNR  (FNR = 1 - TPR)
    fnr = 1.0 - tpr
    eer_idx = np.argmin(np.abs(fpr - fnr))
    eer      = float((fpr[eer_idx] + fnr[eer_idx]) / 2.0)
    eer_thr  = float(roc_thresholds[eer_idx])

    # ── Optimal F1 threshold ──────────────────────────────────
    # Search over PR-curve thresholds for best F1
    if len(pr_thresholds) > 0:
        f1_scores  = np.where(
            (prec[:-1] + rec[:-1]) > 0,
            2 * prec[:-1] * rec[:-1] / (prec[:-1] + rec[:-1]),
            0.0,
        )
        best_f1_idx  = int(np.argmax(f1_scores))
        opt_threshold = float(pr_thresholds[best_f1_idx])
        opt_f1        = float(f1_scores[best_f1_idx])
    else:
        opt_threshold = threshold
        opt_f1        = 0.0

    # ── Score distribution stats ──────────────────────────────
    abn_scores  = all_scores[all_labels == 1]
    norm_scores = all_scores[all_labels == 0]
    sep_gap     = float(np.mean(abn_scores) - np.mean(norm_scores))  # positive = correct

    # ── Binary predictions at fixed threshold ─────────────────
    predictions = (all_scores >= threshold).astype(int)
    report = classification_report(
        all_labels, predictions,
        target_names=['Normal', 'Anomaly'],
        digits=4,
    )
    cm = confusion_matrix(all_labels, predictions)

    # ── Binary predictions at optimal threshold ───────────────
    opt_predictions = (all_scores >= opt_threshold).astype(int)
    opt_report = classification_report(
        all_labels, opt_predictions,
        target_names=['Normal', 'Anomaly'],
        digits=4,
    )
    opt_cm = confusion_matrix(all_labels, opt_predictions)

    # ── Console output ────────────────────────────────────────
    sep = "=" * 60
    print(f"\n{sep}")
    print("  HRM Model  —  Test Set Evaluation")
    print(sep)
    print(f"  AUC-ROC          : {auc:.4f}   (random=0.50, target≥0.92)")
    print(f"  AUC-PR           : {auc_pr:.4f}   (random={np.mean(all_labels):.2f}, prevalence)")
    print(f"  EER              : {eer:.4f}   (lower is better; at thr={eer_thr:.3f})")
    print(f"  Opt-F1           : {opt_f1:.4f}   (best achievable F1; at thr={opt_threshold:.3f})")
    print()
    print(f"  Score distributions:")
    print(f"    Anomaly  — mean={np.mean(abn_scores):.3f}  std={np.std(abn_scores):.3f}"
          f"  median={np.median(abn_scores):.3f}")
    print(f"    Normal   — mean={np.mean(norm_scores):.3f}  std={np.std(norm_scores):.3f}"
          f"  median={np.median(norm_scores):.3f}")
    print(f"    Gap (abn-norm mean): {sep_gap:+.3f}"
          f"  {'[OK — correct direction]' if sep_gap > 0 else '[WARNING — inverted!]'}")
    print()
    print(f"  --- At fixed threshold {threshold} ---")
    print(report)
    print(f"  Confusion Matrix (thr={threshold}):")
    _print_confusion_matrix(cm)
    print()
    print(f"  --- At optimal threshold {opt_threshold:.3f} (max-F1) ---")
    print(opt_report)
    print(f"  Confusion Matrix (thr={opt_threshold:.3f}):")
    _print_confusion_matrix(opt_cm)
    print(sep + "\n")

    # ── Plots ─────────────────────────────────────────────────
    _plot_roc_curve(fpr, tpr, auc, eer, eer_thr, results_dir)
    _plot_pr_curve(prec, rec, auc_pr, opt_f1, opt_threshold, results_dir)
    _plot_confusion_matrix(cm, results_dir, threshold)
    _plot_score_distributions(abn_scores, norm_scores, threshold, opt_threshold, results_dir)

    logger.info(
        f"Test  AUC-ROC={auc:.4f}  AUC-PR={auc_pr:.4f}  "
        f"EER={eer:.4f}  OptF1={opt_f1:.4f}(thr={opt_threshold:.3f})"
    )

    return {
        'auc':           auc,
        'auc_pr':        auc_pr,
        'eer':           eer,
        'eer_threshold': eer_thr,
        'opt_threshold': opt_threshold,
        'opt_f1':        opt_f1,
        'fpr':           fpr,
        'tpr':           tpr,
        'predictions':   predictions,
        'scores':        all_scores,
        'labels':        all_labels,
    }


# ─────────────────────────────────────────────────────────────
# Plot helpers
# ─────────────────────────────────────────────────────────────

def _plot_roc_curve(fpr, tpr, auc, eer, eer_thr, results_dir):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(fpr, tpr, color='darkorange', lw=2,
            label=f'HRM Model  (AUC-ROC = {auc:.4f})')
    ax.plot([0, 1], [0, 1], color='navy', lw=1.5,
            linestyle='--', label='Random classifier')
    # Mark EER point
    ax.scatter([eer], [1 - eer], color='red', zorder=5, s=60,
               label=f'EER = {eer:.4f}  (thr={eer_thr:.3f})')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=13)
    ax.set_ylabel('True Positive Rate', fontsize=13)
    ax.set_title('ROC Curve — HRM Crime Detection\n(UCF-Crime Dataset)', fontsize=14)
    ax.legend(loc='lower right', fontsize=11)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = os.path.join(results_dir, 'roc_curve.png')
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"ROC curve saved: {path}")


def _plot_pr_curve(prec, rec, auc_pr, opt_f1, opt_thr, results_dir):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(rec, prec, color='steelblue', lw=2,
            label=f'HRM Model  (AUC-PR = {auc_pr:.4f})')
    ax.axhline(y=0.5, color='navy', lw=1.5, linestyle='--',
               label='Random baseline (≈ prevalence)')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('Recall', fontsize=13)
    ax.set_ylabel('Precision', fontsize=13)
    ax.set_title(f'Precision-Recall Curve\nOpt F1 = {opt_f1:.4f}  at thr={opt_thr:.3f}',
                 fontsize=14)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = os.path.join(results_dir, 'pr_curve.png')
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"PR curve saved: {path}")


def _plot_score_distributions(abn_scores, norm_scores, fixed_thr, opt_thr, results_dir):
    fig, ax = plt.subplots(figsize=(9, 5))
    bins = np.linspace(0, 1, 40)
    ax.hist(norm_scores, bins=bins, alpha=0.6, color='steelblue',
            label=f'Normal   (n={len(norm_scores)}, mean={np.mean(norm_scores):.3f})')
    ax.hist(abn_scores,  bins=bins, alpha=0.6, color='tomato',
            label=f'Anomaly  (n={len(abn_scores)}, mean={np.mean(abn_scores):.3f})')
    ax.axvline(fixed_thr, color='black',  lw=1.5, linestyle='--',
               label=f'Fixed thr = {fixed_thr}')
    ax.axvline(opt_thr,   color='purple', lw=1.5, linestyle=':',
               label=f'Opt-F1 thr = {opt_thr:.3f}')
    ax.set_xlabel('Anomaly Score', fontsize=13)
    ax.set_ylabel('Count', fontsize=13)
    ax.set_title('Score Distributions — Normal vs Anomaly', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = os.path.join(results_dir, 'score_distributions.png')
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"Score distributions saved: {path}")


def _plot_confusion_matrix(cm, results_dir, threshold):
    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.colorbar(im, ax=ax)
    classes = ['Normal', 'Anomaly']
    tick_marks = range(len(classes))
    ax.set_xticks(tick_marks)
    ax.set_yticks(tick_marks)
    ax.set_xticklabels(classes, fontsize=12)
    ax.set_yticklabels(classes, fontsize=12)
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]),
                    ha='center', va='center',
                    color='white' if cm[i, j] > thresh else 'black',
                    fontsize=14)
    ax.set_ylabel('True label', fontsize=12)
    ax.set_xlabel('Predicted label', fontsize=12)
    ax.set_title(f'Confusion Matrix  (thr={threshold})', fontsize=14)
    plt.tight_layout()
    path = os.path.join(results_dir, 'confusion_matrix.png')
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"Confusion matrix saved: {path}")


def _print_confusion_matrix(cm):
    classes = ['Normal ', 'Anomaly']
    print(f"              Predicted")
    print(f"              {classes[0]}  {classes[1]}")
    for i, row in enumerate(cm):
        print(f"  True {classes[i]}  {row[0]:6d}  {row[1]:6d}")
