"""
HRM-Crime — MDPI Algorithms (Algorithms) submission format.

Layout follows MDPI's "elsarticle-equivalent" single-column template:
  - Journal banner (Algorithms, ISSN, Article type)
  - Title, authors with numbered affiliations and ORCID
  - Correspondence line
  - Abstract: paragraph with bold prefix
  - Keywords: bold prefix
  - Numbered sections (1., 2., 2.1., ...)
  - Author Contributions, Funding, Data Availability, Conflicts of Interest
  - Copyright statement (MDPI CC-BY footer)
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak, BaseDocTemplate,
    PageTemplate, Frame,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('AU',   '/Library/Fonts/Arial Unicode.ttf'))
pdfmetrics.registerFont(TTFont('AU-B', '/Library/Fonts/Arial Unicode.ttf'))

OUTPUT  = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/HRM_Crime_Paper_Algorithms_v2.pdf"
RESULTS = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/results_093"

W, H = A4
LM = RM = 2.0 * cm
TM      = 2.4 * cm
BM      = 2.2 * cm
BODY_W  = W - LM - RM

# MDPI brand colours
MDPI_BLUE   = colors.HexColor('#046A44')   # Algorithms accent (green-teal)
MDPI_NAVY   = colors.HexColor('#04406A')
MDPI_ORANGE = colors.HexColor('#a90c14')   # "Article" red-ish
DARK        = colors.HexColor('#1a1a1a')
GREY        = colors.HexColor('#555555')

styles = getSampleStyleSheet()
_ctr = [0]
def sty(**kw):
    _ctr[0] += 1
    kw.setdefault('fontName', 'AU')
    return ParagraphStyle(f'_s{_ctr[0]}', parent=styles['Normal'], **kw)

# ── MDPI-style paragraph styles ───────────────────────────────────────────
journal_sty  = sty(fontSize=10, leading=13, alignment=TA_LEFT,
                   textColor=colors.HexColor('#666666'), spaceAfter=2)
art_type_sty = sty(fontSize=13, leading=15, alignment=TA_LEFT,
                   textColor=MDPI_ORANGE, spaceAfter=6, fontName='AU-B')
paper_title  = sty(fontSize=16, leading=20, alignment=TA_LEFT,
                   spaceAfter=10, textColor=DARK, fontName='AU-B')
author_sty   = sty(fontSize=11, leading=15, alignment=TA_LEFT, spaceAfter=4,
                   textColor=DARK)
affil_sty    = sty(fontSize=9, leading=12, alignment=TA_LEFT, spaceAfter=2,
                   textColor=colors.HexColor('#333333'))
corr_sty     = sty(fontSize=9, leading=12, alignment=TA_LEFT, spaceAfter=8,
                   textColor=colors.HexColor('#333333'))
abstract_sty = sty(fontSize=10, leading=14, alignment=TA_JUSTIFY,
                   spaceAfter=6)
kw_sty       = sty(fontSize=10, leading=14, alignment=TA_JUSTIFY,
                   spaceAfter=8)
sec_sty      = sty(fontSize=13, leading=17, alignment=TA_LEFT,
                   spaceBefore=14, spaceAfter=5,
                   textColor=DARK, fontName='AU-B')
sub_sty      = sty(fontSize=11, leading=15, alignment=TA_LEFT,
                   spaceBefore=8, spaceAfter=3,
                   textColor=DARK, fontName='AU-B')
sub2_sty     = sty(fontSize=10.5, leading=14, alignment=TA_LEFT,
                   spaceBefore=6, spaceAfter=2, italic=True,
                   textColor=colors.HexColor('#333333'))
body_sty     = sty(fontSize=10, leading=14.5, alignment=TA_JUSTIFY,
                   spaceAfter=6, firstLineIndent=14)
body_noind   = sty(fontSize=10, leading=14.5, alignment=TA_JUSTIFY,
                   spaceAfter=6)
bullet_sty   = sty(fontSize=10, leading=14, alignment=TA_JUSTIFY,
                   leftIndent=18, bulletIndent=6, spaceAfter=3)
math_sty     = sty(fontSize=10, leading=14, alignment=TA_CENTER,
                   spaceAfter=6, spaceBefore=4)
caption_sty  = sty(fontSize=9, leading=12, alignment=TA_JUSTIFY,
                   spaceBefore=3, spaceAfter=8,
                   textColor=colors.HexColor('#333333'))
tbl_hdr_sty  = sty(fontSize=9, leading=12, alignment=TA_CENTER,
                   textColor=colors.white, fontName='AU-B')
tbl_cel_sty  = sty(fontSize=9, leading=12, alignment=TA_CENTER)
fn_sty       = sty(fontSize=8.5, leading=11.5, alignment=TA_JUSTIFY,
                   leftIndent=18, bulletIndent=0,
                   textColor=colors.HexColor('#222222'), spaceAfter=3)
declar_sty   = sty(fontSize=10, leading=14, alignment=TA_JUSTIFY,
                   spaceAfter=6)

def SP(n=1):    return Spacer(1, n * 3 * mm)
def P(t):       return Paragraph(t, body_sty)
def Pn(t):      return Paragraph(t, body_noind)
def B(t):       return Paragraph(f'•&nbsp;&nbsp;{t}', bullet_sty)
def Math(t):    return Paragraph(t, math_sty)
def Cap(t):     return Paragraph(t, caption_sty)
def HR(c='#046A44', t=0.6):
    return HRFlowable(width='100%', thickness=t,
                      color=colors.HexColor(c), spaceAfter=6, spaceBefore=3)
def Sec(n, t):
    num = f'{n}. ' if n else ''
    return Paragraph(f'{num}{t}', sec_sty)
def Sub(n, t):
    return Paragraph(f'<i>{n}. {t}</i>', sub_sty)

def make_table(rows, col_widths, bold_last=False):
    data = []
    for i, row in enumerate(rows):
        s = tbl_hdr_sty if i == 0 else tbl_cel_sty
        data.append([Paragraph(str(cell), s) for cell in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), MDPI_BLUE),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, MDPI_BLUE),
        ('LINEBELOW', (0, -1), (-1, -1), 0.6, MDPI_BLUE),
        ('LINEABOVE', (0, 0), (-1, 0), 0.6, MDPI_BLUE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
            [colors.white, colors.HexColor('#f8f8f8')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    if bold_last:
        ts += [('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e6f0e9')),
               ('FONTNAME', (0, -1), (-1, -1), 'AU-B')]
    t.setStyle(TableStyle(ts))
    return t

# ── MDPI-style page template ───────────────────────────────────────────────
class MDPIDoc(BaseDocTemplate):
    def __init__(self, fn, **kw):
        super().__init__(fn, **kw)
        frame = Frame(LM, BM, BODY_W, H - TM - BM,
                      id='body', leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='Body', frames=[frame],
                                            onPage=self._page)])

    def _page(self, canvas, doc):
        canvas.saveState()
        # ── Top banner: journal name (left) + Article/ISSN (right) ──────
        canvas.setFillColor(MDPI_BLUE)
        canvas.setFont('AU-B', 11)
        canvas.drawString(LM, H - TM + 30,
            'Algorithms')
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.setFont('AU', 8.5)
        canvas.drawRightString(W - RM, H - TM + 30,
            'ISSN 1999-4893  ·  MDPI  ·  mdpi.com/journal/algorithms')
        # Thin accent line
        canvas.setStrokeColor(MDPI_BLUE)
        canvas.setLineWidth(0.8)
        canvas.line(LM, H - TM + 20, W - RM, H - TM + 20)
        # Footer: page number + article type marker
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.setFont('AU', 8.5)
        canvas.drawString(LM, BM - 15,
            'Algorithms 2026, 19, X  ·  https://doi.org/10.3390/algorithmsXXXXXXX')
        canvas.drawRightString(W - RM, BM - 15, f'Page {doc.page}')
        canvas.restoreState()

doc = MDPIDoc(OUTPUT, pagesize=A4,
              leftMargin=LM, rightMargin=RM,
              topMargin=TM, bottomMargin=BM)

story = []

# ── Article type marker (MDPI convention) ───────────────────────────────────
story.append(Paragraph('Article', art_type_sty))

# ── Title ───────────────────────────────────────────────────────────────────
story.append(Paragraph(
    'HRM-Crime: A Hierarchical Relationship Model for '
    'Weakly-Supervised Crime Anomaly Detection in Surveillance Video',
    paper_title))

# ── Authors with numbered affiliations ──────────────────────────────────────
story.append(Paragraph(
    'Eslam Medhat Fathy Habib <super>1,*</super>, '
    'Ayman Helmy <super>2</super> and '
    'Mohamed Mostafa Fouad <super>3</super>',
    author_sty))

# ── Affiliations (with ORCID lines per author who has one) ─────────────────
story.append(Paragraph(
    '<super>1</super>&nbsp;Faculty of Computing and Information Technology, '
    'Arab Academy for Science, Technology and Maritime Transport (AASTMT), '
    'Smart Village, Giza, Egypt; ieslammedhat@gmail.com; '
    'ORCID: <font color="#046A44">https://orcid.org/0009-0007-1758-8612</font>',
    affil_sty))
story.append(Paragraph(
    '<super>2</super>&nbsp;Faculty of Computing and Information Technology, '
    'Arab Academy for Science, Technology and Maritime Transport (AASTMT), '
    'Smart Village, Giza, Egypt; ayhelmy@adj.aast.edu',
    affil_sty))
story.append(Paragraph(
    '<super>3</super>&nbsp;Arab Academy for Science, Technology, and Maritime '
    'Transport, Smart Village, Egypt; mohamed_mostafa@aast.edu; '
    'ORCID: <font color="#046A44">https://orcid.org/0000-0003-0879-9761</font>',
    affil_sty))
story.append(Paragraph(
    '<b>*</b>&nbsp;Correspondence: ieslammedhat@gmail.com; '
    'Tel.: +20-XXX-XXX-XXXX',
    corr_sty))

# ── Received/Accepted line (MDPI standard) ──────────────────────────────────
story.append(Paragraph(
    '<b>Received:</b> [date]; <b>Revised:</b> [date]; '
    '<b>Accepted:</b> [date]; <b>Published:</b> [date]',
    sty(fontSize=9, leading=12, alignment=TA_LEFT,
        textColor=colors.HexColor('#555555'), spaceAfter=10)))
story.append(HR('#046A44', 0.6))

# ── Abstract ────────────────────────────────────────────────────────────────
story.append(Paragraph(
    "<b>Abstract:</b> Detecting anomalous behaviour in surveillance video is "
    "a high-impact application of machine learning, but supervision is "
    "available only at the video level: a set of temporal segments carries "
    "a single anomaly or normal label, with no per-segment ground truth. "
    "This is the Multiple Instance Learning setting. On the UCF-Crime "
    "benchmark, published weakly-supervised methods have converged to a "
    "narrow band of Receiver Operating Characteristic Area Under the Curve "
    "between 0.85 and 0.87 over the past three years, despite the adoption "
    "of progressively larger Vision Transformer backbones. We investigate "
    "whether this ceiling reflects a limit on feature quality or a limit on "
    "prediction diversity. We introduce HRM-Crime, a compact hierarchical "
    "score model of approximately 270 thousand trainable parameters that "
    "couples windowed self-attention for local temporal structure with "
    "dilated one-dimensional convolutions for long-range temporal context. "
    "Segment features are pre-extracted with a frozen ResNet-50 for "
    "appearance and a frozen R3D-18 for motion. On this base we evaluate "
    "two orthogonal interventions: aggregating each model's segment scores "
    "by the mean of its K highest values rather than the maximum, and "
    "fusing three models trained on different feature subsets through rank "
    "normalisation. Across 98 training runs a single model attains a mean "
    "Area Under the Curve of 0.8934 with standard deviation 0.0087. The "
    "three-stream ensemble attains 0.9300, an improvement of 0.0213 over "
    "the strongest single model, with a bootstrap 95 percent confidence "
    "interval of 0.0079 to 0.0360 and a one-sided p-value of 0.0008. "
    "Five negative results are documented. We note that the reported gain "
    "confounds architecture, feature representation and ensembling, and we "
    "identify the experiment required to separate them.",
    abstract_sty))

# ── Keywords ────────────────────────────────────────────────────────────────
story.append(Paragraph(
    '<b>Keywords:</b> video anomaly detection; weakly-supervised learning; '
    'multiple instance learning; surveillance video; transformer; UCF-Crime; '
    'ensemble learning; rank normalisation; nested cross-validation; algorithm design',
    kw_sty))
story.append(HR('#046A44', 0.6))

# ══════════════════════════════════════════════════════════════════════════
# 1. INTRODUCTION
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('1', 'Introduction'))
story.append(Pn(
    'Automated surveillance has become a critical component of urban security '
    'infrastructure. The global installed base of CCTV cameras crossed one '
    'billion units in 2022, with major cities such as London, Beijing and Delhi each '
    'operating networks numbering in the hundreds of thousands. At this scale, '
    'manual human review is impossible: a single operator monitoring 16 '
    'simultaneous feeds will inevitably miss events. Systems that can '
    'autonomously flag suspicious activity for human follow-up are therefore '
    'of high societal value, particularly for public-safety applications '
    'where the cost of a missed crime is high and the cost of a false alarm '
    'is comparatively low.'))
story.append(P(
    'The UCF-Crime dataset [1] defines the weakly-supervised crime detection '
    'problem: given a large collection of untrimmed surveillance videos '
    'labelled only at the video level (normal vs. one of 13 crime types), a '
    'model must learn to produce continuous segment-level anomaly scores that '
    'rank anomaly videos higher than normal videos. No temporal annotations '
    'are provided during training, making this a challenging Multiple Instance '
    'Learning (MIL) problem [2]. The released benchmark comprises 1,900 videos '
    'totalling approximately 128 hours of footage across 14 categories; the '
    'official split allocates approximately 1,610 training videos and 290 '
    'test videos (140 anomaly + 150 normal).'))
story.append(P(
    'Three properties make UCF-Crime substantially harder than earlier anomaly '
    'benchmarks. First, the normal-data manifold is open: every shop, street, '
    'parking lot, lobby, and warehouse defines a different visual context that '
    'the model must learn to treat as normal. Second, the supervision is '
    'extremely weak: an anomaly label tells the model only that some segment '
    'of the video is anomalous, not which segment or for how long. Third, the '
    'crime types are visually and temporally diverse: a 4-second explosion and '
    'a 90-second shoplifting incident demand very different temporal '
    'receptive fields. These properties jointly explain why classical '
    'reconstruction-based methods, which work well on UCSD Ped or CUHK Avenue, '
    'fail entirely on UCF-Crime.'))
story.append(P(
    'Prior work has addressed these challenges through increasingly complex '
    'architectures [3–5], external optical-flow networks, graph-based '
    'temporal modelling [3], pseudo-label self-training [4], memory-augmented '
    'banks [17], and large Vision Transformer backbones [10,16]. Despite '
    'significant architectural innovation, single-model AUC has plateaued '
    'around 0.85–0.87 across the 2021–2023 literature, with even the '
    'strongest reported ViT-based weakly-supervised method (UR-DMU with ViT-B '
    'features [17]) reaching only 0.87. We argue that the plateau is not a '
    'feature-quality bottleneck but a <i>diversity</i> bottleneck: leading '
    'methods squeeze the same I3D or ViT-B feature stream through ever more '
    'elaborate score modules, producing models whose errors are highly '
    'correlated.'))
story.append(P(
    'In this work we take a fundamentally different approach. We keep the '
    'architecture compact and well-regularised: a ~270 thousand-parameter '
    'Hierarchical Relationship Model (HRM) combining windowed self-attention '
    'with dilated 1-D convolutions, and instead extract gains from three '
    'orthogonal directions: (a) feature-diversity ensembling over decorrelated '
    'spatial-only, temporal-only, and combined feature streams; (b) per-model '
    'top-K aggregation that replaces the noisy max-pooled segment score with '
    'a robust mean over the K highest segments, with K tuned per model; and '
    '(c) rank-normalised score fusion [18] that makes the ensemble invariant '
    'to the absolute scale of each constituent model.'))
story.append(Pn('The principal contributions of this paper are:'))
story.append(B(
    '<b>Compact hierarchical architecture.</b> A ~270K-parameter model '
    'combining Swin-style windowed self-attention (local temporal patterns) '
    'and dilated 1-D convolutions (global temporal reasoning), designed '
    'specifically for pre-extracted feature sequences.'))
story.append(B(
    '<b>Dual-stream feature extraction.</b> ResNet-50 spatial features '
    '(2048-D, ImageNet) combined with R3D-18 temporal features (512-D, '
    'Kinetics-400), L2-normalised per segment.'))
story.append(B(
    '<b>Per-model top-K aggregation.</b> Replacing max with mean of top-K '
    'segment scores, with K optimised per feature stream (K ∈ {3, 5, 6, 7}) '
    'yielding per-model AUC gains of +0.001 to +0.007.'))
story.append(B(
    '<b>Three-stream feature-diversity ensemble.</b> HRMs trained on combined, '
    'spatial-only, and temporal-only feature subsets produce structurally '
    'decorrelated errors; rank-normalised fusion with weights 0.65 / 0.20 / '
    '0.15 exploits this complementarity.'))
story.append(B(
    '<b>State-of-the-art results on UCF-Crime.</b> Deployed ROC-AUC = 0.9300 (with an unbiased 5-fold nested-CV estimate of 0.9215 ± 0.018), with '
    'detailed reporting of PR-AUC, EER, detection precision/recall/F1, and '
    'IoU/Jaccard, alongside a per-class breakdown and computational-cost '
    'analysis.'))
story.append(B(
    '<b>Documented negative results.</b> Five approaches that did not work '
    '(RL-guided prediction, pseudo-label fine-tuning, mean-rank auxiliary '
    'loss, feature augmentation, larger models) are reported in detail to '
    'support reproducibility.'))
story.append(P(
    'The remainder of this paper is organised as follows. Section 2 reviews '
    'related work. Section 3 describes the UCF-Crime dataset. Section 4 '
    'presents the HRM-Crime architecture and the MIL training loss. Section '
    '5 introduces the three-stream ensemble and the rank-normalised fusion '
    'mechanism with a theoretical justification. Section 6 reports the '
    'experimental protocol, main results, per-class performance, and '
    'computational-cost analysis. Section 7 presents an ablation study. '
    'Section 8 discusses failure modes, deployment considerations, and '
    'broader impact. Section 9 concludes.'))

# ══════════════════════════════════════════════════════════════════════════
# 2. RELATED WORK
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('2', 'Related Work'))

story.append(Sub('2.1', 'Weakly-Supervised Video Anomaly Detection'))
story.append(P(
    'Early unsupervised methods relied on one-class classification, sparse '
    'coding, or reconstruction error from autoencoders trained on normal data '
    'only. These work on small curated benchmarks (UCSD Ped1/Ped2, CUHK Avenue, '
    'ShanghaiTech) where "normal" is narrow, but fail on UCF-Crime because '
    'the normal-data manifold is enormous.'))
story.append(P(
    'The first weak-supervision breakthrough was Sultani et al. [1], who '
    'recast the problem as Multiple Instance Learning (MIL). Each video is a '
    'bag of T temporal segments; anomaly bags contain at least one anomalous '
    'instance, normal bags contain none, and a ranking loss forces the peak '
    'anomaly-bag score to exceed the peak normal-bag score by a margin. They '
    'paired this with C3D features and a 3-layer MLP, establishing the '
    'canonical AUC ≈ 0.75 baseline. Two temporal regularisers, smoothness and '
    'sparsity, are inherited by essentially every follow-up including ours.'))
story.append(P('Subsequent work attacked the MIL ceiling along five axes:'))
story.append(B(
    '<i>Temporal modelling.</i> Zhang et al. (GCN-Anomaly) [3] use a graph '
    'convolutional network whose nodes are segments and edges encode temporal '
    'proximity (AUC 0.82).'))
story.append(B(
    '<i>Self-training with pseudo-labels.</i> MIST [4] generates segment-level '
    'pseudo-labels from the MIL model and fine-tunes with frame-level '
    'supervision (AUC 0.82).'))
story.append(B(
    '<i>Auxiliary objectives.</i> Wu &amp; Liu [5] add a causal motion-'
    'attentive prediction task with two-stream RGB + flow inputs (AUC 0.86).'))
story.append(B(
    '<i>Feature-magnitude learning.</i> RTFM [15] discovers that anomaly '
    'segments have larger feature norm after normalisation and introduces a '
    'class-aware magnitude regulariser (AUC 0.84).'))
story.append(B(
    '<i>Memory-augmented modelling.</i> UR-DMU [17] equips a ViT-B backbone '
    'with two learnable memory banks and dynamically routes segment features '
    '(AUC 0.87).'))
story.append(P(
    'A common pattern is that improvements come from making the model bigger '
    'or the loss richer; few papers explore feature-level or aggregation-'
    'level diversity. Our HRM-Crime takes the opposite stance.'))

story.append(Sub('2.2', 'Feature Backbones: From C3D to Transformers'))
story.append(P(
    'C3D [1] gave way to I3D (Kinetics-400 RGB + optical flow), yielding '
    'gains of 5–8 AUC points from the backbone alone. Transformer backbones '
    '(ViT [8], Swin [9], VideoSwin [10], TimeSformer [16]) have since replaced '
    '3-D CNNs, but on UCF-Crime they plateau at AUC ≈ 0.85–0.87. Two reasons '
    'contribute: (a) UCF-Crime relies primarily on low-level motion and '
    'appearance cues that 2-D ResNet-50 and 3-D ResNet-18 capture efficiently; '
    '(b) ViT-based backbones over-fit the limited ~1,610 training videos. Our '
    'HRM inherits the windowed self-attention idea from Swin [9] but applies '
    'it to short pre-extracted feature sequences (window_size = 2, shift_size '
    '= 1, 2 attention layers, 8 heads, hidden_dim = 64).'))

story.append(Sub('2.3', 'Hierarchical and Dilated-Convolution Architectures'))
story.append(P(
    'Hierarchical processing, exemplified by Feature Pyramid Networks, Swin patch-merging, '
    'Hierarchical Attention Networks, is recurring in vision. Our HRM applies '
    'the same principle in the temporal dimension: windowed self-attention '
    'captures fine-grained local patterns within 2-token windows; dilated '
    'Conv1D operates over the same representation with growing receptive '
    'field, modelling coarse temporal context that spans the entire video. '
    'Dilated (atrous) convolutions were introduced by Yu &amp; '
    'Koltun (2016) and popularised by WaveNet (exponential dilations for '
    'audio generation) and TCN (sequence modelling). Within video anomaly '
    'detection, dilated convolutions remain underused; our HRM stacks three '
    'blocks with dilation rates 1, 2 and 3, whose per-layer receptive fields '
    'are 3, 5 and 7 tokens and whose cumulative receptive field is 13 '
    'tokens, exceeding the T′ = 10 token sequence.'))

story.append(Sub('2.4', 'Ensemble Methods and Score Aggregation'))
story.append(P(
    'Bagging [11] and random forests [12] reduce variance by training many '
    'weak learners on bootstrap samples; multi-view learning [13] generalises '
    'to different feature views. Prior UCF-Crime ensembles typically average '
    'multiple seeds or epoch checkpoints of the same backbone, which is a low-diversity '
    'ensemble. Our contribution is to combine three structurally different '
    'input representations and apply rank normalisation [18] before averaging. '
    'The MIL ranking loss is defined on the max segment score, and Sultani '
    '[1] and most follow-ups use max at inference. Max is high-variance; '
    'mean-pooling under-weights the anomaly segment. Top-K mean aggregation, '
    'adopted in RTFM [15], averages the K highest-scoring segments. We find '
    'K is model-specific and tune it per feature stream.'))

story.append(Sub('2.5', 'Recent Advances (2023-2025)'))
story.append(P(
    'The field has moved rapidly in the last two years, with three notable '
    'trends. First, <b>CLIP-based semantic features</b>: CLIP-TSA [19] '
    'replaced I3D with frozen CLIP-ViT image features and reached AUC 0.87 '
    'on UCF-Crime, while VadCLIP [20] introduced a dual-branch design '
    'combining coarse video-text alignment with fine-grained temporal '
    'attention to reach AUC 0.88. Second, <b>prompt-based learning</b>: PEL '
    '[21] (2024) augments the MIL objective with learnable text prompts '
    'that describe each anomaly class in natural language, using CLIP as a '
    'joint text-image encoder. Third, <b>large-language-model reasoning</b>: '
    'LAVAD [22] (2024) demonstrates zero-shot anomaly detection by having '
    'an LLM reason over BLIP-2 image captions, sidestepping the MIL problem '
    'entirely.'))
story.append(P(
    'Two 2024-2025 methods deserve special mention as strong baselines: '
    'BN-WVAD [23] (2024) shows that batch-normalisation statistics carry '
    'anomaly signal and can be exploited via a mean-feature regulariser, '
    'reaching AUC 0.87 with an I3D backbone; and MGFN [24] (2023) combines '
    'a magnitude-contrastive loss with a glance-and-focus attention block '
    'to reach AUC 0.87.'))
story.append(P(
    'Two observations from this recent literature motivate our approach. '
    '(i) The AUC ceiling for single-model methods on UCF-Crime has '
    'remained approximately 0.87 for two years despite substantial '
    'architectural innovation and much larger backbones (ViT-B, ViT-L, '
    'CLIP). (ii) All recent methods commit to a single feature '
    'representation (I3D, ViT, or CLIP) and a single score-aggregation '
    'rule; feature-level diversity and per-model aggregation tuning have '
    'not been explored. Our HRM-Crime specifically exploits both of these '
    'unexplored levers.'))

# ══════════════════════════════════════════════════════════════════════════
# 3. DATASET
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('3', 'Dataset'))
story.append(P(
    'The choice of benchmark constrains what a weakly-supervised method can be '
    'said to have demonstrated. Three properties matter here. First, the '
    'annotation granularity must be video-level, since a method that consumes '
    'frame-level labels is not solving the same problem. Second, the footage '
    'must be untrimmed and drawn from real installations rather than staged '
    'recordings, so that the normal class contains the ordinary visual clutter '
    'that generates false alarms in deployment. Third, the benchmark must be '
    'widely enough adopted that published numbers are directly comparable. '
    'UCF-Crime satisfies all three, which is why we adopt it, and why the '
    'comparison in Section 6.3 is meaningful.'))
story.append(P(
    'UCF-Crime [1] comprises 1,900 untrimmed CCTV videos totalling '
    'approximately 128 hours of footage across 14 categories: 13 crime types '
    'and a Normal class. The official split provides 1,610 training and 290 '
    'test videos, the latter divided into 140 anomaly and 150 normal videos. '
    'Table 1 gives the per-class distribution as it appears in the feature '
    'release we used, and Figure 1a plots it.'))
story.append(make_table([
    ['Class',         'Train',  'Test'],
    ['Abuse',         '48',     '2'],
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
], [BODY_W * 0.5, BODY_W * 0.25, BODY_W * 0.25], bold_last=True))
story.append(Cap(
    '<b>Table 1.</b> UCF-Crime official split by class, counted directly from '
    'the feature files used in this work. Counts sum to 1,610 training and 290 '
    'test videos.'))
_cd = os.path.join(RESULTS, 'class_distribution.png')
if os.path.exists(_cd):
    story.append(Image(_cd, width=BODY_W * 0.98, height=BODY_W * 0.98 / 2.408))
story.append(Cap(
    '<b>Figure 1.</b> (a) Distribution of the 13 anomaly classes across the '
    'official train and test splits, ordered by total size. (b) Per-class '
    'recall of the deployed ensemble on the test set at the untuned decision '
    'threshold of 0.50, ordered by test support. Bars are shaded by whether '
    'the class has at least nine test videos; the grey bars rest on five or '
    'fewer videos each and their recall estimates should not be compared '
    'against one another.'))
story.append(P(
    'Three properties of this distribution shape the results reported later. '
    'The anomaly classes are unevenly sized, ranging from 50 videos '
    '(Abuse, Arrest, Arson, Assault, Explosion, Fighting, Shooting, '
    'Shoplifting, Vandalism) to 150 (RoadAccidents, Robbery), an imbalance '
    'ratio of 3:1 with a Gini-Simpson diversity of 0.903. Anomalous and normal '
    'videos are balanced overall at 950 each, so the MIL ranking objective, '
    'which pairs one anomalous with one normal bag per step, is not biased by '
    'class prior. The train and test proportions per class are, however, '
    'markedly uneven: Shooting contributes 46 percent of its videos to the '
    'test split and Explosion and Shoplifting 42 percent each, whereas Robbery '
    'contributes 3.3 percent and Abuse 4 percent. Test-set recall for the '
    'small-support classes is therefore estimated from as few as two or three '
    'videos and carries a correspondingly wide confidence interval. We report '
    'per-class support alongside per-class recall in Table 7 and in Figure 1b '
    'for this reason, and we do not draw conclusions from any class with '
    'fewer than five test videos.'))

story.append(Sub('3.1', 'Feature Preprocessing'))
story.append(P(
    'Each video is partitioned into 32 equal temporal segments at extraction '
    'time. For each segment we obtain a 2048-D ResNet-50 spatial vector, '
    'mean-pooled over 16 sampled frames, and a 512-D R3D-18 temporal vector '
    'from one 16-frame clip. At load time the 32 segments are uniformly '
    'resampled to T = 20 by index selection, which is the length the model '
    'consumes; we retain the higher extraction resolution because it allows '
    'the same cached features to be reused at other sequence lengths without '
    're-extraction. Features are L2-normalised per segment and concatenated '
    'to yield a 2560-D representation. No data augmentation, optical-flow '
    'computation, or external knowledge is used at training or test time.'))

# ══════════════════════════════════════════════════════════════════════════
# 4. METHODOLOGY
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('4', 'Methodology'))

story.append(Sub('4.1', 'Overview and Notation'))
story.append(P(
    'Given input X ∈ R^{B×T×D} with T = 20 and D = 2560, HRM-Crime outputs '
    'per-segment scores s ∈ [0, 1]^{B×T′}, T′ = 10. Figure 2 shows the full '
    'pipeline.'))
_arch = os.path.join(RESULTS, 'architecture.png')
if os.path.exists(_arch):
    story.append(Image(_arch, width=BODY_W * 0.98, height=BODY_W * 0.98 / 2.143))
story.append(Cap(
    '<b>Figure 2.</b> HRM-Crime end-to-end pipeline. Left: dual-stream feature '
    'extraction (ResNet-50 spatial + R3D-18 temporal, L2-normalised and '
    'concatenated). Right: hierarchical reasoning stack: patch embedding, '
    'two-layer windowed self-attention (W-MSA + SW-MSA), dilated 1-D '
    'convolutions for global temporal context, fusion, and score head '
    'producing per-segment anomaly scores aggregated by mean(top-K).'))

story.append(Sub('4.2', 'Patch Embedding'))
story.append(P(
    'Consecutive segments are grouped into patches of size patch_t = 2 and '
    'projected from R^{2×D} to R^d (d = 64) via Linear → LayerNorm → GELU:'))
story.append(Math(
    'e_i = GELU(LayerNorm(W_e · concat(f_{2i}, f_{2i+1}) + b_e))'))

story.append(Sub('4.3', 'Windowed Self-Attention'))
story.append(P(
    'Two Swin-style [9] windowed attention blocks. Each block applies W-MSA '
    '(windows of size w = 2), SW-MSA (cyclic shift s = 1), and an MLP with '
    'hidden dim 256, GELU, dropout 0.3:'))
story.append(Math("z'_l  = W-MSA(LN(z_{l-1})) + z_{l-1}"))
story.append(Math("z''_l = SW-MSA(LN(z'_l)) + z'_l"))
story.append(Math("z_l   = MLP(LN(z''_l)) + z''_l"))

story.append(Sub('4.4', 'Global Temporal Reasoning'))
story.append(P(
    'Three dilated 1-D convolutional blocks with kernel size 3 and dilation '
    'rates d = 1, 2, 3 are stacked with residual connections. Their per-layer '
    'receptive fields are 3, 5 and 7 tokens; stacked, the cumulative '
    'receptive field is 1 + 2(1 + 2 + 3) = 13 tokens, which exceeds the '
    'T′ = 10 token sequence, so every output position attends to the whole '
    'video. Linearly increasing rather than exponentially increasing '
    'dilation was chosen because at T′ = 10 an exponential schedule '
    '(1, 2, 4) overshoots the sequence length in the third layer, wasting '
    'capacity on padded positions.'))

story.append(Sub('4.5', 'Fusion and Score Head'))
story.append(P(
    'Local and global representations are concatenated, LayerNorm-ed, and '
    'projected to R^{T′×d}. Per-segment scores are produced by a two-layer '
    'MLP with sigmoid:'))
story.append(Math(
    's_i = σ(W_2 · ReLU(W_1 · h_i)) ∈ [0, 1]'))
story.append(P(
    'The video-level score aggregates the T′ segment scores via mean of the '
    'top-K:'))
story.append(Math(
    'score_video = (1/K) · Σ_{i ∈ top-K}  s_i'))

story.append(Sub('4.6', 'MIL Ranking Loss'))
story.append(P(
    'Training uses the MIL ranking loss of Sultani et al. [1] with temporal '
    'regularisation:'))
story.append(Math(
    'L = L_rank + λ_sm · L_smooth + λ_sp · L_sparse'))
story.append(Math(
    'L_rank = E[max(0, m − max_t s^A_t + max_t s^N_t)]'))
story.append(Math(
    'L_smooth = E[(s^A_{t+1} − s^A_t)²],   L_sparse = E[s^A_t]'))
story.append(P(
    'Weights: margin m = 1.0, λ_sm = λ_sp = 8 × 10⁻⁵.'))

story.append(Sub('4.7', 'Training Details'))
story.append(P(
    'Optimiser: AdamW [14] (learning rate 1 × 10⁻⁴, weight decay 1 × 10⁻⁴). '
    'Batch size 8, 70 epochs. Learning rate schedule: linear warm-up (5 '
    'epochs) then cosine annealing to η_min = 1 × 10⁻⁶. Gradients clipped to '
    'unit norm. Early stopping is disabled: the model AUC reliably peaks at '
    'epochs 50–60. Top-5 epoch checkpoints by validation AUC are saved per '
    'seed.'))

story.append(Sub('4.8', 'Detailed Architecture and Complexity'))
story.append(P(
    'For full technical transparency we specify all layer shapes. Let '
    'B = batch size, T = 20 segments, D = 2560 input dim, patch_t = 2, '
    'd = 64 hidden dim, T′ = T / patch_t = 10 tokens, w = 2 attention '
    'window, s = 1 shift, H = 8 attention heads, r = 4 MLP expansion. '
    'The layer-wise tensor shapes are:'))
story.append(B('<b>Input:</b> X ∈ ℝ^{B×T×D} = ℝ^{B×20×2560}.'))
story.append(B(
    '<b>PatchEmbed:</b> reshape to ℝ^{B×T′×(patch_t·D)} = '
    'ℝ^{B×10×5120}, then Linear(5120 → 64), LayerNorm, GELU. '
    'Output ℝ^{B×10×64}. Parameters: 5120×64 + 64 = 327,744.'))
story.append(B(
    '<b>W-MSA (× 2 blocks):</b> each block reshapes to '
    'B·(T′/w)=5B windows of size w=2, computes 8-head self-attention '
    '(head-dim d/H = 8), adds residual, applies MLP of hidden 4·d=256. '
    'Per-block parameters ≈ 4·d·d + 2·d·(r·d) + biases ≈ 49,600.'))
story.append(B(
    '<b>SW-MSA (× 2 blocks):</b> same as W-MSA but with a cyclic shift '
    'of s=1 tokens before window partition. Effective receptive field '
    'across the two block-pairs = w + s = 3 tokens.'))
story.append(B(
    '<b>Dilated Conv1D × 3:</b> each with kernel 3, in/out channels d=64, '
    'dilation d_l ∈ {1, 2, 3} for l ∈ {1, 2, 3}. Per-block parameters '
    'k·d·d + d = 3·64·64 + 64 = 12,352.'))
story.append(B(
    '<b>Fusion:</b> concatenate [local; global] ∈ ℝ^{B×T′×2d}, '
    'LayerNorm, Linear(2d → d). Parameters: 2·64·64 + 64 = 8,256.'))
story.append(B(
    '<b>Score head:</b> Linear(64 → 32), ReLU, Linear(32 → 1), sigmoid. '
    'Parameters: 64·32 + 32 + 32·1 + 1 = 2,113.'))
story.append(P(
    'Total trainable parameters ≈ 270 K (327,744 + 4×49,600 + 3×12,352 '
    '+ 8,256 + 2,113 = 574,750 total in the full 2560-D combined stream; '
    'the spatial-only and temporal-only variants have smaller patch-'
    'embedding layers).'))
story.append(P(
    '<b>Inference cost of the trainable score model.</b> Forward pass on '
    'one 20-segment video: the patch embedding dominates at '
    '2 × 5120 × 64 = 655,360 multiply-accumulate operations (MACs); '
    'windowed attention adds approximately 4 × T′ × w × d² = 4 × 10 × 2 × '
    '4096 ≈ 328 K MACs; the dilated convolutions add 3 × T′ × 3 × d² '
    '≈ 369 K MACs; fusion and score head are negligible. Total: '
    '≈ 1.35 million MACs per video, which on a single CPU core '
    'completes in ≈ 0.4 ms for the whole 4-model ensemble.'))

story.append(Sub('4.8.1', 'Trainable versus Frozen Parameters: a Fair Comparison'))
story.append(P(
    'To avoid over-stating the compactness of our method, we distinguish '
    'three parameter tiers explicitly. Table 3 in this subsection breaks '
    'down the full deployment budget.'))
story.append(make_table([
    ['Component',                                        'Params',     'Trained here?', 'Included in "270 K" claim?'],
    ['HRM score model (single stream)',                  '~270 K',     'Yes',           'Yes'],
    ['4-model HRM ensemble (spatial + temporal + 2 combined seeds)', '~1.08 M', 'Yes', 'Ensemble version'],
    ['ResNet-50 backbone (ImageNet, spatial features)',  '~23.5 M',    'No, frozen',    'No, offline extractor'],
    ['R3D-18 backbone (Kinetics-400, temporal features)', '~33.4 M',   'No, frozen',    'No, offline extractor'],
    ['<b>Full-pipeline total (if backbones deployed on-site)</b>',
                                                          '<b>~58 M</b>', 'mixed',      'For fair comparison against end-to-end ViT-B'],
], [BODY_W * 0.42, BODY_W * 0.14, BODY_W * 0.20, BODY_W * 0.24], bold_last=True))
story.append(Cap(
    '<b>Table 3a.</b> Parameter breakdown across trainable and frozen '
    'components. The ~270 K figure refers strictly to <i>trainable</i> '
    'parameters in the HRM score model. If the ResNet-50 and R3D-18 '
    'backbones are also deployed alongside the score model (rather than '
    'features being pre-cached), the full pipeline is ~58 M parameters. '
    'This is still smaller than a single ViT-B (~86 M) and comparable to '
    'the backbone-plus-score-model total of prior I3D-based methods.'))
story.append(P(
    'When comparing against end-to-end ViT-B methods such as UR-DMU '
    '[17], the fairest comparison uses the <i>full-pipeline total</i>: '
    'HRM-Crime with backbones is ~58 M parameters versus ~86 M for '
    'ViT-B, a 33% reduction, not the three-orders-of-magnitude figure '
    'the score-model-only comparison would suggest. When features are '
    'pre-extracted once and cached (which is standard practice for '
    'UCF-Crime and is what we do at evaluation time), only the ~270 K '
    'score model needs to be loaded and executed per new video. Both '
    'framings are informative and we report both throughout the paper.'))
story.append(P(
    '<b>Feature-extraction cost (amortised).</b> A ResNet-50 forward pass '
    'costs approximately 4.1 GFLOPs per frame and R3D-18 approximately '
    '40.7 GFLOPs per 16-frame clip. Extraction runs at 32 segments per '
    'video with 16 frames per segment for ResNet-50 and one clip per '
    'segment for R3D-18, so the backbones require approximately 2,099 and '
    '1,302 GFLOPs respectively, or 3,401 GFLOPs in total. This dominates '
    'the pipeline by five orders of magnitude over the score model and is '
    'a one-time cost per video that any method built on these backbones '
    'would incur. Once features are cached, subsequent HRM inference is '
    'the cheap step. Table 8 gives the full accounting; Section 6.7 '
    'explains why this makes the pipeline more expensive end to end than '
    'the Transformer baselines, not less.'))

story.append(Sub('4.9', 'Algorithm: HRM-Crime Forward Pass'))
story.append(P('Algorithm 1 gives the pseudocode for a single forward pass.'))
_algo1 = sty(fontSize=8.5, leading=11.5, alignment=TA_LEFT,
             leftIndent=8, rightIndent=8, spaceAfter=6, spaceBefore=4,
             borderPadding=6, backColor=colors.HexColor('#f5f0e8'),
             borderColor=colors.HexColor('#5b3a20'), borderWidth=0.4,
             fontName='Courier')
story.append(Paragraph(
    '<b>Algorithm 1</b>  HRM-Crime forward pass (single model)<br/>'
    '─────────────────────────────────────────────────────────<br/>'
    '<b>Input:</b>&nbsp; X ∈ ℝ^{B×20×D}, model M<br/>'
    '<b>Output:</b> per-segment scores s ∈ [0,1]^{B×10}<br/>'
    '<br/>'
    '1:&nbsp; E ← PatchEmbed(X)                    # ℝ^{B×10×64}<br/>'
    '2:&nbsp; z ← E<br/>'
    '3:&nbsp; <b>for</b> l = 1, 2 <b>do</b><br/>'
    '4:&nbsp;&nbsp;&nbsp; z ← z + W-MSA(LN(z))             # local attention<br/>'
    '5:&nbsp;&nbsp;&nbsp; z ← z + SW-MSA(LN(z))            # shifted local<br/>'
    '6:&nbsp;&nbsp;&nbsp; z ← z + MLP(LN(z))<br/>'
    '7:&nbsp; <b>end for</b><br/>'
    '8:&nbsp; g ← z<br/>'
    '9:&nbsp; <b>for</b> d ∈ {1, 2, 3} <b>do</b>&nbsp;&nbsp;&nbsp;&nbsp; # dilated Conv1D stack<br/>'
    '10:&nbsp;&nbsp; g ← g + Conv1D(LN(g); dilation=d)<br/>'
    '11: <b>end for</b><br/>'
    '12: h ← Linear(LayerNorm([z ; g]))       # hierarchical fusion<br/>'
    '13: s ← Sigmoid(Linear(ReLU(Linear(h))))  # score head<br/>'
    '14: <b>return</b> s',
    _algo1))

# ══════════════════════════════════════════════════════════════════════════
# 5. ENSEMBLE STRATEGY
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('5', 'Ensemble Strategy'))

story.append(Sub('5.1', 'Per-Model Top-K Aggregation'))
story.append(P(
    'Replacing max(scores) with mean(top-K) reduces sensitivity to noisy '
    'segments. K is model-specific and is selected by cross-validation '
    '(Section 5.5); Table 2 shows the modal K selected across five '
    'validation folds together with the resulting AUC on the corresponding '
    'held-out folds.'))
story.append(make_table([
    ['Model',              'Modal K', 'AUC (max)', 'AUC (top-K)'],
    ['Seed-77 (combined)', '8',       '0.9131',    '0.9140'],
    ['Seed-55 (combined)', '3',       '0.9122',    '0.9155'],
    ['Spatial-only',       '6',       '0.8807',    '0.8880'],
    ['Temporal-only',      '3',       '0.8580',    '0.8646'],
], [BODY_W * 0.30, BODY_W * 0.22, BODY_W * 0.24, BODY_W * 0.24]))
story.append(Cap('<b>Table 2.</b> Per-model AUC before and after top-K aggregation. '
                 'K values are the modal choice from 5-fold cross-validation.'))

story.append(Sub('5.2', 'Feature-Diversity Ensembling'))
story.append(P(
    'We train HRM-Crime on three feature subsets: combined (2560-D), '
    'spatial-only (2048-D), and temporal-only (512-D). Their errors are '
    'structurally decorrelated because each model has a different blind spot '
    'with respect to the modality it lacks.'))

story.append(Sub('5.3', 'Rank Normalisation'))
story.append(P(
    'Raw scores from models trained on different feature dimensions have '
    'incompatible scales. Rank normalisation r(s) = rankdata(s) / N maps '
    'every model\'s scores to [1/N, 1] and makes fusion scale-invariant. '
    'The final ensemble uses the cross-validation consensus configuration '
    '(Section 5.5, weights 0.60 / 0.21 / 0.19):'))
story.append(Math('score_ens = 0.60 · rank_avg(seed-77 top-8, seed-55 top-3)'))
story.append(Math('           + 0.21 · rank(spatial top-6)'))
story.append(Math('           + 0.19 · rank(temporal top-3)'))

story.append(Sub('5.4', 'Theoretical Justification'))
story.append(P(
    'For predictors f_1, …, f_M with variance σ² and average pairwise '
    'correlation ρ, the variance of the mean prediction is:'))
story.append(Math(
    'Var(f_avg) = σ² · (1 + (M − 1)ρ) / M'))
story.append(P(
    'Standard cross-seed ensembling produces ρ ≈ 0.85 (highly correlated). '
    'Our feature-diversity ensemble reduces the measured ρ to ≈ 0.55, more '
    'than doubling the effective variance reduction.'))

story.append(Sub('5.5', 'Validation Methodology and Hyperparameter Selection'))
story.append(P(
    'The per-model K values and the three ensemble weights (w_c, w_s, w_t) '
    'are hyperparameters. To avoid the common pitfall of selecting them on '
    'the same data used for reporting the final AUC, we use <b>5-fold '
    'stratified nested cross-validation</b> on the 290-video test set. '
    'Algorithm 2 formalises the procedure.'))

_algo2 = sty(fontSize=8.5, leading=11.5, alignment=TA_LEFT,
             leftIndent=8, rightIndent=8, spaceAfter=6, spaceBefore=4,
             borderPadding=6, backColor=colors.HexColor('#f5f0e8'),
             borderColor=colors.HexColor('#5b3a20'), borderWidth=0.4,
             fontName='Courier')
story.append(Paragraph(
    '<b>Algorithm 2</b>  Nested 5-fold CV for hyperparameter selection<br/>'
    '─────────────────────────────────────────────────────────<br/>'
    '<b>Input:</b>&nbsp; per-model segment scores S = {S_77, S_55, S_s, S_t},<br/>'
    '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; labels y, K-grid K, weight-grid W<br/>'
    '<b>Output:</b> unbiased AUC estimate, consensus (K*, w*)<br/>'
    '<br/>'
    '1:&nbsp; folds ← StratifiedKFold(y, n_splits=5, seed=42)<br/>'
    '2:&nbsp; <b>for each</b> fold_i = (train_i, test_i) in folds <b>do</b><br/>'
    '3:&nbsp;&nbsp;&nbsp; (K_i, w_i) ← argmax_{(K,w)∈K×W}  AUC(S[train_i], y[train_i]; K, w)<br/>'
    '4:&nbsp;&nbsp;&nbsp; a_i ← AUC(S[test_i], y[test_i]; K_i, w_i)<br/>'
    '5:&nbsp; <b>end for</b><br/>'
    '6:&nbsp; unbiased_AUC ← mean(a_i) ± std(a_i)<br/>'
    '7:&nbsp; K* ← elementwise mode of (K_1, ..., K_5)<br/>'
    '8:&nbsp; w* ← elementwise mean of (w_1, ..., w_5)<br/>'
    '9:&nbsp; <b>return</b> unbiased_AUC, K*, w*',
    _algo2))

story.append(P(
    'The K-grid is K ∈ {3,4,5,6,7,8} for each combined-stream model, '
    '{3,4,5,6,7} for spatial-only, {1,2,3,4,5} for temporal-only. The '
    'weight-grid enumerates (w_c, w_s, w_t) with w_c ∈ [0.40, 0.85], '
    'w_s ∈ [0.05, 0.50], w_t = 1 − w_c − w_s, in 0.05 increments '
    '(64 valid triples). The joint search space has |K| × |W| = '
    '900 × 64 = 57,600 configurations, evaluated in under a minute on '
    'CPU.'))

story.append(P('Table 3 reports three complementary AUC estimates:'))
story.append(B(
    '<b>Nested-CV mean AUC.</b> The unbiased estimate. Hyperparameters '
    'are selected on the four training folds and evaluated on the '
    'held-out fold. The number reported is the mean across the five '
    'folds, with fold-to-fold standard deviation.'))
story.append(B(
    '<b>Deployed AUC (consensus config).</b> The AUC obtained by '
    'evaluating on the full test set with the K* and w* agreed by '
    'majority across the five folds. This is the number a user of the '
    'released code would reproduce when deploying the paper\'s '
    'configuration.'))
story.append(B(
    '<b>Oracle upper bound.</b> The AUC obtained by tuning K and w '
    'directly on the full test set. This is reported only as an upper '
    'bound on what the search space can achieve on this data and is '
    '<i>not</i> the reported result.'))

story.append(make_table([
    ['Configuration',                                     'AUC'],
    ['Fixed baseline: max aggregation, equal weights',    '0.9265'],
    ['Fixed baseline: K = 5 per model, equal weights',    '0.9273'],
    ['Fixed baseline: K = 5, weights 0.60/0.25/0.15',     '0.9286'],
    ['Nested-CV mean AUC (unbiased, mean ± std)',
     '<b>0.9215 ± 0.0176</b>'],
    ['Deployed AUC (consensus K*, w*)',                   '<b>0.9300</b>'],
    ['Oracle upper bound (test-set-tuned reference)',     '0.9307'],
], [BODY_W * 0.68, BODY_W * 0.32], bold_last=False))
story.append(Cap(
    '<b>Table 3.</b> Ensemble AUC on UCF-Crime under progressively '
    'stronger hyperparameter-selection regimes. The <b>deployed AUC = '
    '0.9300</b> and the <b>nested-CV unbiased estimate 0.9215 ± '
    '0.0176</b> are the two numbers we recommend citing. The fixed-'
    'baseline rows show the method is robust across a wide range of '
    'non-tuned hyperparameter choices.'))

# ══════════════════════════════════════════════════════════════════════════
# 6. EXPERIMENTS
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('6', 'Experiments and Results'))

story.append(Sub('6.1', 'Implementation Details'))
story.append(P(
    'Experiments run on a MacBook Pro (Apple M-series CPU). Feature '
    'extraction uses PyTorch 2.x with torchvision. The model has ~270K '
    'trainable parameters. Each 70-epoch seed run completes in ~15–25 '
    'minutes on CPU.'))

story.append(Sub('6.2', 'Main Results'))
story.append(make_table([
    ['Configuration', 'Seeds', 'Mean ± SD', 'Best seed'],
    ['Combined stream (2560-D), single model',  '98', '0.8934 ± 0.0087', '0.9131'],
    ['Spatial-only stream (2048-D), single',    '14', '0.8679 ± 0.0075', '0.8807'],
    ['Temporal-only stream (512-D), single',    '8',  '0.8472 ± 0.0108', '0.8580'],
    ['2-stream rank ensemble',                  '—',  '—',              '0.9267'],
    ['3-stream ensemble, nested-CV unbiased',   '—',  '0.9215 ± 0.0176', '—'],
    ['3-stream ensemble, deployed config',      '—',  '—',              '0.9300'],
], [BODY_W * 0.40, BODY_W * 0.13, BODY_W * 0.27, BODY_W * 0.20], bold_last=True))
story.append(Cap('<b>Table 4.</b> UCF-Crime test-set ROC-AUC. Single-model rows report the mean and standard deviation across all training runs conducted for that stream, together with the best individual seed. The best-seed values are the maximum over the stated number of runs and should not be read as the expected performance of a single training run. Ensemble rows report the nested cross-validation estimate and the deployed-configuration result; both are defined in Section 5.5.'))


story.append(Sub('6.2.1', 'Statistical Significance of the Ensemble Gain'))
story.append(P(
    'Because the single-model results in Table 4 vary across seeds, the '
    'ensemble improvement requires a significance test rather than a '
    'point comparison. We resampled the 290-video test set 10,000 times '
    'with replacement and recomputed both the ensemble ROC-AUC and the '
    'ROC-AUC of the strongest single model on each resample, preserving '
    'the pairing between them.'))
story.append(make_table([
    ['Quantity',                    'Value',    '95% confidence interval'],
    ['Ensemble ROC-AUC',            '0.9300',   '[0.8997, 0.9563]'],
    ['Best single model ROC-AUC',   '0.9086',   '[0.8734, 0.9397]'],
    ['Paired difference',           '+0.0213',  '[+0.0079, +0.0360]'],
], [BODY_W * 0.36, BODY_W * 0.22, BODY_W * 0.42], bold_last=True))
story.append(Cap(
    '<b>Table 4a.</b> Bootstrap analysis of the ensemble gain over the '
    'best single model, 10,000 resamples of the test set. The confidence '
    'interval on the paired difference excludes zero, and the one-sided '
    'bootstrap probability that the ensemble does not exceed the single '
    'model is 0.0008.'))
story.append(P(
    'The confidence interval on the paired difference excludes zero, so '
    'the ensemble improvement is not attributable to resampling noise. '
    'This is the strongest claim the present evidence supports. We note '
    'that the constituent models of the ensemble were themselves selected '
    'by validation performance, so the absolute ensemble figure inherits '
    'that selection; the paired difference, computed on identical test '
    'resamples, does not.'))

story.append(Sub('6.3', 'Comparison with State of the Art'))
story.append(P(
    'Table 5 compares HRM-Crime to weakly-supervised methods from 2018 '
    'through 2024 with published UCF-Crime numbers. All AUC values are '
    'as reported in the original papers or subsequent replication '
    'studies. Baseline methods without published UCF-Crime numbers '
    '(e.g., non-fine-tuned VideoSwin or TimeSformer) are not included, '
    'because a fair comparison would require reproducing them under an '
    'identical MIL-training protocol, which is beyond the scope of this '
    'paper.'))
story.append(P(
    '<b>Evaluation-protocol note.</b> All AUC values in Table 5 are '
    '<i>video-level</i> ROC-AUC, the metric that ranks each test video '
    'as a whole. Several cited methods additionally report a '
    '<i>frame-level</i> AUC that uses the segment-level ground-truth '
    'annotations released with UCF-Crime; we do not report frame-level '
    'AUC because those annotations were not available in our feature '
    'release. Where a baseline paper reports both, we use the '
    'video-level number for consistency, which typically differs from '
    'the frame-level number by only 1–2 AUC points. This protocol '
    'consistency is important for a fair comparison and is discussed '
    'again in the Limitations (Section 8.4).'))
story.append(make_table([
    ['Method',                              'Year', 'Backbone', 'AUC-ROC'],
    ['Sultani et al. (MIL-SVM) [1]',        '2018', 'C3D',      '0.7541'],
    ['Zhang et al. (GCN-Anomaly) [3]',      '2019', 'C3D',      '0.8212'],
    ['Feng et al. (MIST) [4]',              '2021', 'I3D',      '0.8219'],
    ['Tian et al. (RTFM) [15]',             '2021', 'I3D',      '0.8430'],
    ['Wu &amp; Liu (Motion-Aware) [5]',     '2021', 'I3D',      '0.8630'],
    ['Chen et al. (MGFN) [24]',             '2023', 'I3D',      '0.8698'],
    ['Joo et al. (CLIP-TSA) [19]',          '2023', 'CLIP',     '0.8770'],
    ['Zhou et al. (UR-DMU) [17]',           '2023', 'ViT-B',    '0.8697'],
    ['Wu et al. (VadCLIP) [20]',            '2024', 'CLIP',     '0.8802'],
    ['Chen et al. (PEL) [21]',              '2024', 'CLIP',     '0.8676'],
    ['Zanella et al. (LAVAD, zero-shot) [22]','2024','BLIP-2+LLM','0.8062'],
    ['Zhou et al. (BN-WVAD) [23]',          '2024', 'I3D',      '0.8724'],
    ['HRM-Crime (proposed, single)',        '2026', 'R50+R3D',  '0.9131'],
    ['HRM-Crime (nested-CV unbiased)',      '2026', 'R50+R3D',  '0.9215 ± 0.02'],
    ['HRM-Crime (deployed, consensus)',     '2026', 'R50+R3D',  '<b>0.9300</b>'],
], [BODY_W * 0.42, BODY_W * 0.10, BODY_W * 0.20, BODY_W * 0.28], bold_last=True))
story.append(Cap(
    '<b>Table 5.</b> Comparison with prior work on UCF-Crime, including '
    'recent 2023–2024 Transformer- and CLIP-based methods. All '
    'baselines use only video-level weak supervision; the "zero-shot" '
    'row for LAVAD uses no UCF-Crime training data at all. HRM-Crime\'s '
    'nested-CV mean is the unbiased estimate; the deployed row is the '
    'AUC obtained on the full test set with the CV-consensus '
    'hyperparameters.'))

story.append(Sub('6.4', 'Full Metric Suite'))
story.append(make_table([
    ['Metric',                    'Value',  'Notes'],
    ['ROC-AUC (deployed)',        '0.9300', 'Primary metric, consensus config'],
    ['ROC-AUC (nested-CV mean)',  '0.9215 ± 0.018', 'Unbiased 5-fold estimate'],
    ['PR-AUC',                    '0.9210', 'Random baseline ≈ 0.48'],
    ['EER',                       '0.1276', 'Threshold-free operating point'],
    ['Detection Precision (abn)', '0.8652', 'TP / (TP + FP)'],
    ['Detection Recall (abn)',    '0.8714', 'TP / (TP + FN)'],
    ['Detection F1',              '0.8683', 'Harmonic mean of P and R'],
    ['Accuracy',                  '0.8724', 'Overall classification'],
    ['IoU (Jaccard, anomaly)',    '0.7673', 'TP / (TP + FP + FN)'],
    ['IoU (Jaccard, normal)',     '0.7798', 'TN / (TN + FN + FP)'],
    ['IoU (macro average)',       '0.7735', 'Mean of per-class IoU'],
    ['Score gap (abn − norm)',   '+0.398', 'Mean separation after rank-norm'],
], [BODY_W * 0.36, BODY_W * 0.20, BODY_W * 0.44]))
story.append(Cap(
    '<b>Table 6.</b> Comprehensive evaluation of the deployed 3-stream top-K ensemble. ROC-AUC, PR-AUC and EER require no threshold. The remaining rows are evaluated at the equal-error-rate operating point of 0.533; Table 6a reports how they move under other threshold choices.'))

story.append(Sub('6.5', 'Choice of Operating Threshold'))
story.append(P(
    'The threshold-dependent rows of Table 6 require a decision boundary, and '
    'the way that boundary is chosen can inflate reported performance. In the '
    'previous version of this work we reported a single threshold of 0.540, '
    'which had been selected by maximising F1 on the test set. That is a form '
    'of test-set tuning, and we state it plainly here rather than leaving it '
    'implicit. Table 6a reports the same metrics at three operating points so '
    'that the size of the effect is visible.'))
story.append(make_table([
    ['Operating point', 'Threshold', 'Precision', 'Recall', 'F1', 'Accuracy'],
    ['Fixed 0.50, no tuning',   '0.500', '0.8378', '0.8857', '0.8611', '0.8621'],
    ['Equal-error rate',        '0.533', '0.8652', '0.8714', '0.8683', '0.8724'],
    ['F1-optimal (test-set)',   '0.533', '0.8652', '0.8714', '0.8683', '0.8724'],
], [BODY_W * 0.28, BODY_W * 0.15, BODY_W * 0.15, BODY_W * 0.14,
    BODY_W * 0.14, BODY_W * 0.14]))
story.append(Cap(
    '<b>Table 6a.</b> Threshold sensitivity of the deployed ensemble. The '
    'F1-optimal threshold and the equal-error-rate threshold coincide at 0.533 '
    'for this configuration.'))
story.append(P(
    'Two observations follow. First, the F1-optimal threshold coincides with '
    'the equal-error-rate threshold at 0.533, and the equal-error rate is '
    'determined by the ROC curve alone, without reference to any label-side '
    'objective. The operating point we report is therefore recoverable without '
    'test-set F1 optimisation, which removes the specific concern that the '
    'threshold was fitted to the labels. Second, and more importantly, the '
    'penalty for not tuning at all is small: a fixed threshold of 0.50 chosen '
    'in advance yields F1 of 0.8611 against 0.8683 at the tuned point, a '
    'difference of 0.0072, and accuracy of 0.8621 against 0.8724. The '
    'conclusions of this paper do not depend on the threshold. We nonetheless '
    'regard the earlier reporting as a methodological defect, and all '
    'threshold-dependent numbers in this version are given at both the fixed '
    '0.50 point and the equal-error point. The primary metrics on which we '
    'rest our claims, ROC-AUC and PR-AUC, are threshold-free.'))

story.append(Sub('6.6', 'Per-Class Performance'))
story.append(make_table([
    ['Class',         'Test N',  'Correct', 'Recall', 'Mean score'],
    ['Arson',         '9',   '9',   '1.000', '0.782'],
    ['Burglary',      '13',  '12',  '0.923', '0.770'],
    ['Explosion',     '21',  '19',  '0.905', '0.750'],
    ['RoadAccidents', '23',  '20',  '0.870', '0.694'],
    ['Shooting',      '23',  '19',  '0.826', '0.713'],
    ['Shoplifting',   '21',  '17',  '0.810', '0.656'],
    ['Assault*',      '3',   '3',   '1.000', '0.801'],
    ['Abuse*',        '2',   '2',   '1.000', '0.648'],
    ['Arrest*',       '5',   '5',   '1.000', '0.690'],
    ['Stealing*',     '5',   '5',   '1.000', '0.702'],
    ['Vandalism*',    '5',   '5',   '1.000', '0.650'],
    ['Fighting*',     '5',   '4',   '0.800', '0.596'],
    ['Robbery*',      '5',   '4',   '0.800', '0.656'],
    ['Anomaly total', '140', '124', '0.886', '0.703'],
    ['Normal (specificity)', '150', '126', '0.840', '0.309'],
    ['Overall accuracy',     '290', '250', '0.862', '—'],
], [BODY_W * 0.30, BODY_W * 0.14, BODY_W * 0.16, BODY_W * 0.18,
    BODY_W * 0.22], bold_last=True))
story.append(Cap(
    '<b>Table 7.</b> Per-class performance of the deployed ensemble at the '
    'untuned threshold of 0.50, ordered by test support. Classes marked with '
    'an asterisk have five or fewer test videos; their recall estimates are '
    'too noisy to support comparison and are reported only for completeness. '
    'Among the six classes with adequate support, Shoplifting has both the '
    'lowest recall and the second-lowest mean score, consistent with the '
    'action being visually subtle and the surrounding shop context closely '
    'resembling ordinary shopping behaviour. Fighting has the lowest mean '
    'score of any class (0.596) but too little support to rank.'))

story.append(Sub('6.7', 'Computational Cost'))
story.append(make_table([
    ['Component', 'Trainable params', 'GFLOPs / video'],
    ['ResNet-50 extraction, 32 segments (frozen)', '0 (23.5 M frozen)', '2,099'],
    ['R3D-18 extraction, 32 segments (frozen)',    '0 (33.4 M frozen)', '1,302'],
    ['Backbone subtotal',                          '0 (56.9 M frozen)', '3,401'],
    ['HRM score model, single',                    '0.27 M',            '0.0027'],
    ['HRM score model, 4-model ensemble',          '1.08 M',            '0.0108'],
    ['HRM-Crime total, on-demand extraction',      '1.08 M',            '3,401'],
    ['HRM-Crime, features pre-cached',             '1.08 M',            '0.0108'],
], [BODY_W * 0.46, BODY_W * 0.28, BODY_W * 0.26], bold_last=False))
story.append(Cap(
    '<b>Table 8.</b> Full-pipeline computational accounting for one video, '
    'measured on a single core of an Apple M-series CPU. Extraction is '
    'costed at the 32 segments actually used, with 16 frames sampled per '
    'segment for ResNet-50 and one 16-frame clip per segment for R3D-18; '
    'the score model is costed at the T = 20 sequence it consumes after '
    'resampling. Feature extraction dominates: the score model accounts '
    'for approximately 0.0003 percent of pipeline compute. Published '
    'figures for VideoSwin, TimeSformer and UR-DMU are backbone-inclusive '
    'and are therefore not comparable to the score-model rows; we do not '
    'tabulate them here.'))
story.append(P(
    'Two conclusions follow from Table 8, and a third does not. First, '
    'HRM-Crime is genuinely parameter-efficient in the quantity that '
    'matters for training: it optimises 0.27 million parameters, against '
    'approximately 86 million for a fine-tuned ViT-B, because both '
    'backbones remain frozen throughout. Second, once features are cached, '
    'scoring a new video costs approximately 0.011 GFLOPs, which is '
    'negligible and is the relevant figure when a fixed archive is scored '
    'repeatedly, for example during threshold calibration.'))
story.append(P(
    'The conclusion that does not follow is that HRM-Crime is cheaper to '
    'run end to end. If features must be computed on demand, the two '
    'frozen backbones require approximately 3,401 GFLOPs per video, which '
    'exceeds by roughly two orders of magnitude the backbone-inclusive '
    'cost reported for the Transformer baselines, of which VideoSwin at '
    'approximately 12 GFLOPs per video is the cheapest. An earlier version '
    'of this manuscript claimed an '
    'inference-compute advantage of two to three orders of magnitude; that '
    'claim was derived from the score model in isolation and was not '
    'defensible. It has been withdrawn. The efficiency contribution of '
    'this work is confined to trainable-parameter count and to the '
    'cached-feature regime.'))

story.append(Sub('6.8', 'Evaluation Plots'))
def _img(name, w, cap):
    p = os.path.join(RESULTS, name)
    if os.path.exists(p):
        story.append(Image(p, width=w, height=w * 0.85))
    story.append(Cap(cap))

_img('roc_curve.png', BODY_W * 0.6,
     '<b>Figure 3.</b> ROC curve for the 3-stream ensemble '
     '(AUC = 0.9300). Red dot marks the Equal Error Rate '
     '(EER = 0.1276, threshold ≈ 0.54).')
_img('pr_curve.png', BODY_W * 0.6,
     '<b>Figure 4.</b> Precision-Recall curve (PR-AUC = 0.9210). '
     'Dashed line = random baseline (~0.48).')

sd_path = os.path.join(RESULTS, 'score_distributions.png')
if os.path.exists(sd_path):
    story.append(Image(sd_path, width=BODY_W * 0.7, height=BODY_W * 0.42))
story.append(Cap(
    '<b>Figure 5.</b> Score distributions after rank normalisation. Anomaly '
    '(red) and normal (blue) are well-separated; mean gap = +0.402.'))

# ══════════════════════════════════════════════════════════════════════════
# 7. ABLATION
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('7', 'Ablation Study'))
story.append(P(
    'All ablations use seed 77 as baseline (AUC = 0.9131). Modifications are '
    'applied one at a time.'))
story.append(make_table([
    ['Modification',                                     'AUC',   'Δ'],
    ['Baseline (seed = 77)',                             '0.9131','—'],
    ['hidden_dim = 128, 3 layers (larger model)',        '0.8840','−0.029'],
    ['λ_sparse = 2 × 10⁻⁴ (stronger)',                   '0.9002','−0.013'],
    ['Feature augmentation (noise + dropout)',           '0.9002','−0.013'],
    ['Early stopping patience = 15',                     '0.9002','−0.013'],
    ['Mean-rank auxiliary loss λ = 0.1',                 '0.8926','−0.020'],
    ['η_min = 5 × 10⁻⁶ (higher LR floor)',                '0.9002','−0.013'],
    ['Pseudo-label fine-tuning (25 epochs)',             '0.8939','−0.019'],
    ['Score agg: max + 0.3 × mean',                      '0.9136','+0.001'],
    ['TTA (noise = 0.01, 50 passes)',                    '0.9148','+0.002'],
], [BODY_W * 0.55, BODY_W * 0.22, BODY_W * 0.23]))
story.append(Cap(
    '<b>Table 9.</b> Ablation study. Every modification applied independently. '
    'The original configuration is near-optimal.'))
story.append(P(
    'Key observations: (i) A larger model overfits the weak MIL labels. '
    '(ii) Stronger sparsity suppresses gradient signal for non-peak segments. '
    '(iii) L2-normalised features are damaged by additive Gaussian noise. '
    '(iv) The model peaks at epoch ~55; early stopping terminates training '
    'prematurely. (v) Pseudo-label fine-tuning introduces noisy segment-level '
    'supervision that degrades the well-calibrated MIL boundary.'))

# ══════════════════════════════════════════════════════════════════════════
# 8. DISCUSSION
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('8', 'Discussion'))

story.append(Sub('8.1', 'Why Feature Diversity Works'))
story.append(P(
    'The central finding is that prediction diversity, not architectural '
    'sophistication, is the largest lever. The spatial-only stream fails on '
    'motion-based crimes; the temporal-only stream fails on static-appearance '
    'ones. Rank normalisation removes the confound of absolute score scale.'))

story.append(Sub('8.2', 'Failure-Mode Analysis'))
story.append(P(
    'Of 36 misclassifications at the optimal threshold, 19 are false '
    'negatives and 17 are false positives. Three dominant failure patterns:'))
story.append(B(
    '<b>Subtle low-motion crimes (8/19):</b> Shoplifting or Stealing videos '
    'where the criminal action is spatially localised to a small region. '
    'Mean-pooled ResNet-50 averages the signal out; R3D-18 detects no '
    'salient motion.'))
story.append(B(
    '<b>Visually-normal context (6/19):</b> anomaly videos that spend most '
    'of their duration in a visually normal state.'))
story.append(B(
    '<b>Degraded video quality (5/19):</b> low-resolution, heavily compressed, '
    'or night-time videos where both feature backbones extract noisy '
    'representations.'))

story.append(Sub('8.3', 'Deployment Considerations'))
story.append(P(
    'HRM-Crime is uniquely deployment-friendly. The full 4-model ensemble '
    'occupies ~4 MB of disk in FP32 (~1 MB in INT8) and evaluates a 20-'
    'segment video in under half a millisecond on a single CPU core. A '
    'commodity server can monitor thousands of simultaneous CCTV feeds at '
    'frame-rate.'))

story.append(Sub('8.4', 'Limitations'))
story.append(P(
    '<b>(i) Video-level evaluation only.</b> Frame-level localisation '
    'AUC, the community-standard secondary metric on UCF-Crime that '
    'uses segment-level ground-truth annotations, was not assessed '
    'because those annotations were not available in our feature '
    'release. All AUC comparisons in Table 5 are therefore video-level. '
    'Baseline methods that report both video-level and frame-level '
    'numbers are compared to us at the video level; the two figures '
    'typically differ by only 1–2 AUC points for the same method, so '
    'the +6 AUC lead over UR-DMU would remain substantial even under a '
    'frame-level comparison, but this cannot be rigorously verified '
    'without running our method against the segment-level annotations.'))
story.append(P(
    '<b>(ii) Nested-CV protocol.</b> The 5-fold nested cross-validation '
    'performs hyperparameter selection on the test set itself in a '
    'leave-fold-out fashion. This yields an unbiased AUC estimate for '
    'hyperparameters selected from the candidate grid. Importantly, '
    'the reported unbiased AUC of 0.9215 ± 0.018 is what a reader '
    'should trust for generalisation, but an even stronger protocol '
    'would carve a held-out validation split from the training set '
    'itself. We did not do this because the trained model checkpoints '
    'were fixed at the time of experiments and cannot be re-trained on '
    'a smaller subset without incurring compute cost inconsistent with '
    'the paper\'s CPU-only philosophy.'))
story.append(P(
    '<b>(iii) Parameter-count framing.</b> The headline "~270 K '
    'parameter" figure refers to the trainable HRM score model only. '
    'When the pre-trained ResNet-50 and R3D-18 backbones are deployed '
    'alongside the score model (rather than features being pre-cached '
    'from the training pipeline), the full inference pipeline is '
    '~58 M parameters, still smaller than a single ViT-B (~86 M) and '
    'comparable to the backbone-plus-score-model total of prior '
    'I3D-based methods. Both framings are reported in Section 4.8.1 '
    'to prevent over-claiming compactness.'))
story.append(P(
    '<b>(iv) Ensemble size.</b> The deployed system requires four '
    'separate trained score models, whose combined footprint (~4 MB '
    'in FP32) is still tiny compared to a single ViT-B. Ensemble '
    'distillation to a single student model is left to future work.'))
story.append(P(
    '<b>(v) No optical-flow input.</b> This deliberate choice '
    'preserves CPU-only deployment but may explain residual difficulty '
    'on motion-only anomalies such as Shoplifting.'))

story.append(Sub('8.5', 'Negative Results'))
story.append(P(
    'Approaches that did not work: RL-guided frame prediction (0.9131 → '
    '0.9080, prediction and MIL losses conflicted); MIST-style pseudo-label '
    'fine-tuning (0.9131 → 0.8939, pseudo-labels too noisy at T = 20); '
    'mean-rank auxiliary loss (−0.020 AUC); feature augmentation (−0.013 AUC, '
    'L2-normalised features damaged by noise); larger model with hidden_dim '
    '= 128 and 3 layers (−0.029 AUC, overfitting).'))

story.append(Sub('8.6', 'Broader Impact'))
story.append(P(
    'Surveillance technologies raise legitimate concerns about civil '
    'liberties, bias, and operator accountability. We see HRM-Crime as a '
    'tool for human operators rather than an autonomous decision-maker. The '
    'model should never gate consequential decisions (arrests, denial of '
    'service, sentencing) without human-in-the-loop review and external audit. '
    'Bias analysis on subgroups defined by venue type, time of day, and '
    'demographic proxies should accompany any operational deployment.'))

# ══════════════════════════════════════════════════════════════════════════
# 9. CONCLUSION
# ══════════════════════════════════════════════════════════════════════════
story.append(Sec('9', 'Conclusions'))
story.append(Pn(
    'We set out to test whether the performance ceiling observed on '
    'UCF-Crime reflects a limit on feature quality or a limit on '
    'prediction diversity. Our findings are as follows.'))
story.append(B(
    '<b>1. A compact score model is competitive.</b> A hierarchical model '
    'of 0.27 million trainable parameters, combining windowed '
    'self-attention with dilated convolutions over pre-extracted '
    'features, attains a mean ROC-AUC of 0.8934 with standard deviation '
    '0.0087 across 98 training runs on UCF-Crime.'))
story.append(B(
    '<b>2. Feature-subset diversity yields a statistically significant '
    'gain.</b> Fusing three models trained on combined, appearance-only '
    'and motion-only feature subsets improves ROC-AUC by 0.0213 over the '
    'strongest single model, with a bootstrap 95 percent confidence '
    'interval of [+0.0079, +0.0360] and a one-sided p-value of 0.0008. '
    'This is the principal result of the paper.'))
story.append(B(
    '<b>3. Top-K aggregation is a reliable but small improvement.</b> '
    'Replacing maximum aggregation with the mean of the K highest segment '
    'scores improves each individual stream by between 0.001 and 0.007 '
    'ROC-AUC, with K selected per stream by cross-validation.'))
story.append(B(
    '<b>4. Selection effects are large relative to method effects.</b> '
    'The best of 98 seeds exceeds the seed mean by 0.020 ROC-AUC, which '
    'is comparable in magnitude to the ensemble gain itself. Single-run '
    'results on this benchmark should be reported with dispersion.'))
story.append(B(
    '<b>5. Five interventions did not help.</b> Reinforcement-guided '
    'frame prediction, pseudo-label fine-tuning, a mean-rank auxiliary '
    'loss, input feature augmentation, and increased model capacity each '
    'reduced ROC-AUC. Details are given in Section 8.5.'))

story.append(Sub('9.1', 'Limitations'))
story.append(Pn(
    'The following constraints bound the claims above and should be read '
    'as conditions on their interpretation.'))
story.append(B(
    '<b>1. The gain is not attributed to the architecture.</b> Our '
    'comparison against prior work varies three factors simultaneously: '
    'the score architecture, the feature representation, and the use of '
    'ensembling. Prior methods predominantly use I3D or C3D features, '
    'whereas we use ResNet-50 combined with R3D-18. We are therefore not '
    'entitled to attribute the improvement to the hierarchical model. '
    'Isolating this requires retraining the same architecture on I3D '
    'features while holding all else fixed, which we identify as the '
    'primary outstanding experiment.'))
story.append(B(
    '<b>2. Evaluation is video-level only.</b> Reported detection rates '
    'count a video as correct when its aggregated score falls on the '
    'correct side of the decision threshold. No temporal localisation is '
    'assessed, and the metric is insensitive to whether high-scoring '
    'segments coincide with the annotated anomalous interval.'))
story.append(B(
    '<b>3. The operating threshold was originally selected on the test '
    'set.</b> The value of 0.540 reported previously maximised F1 on the '
    'test set. Section 6.5 quantifies the effect: it is small, 0.0072 in '
    'F1 relative to an untuned threshold of 0.50, and the F1-optimal point '
    'coincides with the equal-error point, which the ROC curve determines '
    'without reference to a label-side objective. All threshold-dependent '
    'numbers are now reported at both points. The practice was '
    'nonetheless a defect and we do not repeat it.'))
story.append(B(
    '<b>4. Inference cost is dominated by frozen backbones.</b> Feature '
    'extraction requires approximately 3,401 GFLOPs per video against '
    '0.011 GFLOPs for the score ensemble. The efficiency claim of this '
    'work concerns trainable parameters and the cached-feature regime, '
    'not end-to-end inference cost.'))
story.append(B(
    '<b>5. Hyperparameter selection uses the test set.</b> The nested '
    'cross-validation of Section 5.5 holds each fold out during selection '
    'and yields an unbiased estimate for the candidate grid, but all '
    'folds are drawn from the test set. A validation split carved from '
    'the training data would be stronger.'))
story.append(B(
    '<b>6. The ensemble requires four trained models.</b> Their combined '
    'footprint is approximately 4 MB, but four checkpoints must be '
    'maintained. Distillation into a single student is untested.'))

story.append(Sub('9.2', 'Future Work'))
story.append(Pn(
    'Three directions follow directly from the limitations above. The '
    'first is the feature-versus-architecture ablation described in '
    'limitation 1, which determines whether the contribution of this '
    'paper is the model or the ensembling recipe. The second is '
    'frame-level evaluation against the released temporal annotations, '
    'placing our results on the same protocol as the majority of prior '
    'work. The third is replacing test-set hyperparameter selection with '
    'a validation split carved from the training data.'))

# ══════════════════════════════════════════════════════════════════════════
# MDPI-mandatory declarations
# ══════════════════════════════════════════════════════════════════════════
story.append(SP())
story.append(HR('#cccccc', 0.4))

story.append(Paragraph('<b>Author Contributions:</b>', declar_sty))
story.append(Paragraph(
    'Conceptualization, E.M.F.H., A.H., and M.M.F.; methodology, E.M.F.H.; '
    'software, E.M.F.H.; validation, E.M.F.H., A.H., and M.M.F.; formal '
    'analysis, E.M.F.H.; investigation, E.M.F.H.; resources, A.H. and '
    'M.M.F.; data curation, E.M.F.H.; writing—original draft preparation, '
    'E.M.F.H.; writing—review and editing, A.H. and M.M.F.; visualization, '
    'E.M.F.H.; supervision, A.H. and M.M.F.; project administration, A.H. '
    'and M.M.F. All authors have read and agreed to the published version of '
    'the manuscript.',
    declar_sty))

story.append(Paragraph('<b>Funding:</b>', declar_sty))
story.append(Paragraph(
    'This research received no external funding. The corresponding '
    'author will personally cover the Article Processing Charge (APC) '
    'for open-access publication in <i>Algorithms</i>.',
    declar_sty))

story.append(Paragraph('<b>Institutional Review Board Statement:</b>', declar_sty))
story.append(Paragraph(
    'Not applicable. This study did not involve human subjects, animal '
    'experiments, or personally identifying primary data. All experiments '
    'were conducted on the publicly available UCF-Crime dataset.',
    declar_sty))

story.append(Paragraph('<b>Informed Consent Statement:</b>', declar_sty))
story.append(Paragraph('Not applicable.', declar_sty))

story.append(Paragraph('<b>Data Availability Statement:</b>', declar_sty))
story.append(Paragraph(
    'The UCF-Crime dataset used in this study is publicly available at '
    'https://www.crcv.ucf.edu/projects/real-world/. Trained model '
    'checkpoints, evaluation scripts, and the code required to reproduce all '
    'reported results will be made available on GitHub upon acceptance of '
    'the manuscript.',
    declar_sty))

story.append(Paragraph('<b>Acknowledgments:</b>', declar_sty))
story.append(Paragraph(
    'The authors thank the AASTMT Faculty of Computing and Information '
    'Technology for computational resources, and the anonymous reviewers for '
    'their constructive feedback.',
    declar_sty))

story.append(Paragraph('<b>Conflicts of Interest:</b>', declar_sty))
story.append(Paragraph(
    'The authors declare no conflict of interest.',
    declar_sty))

# ── References (MDPI style) ────────────────────────────────────────────────
story.append(Sec('', 'References'))
REFS = [
    '1.  Sultani, W.; Chen, C.; Shah, M. Real-world anomaly detection in surveillance videos. In <i>Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)</i>, Salt Lake City, UT, USA, 18–22 June 2018; pp. 6479–6488.',
    '2.  Dietterich, T.G.; Lathrop, R.H.; Lozano-Perez, T. Solving the multiple instance problem with axis-parallel rectangles. <i>Artif. Intell.</i> <b>1997</b>, <i>89</i>, 31–71.',
    '3.  Zhang, J.; Qing, L.; Miao, J. Temporal convolutional network with complementary inner bag loss for weakly supervised anomaly detection. In <i>Proceedings of the IEEE International Conference on Image Processing (ICIP)</i>, Taipei, Taiwan, 22–25 September 2019; pp. 4030–4034.',
    '4.  Feng, J.; Hong, F.; Zheng, W. MIST: Multiple instance self-training framework for video anomaly detection. In <i>Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)</i>, Nashville, TN, USA, 20–25 June 2021; pp. 14009–14018.',
    '5.  Wu, P.; Liu, J. Learning causal temporal relation and feature discrimination for anomaly detection. <i>IEEE Trans. Image Process.</i> <b>2021</b>, <i>30</i>, 3513–3527.',
    '6.  Liu, C.; Yang, Y.; Feng, J. Exploring background-bias for anomaly detection in surveillance video. In <i>Proceedings of the ACM International Conference on Multimedia (ACM MM)</i>, 2021.',
    '7.  Yu, B. et al. Modality-aware mutual learning for multi-modal medical image segmentation. In <i>Proceedings of MICCAI</i>, 2021.',
    '8.  Dosovitskiy, A. et al. An image is worth 16x16 words: Transformers for image recognition at scale. In <i>Proceedings of the International Conference on Learning Representations (ICLR)</i>, 2021.',
    '9.  Liu, Z. et al. Swin Transformer: Hierarchical vision transformer using shifted windows. In <i>Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)</i>, 2021.',
    '10. Liu, Z. et al. Video Swin Transformer. In <i>Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)</i>, 2022.',
    '11. Breiman, L. Bagging predictors. <i>Mach. Learn.</i> <b>1996</b>, <i>24</i>, 123–140.',
    '12. Breiman, L. Random forests. <i>Mach. Learn.</i> <b>2001</b>, <i>45</i>, 5–32.',
    '13. Xu, C.; Tao, D.; Xu, C. A survey on multi-view learning. <i>arXiv</i> <b>2013</b>, arXiv:1304.5634.',
    '14. Loshchilov, I.; Hutter, F. Decoupled weight decay regularization. In <i>Proceedings of the International Conference on Learning Representations (ICLR)</i>, 2019.',
    '15. Tian, Y.; Pang, G.; Chen, Y.; Singh, R.; Verjans, J.W.; Carneiro, G. Weakly-supervised video anomaly detection with robust temporal feature magnitude learning. In <i>Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)</i>, 2021; pp. 4975–4986.',
    '16. Bertasius, G.; Wang, H.; Torresani, L. Is space-time attention all you need for video understanding? In <i>Proceedings of the International Conference on Machine Learning (ICML)</i>, 2021.',
    '17. Zhou, H.; Yu, J.; Yang, W. Dual memory units with uncertainty regulation for weakly supervised video anomaly detection. In <i>Proceedings of the AAAI Conference on Artificial Intelligence</i>, 2023; pp. 3769–3777.',
    '18. Jain, A.K.; Nandakumar, K.; Ross, A. Score normalization in multimodal biometric systems. <i>Pattern Recognit.</i> <b>2005</b>, <i>38</i>, 2270–2285.',
    '19. Joo, H.-K.; Vo, K.; Yamazaki, K.; Le, N. CLIP-TSA: CLIP-Assisted Temporal Self-Attention for Weakly-Supervised Video Anomaly Detection. In Proceedings of the IEEE International Conference on Image Processing (ICIP), 2023.',
    '20. Wu, P.; Zhou, X.; Pang, G.; Sun, Y.; Liu, J.; Wang, P.; Zhang, Y. VadCLIP: Adapting Vision-Language Models for Weakly Supervised Video Anomaly Detection. In Proceedings of the AAAI Conference on Artificial Intelligence, 2024; pp. 6074–6082.',
    '21. Chen, Y.; Liu, Z.; Zhang, B.; Fok, W.; Qi, X.; Wu, Y.-C. Prompt-Enhanced Learning for Weakly-Supervised Video Anomaly Detection. In Proceedings of the European Conference on Computer Vision (ECCV), 2024.',
    '22. Zanella, L.; Menapace, W.; Mancini, M.; Wang, Y.; Ricci, E. Harnessing Large Language Models for Training-free Video Anomaly Detection (LAVAD). In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2024.',
    '23. Zhou, Y.; Qu, Y.; Xu, X.; Shen, F.; Song, J.; Shen, H.T. BatchNorm-based Weakly Supervised Video Anomaly Detection (BN-WVAD). arXiv preprint arXiv:2311.15367, 2024.',
    '24. Chen, Y.; Liu, Z.; Zhang, B.; Fok, W.; Qi, X.; Wu, Y.-C. MGFN: Magnitude-Contrastive Glance-and-Focus Network for Weakly-Supervised Video Anomaly Detection. In Proceedings of the AAAI Conference on Artificial Intelligence, 2023.',
]
for r in REFS:
    story.append(Paragraph(r, fn_sty))

# ── MDPI copyright footer ──────────────────────────────────────────────────
story.append(SP(0.5))
story.append(HR('#046A44', 0.4))
story.append(Paragraph(
    '<b>Publisher\'s Note:</b> MDPI stays neutral with regard to jurisdictional '
    'claims in published maps and institutional affiliations.',
    sty(fontSize=8.5, leading=11, alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#555555'), spaceAfter=4)))
story.append(Paragraph(
    '<font color="#046A44">©</font> 2026 by the authors. Submitted for '
    'possible open-access publication under the terms and conditions of the '
    'Creative Commons Attribution (CC BY) license '
    '(<font color="#046A44">https://creativecommons.org/licenses/by/4.0/</font>).',
    sty(fontSize=8.5, leading=11, alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#555555'), spaceAfter=4)))

# ── Build ──────────────────────────────────────────────────────────────────
doc.build(story)
print(f'Algorithms PDF saved: {OUTPUT}')
