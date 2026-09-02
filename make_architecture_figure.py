# -*- coding: utf-8 -*-
"""Regenerate Figure 2 (HRM-Crime architecture) with print-legible fonts.

Addresses Reviewer 2 comment 1: figure fonts too small at page width.
The canvas is deliberately wide and short so that, scaled to the text
column, glyph height stays above ~8 pt.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

NAVY = '#12276b'
GREY = '#3d3d3d'

fig, ax = plt.subplots(figsize=(14, 7.6))
ax.set_xlim(0, 100); ax.set_ylim(0, 56); ax.axis('off')

def box(x, y, w, h, title, sub, fc, ts=19, ss=15):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
        boxstyle='round,pad=0.28,rounding_size=1.0',
        linewidth=1.6, edgecolor='#5a5a5a', facecolor=fc))
    if sub:
        ax.text(x + w/2, y + h*0.63, title, ha='center', va='center',
                fontsize=ts, fontweight='bold', color=NAVY)
        ax.text(x + w/2, y + h*0.26, sub, ha='center', va='center',
                fontsize=ss, style='italic', color=GREY)
    else:
        ax.text(x + w/2, y + h/2, title, ha='center', va='center',
                fontsize=ts, fontweight='bold', color=NAVY)

def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), color=NAVY,
        linewidth=2.4, arrowstyle='-|>', mutation_scale=26,
        shrinkA=0, shrinkB=0))

ax.text(50, 54.0, 'HRM-Crime Architecture', ha='center',
        fontsize=24, fontweight='bold', color=NAVY)

# ── Left column: offline feature extraction ──────────────────────────────
ax.text(18, 49.6, 'Offline extraction (frozen)', ha='center',
        fontsize=17, fontweight='bold', color=GREY)
box(1, 41.0, 34, 6.4, 'Input video  —  32 segments',
    'resampled to T = 20', '#e3f0fc')
box(1, 30.6, 16, 6.8, 'ResNet-50', '2048-D', '#aed4f2')
box(19, 30.6, 16, 6.8, 'R3D-18', '512-D', '#aed4f2')
box(1, 20.6, 34, 6.4, 'L2-norm  ⊕  concat',
    r'$f \in \mathbb{R}^{2560}$ per segment', '#b9bce0')
arrow(13, 41.0, 9, 37.6); arrow(23, 41.0, 27, 37.6)
arrow(9, 30.6, 13, 27.2); arrow(27, 30.6, 23, 27.2)

ax.text(18, 15.4, '0 trainable params  ·  56.9 M frozen',
        ha='center', fontsize=16, style='italic', color=GREY)
ax.text(18, 11.8, '3,401 GFLOPs / video, cached once',
        ha='center', fontsize=16, style='italic', color=GREY)

# ── Right column: the trained hierarchical reasoning stack ───────────────
ax.text(75, 49.6, 'Reasoning module (trained)', ha='center',
        fontsize=17, fontweight='bold', color=GREY)
rows = [
    (41.0, 'Patch embedding (patch_t = 2)',
     'Linear → LN → GELU  →  [B, 10, 64]', '#dfe0f2'),
    (33.0, 'Windowed self-attention  × 2',
     'W-MSA + SW-MSA,  8 heads', '#dbeedd'),
    (25.0, 'Dilated Conv1D  (d = 1, 2, 3)',
     'receptive field 13  >  T′ = 10', '#fdecd2'),
    (17.0, 'Hierarchical fusion',
     'concat[local; global] → LN', '#fadfe4'),
    (9.0, 'Score head + MIL ranking loss',
     'sigmoid  →  mean(top-K)', '#f2ddf2'),
]
for i, (y, t, sb, c) in enumerate(rows):
    box(52, y, 47, 6.2, t, sb, c, ts=17, ss=13.5)
    if i:
        arrow(75.5, rows[i-1][0], 75.5, y + 6.2)

arrow(35, 23.8, 52, 44.1)          # cached features into the stack
ax.text(43.5, 35.0, 'cached\nfeatures', ha='center', va='center',
        fontsize=15, style='italic', color=GREY, rotation=42)

ax.text(75.5, 5.2, '270 K trainable params  ·  0.0027 GFLOPs / video',
        ha='center', fontsize=16, style='italic', color=GREY)
ax.text(50, 1.4,
        'Deployed system: four such models — two combined-stream seeds, one '
        'spatial-only, one temporal-only — fused by weighted rank averaging',
        ha='center', fontsize=16, style='italic', color=GREY)

plt.tight_layout()
plt.savefig('results_093/architecture.png', dpi=220, bbox_inches='tight',
            facecolor='white')
print('Saved: results_093/architecture.png')
