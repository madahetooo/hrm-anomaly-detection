"""
HRM (Hierarchical Relationship Model) for Crime Detection.

Architecture (two-level hierarchy with patch embedding):
─────────────────────────────────────────────────────────────
  Input:  [Batch, T=20, feature_dim=2048]  (T temporal segments)

  Patch Embedding (2×2 patch)
      Groups every patch_t=2 consecutive temporal segments into one token.
      Projects [patch_t × feature_dim] → hidden_dim=64.
      Output: [Batch, T//patch_t = 10, hidden_dim=64]

  Level 1 — Windowed Attention Module (Swin-Transformer style)
      W-MSA : attention within non-overlapping windows of window_size=2
      SW-MSA: attention in cyclically-shifted windows (shift=1)
      Followed by MLP (dim_feedforward=256)
      Captures local relationships with reduced quadratic complexity.

  Level 2 — Global Temporal Reasoning Module
      Dilated 1-D Convolutions with growing receptive fields
      Models temporal evolution over the full video timeline.

  Fusion
      Concatenate local + global → linear projection back to hidden_dim

  Output:  Per-patch anomaly score ∈ [0, 1]
           shape [Batch, T//patch_t]
─────────────────────────────────────────────────────────────
Training uses Multiple Instance Learning (MIL):
  - No frame-level labels required during training
  - Ranking Loss separates the peak score of anomalous videos
    from the peak score of normal videos
"""

import torch
import torch.nn as nn


# ─────────────────────────────────────────────────────────────
# Patch Embedding
# ─────────────────────────────────────────────────────────────

class PatchEmbedding(nn.Module):
    """
    Temporal patch embedding (2×2 patch size).

    Groups `patch_t` consecutive temporal segments into one token and
    projects the concatenated features to `hidden_dim`.

    Input : [B, T,        feature_dim]
    Output: [B, T//patch_t, hidden_dim]
    """

    def __init__(
        self,
        feature_dim: int = 2048,
        hidden_dim: int  = 64,
        patch_t: int     = 2,
        dropout: float   = 0.03,
    ):
        super().__init__()
        self.patch_t = patch_t
        # patch_t segments × feature_dim → hidden_dim
        self.proj = nn.Sequential(
            nn.Linear(patch_t * feature_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: [B, T, feature_dim]
        Returns: [B, T//patch_t, hidden_dim]
        """
        B, T, C = x.shape
        # Pad T to be divisible by patch_t if needed
        pad = (self.patch_t - T % self.patch_t) % self.patch_t
        if pad > 0:
            x = torch.cat([x, x[:, -pad:, :]], dim=1)
            T = T + pad
        # Reshape: [B, T//patch_t, patch_t * C]
        x = x.reshape(B, T // self.patch_t, self.patch_t * C)
        return self.proj(x)   # [B, T//patch_t, hidden_dim]


# ─────────────────────────────────────────────────────────────
# Windowed Attention Module  (Level 1)
# ─────────────────────────────────────────────────────────────

class WindowedAttentionLayer(nn.Module):
    """
    One Swin-style block: W-MSA → residual → SW-MSA → residual → MLP.

    W-MSA  : standard windowed self-attention (no shift)
    SW-MSA : shifted windowed self-attention (cyclic shift by shift_size)
    """

    def __init__(
        self,
        embed_dim: int,
        n_heads: int,
        window_size: int,
        shift_size: int,
        mlp_dim: int,
        dropout: float,
    ):
        super().__init__()
        self.window_size = window_size
        self.shift_size  = shift_size

        # Shared attention (W-MSA and SW-MSA share weights)
        self.norm1  = nn.LayerNorm(embed_dim)
        self.norm1s = nn.LayerNorm(embed_dim)   # norm before SW-MSA
        self.norm2  = nn.LayerNorm(embed_dim)

        self.attn = nn.MultiheadAttention(
            embed_dim, n_heads, dropout=dropout, batch_first=True
        )

        self.mlp = nn.Sequential(
            nn.Linear(embed_dim, mlp_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(mlp_dim, embed_dim),
            nn.Dropout(dropout),
        )

    # ── helpers ───────────────────────────────────────────────

    def _partition(self, x: torch.Tensor) -> tuple:
        """[B, T, C] → [B*nW, ws, C],  nW = T // window_size"""
        B, T, C = x.shape
        nW = T // self.window_size
        x  = x.view(B, nW, self.window_size, C)
        return x.reshape(B * nW, self.window_size, C), B, T, C

    def _reverse(self, x: torch.Tensor, B: int, T: int) -> torch.Tensor:
        """[B*nW, ws, C] → [B, T, C]"""
        C  = x.shape[-1]
        nW = T // self.window_size
        x  = x.view(B, nW, self.window_size, C)
        return x.reshape(B, T, C)

    # ── forward ───────────────────────────────────────────────

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: [B, T, embed_dim]  →  [B, T, embed_dim]"""
        B, T, _ = x.shape

        # ── W-MSA (regular windows) ───────────────────────────
        shortcut   = x
        x_norm, _, _ , _= self._partition(self.norm1(x))
        attn_out, _ = self.attn(x_norm, x_norm, x_norm)
        x = shortcut + self._reverse(attn_out, B, T)

        # ── SW-MSA (shifted windows) ──────────────────────────
        if self.shift_size > 0:
            shortcut = x
            x_shifted = torch.roll(x, shifts=-self.shift_size, dims=1)
            x_norm_s, _, _, _ = self._partition(self.norm1s(x_shifted))
            attn_out, _ = self.attn(x_norm_s, x_norm_s, x_norm_s)
            x_unshift = self._reverse(attn_out, B, T)
            x = shortcut + torch.roll(x_unshift, shifts=self.shift_size, dims=1)

        # ── MLP ───────────────────────────────────────────────
        x = x + self.mlp(self.norm2(x))
        return x


class WindowedAttentionModule(nn.Module):
    """
    Level 1: Stacked windowed attention layers.
    """

    def __init__(
        self,
        embed_dim: int,
        n_heads: int,
        window_size: int,
        shift_size: int,
        mlp_dim: int,
        n_layers: int,
        dropout: float,
    ):
        super().__init__()
        self.layers = nn.ModuleList([
            WindowedAttentionLayer(
                embed_dim=embed_dim,
                n_heads=n_heads,
                window_size=window_size,
                shift_size=shift_size,
                mlp_dim=mlp_dim,
                dropout=dropout,
            )
            for _ in range(n_layers)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x)
        return x


# ─────────────────────────────────────────────────────────────
# Global Temporal Reasoning  (Level 2)
# ─────────────────────────────────────────────────────────────

class GlobalTemporalReasoning(nn.Module):
    """
    Level 2: Models long-range temporal evolution with dilated 1-D convolutions.
    Three layers with dilation 1 → 2 → 4.
    """

    def __init__(self, hidden_dim: int = 64, dropout: float = 0.03):
        super().__init__()

        def _block(dilation):
            return nn.Sequential(
                nn.Conv1d(
                    hidden_dim, hidden_dim,
                    kernel_size=3,
                    padding=dilation,
                    dilation=dilation,
                ),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
            )

        self.conv_layers = nn.Sequential(
            _block(dilation=1),
            _block(dilation=2),
            _block(dilation=4),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: [B, T, hidden_dim]  →  [B, T, hidden_dim]"""
        out = self.conv_layers(x.permute(0, 2, 1))
        return out.permute(0, 2, 1)


# ─────────────────────────────────────────────────────────────
# Full HRM Model
# ─────────────────────────────────────────────────────────────

class HRM_Model(nn.Module):
    """
    Full Hierarchical Relationship Model with Patch Embedding
    and Windowed Self-Attention.

    Parameters
    ----------
    feature_dim          : int   Dimension of input ResNet-50 features (2048).
    hidden_dim           : int   Embedding/token dimension (64).
    mlp_dim              : int   MLP hidden size in Transformer blocks (256).
    n_heads              : int   Attention heads (8).
    n_transformer_layers : int   Number of windowed-attention layers (2).
    dropout              : float Dropout rate (0.03).
    patch_size           : tuple (temporal_patch, feature_patch) — (2, 2).
    window_size          : int   Self-attention window size in tokens (2).
    window_shift_size    : int   Cyclic shift for SW-MSA (1).
    """

    def __init__(
        self,
        feature_dim: int          = 2048,
        hidden_dim: int           = 64,
        mlp_dim: int              = 256,
        n_heads: int              = 8,
        n_transformer_layers: int = 2,
        dropout: float            = 0.03,
        patch_size: tuple         = (2, 2),
        window_size: int          = 2,
        window_shift_size: int    = 1,
    ):
        super().__init__()
        patch_t = patch_size[0]

        # ── Patch Embedding ──────────────────────────────────
        self.patch_embed = PatchEmbedding(
            feature_dim=feature_dim,
            hidden_dim=hidden_dim,
            patch_t=patch_t,
            dropout=dropout,
        )

        # ── Level 1: Windowed Self-Attention ─────────────────
        self.local_module = WindowedAttentionModule(
            embed_dim=hidden_dim,
            n_heads=n_heads,
            window_size=window_size,
            shift_size=window_shift_size,
            mlp_dim=mlp_dim,
            n_layers=n_transformer_layers,
            dropout=dropout,
        )

        # ── Level 2: Global Temporal Reasoning ───────────────
        self.global_module = GlobalTemporalReasoning(
            hidden_dim=hidden_dim,
            dropout=dropout,
        )

        # ── Fusion: concat local + global → hidden_dim ───────
        self.fusion = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )

        # ── Per-patch Anomaly Score Head ─────────────────────
        self.score_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : torch.Tensor  [Batch, T, feature_dim]
            T=20 temporal segments per video.

        Returns
        -------
        scores : torch.Tensor  [Batch, T//patch_t]
            Per-patch anomaly score ∈ [0, 1].
        """
        # Patch embedding: [B, T, 2048] → [B, T//patch_t, hidden_dim]
        x_pat = self.patch_embed(x)

        # Level 1 — windowed self-attention (local)
        local_out = self.local_module(x_pat)       # [B, T', hidden_dim]

        # Level 2 — dilated conv (global temporal)
        global_out = self.global_module(local_out)  # [B, T', hidden_dim]

        # Hierarchical fusion
        fused  = torch.cat([local_out, global_out], dim=-1)  # [B, T', 2*hidden]
        fused  = self.fusion(fused)                           # [B, T', hidden_dim]

        # Anomaly scores
        scores = self.score_head(fused).squeeze(-1)   # [B, T']
        return scores

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
