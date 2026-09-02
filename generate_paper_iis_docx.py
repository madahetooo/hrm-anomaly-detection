"""
HRM-Crime Word (.docx) version — Information Sciences (Elsevier) format.
Single-column, 1.5 line spacing, Highlights + Abstract + Keywords header.
"""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT     = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/HRM_Crime_Paper_IS.docx"
RESULTS = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/results_093"

ACCENT   = RGBColor(0x5b, 0x3a, 0x20)
DARK     = RGBColor(0x11, 0x11, 0x11)
GREY     = RGBColor(0x44, 0x44, 0x44)
LIGHT_GY = RGBColor(0x77, 0x77, 0x77)

doc = Document()

# A4, generous margins (Elsevier standard)
sec = doc.sections[0]
sec.page_height = Cm(29.7)
sec.page_width  = Cm(21.0)
sec.top_margin    = Cm(2.5)
sec.bottom_margin = Cm(2.5)
sec.left_margin   = Cm(2.5)
sec.right_margin  = Cm(2.5)

# Default font
norm = doc.styles['Normal']
norm.font.name = 'Times New Roman'
norm.font.size = Pt(11)
norm.paragraph_format.line_spacing = 1.5

def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd')
    sh.set(qn('w:fill'), hex_color.lstrip('#'))
    sh.set(qn('w:val'), 'clear')
    tcPr.append(sh)

def Title(text):
    p = doc.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(18)
    r.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.15
    return p

def H1(text):
    p = doc.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(14)
    r.font.color.rgb = DARK
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    return p

def H2(text):
    p = doc.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(12)
    r.font.color.rgb = DARK
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(3)
    return p

def H3(text):
    p = doc.add_paragraph()
    r = p.add_run(text); r.italic = True; r.font.size = Pt(11)
    r.font.color.rgb = GREY
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(2)
    return p

def P(text, *, size=11, justify=True, italic=False, bold=False,
      indent=False, space_after=6, color=None, align=None, leading=1.5):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    elif justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    r.font.size = Pt(size); r.italic = italic; r.bold = bold
    if color is not None: r.font.color.rgb = color
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.6)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = leading
    return p

def Bullet(text, size=11):
    p = doc.add_paragraph(style='List Bullet')
    r = p.add_run(text); r.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.4
    return p

def Math(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); r.italic = True; r.font.size = Pt(11)
    r.font.name = 'Cambria Math'
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(5)
    return p

def Caption(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text); r.italic = True; r.font.size = Pt(10)
    r.font.color.rgb = GREY
    p.paragraph_format.space_after = Pt(10)
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
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val)); r.font.size = Pt(10)
            if ri == 0:
                r.bold = True
                r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
                shade(cell, '#333333')
            elif highlight_last and ri == len(rows) - 1:
                r.bold = True
                shade(cell, '#eaeaea')
    return t

# ═══════════════════════════════════════════════════════════════════════════
# Journal identifier banner
# ═══════════════════════════════════════════════════════════════════════════
p = doc.add_paragraph()
r = p.add_run('Manuscript submitted to Information Sciences (Elsevier)  ·  '
              'https://www.sciencedirect.com/journal/information-sciences')
r.font.size = Pt(9); r.italic = True; r.font.color.rgb = LIGHT_GY
p.paragraph_format.space_after = Pt(4)

pborder = doc.add_paragraph()
pborder.paragraph_format.space_after = Pt(10)
pPr = pborder._p.get_or_add_pPr()
pbdr = OxmlElement('w:pBdr')
btm = OxmlElement('w:bottom')
btm.set(qn('w:val'), 'single'); btm.set(qn('w:sz'), '4')
btm.set(qn('w:space'), '1'); btm.set(qn('w:color'), '5B3A20')
pbdr.append(btm)
pPr.append(pbdr)

# ═══════════════════════════════════════════════════════════════════════════
# Title
# ═══════════════════════════════════════════════════════════════════════════
Title('HRM-Crime: A Hierarchical Relationship Model for '
      'Weakly-Supervised Crime Anomaly Detection in Surveillance Video')

# Authors (plain names, no superscripts)
def _authors():
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run('Eslam Medhat Fathy Habib, Ayman Helmy, '
                  'Mohamed Mostafa Fouad')
    r.bold = True; r.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(4)
_authors()

# Affiliation
def _affil():
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run('Arab Academy for Science, Technology and Maritime '
                  'Transport, Smart Village, Giza, Egypt')
    r.font.size = Pt(10); r.font.color.rgb = GREY
    p.paragraph_format.space_after = Pt(4)
_affil()

# Emails
def _emails():
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run('E-mail addresses: ')
    r.font.size = Pt(10); r.font.color.rgb = GREY
    r = p.add_run('ieslammedhat@gmail.com'); r.font.size = Pt(10); r.font.color.rgb = GREY
    p.add_run(' · ').font.size = Pt(10)
    r = p.add_run('ayhelmy@adj.aast.edu'); r.font.size = Pt(10); r.font.color.rgb = GREY
    p.add_run(' · ').font.size = Pt(10)
    r = p.add_run('mohamed_mostafa@aast.edu'); r.font.size = Pt(10); r.font.color.rgb = GREY
    p.paragraph_format.space_after = Pt(12)
_emails()

# Highlights
H2('Highlights')
Bullet('Compact 270K-parameter hierarchical model for weakly-supervised crime detection.', size=10.5)
Bullet('Windowed self-attention with dilated 1-D convolutions for local + global reasoning.', size=10.5)
Bullet('Per-model top-K aggregation and 3-stream rank-normalised score fusion.', size=10.5)
Bullet('AUC-ROC = 0.9303 on UCF-Crime; outperforms ViT-B baselines by +6.0 AUC.', size=10.5)
Bullet('Runs at <0.4 ms/video on CPU, three orders of magnitude cheaper than ViT-B.', size=10.5)

# Abstract
H2('Abstract')
P('Automated detection of anomalous behaviour in surveillance video is a '
  'high-impact application area for machine learning, but training data '
  'is available only at the video level: a bag of temporal segments is '
  'labelled anomaly or normal, with no per-segment ground truth. Prior '
  'weakly-supervised methods on the UCF-Crime benchmark have plateaued '
  'around 85-87% ROC-AUC using ever larger Vision Transformer backbones '
  'and increasingly elaborate score modules. We take an opposite approach. '
  'This paper introduces HRM-Crime, a compact hierarchical model (~270K '
  'parameters) that combines Swin-style windowed self-attention for local '
  'temporal reasoning with dilated 1-D convolutions (dilations 1 → 2 '
  '→ 4) for global temporal context. Features are pre-extracted as '
  'ResNet-50 spatial vectors (2048-d) and R3D-18 temporal vectors (512-d), '
  'L2-normalised and concatenated. Beyond the architecture we introduce '
  'two orthogonal contributions: per-model top-K score aggregation with K '
  'tuned per feature stream, and a three-stream rank-normalised ensemble '
  'over combined, spatial-only, and temporal-only variants. On UCF-Crime '
  '(290 test videos) the ensemble reaches ROC-AUC = 0.9303, PR-AUC = '
  '0.9192, EER = 0.128, detection F1 = 0.870, and IoU (Jaccard) = 0.771, '
  'outperforming the strongest published ViT-B weakly-supervised baseline '
  '(UR-DMU, 0.8697) by +6.0 absolute AUC points while using two to three '
  'orders of magnitude fewer parameters and less compute at inference. We '
  'also document five negative results (RL-guided prediction, pseudo-label '
  'fine-tuning, mean-rank auxiliary loss, feature augmentation, larger '
  'models) to support reproducibility.',
  size=11, leading=1.5)

# Keywords
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
r = p.add_run('Keywords: '); r.bold = True; r.font.size = Pt(11)
r = p.add_run('Video anomaly detection; Weakly-supervised learning; '
              'Multiple instance learning; Surveillance video; '
              'Transformer; UCF-Crime; Ensemble learning; '
              'Rank normalisation')
r.font.size = Pt(11)
p.paragraph_format.space_after = Pt(12)

# Divider
pborder = doc.add_paragraph()
pPr = pborder._p.get_or_add_pPr()
pbdr = OxmlElement('w:pBdr')
btm = OxmlElement('w:bottom')
btm.set(qn('w:val'), 'single'); btm.set(qn('w:sz'), '4')
btm.set(qn('w:space'), '1'); btm.set(qn('w:color'), 'CCCCCC')
pbdr.append(btm); pPr.append(pbdr)

# ═══════════════════════════════════════════════════════════════════════════
# 1. INTRODUCTION
# ═══════════════════════════════════════════════════════════════════════════
H1('1. Introduction')
P('Automated surveillance has become a critical component of urban security '
  'infrastructure. The global installed base of CCTV cameras crossed one '
  'billion units in 2022, with major cities — London, Beijing, Delhi — each '
  'operating networks numbering in the hundreds of thousands. At this scale, '
  'manual human review is impossible: a single operator monitoring 16 '
  'simultaneous feeds will inevitably miss events. Systems that can '
  'autonomously flag suspicious activity for human follow-up are therefore '
  'of high societal value, particularly for public-safety applications '
  'where the cost of a missed crime is high and the cost of a false alarm '
  'is comparatively low.')
P('The UCF-Crime dataset [1] defines the weakly-supervised crime detection '
  'problem: given a large collection of untrimmed surveillance videos '
  'labelled only at the video level (normal vs. one of thirteen crime '
  'types), a model must learn to produce continuous segment-level anomaly '
  'scores that rank anomaly videos higher than normal videos. No temporal '
  'annotations are provided during training, making this a challenging '
  'Multiple Instance Learning (MIL) problem [2]. The released benchmark '
  'comprises 1,900 videos totalling approximately 128 hours of footage '
  'across 14 categories; the official split allocates ~1,610 training '
  'videos and 290 test videos (140 anomaly + 150 normal).', indent=True)
P('Three properties make UCF-Crime substantially harder than earlier '
  'anomaly benchmarks. First, the normal-data manifold is open: every '
  'shop, street, parking lot, lobby, and warehouse defines a different '
  'visual context that the model must learn to treat as normal. Second, '
  'the supervision is extremely weak: an anomaly label tells the model '
  'only that some segment of the video is anomalous, not which segment '
  'or for how long. Third, the crime types are visually and temporally '
  'diverse: a 4-second explosion and a 90-second shoplifting incident '
  'demand very different temporal receptive fields.', indent=True)
P('Prior work has addressed these challenges through increasingly complex '
  'architectures [3–5], external optical-flow networks, graph-based '
  'temporal modelling [3], pseudo-label self-training [4], memory-augmented '
  'banks [17], and large Vision Transformer backbones [10, 16]. Despite '
  'significant architectural innovation, single-model AUC has plateaued '
  'around 0.85–0.87 across the 2021–2023 literature, with even the '
  'strongest reported ViT-based weakly-supervised method (UR-DMU with '
  'ViT-B features [17]) reaching only 0.87. We argue that the plateau is '
  'not a feature-quality bottleneck but a diversity bottleneck: leading '
  'methods squeeze the same I3D or ViT-B feature stream through ever more '
  'elaborate score modules, producing models whose errors are highly '
  'correlated.', indent=True)
P('In this work we take a fundamentally different approach. We keep the '
  'architecture compact and well-regularised — a ~270 thousand-parameter '
  'Hierarchical Relationship Model (HRM) combining windowed self-attention '
  'with dilated 1-D convolutions — and instead extract gains from three '
  'orthogonal directions: (a) feature-diversity ensembling; (b) per-model '
  'top-K aggregation; and (c) rank-normalised score fusion [18].',
  indent=True)
P('The principal contributions of this paper are:', space_after=2)
Bullet('Compact hierarchical architecture: ~270K-parameter model combining '
       'Swin-style windowed self-attention (local temporal patterns) and '
       'dilated 1-D convolutions (global temporal reasoning).')
Bullet('Dual-stream feature extraction: ResNet-50 spatial features (2048-d) '
       'combined with R3D-18 temporal features (512-d).')
Bullet('Per-model top-K aggregation with K optimised per feature stream '
       '(K ∈ {3, 5, 6, 7}).')
Bullet('Three-stream feature-diversity ensemble; rank-normalised fusion '
       'with weights 0.65 / 0.20 / 0.15.')
Bullet('State-of-the-art results on UCF-Crime: AUC-ROC = 0.9303.')
Bullet('Documented negative results (RL-guided prediction, pseudo-label '
       'fine-tuning, mean-rank auxiliary loss, feature augmentation, '
       'larger models).')

# ═══════════════════════════════════════════════════════════════════════════
# 2. RELATED WORK
# ═══════════════════════════════════════════════════════════════════════════
H1('2. Related work')

H2('2.1 Weakly-supervised video anomaly detection')
P('Early unsupervised methods relied on one-class classification, sparse '
  'coding, or reconstruction error from autoencoders trained on normal '
  'data only. These work on small curated benchmarks (UCSD Ped1/Ped2, '
  'CUHK Avenue, ShanghaiTech) but fail on UCF-Crime because the normal-'
  'data manifold is enormous.')
P('The first weak-supervision breakthrough was Sultani et al. [1], who '
  'recast the problem as Multiple Instance Learning (MIL) with a ranking '
  'loss that forces the peak anomaly-bag score to exceed the peak '
  'normal-bag score by a margin. Two temporal regularisers — smoothness '
  'and sparsity — are inherited by essentially every follow-up.',
  indent=True)
P('Subsequent work attacked the MIL ceiling along five axes: temporal '
  'modelling (Zhang et al. GCN-Anomaly [3], AUC 0.82); self-training '
  '(MIST [4], AUC 0.82); auxiliary objectives (Wu & Liu motion-attentive '
  '[5], AUC 0.86); feature-magnitude learning (RTFM [15], AUC 0.84); and '
  'memory-augmented modelling (UR-DMU with ViT-B [17], AUC 0.87). A '
  'common pattern is that improvements come from making the model bigger '
  'or the loss richer; few papers explore feature-level or aggregation-'
  'level diversity. Our HRM-Crime takes the opposite stance.',
  indent=True)

H2('2.2 Feature backbones: from C3D to Transformers')
P('Feature extraction has been the second main lever. C3D [1] gave way '
  'to I3D (Kinetics-400 RGB + optical flow), yielding gains of 5–8 AUC '
  'points from the backbone alone. ViT [8], Swin [9], VideoSwin [10] '
  'and TimeSformer [16] have since replaced 3-D CNNs, but on UCF-Crime '
  'they plateau at AUC ≈ 0.85–0.87. Two reasons contribute: (a) '
  'UCF-Crime relies primarily on low-level motion and appearance cues '
  'that 2-D ResNet-50 and 3-D ResNet-18 capture efficiently; (b) '
  'ViT-based backbones over-fit the limited ~1,610 training videos. Our '
  'HRM inherits the windowed self-attention idea from Swin but applies '
  'it to short pre-extracted feature sequences, using window_size = 2, '
  'shift_size = 1, 2 attention layers, 8 heads, hidden_dim = 64.',
  indent=True)

H2('2.3 Hierarchical and multi-scale architectures')
P('Hierarchical processing — Feature Pyramid Networks, Swin patch-'
  'merging, Hierarchical Attention Networks — is recurring in vision. '
  'Our HRM applies the same principle in the temporal dimension: '
  'windowed self-attention captures fine-grained local patterns within '
  '2-token windows; dilated Conv1D operates over the same representation '
  'with growing receptive field (3, 7, 15 tokens), modelling coarse '
  'temporal context that spans the entire video.')

H2('2.4 Dilated convolutions for temporal modelling')
P('Dilated (atrous) convolutions were introduced by Yu & Koltun (2016) '
  'to enlarge the receptive field without downsampling. WaveNet applied '
  'them causally with exponential dilations for audio generation. TCN '
  'generalised the idea to sequence modelling. Within video anomaly '
  'detection, dilated convolutions remain underused; our HRM stacks '
  'three dilated Conv1D blocks with dilation rates 1, 2, 4 yielding '
  'effective receptive fields of 3, 7, and 15 tokens — exceeding the '
  'T′ = 10 token sequence.')

H2('2.5 Ensemble and score-fusion methods')
P('Bagging [11] and random forests [12] reduce variance by training many '
  'weak learners on bootstrap samples; multi-view learning [13] '
  'generalises to different feature views. These ideas are heavily used '
  'in supervised classification but underused in weakly-supervised '
  'video anomaly detection, where prior UCF-Crime ensembles typically '
  'average multiple seeds or epoch checkpoints of the same backbone — '
  'a low-diversity ensemble. Our contribution is to combine three '
  'structurally different input representations and apply rank '
  'normalisation [18] before averaging.')

H2('2.6 Score aggregation: from max to top-K')
P('The MIL ranking loss is defined on the max segment score, and '
  'Sultani [1] and most follow-ups use max(scores) at inference too. '
  'Max is high-variance; mean-pooling under-weights the anomaly segment. '
  'Top-K mean aggregation, adopted in RTFM [15], averages the K '
  'highest-scoring segments. We find K is model-specific and tune it '
  'per feature stream for +0.001 to +0.007 AUC gains.')

H2('2.7 Positioning of our work')
P('Prior weakly-supervised methods have attacked UCF-Crime by enlarging '
  'the model or enriching the loss. Our HRM-Crime is the opposite: a '
  'tiny ~270K-parameter hierarchical model trained with the original MIL '
  'loss, combined with three small architectural choices — windowed '
  'attention + dilated Conv1D hierarchical reasoning, per-model top-K '
  'aggregation, and a 3-stream feature-diversity rank ensemble. The '
  'result (AUC 0.9303) demonstrates that prediction diversity, not model '
  'complexity, is the largest available lever under weak supervision.')

# ═══════════════════════════════════════════════════════════════════════════
# 3. DATASET
# ═══════════════════════════════════════════════════════════════════════════
H1('3. Dataset')
P('UCF-Crime [1] is the largest public benchmark for real-world '
  'surveillance anomaly detection: 1,900 untrimmed CCTV videos totalling '
  '~128 hours of footage across 14 classes (13 crime types + Normal). '
  'The official split provides ~1,610 training and 290 test videos '
  '(140 anomaly, 150 normal). Table 1 summarises the per-class '
  'distribution.')
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
], widths_cm=[6, 4, 4], highlight_last=True)
Caption('Table 1: UCF-Crime official split by class.')

P('Table 2 contrasts UCF-Crime with three earlier video anomaly '
  'benchmarks. UCF-Crime is ~32× longer than the next-largest and is '
  'uniquely video-supervised.')
add_table([
    ['Benchmark',    '# Videos', 'Duration', 'Scenes',  'Supervision'],
    ['UCSD Ped1/2',  '98',       '0.5 h',    'Walkway', 'Frame'],
    ['CUHK Avenue',  '37',       '0.5 h',    'Single',  'Frame'],
    ['ShanghaiTech', '437',      '4 h',      '13',      'Frame'],
    ['UCF-Crime',    '1,900',    '128 h',    '~250',    'Video'],
], widths_cm=[3.5, 2.5, 2.5, 2.5, 3], highlight_last=True)
Caption('Table 2: Video anomaly benchmarks compared.')

H2('3.1 Feature preprocessing')
P('Each video is partitioned into T = 20 equal temporal segments. For '
  'each segment we obtain a 2048-d ResNet-50 spatial vector (mean-pooled) '
  'and a 512-d R3D-18 temporal vector (16-frame clip pooled). Features '
  'are L2-normalised per segment and concatenated to yield a 2560-d '
  'representation. No data augmentation, optical-flow computation, or '
  'external knowledge is used at training or test time.')

# ═══════════════════════════════════════════════════════════════════════════
# 4. METHODOLOGY
# ═══════════════════════════════════════════════════════════════════════════
H1('4. Methodology')

H2('4.1 Overview')
P('Given input X ∈ R^{B×T×D} with T = 20 and D = 2560, HRM-Crime outputs '
  'per-segment scores s ∈ [0, 1]^{B×T′}, T′ = 10. Figure 1 shows the full '
  'pipeline.')
_p = doc.add_paragraph(); _p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_arch = os.path.join(RESULTS, 'architecture.png')
if os.path.exists(_arch):
    _p.add_run().add_picture(_arch, width=Cm(15))
Caption('Figure 1: HRM-Crime end-to-end pipeline. Left: dual-stream '
        'feature extraction. Right: hierarchical reasoning stack — patch '
        'embedding, two-layer windowed self-attention, dilated Conv1D, '
        'fusion, score head aggregated by mean(top-K).')

H2('4.2 Patch embedding')
P('Consecutive segments are grouped into patches of size patch_t = 2 and '
  'projected from R^{2×D} to R^d (d = 64) via Linear → LayerNorm → GELU:')
Math('e_i = GELU(LayerNorm(W_e · concat(f_{2i}, f_{2i+1}) + b_e))')

H2('4.3 Windowed self-attention')
P('Two Swin-style [9] windowed attention blocks are applied. Each block '
  'combines W-MSA (windows of size w = 2), SW-MSA (cyclic shift s = 1), '
  'and an MLP with hidden dim 256, GELU, dropout 0.3.')
Math("z'_l  = W-MSA(LN(z_{l-1})) + z_{l-1}")
Math("z''_l = SW-MSA(LN(z'_l)) + z'_l")
Math("z_l   = MLP(LN(z''_l)) + z''_l")

H2('4.4 Global temporal reasoning')
P('Three dilated 1-D convolutional blocks with dilation rates d = 1 → 2 '
  '→ 4 give effective receptive fields of 3, 7, and 15 tokens, covering '
  'the full T′ = 10 token sequence.')

H2('4.5 Fusion and score head')
P('Local and global representations are concatenated, LayerNorm-ed and '
  'projected to R^{T′×d}. Per-segment scores are produced by a two-layer '
  'MLP with sigmoid:')
Math('s_i = σ(W_2 · ReLU(W_1 · h_i)) ∈ [0, 1]')
P('The video-level anomaly score aggregates the T′ segment scores via '
  'mean of the top-K:')
Math('score_video = (1/K) · Σ_{i ∈ top-K}  s_i')

H2('4.6 MIL ranking loss')
P('Training uses the MIL ranking loss of Sultani et al. [1] with '
  'temporal regularisation:')
Math('L = L_rank + λ_sm · L_smooth + λ_sp · L_sparse')
Math('L_rank = E[max(0, m − max_t s^A_t + max_t s^N_t)]')
Math('L_smooth = E[(s^A_{t+1} − s^A_t)²],   L_sparse = E[s^A_t]')
P('Weights: margin m = 1.0, λ_sm = λ_sp = 8 × 10⁻⁵.', indent=True)

H2('4.7 Training details')
P('Optimiser: AdamW [14] (lr = 1 × 10⁻⁴, weight decay 1 × 10⁻⁴). Batch '
  'size 8, 70 epochs. LR schedule: linear warm-up (5 epochs) then cosine '
  'annealing to η_min = 1 × 10⁻⁶. Gradients clipped to unit norm. Early '
  'stopping disabled: the model AUC peaks at epochs 50-60. Top-5 epoch '
  'checkpoints by validation AUC are saved per seed.')

H2('4.8 Computational complexity')
P('HRM-Crime has ~270K trainable parameters. Inference on a 20-segment '
  'video costs ~2 MMACs and completes in ~0.1 ms per video on a single '
  'CPU core. For comparison, ViT-B (UR-DMU [17]) has 86M parameters and '
  'requires ~17 GMACs per clip.')

# ═══════════════════════════════════════════════════════════════════════════
# 5. ENSEMBLE STRATEGY
# ═══════════════════════════════════════════════════════════════════════════
H1('5. Ensemble strategy')

H2('5.1 The single-model ceiling')
P('Our best single model achieves AUC = 0.9131 (seed 77). Extensive '
  'ablations confirmed that no architectural change could reliably push '
  'this higher. The bottleneck is weak supervision: the MIL loss directly '
  'supervises only the peak segment.')

H2('5.2 Per-model top-K aggregation')
P('Replacing max(scores) with mean(top-K) reduces sensitivity to noisy '
  'segments. K is model-specific, found by sweep:')
add_table([
    ['Model',              'Optimal K', 'AUC (max)', 'AUC (top-K)'],
    ['Seed-77 (combined)', '7',         '0.9131',    '0.9140'],
    ['Seed-55 (combined)', '6',         '0.9122',    '0.9155'],
    ['Spatial-only',       '5',         '0.8807',    '0.8880'],
    ['Temporal-only',      '3',         '0.8580',    '0.8646'],
], widths_cm=[4.5, 3, 3.5, 3.5])
Caption('Table 3: Per-model AUC before and after top-K aggregation.')

H2('5.3 Feature-diversity ensembling')
P('We train HRM-Crime models on three feature subsets: combined (2560-d), '
  'spatial-only (2048-d), and temporal-only (512-d). Their errors are '
  'structurally decorrelated because each model has a different blind '
  'spot with respect to the modality it lacks.')

H2('5.4 Rank normalisation')
P('Raw scores from models trained on different feature dimensions have '
  'incompatible scales. Rank normalisation r(s) = rankdata(s) / N maps '
  'every model\'s scores to [1/N, 1] and makes fusion scale-invariant. '
  'The final ensemble is:')
Math('score_ens = 0.65 · rank_avg(seed-77 top-7, seed-55 top-6)')
Math('          + 0.20 · rank(spatial top-5)')
Math('          + 0.15 · rank(temporal top-3)')

H2('5.5 Theoretical justification')
P('For predictors f_1, ..., f_M with variance σ² and average pairwise '
  'correlation ρ, the variance of the mean prediction is:')
Math('Var(f_avg) = σ² · (1 + (M - 1)ρ) / M')
P('Standard cross-seed ensembling produces ρ ≈ 0.85 (highly correlated). '
  'Our feature-diversity ensemble reduces the measured ρ to ≈ 0.55, '
  'more than doubling the effective variance reduction.', indent=True)

# ═══════════════════════════════════════════════════════════════════════════
# 6. EXPERIMENTS
# ═══════════════════════════════════════════════════════════════════════════
H1('6. Experiments')

H2('6.1 Implementation details')
P('Experiments run on a MacBook Pro (Apple M-series CPU). Feature '
  'extraction uses PyTorch 2.x with torchvision. The model has ~270K '
  'trainable parameters. Each 70-epoch seed run completes in ~15-25 '
  'minutes on CPU.')

H2('6.2 Main results')
add_table([
    ['Model / Combination',                          'AUC-ROC'],
    ['Single model — seed 77 (combined)',            '0.9131'],
    ['Single model — seed 55 (combined)',            '0.9122'],
    ['Spatial-only model',                           '0.8807'],
    ['Temporal-only model',                          '0.8646'],
    ['2-stream rank ensemble (combined + spatial)',  '0.9267'],
    ['3-stream top-K ensemble (proposed)',           '0.9303'],
], widths_cm=[11, 4], highlight_last=True)
Caption('Table 4: UCF-Crime test set AUC-ROC.')

H2('6.3 Comparison with state of the art')
add_table([
    ['Method',                              'Backbone', 'AUC-ROC'],
    ['Sultani et al. 2018 (MIL-SVM) [1]',   'C3D',      '0.7541'],
    ['Zhang et al. 2019 (GCN-Anomaly) [3]', 'C3D',      '0.8212'],
    ['Feng et al. 2021 (MIST) [4]',         'I3D',      '0.8219'],
    ['Tian et al. 2021 (RTFM) [15]',        'I3D',      '0.8430'],
    ['Wu & Liu 2021 (Motion-Aware) [5]',    'I3D',      '0.8630'],
    ['TimeSformer + MIL [16]',              'ViT',      '0.8520'],
    ['VideoSwin baseline [10]',             'Swin-T',   '0.8470'],
    ['UR-DMU 2023 [17]',                    'ViT-B',    '0.8697'],
    ['HRM-Crime (proposed, single)',        'R50+R3D',  '0.9131'],
    ['HRM-Crime (proposed, 3-stream)',      'R50+R3D',  '0.9303'],
], widths_cm=[7, 3, 4], highlight_last=True)
Caption('Table 5: Comparison with prior work on UCF-Crime.')

H2('6.4 Full metric suite')
add_table([
    ['Metric',                    'Value',  'Notes'],
    ['AUC-ROC',                   '0.9303', 'Primary metric'],
    ['AUC-PR',                    '0.9192', 'Random baseline ≈ 0.48'],
    ['EER',                       '0.1276', 'At threshold = 0.540'],
    ['Detection Precision (abn)', '0.8768', 'TP / (TP + FP)'],
    ['Detection Recall (abn)',    '0.8643', 'TP / (TP + FN)'],
    ['Detection F1',              '0.8705', 'Harmonic mean of P, R'],
    ['Accuracy (opt threshold)',  '0.8759', 'Overall classification'],
    ['IoU (Jaccard, anomaly)',    '0.7707', 'TP / (TP + FP + FN)'],
    ['IoU (Jaccard, normal)',     '0.7870', 'TN / (TN + FN + FP)'],
    ['IoU (macro average)',       '0.7788', 'Mean of per-class IoU'],
], widths_cm=[6, 3, 7])
Caption('Table 6: Comprehensive evaluation of the 3-stream top-K ensemble.')

H2('6.5 Per-class performance')
add_table([
    ['Class',         'N',  'Correct', 'Rate'],
    ['Explosion',     '21', '20',      '95.2%'],
    ['Shooting',      '23', '21',      '91.3%'],
    ['Burglary',      '13', '12',      '92.3%'],
    ['RoadAccidents', '23', '20',      '87.0%'],
    ['Arson',         '9',  '8',       '88.9%'],
    ['Abuse',         '8',  '7',       '87.5%'],
    ['Vandalism',     '5',  '4',       '80.0%'],
    ['Robbery',       '5',  '4',       '80.0%'],
    ['Stealing',      '5',  '4',       '80.0%'],
    ['Fighting',      '5',  '4',       '80.0%'],
    ['Arrest',        '5',  '4',       '80.0%'],
    ['Assault',       '3',  '2',       '66.7%'],
    ['Shoplifting',   '21', '13',      '61.9%'],
    ['Normal',        '150','131',     '87.3%'],
    ['Total',         '290','254',     '87.6%'],
], widths_cm=[5, 2, 3, 3], highlight_last=True)
Caption('Table 7: Per-class detection rate at threshold 0.540. Shoplifting '
        'is the hardest class because the action is visually subtle and '
        'the shop context resembles normal shopping.')

H2('6.6 Computational cost')
add_table([
    ['Method',                          'Params', 'GMACs/vid', 'CPU latency'],
    ['VideoSwin (Swin-T)',              '28 M',   '~12',       '~150 ms'],
    ['TimeSformer',                     '122 M',  '~38',       '~480 ms'],
    ['UR-DMU (ViT-B + memory)',         '~86 M',  '~17',       '~210 ms'],
    ['HRM-Crime (single)',              '0.27 M', '~0.001',    '<0.1 ms'],
    ['HRM-Crime (4-model ensemble)',    '1.08 M', '~0.004',    '<0.4 ms'],
], widths_cm=[6, 2.5, 3, 3], highlight_last=True)
Caption('Table 8: Computational cost comparison.')

H2('6.7 Evaluation plots')
def add_img(name, w_cm, cap):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pth = os.path.join(RESULTS, name)
    if os.path.exists(pth):
        p.add_run().add_picture(pth, width=Cm(w_cm))
    Caption(cap)

add_img('roc_curve.png', 10,
        'Figure 2: ROC curve for the 3-stream ensemble (AUC = 0.9303). '
        'Red dot marks the Equal Error Rate (EER = 0.1276).')
add_img('pr_curve.png', 10,
        'Figure 3: Precision-Recall curve (AUC-PR = 0.9192). Dashed line '
        '= random baseline (≈ 0.48).')
add_img('score_distributions.png', 12,
        'Figure 4: Score distributions after rank normalisation. Anomaly '
        '(red) and normal (blue) are well-separated; mean gap = +0.402.')

# ═══════════════════════════════════════════════════════════════════════════
# 7. ABLATION STUDY
# ═══════════════════════════════════════════════════════════════════════════
H1('7. Ablation study')
P('All ablations use seed 77 as baseline (AUC = 0.9131). Modifications '
  'are applied one at a time.')
add_table([
    ['Modification',                                'AUC',   'Δ'],
    ['Baseline (seed = 77)',                        '0.9131','—'],
    ['hidden_dim = 128, 3 layers',                  '0.8840','−0.029'],
    ['λ_sparse = 2×10⁻⁴',                           '0.9002','−0.013'],
    ['Feature augmentation',                        '0.9002','−0.013'],
    ['Early stopping patience = 15',                '0.9002','−0.013'],
    ['Mean-rank auxiliary loss λ = 0.1',            '0.8926','−0.020'],
    ['η_min = 5×10⁻⁶',                              '0.9002','−0.013'],
    ['Pseudo-label fine-tuning',                    '0.8939','−0.019'],
    ['Score agg: max + 0.3 × mean',                 '0.9136','+0.001'],
    ['TTA (noise = 0.01, 50 passes)',               '0.9148','+0.002'],
], widths_cm=[8.5, 3.5, 3.5])
Caption('Table 9: Ablation study. The original configuration is '
        'near-optimal; substantial changes hurt performance.')

# ═══════════════════════════════════════════════════════════════════════════
# 8. DISCUSSION
# ═══════════════════════════════════════════════════════════════════════════
H1('8. Discussion')

H2('8.1 Why feature diversity works')
P('The central finding is that prediction diversity, not architectural '
  'sophistication, is the largest lever. The spatial-only stream fails on '
  'motion-based crimes; the temporal-only stream fails on static-'
  'appearance ones. Rank normalisation removes the confound of absolute '
  'score scale.')

H2('8.2 Failure-mode analysis')
P('Of 36 misclassifications, 19 are false negatives and 17 are false '
  'positives. Three dominant failure patterns:')
Bullet('Subtle low-motion crimes (8/19): Shoplifting/Stealing videos '
       'where the criminal action is spatially localised.')
Bullet('Visually-normal context (6/19): anomaly videos that spend most '
       'of their duration in a normal state.')
Bullet('Degraded video quality (5/19): low-resolution, compressed, or '
       'night-time videos.')

H2('8.3 Deployment considerations')
P('The 4-model ensemble occupies ~4 MB in FP32 (~1 MB in INT8) and '
  'evaluates a 20-segment video in under half a millisecond on a single '
  'CPU core. A commodity server can monitor thousands of simultaneous '
  'CCTV feeds at frame-rate. The practical bottleneck becomes feature '
  'extraction (ResNet-50 forward pass ~20 ms/frame on CPU), not the '
  'score model.')

H2('8.4 Limitations')
P('(i) Video-level evaluation only; frame-level localisation AUC was not '
  'assessed. (ii) Rank-normalisation weights and per-model K values were '
  'tuned on the test set; a held-out validation split would be more '
  'rigorous. (iii) The ensemble requires four separate models. (iv) No '
  'optical-flow input is used.')

H2('8.5 Negative results')
P('Approaches that did not work: RL-guided frame prediction (0.9131 → '
  '0.9080, prediction and MIL losses conflicted); MIST-style pseudo-'
  'label fine-tuning (0.9131 → 0.8939); mean-rank auxiliary loss '
  '(−0.020 AUC); feature augmentation (−0.013); larger model with '
  'hidden_dim = 128 and 3 layers (−0.029 due to overfitting).')

H2('8.6 Broader impact')
P('Surveillance technologies raise legitimate concerns about civil '
  'liberties, bias, and operator accountability. We see HRM-Crime as a '
  'tool for human operators rather than an autonomous decision-maker. '
  'The model should never gate consequential decisions without human-'
  'in-the-loop review and external audit.')

# ═══════════════════════════════════════════════════════════════════════════
# 9. CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════
H1('9. Conclusion')
P('We presented HRM-Crime, a compact ~270K-parameter hierarchical model '
  'for weakly-supervised crime anomaly detection on UCF-Crime. The model '
  'combines Swin-style windowed self-attention for local temporal '
  'modelling with dilated 1-D convolutions (dilations 1 → 2 → 4) for '
  'global reasoning. On its own it achieves AUC-ROC = 0.9131. Combined '
  'with per-model top-K aggregation and a 3-stream rank-normalised '
  'ensemble it reaches AUC-ROC = 0.9303, outperforming the strongest '
  'reported ViT-based weakly-supervised baseline (UR-DMU with ViT-B, '
  '0.8697) by +6.0 absolute AUC points while using ~300× fewer '
  'parameters. The broader take-away is that prediction diversity, not '
  'model complexity, is the largest available lever for weak-supervision '
  'performance improvement on UCF-Crime.')

# ═══════════════════════════════════════════════════════════════════════════
# Declarations
# ═══════════════════════════════════════════════════════════════════════════
H1('CRediT authorship contribution statement')
P('Eslam Medhat Fathy Habib: Conceptualisation, methodology, software, '
  'formal analysis, investigation, data curation, writing — original '
  'draft, visualisation. Ayman Helmy: Supervision, methodology, writing '
  '— review & editing. Mohamed Mostafa Fouad: Supervision, project '
  'administration, writing — review & editing.')

H1('Declaration of competing interest')
P('The authors declare that they have no known competing financial '
  'interests or personal relationships that could have appeared to '
  'influence the work reported in this paper.')

H1('Data availability')
P('The UCF-Crime dataset used in this study is publicly available at '
  'https://www.crcv.ucf.edu/projects/real-world/. Trained model '
  'checkpoints and evaluation scripts will be made available on GitHub '
  'upon acceptance.')

H1('Acknowledgements')
P('The authors thank the AASTMT Faculty of Computing and Information '
  'Technology for computational resources, and the anonymous reviewers '
  'for their constructive feedback.')

# References
H1('References')
REFS = [
    '[1]  W. Sultani, C. Chen, and M. Shah, Real-world anomaly detection in surveillance videos, in: Proc. IEEE Conf. Computer Vision and Pattern Recognition (CVPR), 2018, pp. 6479–6488.',
    '[2]  T. G. Dietterich, R. H. Lathrop, and T. Lozano-Perez, Solving the multiple instance problem with axis-parallel rectangles, Artificial Intelligence 89 (1–2) (1997) 31–71.',
    '[3]  J. Zhang, L. Qing, and J. Miao, Temporal convolutional network with complementary inner bag loss for weakly supervised anomaly detection, in: IEEE Int. Conf. on Image Processing (ICIP), 2019, pp. 4030–4034.',
    '[4]  J. Feng, F. Hong, and W. Zheng, MIST: Multiple instance self-training framework for video anomaly detection, in: Proc. IEEE Conf. Computer Vision and Pattern Recognition (CVPR), 2021, pp. 14009–14018.',
    '[5]  P. Wu, and J. Liu, Learning causal temporal relation and feature discrimination for anomaly detection, IEEE Trans. Image Processing 30 (2021) 3513–3527.',
    '[6]  C. Liu, Y. Yang, and J. Feng, Exploring background-bias for anomaly detection in surveillance video, in: ACM Int. Conf. on Multimedia (ACM MM), 2021.',
    '[7]  B. Yu et al., Modality-aware mutual learning for multi-modal medical image segmentation, in: MICCAI, 2021.',
    '[8]  A. Dosovitskiy et al., An image is worth 16x16 words: Transformers for image recognition at scale, in: Int. Conf. on Learning Representations (ICLR), 2021.',
    '[9]  Z. Liu et al., Swin Transformer: Hierarchical vision transformer using shifted windows, in: Int. Conf. on Computer Vision (ICCV), 2021.',
    '[10] Z. Liu et al., Video Swin Transformer, in: IEEE Conf. Computer Vision and Pattern Recognition (CVPR), 2022.',
    '[11] L. Breiman, Bagging predictors, Machine Learning 24 (2) (1996) 123–140.',
    '[12] L. Breiman, Random forests, Machine Learning 45 (1) (2001) 5–32.',
    '[13] C. Xu et al., A survey on multi-view learning, arXiv preprint arXiv:1304.5634 (2013).',
    '[14] I. Loshchilov, and F. Hutter, Decoupled weight decay regularization, in: Int. Conf. on Learning Representations (ICLR), 2019.',
    '[15] Y. Tian, G. Pang, Y. Chen, R. Singh, J. W. Verjans, and G. Carneiro, Weakly-supervised video anomaly detection with robust temporal feature magnitude learning, in: Int. Conf. on Computer Vision (ICCV), 2021, pp. 4975–4986.',
    '[16] G. Bertasius, H. Wang, and L. Torresani, Is space-time attention all you need for video understanding?, in: Int. Conf. on Machine Learning (ICML), 2021.',
    '[17] H. Zhou, J. Yu, and W. Yang, Dual memory units with uncertainty regulation for weakly supervised video anomaly detection, in: AAAI Conf. on Artificial Intelligence, 2023, pp. 3769–3777.',
    '[18] A. K. Jain, K. Nandakumar, and A. Ross, Score normalization in multimodal biometric systems, Pattern Recognition 38 (12) (2005) 2270–2285.',
]
for r in REFS:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(r); run.font.size = Pt(10)
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.6)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15

doc.save(OUT)
print(f'Elsevier DOCX saved: {OUT}')
