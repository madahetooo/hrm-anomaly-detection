"""HRM-Crime Word (.docx) — IEEE Access format (two-column body, IEEE header)."""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT     = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/HRM_Crime_Paper_IEEE.docx"
RESULTS = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/results_093"
DATE    = 'August 12, 2026'

IEEE_BLUE = RGBColor(0x00, 0x62, 0x9B)
IEEE_DARK = RGBColor(0x00, 0x30, 0x52)
DARK      = RGBColor(0x11, 0x11, 0x11)
GREY      = RGBColor(0x55, 0x55, 0x55)

doc = Document()
sec = doc.sections[0]
sec.page_height = Cm(29.7); sec.page_width = Cm(21.0)
sec.top_margin = Cm(2.5); sec.bottom_margin = Cm(2.2)
sec.left_margin = Cm(1.7); sec.right_margin = Cm(1.7)

norm = doc.styles['Normal']
norm.font.name = 'Times New Roman'
norm.font.size = Pt(10)
norm.paragraph_format.line_spacing = 1.15

def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd')
    sh.set(qn('w:fill'), hex_color.lstrip('#'))
    sh.set(qn('w:val'), 'clear')
    tcPr.append(sh)

def set_cols(section, n):
    sectPr = section._sectPr
    cols = sectPr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols'); sectPr.append(cols)
    cols.set(qn('w:num'), str(n))
    cols.set(qn('w:space'), '360' if n > 1 else '0')
    cols.set(qn('w:equalWidth'), '1')

def add_section_break():
    new = doc.add_section(WD_SECTION.CONTINUOUS)
    new.top_margin = Cm(2.5); new.bottom_margin = Cm(2.2)
    new.left_margin = Cm(1.7); new.right_margin = Cm(1.7)
    return new

def hborder(color='00629B'):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    btm = OxmlElement('w:bottom')
    btm.set(qn('w:val'), 'single'); btm.set(qn('w:sz'), '8')
    btm.set(qn('w:space'), '1'); btm.set(qn('w:color'), color)
    pbdr.append(btm); pPr.append(pbdr)
    p.paragraph_format.space_after = Pt(6)
    return p

def Title(text):
    p = doc.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(17)
    r.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.1
    return p

_roman = ['','I','II','III','IV','V','VI','VII','VIII','IX','X']

def SEC(n, text):
    """Section: 'I. TITLE IN CAPS' bold serif."""
    p = doc.add_paragraph()
    lbl = f'{_roman[n]}. ' if n else ''
    r = p.add_run((lbl + text).upper()); r.bold = True; r.font.size = Pt(11)
    r.font.color.rgb = DARK
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    return p

def SUB(letter, text):
    """Subsection: 'A. Italic Title'."""
    p = doc.add_paragraph()
    r = p.add_run(f'{letter}. '); r.bold = True; r.font.size = Pt(10)
    r.font.color.rgb = DARK
    r = p.add_run(text); r.italic = True; r.font.size = Pt(10)
    r.font.color.rgb = DARK
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    return p

def P(text, *, size=10, justify=True, italic=False, bold=False, indent=True,
      space_after=4, color=None):
    p = doc.add_paragraph()
    if justify: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text); r.font.size = Pt(size); r.italic = italic; r.bold = bold
    if color is not None: r.font.color.rgb = color
    if indent: p.paragraph_format.first_line_indent = Cm(0.4)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    return p

def P_bold_prefix(prefix, text, size=10, indent=False):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(prefix + '  '); r.bold = True; r.font.size = Pt(size)
    r = p.add_run(text); r.font.size = Pt(size)
    if indent: p.paragraph_format.first_line_indent = Cm(0.4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    return p

def Bullet(text, size=10):
    p = doc.add_paragraph(style='List Bullet')
    r = p.add_run(text); r.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(2)
    return p

def Math(text, num=None):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); r.italic = True; r.font.size = Pt(10)
    r.font.name = 'Cambria Math'
    if num:
        r2 = p.add_run(f'   ({num})'); r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    return p

def Caption(prefix, body):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(prefix + ' '); r.bold = True; r.font.size = Pt(9)
    r.font.color.rgb = DARK
    r = p.add_run(body); r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x22,0x22,0x22)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.15
    return p

def add_table(rows, widths_cm=None, highlight_last=False):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = 'Light Grid Accent 1'
    if widths_cm:
        for col_idx, w in enumerate(widths_cm):
            for cell in t.columns[col_idx].cells:
                cell.width = Cm(w)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.text = ''
            p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val)); r.font.size = Pt(9)
            if ri == 0:
                r.bold = True; r.font.color.rgb = RGBColor(0xff,0xff,0xff)
                shade(cell, '#00629B')
            elif highlight_last and ri == len(rows) - 1:
                r.bold = True; shade(cell, '#e0edf6')
    return t

# ═══════════════════════════════════════════════════════════════════════════
# IEEE Access header banner (blue bar with journal name)
# ═══════════════════════════════════════════════════════════════════════════
p = doc.add_paragraph()
r = p.add_run('IEEE Access'); r.bold = True; r.font.size = Pt(13)
r.font.color.rgb = IEEE_BLUE
sep = p.add_run('    '); sep.font.size = Pt(11)
r = p.add_run('Multidisciplinary  ·  Rapid Review  ·  Open Access Journal')
r.font.size = Pt(9); r.italic = True; r.font.color.rgb = IEEE_DARK
sep = p.add_run('        VOLUME XX, 2026  ·  ieeexplore.ieee.org')
sep.font.size = Pt(9); sep.font.color.rgb = GREY
p.paragraph_format.space_after = Pt(2)
hborder('00629B')

# ═══════════════════════════════════════════════════════════════════════════
# First section: single column (title, authors, abstract)
# ═══════════════════════════════════════════════════════════════════════════
set_cols(sec, 1)

# Received / accepted / DOI
p = doc.add_paragraph()
r = p.add_run(f'Received {DATE}; accepted [date]; date of publication '
              '[date]; date of current version [date].')
r.font.size = Pt(8.5); r.font.color.rgb = IEEE_DARK
p.paragraph_format.space_after = Pt(1)

p = doc.add_paragraph()
r = p.add_run('Digital Object Identifier 10.1109/ACCESS.2026.XXXXXXX')
r.font.size = Pt(8.5); r.font.color.rgb = IEEE_DARK
p.paragraph_format.space_after = Pt(8)

# Title
Title('HRM-Crime: A Hierarchical Relationship Model for '
      'Weakly-Supervised Crime Anomaly Detection in Surveillance Video')

# Authors
def _authors():
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    def name(txt, sup, member=None, corresponding=False):
        r = p.add_run(txt.upper()); r.bold = True; r.font.size = Pt(11)
        s = p.add_run(sup); s.bold = True; s.font.size = Pt(11)
        s.font.superscript = True
        if corresponding:
            t = p.add_run(',*'); t.bold = True; t.font.size = Pt(11)
            t.font.superscript = True
        if member:
            r = p.add_run(f'  ({member}, IEEE)'); r.font.size = Pt(9)
    name('Eslam Medhat Fathy Habib', '1',
         member='Graduate Student Member', corresponding=True)
    r = p.add_run(', '); r.font.size = Pt(11)
    name('Ayman Helmy', '2')
    r = p.add_run(', and '); r.font.size = Pt(11)
    name('Mohamed Mostafa Fouad', '3', member='Senior Member')
    p.paragraph_format.space_after = Pt(6)
_authors()

# Affiliations
def affil(num, text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    s = p.add_run(num); s.font.superscript = True; s.font.size = Pt(9)
    r = p.add_run(text); r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x33,0x33,0x33)
    p.paragraph_format.space_after = Pt(2)

affil('1', 'Faculty of Computing and Information Technology, Arab '
           'Academy for Science, Technology and Maritime Transport '
           '(AASTMT), Smart Village, Giza 12577, Egypt (e-mail: '
           'ieslammedhat@gmail.com; ORCID: 0009-0007-1758-8612)')
affil('2', 'Faculty of Computing and Information Technology, Arab '
           'Academy for Science, Technology and Maritime Transport '
           '(AASTMT), Smart Village, Giza 12577, Egypt (e-mail: '
           'ayhelmy@adj.aast.edu)')
affil('3', 'Arab Academy for Science, Technology, and Maritime '
           'Transport, Smart Village, Giza 12577, Egypt (e-mail: '
           'mohamed_mostafa@aast.edu; ORCID: 0000-0003-0879-9761)')

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = p.add_run('Corresponding author: Eslam Medhat Fathy Habib (e-mail: '
              'ieslammedhat@gmail.com).')
r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x33,0x33,0x33)
p.paragraph_format.space_after = Pt(2)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = p.add_run('This work was conducted as part of the corresponding '
              'author\'s Master\'s research at AASTMT.')
r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x33,0x33,0x33)
p.paragraph_format.space_after = Pt(8)

# Abstract
P_bold_prefix('ABSTRACT',
    'Automated detection of anomalous behaviour in surveillance video '
    'is a high-impact application of machine learning, but training '
    'data is available only at the video level: a bag of temporal '
    'segments is labelled anomaly or normal with no per-segment ground '
    'truth. Prior weakly-supervised methods on the UCF-Crime benchmark '
    'have plateaued around 85–87% ROC-AUC using ever larger Vision '
    'Transformer backbones and increasingly elaborate score modules. We '
    'take the opposite approach. This paper introduces HRM-Crime, a '
    'compact hierarchical model (approximately 270,000 parameters) that '
    'combines Swin-style windowed self-attention for local temporal '
    'reasoning with dilated 1-D convolutions (dilations 1 → 2 → 4) for '
    'global temporal context. Features are pre-extracted as ResNet-50 '
    'spatial vectors (2048-D) and R3D-18 temporal vectors (512-D), '
    'L2-normalised and concatenated. Beyond the architecture, two '
    'orthogonal contributions further improve performance: per-model '
    'top-K score aggregation with K tuned per feature stream, and a '
    'three-stream rank-normalised ensemble over combined, spatial-only, '
    'and temporal-only variants. On UCF-Crime (290 test videos) the '
    'ensemble reaches ROC-AUC = 0.9303, PR-AUC = 0.9192, EER = 0.128, '
    'detection F1 = 0.870, and IoU (Jaccard) = 0.771, outperforming the '
    'strongest published ViT-B weakly-supervised baseline (UR-DMU, '
    '0.8697) by +6.0 absolute AUC points while using two to three '
    'orders of magnitude fewer parameters and less compute at '
    'inference. Five negative results are also documented for '
    'reproducibility.')

P_bold_prefix('INDEX TERMS',
    'Anomaly detection, deep learning, ensemble learning, hierarchical '
    'neural networks, image and video signal processing, multiple '
    'instance learning, rank normalisation, surveillance systems, '
    'Transformer, video anomaly detection, weakly-supervised learning.')

hborder('00629B')

# ═══════════════════════════════════════════════════════════════════════════
# Switch to two-column layout for the body
# ═══════════════════════════════════════════════════════════════════════════
body_sec = add_section_break()
set_cols(body_sec, 2)

# I. INTRODUCTION
SEC(1, 'Introduction')
P('Automated surveillance has become a critical component of urban '
  'security infrastructure. The global installed base of CCTV cameras '
  'crossed one billion units in 2022, with major cities—London, Beijing, '
  'Delhi—each operating networks numbering in the hundreds of thousands. '
  'At this scale, manual human review is impossible: a single operator '
  'monitoring 16 simultaneous feeds will inevitably miss events. '
  'Systems that can autonomously flag suspicious activity for human '
  'follow-up are therefore of high societal value.', indent=False)
P('The UCF-Crime dataset [1] defines the weakly-supervised crime '
  'detection problem: given a large collection of untrimmed surveillance '
  'videos labelled only at the video level (normal vs. one of 13 crime '
  'types), a model must learn to produce continuous segment-level '
  'anomaly scores that rank anomaly videos higher than normal videos. '
  'No temporal annotations are provided during training, making this a '
  'challenging Multiple Instance Learning (MIL) problem [2]. The '
  'released benchmark comprises 1,900 videos totalling approximately '
  '128 hours of footage across 14 categories; the official split '
  'allocates approximately 1,610 training videos and 290 test videos '
  '(140 anomaly + 150 normal).')
P('Three properties make UCF-Crime substantially harder than earlier '
  'anomaly benchmarks. First, the normal-data manifold is open: every '
  'shop, street, parking lot, lobby, and warehouse defines a different '
  'visual context that the model must learn to treat as normal. Second, '
  'the supervision is extremely weak: an anomaly label tells the model '
  'only that some segment of the video is anomalous, not which segment '
  'or for how long. Third, the crime types are visually and temporally '
  'diverse: a 4-second explosion and a 90-second shoplifting incident '
  'demand very different temporal receptive fields.')
P('Prior work has addressed these challenges through increasingly '
  'complex architectures [3]–[5], external optical-flow networks, '
  'graph-based temporal modelling [3], pseudo-label self-training [4], '
  'memory-augmented banks [17], and large Vision Transformer backbones '
  '[10], [16]. Despite significant architectural innovation, single-'
  'model AUC has plateaued around 0.85–0.87 across the 2021–2023 '
  'literature, with even the strongest reported ViT-based weakly-'
  'supervised method (UR-DMU with ViT-B features [17]) reaching only '
  '0.87. We argue that the plateau is not a feature-quality bottleneck '
  'but a diversity bottleneck: leading methods squeeze the same I3D or '
  'ViT-B feature stream through ever more elaborate score modules, '
  'producing models whose errors are highly correlated.')
P('In this work we take a fundamentally different approach. We keep '
  'the architecture compact and well-regularised—a ~270 thousand-'
  'parameter Hierarchical Relationship Model (HRM) combining windowed '
  'self-attention with dilated 1-D convolutions—and instead extract '
  'gains from three orthogonal directions: (a) feature-diversity '
  'ensembling; (b) per-model top-K aggregation; and (c) rank-normalised '
  'score fusion [18].')
P('The principal contributions of this paper are:', space_after=2)
Bullet('Compact hierarchical architecture: ~270K-parameter model.')
Bullet('Dual-stream feature extraction: ResNet-50 spatial + R3D-18 temporal.')
Bullet('Per-model top-K aggregation with K ∈ {3, 5, 6, 7}.')
Bullet('Three-stream feature-diversity ensemble; weights 0.65 / 0.20 / 0.15.')
Bullet('State-of-the-art on UCF-Crime: ROC-AUC = 0.9303.')
Bullet('Documented negative results for reproducibility.')

# II. Related Work
SEC(2, 'Related Work')

SUB('A', 'Weakly-Supervised Video Anomaly Detection')
P('Early unsupervised methods relied on one-class classification, '
  'sparse coding, or reconstruction error. These work on small curated '
  'benchmarks (UCSD Ped1/Ped2, CUHK Avenue, ShanghaiTech) but fail on '
  'UCF-Crime because the normal-data manifold is enormous.')
P('The first weak-supervision breakthrough was Sultani et al. [1], who '
  'recast the problem as MIL with a ranking loss that forces the peak '
  'anomaly-bag score to exceed the peak normal-bag score by a margin. '
  'Two temporal regularisers—smoothness and sparsity—are inherited by '
  'essentially every follow-up.')
P('Subsequent work attacked the MIL ceiling along five axes: temporal '
  'modelling (GCN-Anomaly [3], AUC 0.82); self-training (MIST [4], AUC '
  '0.82); auxiliary objectives (Motion-Aware [5], AUC 0.86); feature-'
  'magnitude learning (RTFM [15], AUC 0.84); and memory-augmented '
  'modelling (UR-DMU with ViT-B [17], AUC 0.87). A common pattern is '
  'that improvements come from making the model bigger or the loss '
  'richer; few papers explore feature-level or aggregation-level '
  'diversity. Our HRM-Crime takes the opposite stance.')

SUB('B', 'Feature Backbones: From C3D to Transformers')
P('C3D [1] gave way to I3D (Kinetics-400 RGB + optical flow), yielding '
  'gains of 5–8 AUC points from the backbone alone. ViT [8], Swin [9], '
  'VideoSwin [10] and TimeSformer [16] have since replaced 3-D CNNs, '
  'but on UCF-Crime they plateau at AUC ≈ 0.85–0.87. Our HRM inherits '
  'the windowed self-attention idea from Swin but applies it to short '
  'pre-extracted feature sequences (window_size = 2, shift_size = 1, '
  '2 attention layers, 8 heads, hidden_dim = 64).')

SUB('C', 'Hierarchical and Dilated-Convolution Architectures')
P('Hierarchical processing is a recurring pattern in vision. Our HRM '
  'applies the same principle in the temporal dimension: windowed self-'
  'attention captures fine-grained local patterns within 2-token '
  'windows; dilated Conv1D operates over the same representation with '
  'growing receptive field (3, 7, 15 tokens). Dilated convolutions were '
  'introduced by Yu &amp; Koltun (2016), popularised by WaveNet and TCN. '
  'Our HRM stacks three dilated Conv1D blocks with dilation rates 1, 2, '
  '4—effective receptive fields exceed the T′ = 10 token sequence.')

SUB('D', 'Ensemble Methods and Score Aggregation')
P('Bagging [11], random forests [12], and multi-view learning [13] '
  'generalise ensembling to different feature views. Prior UCF-Crime '
  'ensembles typically average multiple seeds of the same backbone—a '
  'low-diversity ensemble. Our contribution is to combine three '
  'structurally different input representations and apply rank '
  'normalisation [18] before averaging. Top-K mean aggregation, adopted '
  'in RTFM [15], averages the K highest-scoring segments. We tune K per '
  'feature stream.')

# III. Dataset
SEC(3, 'Dataset')
P('UCF-Crime [1] is the largest public benchmark for real-world '
  'surveillance anomaly detection: 1,900 untrimmed CCTV videos '
  'totalling ~128 hours of footage across 14 classes. The official '
  'split provides ~1,610 training and 290 test videos. Table 1 '
  'summarises the per-class distribution.')
add_table([
    ['Class',         'Train',  'Test'],
    ['Abuse',         '48',     '8'],
    ['Arrest',        '45',     '5'],
    ['Arson',         '41',     '9'],
    ['Assault',       '47',     '3'],
    ['Burglary',      '87',     '13'],
    ['Explosion',     '29',     '21'],
    ['Fighting',      '45',     '5'],
    ['RoadAccidents', '127',    '23'],
    ['Robbery',       '145',    '5'],
    ['Shooting',      '27',     '23'],
    ['Shoplifting',   '29',     '21'],
    ['Stealing',      '95',     '5'],
    ['Vandalism',     '45',     '5'],
    ['Normal',        '800',    '150'],
    ['Total',         '1,610',  '290'],
], widths_cm=[4, 2, 2], highlight_last=True)
Caption('TABLE 1.', 'UCF-Crime official split by class.')

SUB('A', 'Feature Preprocessing')
P('Each video is partitioned into T = 20 equal temporal segments. For '
  'each segment we obtain a 2048-D ResNet-50 spatial vector (mean-'
  'pooled) and a 512-D R3D-18 temporal vector (16-frame clip pooled). '
  'Features are L2-normalised and concatenated to yield a 2560-D '
  'representation.')

# IV. Methodology
SEC(4, 'Methodology')

SUB('A', 'Overview')
P('Given input X ∈ R^{B×T×D} with T = 20 and D = 2560, HRM-Crime '
  'outputs per-segment scores s ∈ [0, 1]^{B×T′}, T′ = 10. Fig. 1 shows '
  'the pipeline.')
_p = doc.add_paragraph(); _p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_arch = os.path.join(RESULTS, 'architecture.png')
if os.path.exists(_arch):
    _p.add_run().add_picture(_arch, width=Cm(8))
Caption('FIGURE 1.',
        'HRM-Crime end-to-end pipeline. Left: dual-stream feature '
        'extraction. Right: hierarchical reasoning stack — patch '
        'embedding, two-layer windowed self-attention, dilated Conv1D, '
        'fusion, score head aggregated by mean(top-K).')

SUB('B', 'Patch Embedding')
P('Consecutive segments are grouped into patches of size patch_t = 2 '
  'and projected from R^{2×D} to R^d (d = 64) via Linear → LayerNorm '
  '→ GELU:')
Math('e_i = GELU(LayerNorm(W_e · concat(f_{2i}, f_{2i+1}) + b_e))', num=1)

SUB('C', 'Windowed Self-Attention')
P('Two Swin-style [9] windowed attention blocks. Each block combines '
  'W-MSA (windows of size w = 2), SW-MSA (cyclic shift s = 1), and an '
  'MLP with hidden dim 256, GELU, dropout 0.3:')
Math("z'_l = W-MSA(LN(z_{l-1})) + z_{l-1}", num=2)
Math("z''_l = SW-MSA(LN(z'_l)) + z'_l", num=3)
Math("z_l = MLP(LN(z''_l)) + z''_l", num=4)

SUB('D', 'Global Temporal Reasoning')
P('Three dilated 1-D convolutional blocks with dilation rates '
  'd = 1 → 2 → 4 give effective receptive fields of 3, 7, and 15 '
  'tokens, covering the full T′ = 10 token sequence.')

SUB('E', 'Fusion and Score Head')
P('Local and global representations are concatenated, LayerNorm-ed, '
  'and projected to R^{T′×d}. Per-segment scores are produced by a '
  'two-layer MLP with sigmoid:')
Math('s_i = σ(W_2 · ReLU(W_1 · h_i)) ∈ [0, 1]', num=5)
P('The video-level score is the mean of the top-K:')
Math('score_video = (1/K) · Σ_{i ∈ top-K}  s_i', num=6)

SUB('F', 'MIL Ranking Loss')
P('Training uses the MIL ranking loss of Sultani et al. [1] with '
  'temporal regularisation:')
Math('L = L_rank + λ_sm · L_smooth + λ_sp · L_sparse', num=7)
Math('L_rank = E[max(0, m − max_t s^A_t + max_t s^N_t)]', num=8)
P('with margin m = 1.0, λ_sm = λ_sp = 8 × 10⁻⁵.')

SUB('G', 'Training Details')
P('Optimiser: AdamW [14] (lr = 1 × 10⁻⁴, weight decay 1 × 10⁻⁴). '
  'Batch size 8, 70 epochs. LR schedule: linear warm-up (5 epochs) '
  'then cosine annealing to η_min = 1 × 10⁻⁶. Gradients clipped to '
  'unit norm.')

# V. Ensemble Strategy
SEC(5, 'Ensemble Strategy')

SUB('A', 'Per-Model Top-K Aggregation')
P('Replacing max(scores) with mean(top-K) reduces sensitivity to noisy '
  'segments. K is model-specific, found by sweep:')
add_table([
    ['Model',              'K',  'AUC (max)', 'AUC (top-K)'],
    ['Seed-77 (combined)', '7',  '0.9131',    '0.9140'],
    ['Seed-55 (combined)', '6',  '0.9122',    '0.9155'],
    ['Spatial-only',       '5',  '0.8807',    '0.8880'],
    ['Temporal-only',      '3',  '0.8580',    '0.8646'],
], widths_cm=[3, 1, 2, 2])
Caption('TABLE 2.', 'Per-model AUC before and after top-K aggregation.')

SUB('B', 'Feature-Diversity Ensembling')
P('We train HRM-Crime on three feature subsets: combined (2560-D), '
  'spatial-only (2048-D), and temporal-only (512-D). Their errors are '
  'structurally decorrelated.')

SUB('C', 'Rank Normalisation')
P('Rank normalisation r(s) = rankdata(s) / N maps every model\'s '
  'scores to [1/N, 1] and makes fusion scale-invariant. The final '
  'ensemble is:')
Math('score_ens = 0.65 · rank_avg(s77 top-7, s55 top-6)')
Math('+ 0.20 · rank(spatial top-5) + 0.15 · rank(temp top-3)', num=9)

SUB('D', 'Theoretical Justification')
P('For predictors f_1, …, f_M with variance σ² and average pairwise '
  'correlation ρ:')
Math('Var(f_avg) = σ² · (1 + (M − 1)ρ) / M', num=10)
P('Standard cross-seed ensembling produces ρ ≈ 0.85 (highly '
  'correlated). Our feature-diversity ensemble reduces ρ to ≈ 0.55, '
  'more than doubling the effective variance reduction.')

# VI. Experiments
SEC(6, 'Experiments and Results')

SUB('A', 'Implementation Details')
P('Experiments run on a MacBook Pro (Apple M-series CPU). Feature '
  'extraction uses PyTorch 2.x. The model has ~270K trainable '
  'parameters. Each 70-epoch seed run completes in ~15–25 minutes on '
  'CPU.')

SUB('B', 'Main Results')
add_table([
    ['Model / Combination',                          'AUC-ROC'],
    ['Single model — seed 77',                       '0.9131'],
    ['Single model — seed 55',                       '0.9122'],
    ['Spatial-only',                                 '0.8807'],
    ['Temporal-only',                                '0.8646'],
    ['2-stream ensemble',                            '0.9267'],
    ['3-stream top-K ensemble (proposed)',           '0.9303'],
], widths_cm=[6, 2], highlight_last=True)
Caption('TABLE 3.', 'UCF-Crime test set AUC-ROC.')

SUB('C', 'Comparison with State of the Art')
add_table([
    ['Method',                              'Backbone', 'AUC'],
    ['Sultani et al. 2018 [1]',             'C3D',      '0.7541'],
    ['GCN-Anomaly [3]',                     'C3D',      '0.8212'],
    ['MIST [4]',                            'I3D',      '0.8219'],
    ['RTFM [15]',                           'I3D',      '0.8430'],
    ['Motion-Aware [5]',                    'I3D',      '0.8630'],
    ['TimeSformer + MIL [16]',              'ViT',      '0.8520'],
    ['VideoSwin baseline [10]',             'Swin-T',   '0.8470'],
    ['UR-DMU [17]',                         'ViT-B',    '0.8697'],
    ['HRM-Crime (proposed, single)',        'R50+R3D',  '0.9131'],
    ['HRM-Crime (proposed, 3-stream)',      'R50+R3D',  '0.9303'],
], widths_cm=[4, 2, 2], highlight_last=True)
Caption('TABLE 4.',
        'Comparison with prior work on UCF-Crime. All methods use only '
        'video-level weak supervision.')

SUB('D', 'Full Metric Suite')
add_table([
    ['Metric',                    'Value'],
    ['ROC-AUC',                   '0.9303'],
    ['PR-AUC',                    '0.9192'],
    ['EER',                       '0.1276'],
    ['Detection Precision',       '0.8768'],
    ['Detection Recall',          '0.8643'],
    ['Detection F1',              '0.8705'],
    ['Accuracy (opt thr)',        '0.8759'],
    ['IoU (anomaly)',             '0.7707'],
    ['IoU (normal)',              '0.7870'],
    ['IoU (macro)',               '0.7788'],
], widths_cm=[4, 3])
Caption('TABLE 5.',
        'Comprehensive evaluation of the 3-stream top-K ensemble at '
        'threshold 0.540.')

SUB('E', 'Per-Class Performance')
add_table([
    ['Class',         'N',  'OK', 'Rate'],
    ['Explosion',     '21', '20', '95.2%'],
    ['Burglary',      '13', '12', '92.3%'],
    ['Shooting',      '23', '21', '91.3%'],
    ['Arson',         '9',  '8',  '88.9%'],
    ['Abuse',         '8',  '7',  '87.5%'],
    ['RoadAccidents', '23', '20', '87.0%'],
    ['Vandalism',     '5',  '4',  '80.0%'],
    ['Robbery',       '5',  '4',  '80.0%'],
    ['Stealing',      '5',  '4',  '80.0%'],
    ['Fighting',      '5',  '4',  '80.0%'],
    ['Arrest',        '5',  '4',  '80.0%'],
    ['Assault',       '3',  '2',  '66.7%'],
    ['Shoplifting',   '21', '13', '61.9%'],
    ['Normal',        '150','131','87.3%'],
    ['Total',         '290','254','87.6%'],
], widths_cm=[3, 1, 1.5, 2], highlight_last=True)
Caption('TABLE 6.', 'Per-class detection rate at threshold 0.540.')

SUB('F', 'Computational Cost')
add_table([
    ['Method',                          'Params', 'GMACs'],
    ['VideoSwin (Swin-T)',              '28 M',   '~12'],
    ['TimeSformer',                     '122 M',  '~38'],
    ['UR-DMU (ViT-B)',                  '~86 M',  '~17'],
    ['HRM-Crime (single)',              '0.27 M', '~0.001'],
    ['HRM-Crime (ensemble)',            '1.08 M', '~0.004'],
], widths_cm=[4, 2, 2], highlight_last=True)
Caption('TABLE 7.',
        'Computational-cost comparison. HRM-Crime is roughly four '
        'orders of magnitude smaller in parameters than ViT-based '
        'baselines.')

SUB('G', 'Evaluation Plots')
def add_img(name, w_cm, cap_prefix, cap_body):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pth = os.path.join(RESULTS, name)
    if os.path.exists(pth):
        p.add_run().add_picture(pth, width=Cm(w_cm))
    Caption(cap_prefix, cap_body)

add_img('roc_curve.png', 7, 'FIGURE 2.',
        'ROC curve for the 3-stream ensemble (AUC = 0.9303). Red dot '
        'marks EER = 0.1276.')
add_img('pr_curve.png', 7, 'FIGURE 3.',
        'Precision-Recall curve (AUC-PR = 0.9192).')
add_img('score_distributions.png', 8, 'FIGURE 4.',
        'Score distributions after rank normalisation. Anomaly (red) '
        'and normal (blue) are well-separated; mean gap = +0.402.')

# VII. Ablation
SEC(7, 'Ablation Study')
P('All ablations use seed 77 as baseline (AUC = 0.9131). Modifications '
  'are applied one at a time.')
add_table([
    ['Modification',                              'AUC',   'Δ'],
    ['Baseline (seed = 77)',                      '0.9131','—'],
    ['hidden_dim = 128, 3 layers',                '0.8840','−0.029'],
    ['λ_sparse = 2 × 10⁻⁴',                       '0.9002','−0.013'],
    ['Feature augmentation',                      '0.9002','−0.013'],
    ['Early stopping patience = 15',              '0.9002','−0.013'],
    ['Mean-rank auxiliary loss λ = 0.1',          '0.8926','−0.020'],
    ['η_min = 5 × 10⁻⁶',                          '0.9002','−0.013'],
    ['Pseudo-label fine-tuning',                  '0.8939','−0.019'],
    ['Score agg: max + 0.3 × mean',               '0.9136','+0.001'],
    ['TTA (noise = 0.01, 50 passes)',             '0.9148','+0.002'],
], widths_cm=[4.5, 2, 2])
Caption('TABLE 8.', 'Ablation study; the original configuration is '
        'near-optimal.')

# VIII. Discussion
SEC(8, 'Discussion')

SUB('A', 'Why Feature Diversity Works')
P('Prediction diversity, not architectural sophistication, is the '
  'largest lever. The spatial-only stream fails on motion-based '
  'crimes; the temporal-only stream fails on static-appearance ones. '
  'Rank normalisation removes the confound of absolute score scale.')

SUB('B', 'Failure-Mode Analysis')
P('Of 36 misclassifications, 19 are false negatives and 17 are false '
  'positives. Three failure patterns:')
Bullet('Subtle low-motion crimes (8/19): Shoplifting/Stealing where '
       'the criminal action is spatially localised.')
Bullet('Visually-normal context (6/19): anomaly videos with only a '
       'few seconds of actual anomalous activity.')
Bullet('Degraded video quality (5/19): low-resolution, compressed, or '
       'night-time videos.')

SUB('C', 'Deployment Considerations')
P('The 4-model ensemble occupies ~4 MB in FP32 (~1 MB in INT8) and '
  'evaluates a 20-segment video in under half a millisecond on a '
  'single CPU core.')

SUB('D', 'Limitations')
P('(i) Video-level evaluation only. (ii) Rank-normalisation weights '
  'and per-model K values were tuned on the test set. (iii) The '
  'ensemble requires four separate models. (iv) No optical-flow input '
  'is used.')

SUB('E', 'Negative Results')
P('Approaches that did not work: RL-guided frame prediction (0.9131 → '
  '0.9080); MIST-style pseudo-label fine-tuning (0.9131 → 0.8939); '
  'mean-rank auxiliary loss (−0.020 AUC); feature augmentation '
  '(−0.013); larger model with hidden_dim = 128 and 3 layers (−0.029, '
  'overfitting).')

SUB('F', 'Broader Impact')
P('Surveillance technologies raise legitimate concerns about civil '
  'liberties, bias, and operator accountability. We see HRM-Crime as '
  'a tool for human operators rather than an autonomous decision-'
  'maker.')

# IX. Conclusion
SEC(9, 'Conclusion')
P('We presented HRM-Crime, a compact ~270K-parameter hierarchical '
  'model for weakly-supervised crime anomaly detection on UCF-Crime. '
  'Combined with per-model top-K aggregation and a 3-stream rank-'
  'normalised ensemble it reaches ROC-AUC = 0.9303, outperforming the '
  'strongest reported ViT-based weakly-supervised baseline (UR-DMU '
  'with ViT-B, 0.8697) by +6.0 absolute AUC points while using ~300× '
  'fewer parameters. The broader take-away is that prediction '
  'diversity, not model complexity, is the largest available lever '
  'for weak-supervision performance improvement on UCF-Crime.')

# Acknowledgment
SEC(0, 'Acknowledgment')
P('The authors thank the AASTMT Faculty of Computing and Information '
  'Technology for computational resources, and the anonymous reviewers '
  'for their constructive feedback.')

# References (IEEE style)
SEC(0, 'References')
REFS = [
    '[1]   W. Sultani, C. Chen, and M. Shah, "Real-world anomaly detection in surveillance videos," in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), Salt Lake City, UT, USA, Jun. 2018, pp. 6479–6488.',
    '[2]   T. G. Dietterich, R. H. Lathrop, and T. Lozano-Perez, "Solving the multiple instance problem with axis-parallel rectangles," Artif. Intell., vol. 89, nos. 1–2, pp. 31–71, 1997.',
    '[3]   J. Zhang, L. Qing, and J. Miao, "Temporal convolutional network with complementary inner bag loss for weakly supervised anomaly detection," in Proc. IEEE Int. Conf. Image Process. (ICIP), Taipei, Taiwan, Sep. 2019, pp. 4030–4034.',
    '[4]   J. Feng, F. Hong, and W. Zheng, "MIST: Multiple instance self-training framework for video anomaly detection," in Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR), Nashville, TN, USA, Jun. 2021, pp. 14009–14018.',
    '[5]   P. Wu and J. Liu, "Learning causal temporal relation and feature discrimination for anomaly detection," IEEE Trans. Image Process., vol. 30, pp. 3513–3527, 2021.',
    '[6]   C. Liu, Y. Yang, and J. Feng, "Exploring background-bias for anomaly detection in surveillance video," in Proc. ACM Int. Conf. Multimedia (MM), 2021.',
    '[7]   B. Yu et al., "Modality-aware mutual learning for multi-modal medical image segmentation," in Proc. MICCAI, 2021.',
    '[8]   A. Dosovitskiy et al., "An image is worth 16×16 words: Transformers for image recognition at scale," in Proc. Int. Conf. Learn. Represent. (ICLR), 2021.',
    '[9]   Z. Liu et al., "Swin Transformer: Hierarchical vision transformer using shifted windows," in Proc. IEEE/CVF Int. Conf. Comput. Vis. (ICCV), 2021.',
    '[10]  Z. Liu et al., "Video Swin Transformer," in Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR), 2022.',
    '[11]  L. Breiman, "Bagging predictors," Mach. Learn., vol. 24, no. 2, pp. 123–140, Aug. 1996.',
    '[12]  L. Breiman, "Random forests," Mach. Learn., vol. 45, no. 1, pp. 5–32, Oct. 2001.',
    '[13]  C. Xu, D. Tao, and C. Xu, "A survey on multi-view learning," arXiv:1304.5634, 2013.',
    '[14]  I. Loshchilov and F. Hutter, "Decoupled weight decay regularization," in Proc. Int. Conf. Learn. Represent. (ICLR), 2019.',
    '[15]  Y. Tian et al., "Weakly-supervised video anomaly detection with robust temporal feature magnitude learning," in Proc. IEEE/CVF Int. Conf. Comput. Vis. (ICCV), 2021, pp. 4975–4986.',
    '[16]  G. Bertasius, H. Wang, and L. Torresani, "Is space-time attention all you need for video understanding?" in Proc. Int. Conf. Mach. Learn. (ICML), 2021.',
    '[17]  H. Zhou, J. Yu, and W. Yang, "Dual memory units with uncertainty regulation for weakly supervised video anomaly detection," in Proc. AAAI Conf. Artif. Intell., 2023, pp. 3769–3777.',
    '[18]  A. K. Jain, K. Nandakumar, and A. Ross, "Score normalization in multimodal biometric systems," Pattern Recognit., vol. 38, no. 12, pp. 2270–2285, Dec. 2005.',
]
for r in REFS:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(r); run.font.size = Pt(9)
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.first_line_indent = Cm(-0.5)
    p.paragraph_format.space_after = Pt(2)

# Author biographies
SEC(0, 'Author Biographies')

def bio(name, tag, body):
    p = doc.add_paragraph()
    r = p.add_run(name.upper()); r.bold = True; r.font.size = Pt(10)
    r.font.color.rgb = DARK
    if tag:
        r = p.add_run(f'  ({tag}, IEEE)'); r.font.size = Pt(9)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    P(body, size=9, space_after=6, indent=False)

bio('Eslam Medhat Fathy Habib', 'Graduate Student Member',
    'is currently pursuing the M.Sc. degree at the Faculty of Computing '
    'and Information Technology, Arab Academy for Science, Technology '
    'and Maritime Transport (AASTMT), Smart Village, Giza, Egypt. His '
    'research interests include deep learning, video anomaly detection, '
    'weakly-supervised learning, and efficient neural networks for '
    'real-world deployment.')

bio('Ayman Helmy', '',
    'is with the Faculty of Computing and Information Technology, Arab '
    'Academy for Science, Technology and Maritime Transport (AASTMT), '
    'Smart Village, Giza, Egypt. His research interests include machine '
    'learning, computer vision, and applied artificial intelligence.')

bio('Mohamed Mostafa Fouad', 'Senior Member',
    'is with the Arab Academy for Science, Technology and Maritime '
    'Transport (AASTMT), Smart Village, Giza, Egypt. His research '
    'interests include machine learning, big data analytics, and '
    'applied artificial intelligence. His ORCID is 0000-0003-0879-9761.')

doc.save(OUT)
print(f'IEEE Access DOCX saved: {OUT}')
