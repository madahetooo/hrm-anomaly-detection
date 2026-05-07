"""
MIL Ranking Loss for weakly-supervised anomaly detection.

Based on:  Sultani et al., "Real-world Anomaly Detection in Surveillance
           Videos", CVPR 2018.

Loss = Ranking(abn, norm) + λ_smooth * Smoothness + λ_sparse * Sparsity
─────────────────────────────────────────────────────────────
Ranking:
  Forces the maximum anomaly score in an ABNORMAL video to exceed the
  maximum score in a NORMAL video by at least `margin`.
  loss_rank = mean( relu(margin - max(scores_abn) + max(scores_norm)) )

Smoothness:
  Adjacent segment scores should not jump abruptly (crimes happen in
  coherent temporal windows, not scattered single frames).
  loss_smooth = mean( (s_{t+1} - s_t)^2 )  over abnormal videos

Sparsity:
  Anomalies are rare events; only a few segments should have high scores.
  loss_sparse = mean( scores_abn )
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class MILRankingLoss(nn.Module):
    """
    Multiple Instance Learning Ranking Loss with temporal regularisers.

    Parameters
    ----------
    margin : float
        Minimum gap enforced between anomaly and normal max scores.
    lambda_smooth : float
        Weight for the smoothness regularisation term.
    lambda_sparse : float
        Weight for the sparsity regularisation term.
    """

    def __init__(
        self,
        margin: float        = 1.0,
        lambda_smooth: float = 8e-5,
        lambda_sparse: float = 8e-5,
    ):
        super().__init__()
        self.margin        = margin
        self.lambda_smooth = lambda_smooth
        self.lambda_sparse = lambda_sparse

    def forward(
        self,
        scores_abnormal: torch.Tensor,
        scores_normal:   torch.Tensor,
    ):
        """
        Parameters
        ----------
        scores_abnormal : torch.Tensor  [B_abn, T]
            Per-segment scores for abnormal (crime) videos.
        scores_normal : torch.Tensor  [B_norm, T]
            Per-segment scores for normal videos.

        Returns
        -------
        total_loss    : scalar Tensor
        ranking_loss  : scalar Tensor  (for logging)
        smooth_loss   : scalar Tensor  (for logging)
        sparse_loss   : scalar Tensor  (for logging)
        """
        # ── MIL: take the maximum score per video ─────────────
        max_abn  = torch.max(scores_abnormal, dim=1)[0]   # [B_abn]
        max_norm = torch.max(scores_normal,   dim=1)[0]   # [B_norm]

        # Match batch sizes for pairwise comparison
        n = min(max_abn.shape[0], max_norm.shape[0])
        max_abn  = max_abn[:n]
        max_norm = max_norm[:n]

        # Ranking loss: hinge(margin - abn_max + norm_max)
        ranking_loss = torch.mean(
            F.relu(self.margin - max_abn + max_norm)
        )

        # ── Temporal Smoothness ────────────────────────────────
        smooth_loss = torch.mean(
            (scores_abnormal[:, 1:] - scores_abnormal[:, :-1]) ** 2
        )

        # ── Sparsity ───────────────────────────────────────────
        sparse_loss = torch.mean(scores_abnormal)

        total_loss = (
            ranking_loss
            + self.lambda_smooth * smooth_loss
            + self.lambda_sparse * sparse_loss
        )

        return total_loss, ranking_loss, smooth_loss, sparse_loss
