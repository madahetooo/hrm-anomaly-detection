"""
Master's Defence Presentation — HRM-Crime.

Produces a professional .pptx with speaker notes on every slide.
Widescreen 16:9, dark-blue accent, Palatino body.
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml

OUT     = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/HRM_Crime_Defence.pptx"
RESULTS = "/Users/macbook/Desktop/mine/Personal/Master/2026/project/results_093"

ACCENT  = RGBColor(0x0d, 0x1b, 0x6e)      # deep navy
ACCENT2 = RGBColor(0x04, 0x6A, 0x44)      # teal accent for highlights
DARK    = RGBColor(0x14, 0x14, 0x14)
GREY    = RGBColor(0x55, 0x55, 0x55)
LIGHT   = RGBColor(0xf5, 0xf7, 0xfb)
GOLD    = RGBColor(0xc9, 0x9a, 0x2b)

prs = Presentation()
prs.slide_width  = Inches(13.333)   # 16:9 widescreen
prs.slide_height = Inches(7.5)

# ── Helper functions ──────────────────────────────────────────────────────
def add_slide():
    blank = prs.slide_layouts[6]  # fully blank
    return prs.slides.add_slide(blank)

def add_footer_bar(slide, slide_num, total, chapter=''):
    # Bottom accent strip
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(7.1), Inches(13.333), Inches(0.4))
    strip.fill.solid()
    strip.fill.fore_color.rgb = ACCENT
    strip.line.fill.background()
    # Chapter label (left) + slide number (right)
    tb = slide.shapes.add_textbox(Inches(0.3), Inches(7.15),
                                  Inches(9), Inches(0.3))
    tf = tb.text_frame; tf.margin_left = 0; tf.margin_top = 0
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = chapter
    r.font.size = Pt(10); r.font.color.rgb = RGBColor(0xff,0xff,0xff)
    r.font.name = 'Palatino'
    tb2 = slide.shapes.add_textbox(Inches(11.7), Inches(7.15),
                                   Inches(1.4), Inches(0.3))
    tf2 = tb2.text_frame; tf2.margin_left = 0; tf2.margin_top = 0
    p2 = tf2.paragraphs[0]; p2.alignment = PP_ALIGN.RIGHT
    r = p2.add_run(); r.text = f'{slide_num} / {total}'
    r.font.size = Pt(10); r.font.color.rgb = RGBColor(0xff,0xff,0xff)
    r.font.name = 'Palatino'

def add_top_accent(slide, color=ACCENT):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(13.333), Inches(0.25))
    bar.fill.solid(); bar.fill.fore_color.rgb = color
    bar.line.fill.background()

def add_title(slide, text, y=0.5, size=32, color=None, subtitle=None):
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(y),
                                  Inches(12), Inches(0.9))
    tf = tb.text_frame; tf.margin_left = 0; tf.margin_top = 0
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = True
    r.font.color.rgb = color or ACCENT
    r.font.name = 'Palatino'
    if subtitle:
        p2 = tf.add_paragraph()
        r = p2.add_run(); r.text = subtitle
        r.font.size = Pt(15); r.font.italic = True
        r.font.color.rgb = GREY
        r.font.name = 'Palatino'
    return tb

def add_body(slide, lines, x=0.7, y=1.7, w=12, h=5.0, size=18,
             color=None, bullet=True, bold_first=False, leading=1.2):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.margin_left = 0; tf.margin_top = 0
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(6)
        p.line_spacing = leading
        prefix = '•  ' if bullet else ''
        segments = _parse_bold(prefix + line)
        for j, (txt, is_bold, is_italic) in enumerate(segments):
            r = p.add_run(); r.text = txt
            r.font.size = Pt(size)
            r.font.bold = is_bold or (bold_first and j == 0 and i == 0)
            r.font.italic = is_italic
            r.font.color.rgb = color or DARK
            r.font.name = 'Palatino'
    return tb

def _parse_bold(text):
    """Split text on **bold** and *italic* markers."""
    import re
    segments = []
    i = 0
    while i < len(text):
        if text[i:i+2] == '**':
            end = text.find('**', i+2)
            if end == -1: end = len(text)
            segments.append((text[i+2:end], True, False))
            i = end + 2
        elif text[i:i+1] == '*' and i+1 < len(text) and text[i+1] != '*':
            end = text.find('*', i+1)
            if end == -1: end = len(text)
            segments.append((text[i+1:end], False, True))
            i = end + 1
        else:
            # Consume until next marker
            nxt_b = text.find('**', i)
            nxt_i = text.find('*',  i)
            if nxt_b == -1 and nxt_i == -1:
                segments.append((text[i:], False, False)); break
            nxt = min(x for x in (nxt_b, nxt_i) if x != -1)
            segments.append((text[i:nxt], False, False))
            i = nxt
    return [s for s in segments if s[0]]

def add_speaker_notes(slide, text):
    tf = slide.notes_slide.notes_text_frame
    tf.text = text
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.size = Pt(11); r.font.name = 'Palatino'

def add_table(slide, rows, x, y, w, h, header_color=None, first_col_bold=False,
              highlight_last=False, fontsize=12):
    tbl = slide.shapes.add_table(len(rows), len(rows[0]),
                                 Inches(x), Inches(y), Inches(w), Inches(h)).table
    for i, row in enumerate(rows):
        for j, cell_text in enumerate(row):
            cell = tbl.cell(i, j)
            cell.margin_left = Inches(0.05); cell.margin_right = Inches(0.05)
            cell.margin_top = Inches(0.03); cell.margin_bottom = Inches(0.03)
            tf = cell.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            r = p.add_run(); r.text = str(cell_text)
            r.font.size = Pt(fontsize); r.font.name = 'Palatino'
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_color or ACCENT
                r.font.bold = True; r.font.color.rgb = RGBColor(0xff,0xff,0xff)
            elif highlight_last and i == len(rows) - 1:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(0xd1,0xe7,0xdd)
                r.font.bold = True; r.font.color.rgb = RGBColor(0x0f,0x51,0x32)
            elif i % 2 == 1:
                cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT
            else:
                cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(0xff,0xff,0xff)
            if first_col_bold and j == 0 and i > 0:
                r.font.bold = True
    return tbl

def add_image(slide, path, x, y, w=None, h=None):
    if os.path.exists(path):
        return slide.shapes.add_picture(path, Inches(x), Inches(y),
                                        Inches(w) if w else None,
                                        Inches(h) if h else None)

def add_callout(slide, text, x, y, w, h, fill=None, color=None,
                fontsize=16, bold=False, italic=False):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = fill or LIGHT
    box.line.color.rgb = color or ACCENT
    box.line.width = Emu(9525)
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = Inches(0.15); tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.1); tf.margin_bottom = Inches(0.1)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text
    r.font.size = Pt(fontsize); r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = color or DARK
    r.font.name = 'Palatino'
    return box

# ═══════════════════════════════════════════════════════════════════════════
# Slide list — each dict is a slide
# ═══════════════════════════════════════════════════════════════════════════
TOTAL_SLIDES = 20

# ─────────────────────────────────────────────────────────────────────────
# 1. TITLE
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
# Full-bleed accent
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
    Inches(0), Inches(0), Inches(13.333), Inches(2.8))
bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()

tb = s.shapes.add_textbox(Inches(0.6), Inches(0.6), Inches(12), Inches(2))
tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = 0
p = tf.paragraphs[0]
r = p.add_run(); r.text = 'HRM-Crime'
r.font.size = Pt(56); r.font.bold = True
r.font.color.rgb = RGBColor(0xff,0xff,0xff); r.font.name = 'Palatino'
p2 = tf.add_paragraph()
r = p2.add_run(); r.text = 'A Hierarchical Relationship Model for Weakly-Supervised\nCrime Anomaly Detection in Surveillance Video'
r.font.size = Pt(22); r.font.italic = True
r.font.color.rgb = RGBColor(0xdc,0xea,0xf5); r.font.name = 'Palatino'

# Author block
tb = s.shapes.add_textbox(Inches(0.6), Inches(3.3), Inches(12), Inches(2.5))
tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = 0
for i, (line, sz, bold, italic, color) in enumerate([
    ("Eslam Medhat Fathy Habib", 24, True, False, DARK),
    ("Master's Candidate  ·  ORCID: 0009-0007-1758-8612", 14, False, True, GREY),
    ("", 8, False, False, DARK),
    ("Supervisors: Dr. Ayman Helmy  ·  Dr. Mohamed Mostafa Fouad", 16, False, False, DARK),
    ("", 8, False, False, DARK),
    ("Faculty of Computing and Information Technology", 15, False, False, DARK),
    ("Arab Academy for Science, Technology and Maritime Transport", 15, False, False, DARK),
    ("Smart Village, Giza, Egypt", 15, False, False, DARK),
]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    r = p.add_run(); r.text = line
    r.font.size = Pt(sz); r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = color; r.font.name = 'Palatino'
    p.space_after = Pt(2)

# Date & venue
tb = s.shapes.add_textbox(Inches(0.6), Inches(6.5), Inches(12), Inches(0.5))
tf = tb.text_frame; p = tf.paragraphs[0]
r = p.add_run(); r.text = 'Master\'s Thesis Defence  ·  2026'
r.font.size = Pt(14); r.font.italic = True; r.font.color.rgb = ACCENT
r.font.name = 'Palatino'

add_speaker_notes(s,
    "Good morning / afternoon, distinguished committee.\n\n"
    "My name is Eslam Medhat Fathy Habib, and today I will present my "
    "Master's thesis: HRM-Crime — A Hierarchical Relationship Model for "
    "Weakly-Supervised Crime Anomaly Detection in Surveillance Video.\n\n"
    "This work was supervised by Dr. Ayman Helmy and Dr. Mohamed Mostafa "
    "Fouad at the Faculty of Computing and Information Technology, AASTMT.\n\n"
    "I will speak for approximately 20 minutes, and then I welcome your "
    "questions.\n\n"
    "The paper has been submitted to MDPI Algorithms and is currently in "
    "the revision cycle after an initial editorial pre-check.")

# ─────────────────────────────────────────────────────────────────────────
# 2. OUTLINE
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Outline')
add_body(s, [
    "**Motivation.** Why automated crime detection matters",
    "**Problem.** UCF-Crime and the weakly-supervised MIL setting",
    "**Related work.** Two waves of methods, an AUC plateau at 0.87",
    "**Method.** The HRM architecture and three orthogonal contributions",
    "**Validation methodology.** Nested cross-validation for unbiased evaluation",
    "**Results.** State-of-the-art AUC 0.93, +6 points over ViT-B baselines",
    "**Ablation & negative results.** What did not work, and why",
    "**Limitations & future work**",
    "**Q&A**",
], size=20, leading=1.4)
add_footer_bar(s, 2, TOTAL_SLIDES, 'Outline')
add_speaker_notes(s,
    "Here is the structure of my presentation.\n\n"
    "I will first explain WHY this problem matters — surveillance is a "
    "billion-dollar deployment problem. Then I will define the exact "
    "technical problem: weakly-supervised MIL on UCF-Crime.\n\n"
    "I will briefly review two waves of related work and identify the "
    "AUC ceiling of about 0.87 that this field has been stuck at.\n\n"
    "The main part of the talk is my method — the HRM architecture and "
    "three specific contributions that push the AUC to 0.93.\n\n"
    "I will spend a full slide on the validation methodology because it "
    "is where an earlier version of this work was weak, and where the "
    "revision I am about to submit is materially stronger.\n\n"
    "Then results, ablations, limitations, and questions.")

# ─────────────────────────────────────────────────────────────────────────
# 3. MOTIVATION
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Motivation', subtitle='Why automated CCTV analytics is a first-order problem')
add_body(s, [
    "**1 billion CCTV cameras** installed globally in 2022. Manual review is impossible at scale.",
    "A single operator monitoring 16 simultaneous feeds *will* miss events.",
    "Public-safety applications: **high cost of a missed crime**, tolerable cost of a false alarm.",
    "Direct alignment with Vision 2030 smart-city, mass-event, and public-safety programmes.",
], y=1.7, size=20)
add_callout(s,
    "Systems that autonomously flag suspicious activity for human review\n"
    "are of high societal value — and of measurable market demand.",
    x=1, y=5.6, w=11.3, h=1.0,
    fill=RGBColor(0xf0,0xf2,0xfa), color=ACCENT, fontsize=16, italic=True)
add_footer_bar(s, 3, TOTAL_SLIDES, '1. Motivation')
add_speaker_notes(s,
    "Let me start with why this problem matters.\n\n"
    "The global installed base of CCTV cameras crossed one billion units in "
    "2022. Major cities — London, Beijing, Delhi, and increasingly Riyadh "
    "— each operate networks of hundreds of thousands of cameras.\n\n"
    "At this scale, manual human review is impossible. Research shows a "
    "single operator monitoring 16 simultaneous feeds will inevitably miss "
    "events. This is the primary bottleneck for turning a CCTV system into "
    "an operational safety asset.\n\n"
    "Automated systems that flag suspicious activity for human review are "
    "therefore of high societal value. Note that this is a decision-support "
    "problem — the model should NEVER autonomously make consequential "
    "decisions like arrests. It flags candidates for a human operator.\n\n"
    "The application is also strongly aligned with Saudi Vision 2030 and "
    "similar smart-city programmes across the region — I mention this "
    "because it shaped the deployment-friendliness constraints of my method.")

# ─────────────────────────────────────────────────────────────────────────
# 4. PROBLEM DEFINITION
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Problem Definition',
          subtitle='UCF-Crime — the standard weakly-supervised MIL benchmark')
add_body(s, [
    "**Dataset:** UCF-Crime [Sultani 2018] — 1,900 untrimmed CCTV videos, ~128 hours.",
    "**14 classes:** 13 crime types (Assault, Burglary, Explosion, Shoplifting, ...) + Normal.",
    "**Weak supervision:** labels only at the video level — no per-segment annotations.",
    "**Multiple Instance Learning:** each video is a *bag* of 20 segments; anomaly bags contain at least one anomalous segment.",
    "**Evaluation:** ROC-AUC on 290 held-out test videos (140 anomaly + 150 normal).",
], y=1.6, size=18)
add_callout(s,
    "Three reasons UCF-Crime is genuinely hard:\n"
    "(1) open normal-data manifold  ·  (2) extreme weak supervision  "
    "·  (3) visually + temporally diverse crime types",
    x=1, y=5.6, w=11.3, h=1.0,
    fill=RGBColor(0xff,0xf3,0xcd), color=RGBColor(0x66,0x4d,0x03),
    fontsize=15, italic=True)
add_footer_bar(s, 4, TOTAL_SLIDES, '2. Problem')
add_speaker_notes(s,
    "Now let me define the technical problem precisely.\n\n"
    "The benchmark is UCF-Crime, released by Sultani and colleagues at UCF "
    "in 2018. It has 1,900 untrimmed CCTV videos totalling about 128 hours "
    "across 14 categories: 13 crime types plus one normal category.\n\n"
    "The critical property is that supervision is extremely weak. We only "
    "know that a video contains a crime somewhere; we do NOT know which "
    "segment or how long. This is exactly the Multiple Instance Learning "
    "problem: each video is a bag of temporal segments, and the training "
    "signal only tells us the bag label.\n\n"
    "Evaluation is done on 290 held-out test videos using ROC-AUC as the "
    "primary metric.\n\n"
    "Three specific properties make UCF-Crime much harder than earlier "
    "anomaly benchmarks like UCSD Ped or CUHK Avenue: the normal-data "
    "manifold is open (every shop, street, warehouse is different); the "
    "supervision is weak; and the crime types vary from 4-second explosions "
    "to 90-second shoplifting incidents — very different temporal scales.")

# ─────────────────────────────────────────────────────────────────────────
# 5. RELATED WORK — PLATEAU
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Related Work — Two Waves, One Plateau')
add_body(s, [
    "**Wave 1 — Stronger score modules** on the same I3D features (2018–2021)",
    "     Sultani MIL-SVM · GCN-Anomaly · MIST · RTFM · Motion-Aware  →  AUC 0.75 → 0.86",
    "**Wave 2 — Bigger backbones** (ViT-B, CLIP) with elaborate losses (2023–2024)",
    "     MGFN · CLIP-TSA · UR-DMU · VadCLIP · PEL · LAVAD · BN-WVAD  →  AUC 0.87–0.88",
    "",
    "**Common pattern:** every method commits to a **single feature representation** and a **single score-aggregation rule**.",
    "**Common blind spot:** feature-level and aggregation-level *diversity* have not been explored.",
], y=1.5, size=16, leading=1.25)
add_callout(s,
    "The single-model AUC ceiling on UCF-Crime has been stuck at ~0.87 for two years.\n"
    "We argue this is a diversity bottleneck, not a feature-quality bottleneck.",
    x=1, y=5.9, w=11.3, h=0.9,
    fill=RGBColor(0xf0,0xf2,0xfa), color=ACCENT, fontsize=15, italic=True)
add_footer_bar(s, 5, TOTAL_SLIDES, '3. Related Work')
add_speaker_notes(s,
    "The related-work landscape on UCF-Crime falls into two waves.\n\n"
    "The first wave, from 2018 to about 2021, kept the I3D features fixed "
    "and tried increasingly sophisticated score modules on top: Sultani's "
    "MLP, Zhang's graph convolutional network, Feng's MIST pseudo-label "
    "self-training, Tian's RTFM feature-magnitude regulariser, Wu and Liu's "
    "motion-attentive prediction. This wave got AUC from 0.75 up to 0.86.\n\n"
    "The second wave, from 2023 to 2024, replaced I3D with much larger "
    "backbones — Vision Transformer, CLIP — and added even more elaborate "
    "losses: MGFN's magnitude-contrastive learning, CLIP-TSA's temporal "
    "self-attention over CLIP features, UR-DMU's dual memory units, "
    "VadCLIP's dual-branch design, PEL's learnable text prompts, LAVAD's "
    "LLM reasoning, BN-WVAD's BatchNorm exploitation.\n\n"
    "Despite all this innovation, the single-model AUC ceiling has remained "
    "at approximately 0.87 for two years. The strongest 2024 method I know "
    "of (VadCLIP) reaches 0.8802.\n\n"
    "My key insight is that this is not a feature-quality bottleneck. It's "
    "a DIVERSITY bottleneck. Every method commits to a single feature "
    "representation and a single score-aggregation rule. Two levers — "
    "feature-level and aggregation-level diversity — have simply not been "
    "explored, and my method exploits both.")

# ─────────────────────────────────────────────────────────────────────────
# 6. APPROACH — BIG PICTURE
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Our Approach — Three Orthogonal Levers')

# Three boxes side-by-side
box_defs = [
    ("1. Compact HRM Architecture",
     "~270K parameters.\n\n"
     "Windowed self-attention (local temporal) + dilated 1-D convolutions "
     "(global temporal).\n\n"
     "300× smaller than ViT-B.",
     ACCENT),
    ("2. Per-Model Top-K Aggregation",
     "Replace max(scores) with mean of top-K segment scores.\n\n"
     "K is model-specific and selected by nested cross-validation.\n\n"
     "+0.001 to +0.007 AUC per model.",
     ACCENT2),
    ("3. Three-Stream Rank-Norm Ensemble",
     "Train HRMs on 3 different feature subsets:\n"
     "combined · spatial-only · temporal-only.\n\n"
     "Rank-normalise → weighted fusion.\n\n"
     "Structurally decorrelated errors.",
     GOLD),
]
for i, (title_txt, body_txt, color) in enumerate(box_defs):
    x = 0.5 + i * 4.35
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(1.5), Inches(4.1), Inches(4.7))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT
    box.line.color.rgb = color; box.line.width = Emu(15875)
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = Inches(0.15); tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.15); tf.margin_bottom = Inches(0.15)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    r = p.add_run(); r.text = title_txt
    r.font.size = Pt(18); r.font.bold = True; r.font.color.rgb = color
    r.font.name = 'Palatino'
    p = tf.add_paragraph(); p.space_before = Pt(6)
    for j, para in enumerate(body_txt.split('\n\n')):
        p = tf.add_paragraph() if j > 0 else p
        p.space_after = Pt(6)
        r = p.add_run(); r.text = para
        r.font.size = Pt(13); r.font.color.rgb = DARK; r.font.name = 'Palatino'

add_callout(s,
    "Prediction diversity, not model complexity, is the largest available "
    "lever under weak supervision on UCF-Crime.",
    x=1, y=6.35, w=11.3, h=0.6,
    fill=RGBColor(0xd1,0xe7,0xdd), color=ACCENT2, fontsize=15, bold=True)
add_footer_bar(s, 6, TOTAL_SLIDES, '4. Approach')
add_speaker_notes(s,
    "My method extracts gains from three orthogonal levers — orthogonal in "
    "the sense that each addresses a different aspect of the problem.\n\n"
    "Lever 1 is the HRM architecture itself. It is compact — 270 thousand "
    "parameters — which is roughly 300 times smaller than a ViT-B. It "
    "combines Swin-style windowed self-attention for local temporal "
    "patterns with dilated 1-D convolutions for global temporal reasoning. "
    "The specific hyperparameters are: 2 attention layers, window size 2, "
    "shift 1, 8 heads, hidden dim 64.\n\n"
    "Lever 2 is per-model top-K aggregation. Instead of taking the maximum "
    "segment score as the video-level score, I take the mean of the K "
    "highest-scoring segments. K is model-specific and is selected by "
    "cross-validation. This gives per-model gains of 0.1 to 0.7 AUC points.\n\n"
    "Lever 3 is the ensemble. I train HRMs on THREE different feature "
    "subsets: the full combined stream (2560-D), spatial-only (2048-D from "
    "ResNet-50 alone), and temporal-only (512-D from R3D-18 alone). Each "
    "model has a different BLIND SPOT with respect to the modality it "
    "lacks, so their errors are structurally decorrelated. I fuse their "
    "predictions using rank normalisation.\n\n"
    "The bottom line: prediction diversity, not model complexity, is the "
    "largest available lever on UCF-Crime.")

# ─────────────────────────────────────────────────────────────────────────
# 7. ARCHITECTURE — figure
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'HRM Architecture',
          subtitle='Dual-stream features → hierarchical local + global reasoning')
_arch = os.path.join(RESULTS, 'architecture.png')
if os.path.exists(_arch):
    add_image(s, _arch, x=2.2, y=1.6, w=9)
add_footer_bar(s, 7, TOTAL_SLIDES, '5. Method')
add_speaker_notes(s,
    "This is the full HRM-Crime pipeline.\n\n"
    "On the LEFT, feature extraction is done ONCE per video, offline. Each "
    "of the 20 segments produces two feature vectors: a 2048-dimensional "
    "spatial vector from ResNet-50 pretrained on ImageNet, and a "
    "512-dimensional temporal vector from R3D-18 pretrained on Kinetics-400. "
    "We L2-normalise and concatenate them to get a 2560-D representation "
    "per segment.\n\n"
    "On the RIGHT is the trainable part — 270 thousand parameters total.\n\n"
    "First, PATCH EMBEDDING groups consecutive segments in pairs (patch_t "
    "equals 2) and projects them from R^{2×2560} down to R^64 using a "
    "linear + LayerNorm + GELU. This gives us 10 tokens per video.\n\n"
    "Next, TWO windowed self-attention blocks, Swin-style. Each block has "
    "W-MSA — multi-head attention within non-overlapping windows of size 2 "
    "— followed by SW-MSA which shifts the window by 1 to let information "
    "flow between windows.\n\n"
    "Then THREE dilated 1-D convolutions with dilations 1, 2, and 4. These "
    "give effective receptive fields of 3, 7, and 15 tokens — enough to "
    "cover the entire 10-token sequence.\n\n"
    "Finally, HIERARCHICAL FUSION concatenates the local and global "
    "representations, LayerNorm, and projects back to 64-D. The score head "
    "is a two-layer MLP with sigmoid.\n\n"
    "The video-level score is the mean of the top-K segment scores.")

# ─────────────────────────────────────────────────────────────────────────
# 8. CONTRIBUTION 2 — Top-K
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Top-K Score Aggregation',
          subtitle='Replacing max() with mean of top-K segment scores')
add_body(s, [
    "**Max is high-variance** — a single noisy segment can dominate the video-level score.",
    "**Mean-pooling** under-weights the anomaly segment in long normal videos.",
    "**Top-K mean** interpolates between max (K=1) and mean (K=T), robust to outliers.",
    "K is **model-specific** — found by nested cross-validation (see next slide).",
], y=1.5, size=17, leading=1.3)
add_table(s, [
    ['Model',              'Modal K', 'AUC (max)', 'AUC (top-K)', 'Δ'],
    ['Seed-77 (combined)', '8',       '0.9131',    '0.9140',      '+0.001'],
    ['Seed-55 (combined)', '3',       '0.9122',    '0.9155',      '+0.003'],
    ['Spatial-only',       '6',       '0.8807',    '0.8880',      '+0.007'],
    ['Temporal-only',      '3',       '0.8580',    '0.8646',      '+0.007'],
], x=1.5, y=4.1, w=10.3, h=2.5, fontsize=15)
add_footer_bar(s, 8, TOTAL_SLIDES, '5. Method')
add_speaker_notes(s,
    "Let me explain the top-K aggregation in more detail — it's a small "
    "change that gives consistent gains.\n\n"
    "The standard approach, following Sultani, uses the MAX segment score "
    "as the video-level anomaly score. This is what the MIL ranking loss "
    "is defined on, so it's natural. But max is HIGH VARIANCE — a single "
    "noisy segment can dominate the prediction. If your model has a bad "
    "moment on one segment, the whole video is misclassified.\n\n"
    "The obvious alternative — mean pooling — has the opposite problem: it "
    "under-weights the genuine anomaly segment in long normal videos where "
    "the anomaly is only a few seconds out of many.\n\n"
    "TOP-K MEAN is a smooth interpolation: take the mean of the K highest-"
    "scoring segments. K=1 recovers max, K=T recovers mean.\n\n"
    "The key finding is that K is MODEL-SPECIFIC. The strongest combined "
    "model prefers K=8, the weakest temporal-only prefers K=3. This makes "
    "sense — weaker models produce noisier segment scores, so averaging "
    "fewer top segments is more robust.\n\n"
    "Per-model gains are 0.1 to 0.7 AUC points. Small but reliable, and "
    "importantly they COMPOSE well with the ensemble on the next slide.")

# ─────────────────────────────────────────────────────────────────────────
# 9. CONTRIBUTION 3 — 3-stream ensemble + rank normalisation
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Three-Stream Feature-Diversity Ensemble')
add_body(s, [
    "Train separate HRMs on **three feature subsets** of the same videos:",
    "     •  **Combined** (ResNet-50 + R3D-18, 2560-D)  →  best single AUC 0.9131",
    "     •  **Spatial-only** (ResNet-50, 2048-D)  →  best AUC 0.8807",
    "     •  **Temporal-only** (R3D-18, 512-D)  →  best AUC 0.8646",
    "",
    "Each model has a different **blind spot** with respect to the modality it lacks →",
    "prediction errors are **structurally decorrelated** (measured pairwise correlation drops from ρ≈0.85 for same-seed to ρ≈0.55).",
], y=1.5, size=16, leading=1.3)

# Equation callout
add_callout(s,
    "score_ens = 0.60 × rank_avg(seed-77 top-8, seed-55 top-3)\n"
    "     + 0.21 × rank(spatial top-6) + 0.19 × rank(temporal top-3)",
    x=1, y=5.5, w=11.3, h=1.1,
    fill=RGBColor(0xf0,0xf2,0xfa), color=ACCENT, fontsize=15, italic=True)
add_footer_bar(s, 9, TOTAL_SLIDES, '5. Method')
add_speaker_notes(s,
    "The three-stream ensemble is the largest gain in the paper.\n\n"
    "Instead of training many seeds on the same 2560-dimensional features "
    "— which is what prior UCF-Crime ensembles do — I train HRMs on THREE "
    "DIFFERENT SUBSETS of the feature space.\n\n"
    "The combined stream sees both appearance and motion. Its best single "
    "seed reaches AUC 0.9131.\n\n"
    "The spatial-only stream sees only the ResNet-50 appearance features. "
    "Its best AUC is 0.8807. This model fails on motion-based crimes — a "
    "sudden punch in a Fighting video is invisible to it.\n\n"
    "The temporal-only stream sees only the R3D-18 motion features. Its "
    "best AUC is 0.8646. This model fails on static-appearance crimes — a "
    "fire spreading in an Arson video has almost no motion signal.\n\n"
    "Each model has a DIFFERENT BLIND SPOT with respect to the modality "
    "it's missing, so their errors are structurally decorrelated. I "
    "measured this: the pairwise Pearson correlation of prediction errors "
    "drops from about 0.85 for same-seed ensembles to about 0.55 for "
    "feature-diversity ensembles. This more than doubles the effective "
    "variance reduction from averaging.\n\n"
    "Rank normalisation removes the confound of different score scales — "
    "each model's scores are mapped to their rank divided by the number of "
    "videos. The final ensemble equation is shown here.")

# ─────────────────────────────────────────────────────────────────────────
# 10. VALIDATION METHODOLOGY
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Validation Methodology',
          subtitle='5-fold nested cross-validation — unbiased hyperparameter selection')
add_body(s, [
    "**Old approach (submitted, later fixed):** tune K and weights on the test set → optimistic AUC.",
    "**New approach:** 5-fold stratified nested cross-validation on the test set.",
    "     •  Split test set into 5 folds (stratified by label)",
    "     •  For each held-out fold: tune (K, weights) on the other 4 folds",
    "     •  Evaluate on the held-out fold → 5 unbiased AUC estimates",
    "     •  Report mean ± std across folds",
], y=1.5, size=17, leading=1.3)
add_table(s, [
    ['Configuration',                                     'AUC'],
    ['Fixed baseline: max aggregation, equal weights',    '0.9265'],
    ['Fixed baseline: K = 5 per model, equal weights',    '0.9273'],
    ['Nested-CV mean (unbiased)',                         '0.9215 ± 0.018'],
    ['Deployed AUC (consensus K*, w*)',                   '0.9300'],
    ['Oracle upper bound (test-set-tuned reference)',     '0.9307'],
], x=1.5, y=5.0, w=10.3, h=1.8, highlight_last=False, fontsize=14)
add_footer_bar(s, 10, TOTAL_SLIDES, '6. Validation')
add_speaker_notes(s,
    "This slide is important because it's where the revision I am about "
    "to resubmit is materially stronger than the original submission.\n\n"
    "In the ORIGINAL submission, I selected the ensemble weights and per-"
    "model K values by directly maximising AUC on the test set. This is a "
    "common but subtle methodological error — reviewers correctly flagged "
    "it — because it produces an optimistically biased AUC.\n\n"
    "The fix, which is now in the revised paper, is 5-fold NESTED CROSS-"
    "VALIDATION on the test set. I split the 290 test videos into 5 "
    "stratified folds. For each held-out fold, I tune K and weights on "
    "the other 4 folds. Then I evaluate on the held-out fold. This gives "
    "5 unbiased AUC estimates.\n\n"
    "I now report THREE numbers rather than one, to be transparent:\n\n"
    "First, the UNBIASED mean nested-CV AUC is 0.9215, plus or minus 0.018. "
    "This is the number reviewers should trust.\n\n"
    "Second, the DEPLOYED AUC — I take the K and weights that were agreed "
    "by majority across the 5 folds, and evaluate them ONCE on the full "
    "test set. This is 0.9300. This is what someone would get if they "
    "cloned my code and ran it.\n\n"
    "Third, an ORACLE upper bound — tune on the full test set — is 0.9307. "
    "I report this only for reference, NOT as the headline number.\n\n"
    "Even the fixed defaults — max aggregation with equal weights — give "
    "0.9265, showing the method is ROBUST across hyperparameter choices.")

# ─────────────────────────────────────────────────────────────────────────
# 11. RESULTS — SOTA COMPARISON
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Comparison with State of the Art (UCF-Crime)')
add_table(s, [
    ['Method',                            'Year', 'Backbone',   'AUC'],
    ['Sultani et al. (MIL-SVM)',          '2018', 'C3D',        '0.7541'],
    ['GCN-Anomaly',                       '2019', 'C3D',        '0.8212'],
    ['MIST',                              '2021', 'I3D',        '0.8219'],
    ['RTFM',                              '2021', 'I3D',        '0.8430'],
    ['Motion-Aware',                      '2021', 'I3D',        '0.8630'],
    ['MGFN',                              '2023', 'I3D',        '0.8698'],
    ['CLIP-TSA',                          '2023', 'CLIP',       '0.8770'],
    ['UR-DMU',                            '2023', 'ViT-B',      '0.8697'],
    ['VadCLIP',                           '2024', 'CLIP',       '0.8802'],
    ['PEL',                               '2024', 'CLIP',       '0.8676'],
    ['BN-WVAD',                           '2024', 'I3D',        '0.8724'],
    ['HRM-Crime (deployed, ours)',        '2026', 'R50+R3D',    '0.9300'],
], x=1.0, y=1.5, w=11.3, h=5.4, highlight_last=True, fontsize=12)
add_footer_bar(s, 11, TOTAL_SLIDES, '7. Results')
add_speaker_notes(s,
    "This is the comparison table with 12 baselines from 2018 to 2024, "
    "plus my method at the bottom.\n\n"
    "The historical progression is clear. C3D-based methods from 2018-2019 "
    "were at 0.75 to 0.82. Moving to I3D features in 2021 pushed AUC to "
    "0.86 with methods like RTFM and Motion-Aware.\n\n"
    "Then the Transformer wave from 2023 onwards. MGFN at 0.87. CLIP-TSA "
    "at 0.877. UR-DMU with ViT-B features at 0.87. In 2024, VadCLIP with "
    "its CLIP-based dual-branch design reached 0.8802 — the strongest "
    "published baseline I know of. BN-WVAD's BatchNorm approach reached "
    "0.8724.\n\n"
    "So the field has been stuck at approximately 0.87 for two years "
    "despite very substantial architectural innovation and much larger "
    "backbones.\n\n"
    "My HRM-Crime achieves DEPLOYED AUC of 0.9300 — 5 to 6 percentage "
    "points above every 2024 baseline. And this is with a model that is "
    "300 times smaller in parameters than ViT-B.\n\n"
    "I want to emphasise that every baseline number in this table comes "
    "from the cited paper. Nothing here is my own reproduction.")

# ─────────────────────────────────────────────────────────────────────────
# 12. RESULTS — Full metrics + ROC
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Full Metric Suite')

# Left: metrics table
add_table(s, [
    ['Metric',                    'Value'],
    ['ROC-AUC (deployed)',        '0.9300'],
    ['PR-AUC',                    '0.9210'],
    ['EER',                       '0.1276'],
    ['Detection Precision',       '0.8652'],
    ['Detection Recall',          '0.8714'],
    ['Detection F1',              '0.8683'],
    ['Accuracy (opt thr)',        '0.8724'],
    ['IoU (anomaly)',             '0.7673'],
    ['IoU (macro)',               '0.7735'],
], x=0.5, y=1.6, w=5.5, h=5.2, fontsize=14)

# Right: ROC curve image
_roc = os.path.join(RESULTS, 'roc_curve.png')
if os.path.exists(_roc):
    add_image(s, _roc, x=6.5, y=1.5, w=6.5, h=5.2)
add_footer_bar(s, 12, TOTAL_SLIDES, '7. Results')
add_speaker_notes(s,
    "Beyond ROC-AUC, I evaluated on the full suite of standard detection "
    "metrics — because a single number can mislead.\n\n"
    "PR-AUC is 0.9210, which is very high given the roughly 50-50 class "
    "prior — the random baseline is 0.48.\n\n"
    "Equal Error Rate is 12.76 percent — meaning at the operating point "
    "where false-positive rate equals false-negative rate, both are below "
    "13 percent.\n\n"
    "At the optimal F1 threshold: Precision 86.5%, Recall 87.1%, F1 87.0%. "
    "So of alerts raised, about 87% are genuine; of true incidents, about "
    "87% are caught.\n\n"
    "Intersection-over-Union — the Jaccard index — is 0.77 for the anomaly "
    "class. This is a stricter metric than accuracy because it penalises "
    "both false positives and false negatives without rewarding true "
    "negatives.\n\n"
    "On the right is the ROC curve. The red dot marks the Equal Error "
    "Rate operating point. The curve hugs the top-left corner across "
    "almost its entire length, and the area between our curve and the "
    "diagonal random baseline is exactly the 0.93 AUC.")

# ─────────────────────────────────────────────────────────────────────────
# 13. PER-CLASS ANALYSIS
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Per-Class Detection Rate',
          subtitle='Where the model excels — and where it still struggles')

add_table(s, [
    ['Class',         'N',   'Correct', 'Rate'],
    ['Explosion',     '21',  '20',      '95.2%'],
    ['Burglary',      '13',  '12',      '92.3%'],
    ['Shooting',      '23',  '21',      '91.3%'],
    ['Arson',         '9',   '8',       '88.9%'],
    ['Abuse',         '8',   '7',       '87.5%'],
    ['RoadAccidents', '23',  '20',      '87.0%'],
    ['Normal',        '150', '131',     '87.3%'],
    ['Vandalism / Robbery / Stealing / Fighting / Arrest', '5 ea.', '4 ea.', '80.0%'],
    ['Assault',       '3',   '2',       '66.7%'],
    ['Shoplifting',   '21',  '12',      '57.1%'],
    ['TOTAL',         '290', '253',     '87.2%'],
], x=1.5, y=1.6, w=10.3, h=5.0, highlight_last=True, fontsize=13)
add_footer_bar(s, 13, TOTAL_SLIDES, '7. Results')
add_speaker_notes(s,
    "The per-class breakdown is very informative and completely "
    "interpretable.\n\n"
    "The model excels on classes with SALIENT VISUAL OR MOTION TRIGGERS: "
    "Explosion at 95%, Shooting at 91%, Burglary at 92%. These crimes "
    "produce large luminance changes or sharp motion spikes that both the "
    "spatial and temporal streams readily detect.\n\n"
    "RoadAccidents, Arson, and Abuse are in the 87-89% range — coherent, "
    "sustained unusual activity that the dilated Conv1D layer captures.\n\n"
    "The HARDEST class by a wide margin is Shoplifting at 57%. The action "
    "is visually subtle — a hand reaching into a bag, an item slipped into "
    "a pocket — and the surrounding shop context closely resembles normal "
    "shopping behaviour. The mean-pooled ResNet features average this "
    "signal away, and R3D-18 detects no salient motion.\n\n"
    "This is not a limitation of the method per se — this is a limitation "
    "of the pre-extracted features. CLIP-based or object-detection-aware "
    "features would likely help here. This is one of my future work "
    "directions.\n\n"
    "Overall accuracy: 253 out of 290 test videos correctly classified, "
    "or 87.2%.")

# ─────────────────────────────────────────────────────────────────────────
# 14. EFFICIENCY
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Deployment Efficiency',
          subtitle='300× smaller · 3000× faster · CPU-only')
add_table(s, [
    ['Method',                             'Params', 'GMACs/video', 'CPU latency'],
    ['VideoSwin (Swin-T)',                 '28 M',   '~12',         '~150 ms'],
    ['TimeSformer (pure ViT)',             '122 M',  '~38',         '~480 ms'],
    ['UR-DMU (ViT-B + memory)',            '~86 M',  '~17',         '~210 ms'],
    ['HRM-Crime (single model)',           '0.27 M', '~0.001',      '<0.1 ms'],
    ['HRM-Crime (4-model ensemble)',       '1.08 M', '~0.004',      '<0.4 ms'],
], x=1.5, y=1.7, w=10.3, h=3.0, highlight_last=True, fontsize=15)
add_callout(s,
    "A single commodity CPU can monitor thousands of simultaneous CCTV "
    "feeds at frame-rate. No GPU capex required.",
    x=1, y=5.2, w=11.3, h=1.0,
    fill=RGBColor(0xd1,0xe7,0xdd), color=ACCENT2, fontsize=17, italic=True)
add_footer_bar(s, 14, TOTAL_SLIDES, '7. Results')
add_speaker_notes(s,
    "Efficiency is where HRM-Crime is most distinctive from the ViT "
    "baselines it beats.\n\n"
    "Look at the size difference. VideoSwin-Tiny is 28 million parameters. "
    "TimeSformer is 122 million. UR-DMU with ViT-B features is 86 million. "
    "My HRM-Crime single model is 270 THOUSAND parameters — three orders "
    "of magnitude smaller.\n\n"
    "Compute is even more dramatic. VideoSwin needs about 12 giga-MACs per "
    "video. TimeSformer needs 38. HRM-Crime needs 1 million MACs — that's "
    "12,000 times less compute for the single model, and 3,000 times less "
    "for the full ensemble.\n\n"
    "On a single CPU core, the entire 4-model ensemble runs in under 0.4 "
    "milliseconds per 20-segment video. This means a single commodity "
    "server can monitor thousands of CCTV feeds at frame rate. No GPU "
    "capital expense.\n\n"
    "This is not a theoretical claim — I measured it on a MacBook Pro "
    "with an Apple M-series CPU. The model files, four checkpoints in "
    "total, fit in about 4 megabytes in FP32, or 1 megabyte after INT8 "
    "quantisation.\n\n"
    "For real-world CCTV deployment in a smart-city context, this "
    "efficiency profile is arguably more important than the AUC advantage.")

# ─────────────────────────────────────────────────────────────────────────
# 15. ABLATION
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Ablation Study',
          subtitle='The original recipe is near-optimal; substantial changes hurt')
add_table(s, [
    ['Modification',                                    'AUC',    'Δ'],
    ['Baseline (seed = 77)',                            '0.9131', '—'],
    ['hidden_dim = 128, 3 layers (larger model)',       '0.8840', '−0.029'],
    ['λ_sparse = 2 × 10⁻⁴ (stronger sparsity)',         '0.9002', '−0.013'],
    ['Feature augmentation (Gaussian noise + dropout)', '0.9002', '−0.013'],
    ['Mean-rank auxiliary loss (λ = 0.1)',              '0.8926', '−0.020'],
    ['Pseudo-label fine-tuning (MIST-style)',           '0.8939', '−0.019'],
    ['RL-guided frame prediction',                      '0.9080', '−0.005'],
    ['Test-Time Augmentation (noise 0.01, 50 passes)',  '0.9148', '+0.002'],
], x=1.5, y=1.6, w=10.3, h=4.7, fontsize=13)
add_footer_bar(s, 15, TOTAL_SLIDES, '8. Ablation')
add_speaker_notes(s,
    "The ablation study is where I document what I tried that DIDN'T work.\n\n"
    "This is unusual to include in a paper — most papers only report what "
    "worked — but I believe it's important for reproducibility. It saves "
    "future researchers time.\n\n"
    "A LARGER MODEL — hidden dim 128, three attention layers instead of "
    "two — costs 2.9 AUC points. The larger model overfits the weak MIL "
    "labels. This is my strongest evidence that ViT-B fails on UCF-Crime "
    "partly due to over-parameterisation.\n\n"
    "STRONGER SPARSITY REGULARISATION suppresses the gradient signal for "
    "non-peak segments and costs 1.3 AUC.\n\n"
    "FEATURE AUGMENTATION with Gaussian noise costs 1.3 AUC. The reason: "
    "L2-normalised features lie on the unit hypersphere, and additive "
    "noise pushes them off that manifold.\n\n"
    "MEAN-RANK AUXILIARY LOSS — a regulariser I added on top of the MIL "
    "loss — hurts by 2 AUC.\n\n"
    "PSEUDO-LABEL FINE-TUNING in the MIST style costs 1.9 AUC. Pseudo-"
    "labels are too noisy at 20 segments per video, and fine-tuning "
    "destroys the well-calibrated MIL boundary.\n\n"
    "RL-GUIDED FRAME PREDICTION — an auxiliary head that predicts the "
    "next segment — cost 0.5 AUC because the prediction and MIL losses "
    "structurally conflict.\n\n"
    "The take-away: the ORIGINAL Sultani training recipe is very close to "
    "a local optimum. Every INSIDE-THE-TRAINING-LOOP intervention I tried "
    "hurt performance. The two interventions that HELPED — top-K and "
    "feature-diversity ensembling — operate OUTSIDE the training loop.")

# ─────────────────────────────────────────────────────────────────────────
# 16. LIMITATIONS
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Limitations')
add_body(s, [
    "**Video-level evaluation only.** Frame-level localisation AUC was not assessed — segment-level ground-truth annotations were not available in our feature release.",
    "**Ensemble requires four models.** Total footprint is ~4 MB in FP32; still tiny vs. a single ViT-B, but four separate checkpoints must be maintained.",
    "**No optical-flow input.** May explain residual difficulty on motion-only anomalies such as Shoplifting.",
    "**Hyperparameters selected on the test set** (albeit via nested CV). A held-out validation split from the training set would be strictly stronger, but requires re-training.",
    "**English-only literature review.** Recent 2025 UCF-Crime papers were mostly preprints without stable published numbers at the time of writing.",
], y=1.5, size=15, leading=1.3)
add_footer_bar(s, 16, TOTAL_SLIDES, '9. Limitations')
add_speaker_notes(s,
    "Honest limitations of the work.\n\n"
    "First, evaluation is at the VIDEO LEVEL only. The UCF-Crime benchmark "
    "also provides frame-level annotations for a subset of the test set, "
    "and most published methods report frame-level AUC. I did not compute "
    "frame-level AUC because those annotations were not available in the "
    "feature release I worked with. Adding this evaluation is my top "
    "priority for future work.\n\n"
    "Second, the ensemble requires four separate models. Their combined "
    "footprint is tiny — 4 megabytes — but you do have to maintain and "
    "load four checkpoints.\n\n"
    "Third, I don't use optical flow. Some prior methods do, and it might "
    "help on motion-only anomalies like Shoplifting where our AUC is "
    "weakest.\n\n"
    "Fourth, even with nested cross-validation, hyperparameter selection "
    "happens on the test set — just in a leave-fold-out fashion. A STRICTLY "
    "STRONGER protocol would carve a held-out validation split from the "
    "TRAINING set. I did not do this because the trained checkpoints were "
    "fixed at the time of these experiments and re-training on a smaller "
    "training set would incur compute cost inconsistent with the paper's "
    "CPU-only philosophy.\n\n"
    "Fifth, my literature review was English-only, and the very newest "
    "2025 UCF-Crime papers were preprints without stable numbers when I "
    "wrote the revision.")

# ─────────────────────────────────────────────────────────────────────────
# 17. FUTURE WORK
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Future Work')
add_body(s, [
    "**Frame-level localisation AUC** — the community-standard evaluation on UCF-Crime.",
    "**CLIP-based feature streams** — extend the 3-stream ensemble with a fourth CLIP branch. VadCLIP shows CLIP contains signal complementary to R50+R3D.",
    "**Ensemble distillation** — train a single student HRM to mimic the 4-model ensemble; recover ensemble accuracy at single-model inference cost.",
    "**Frame-level pseudo-label validation** — the negative-results section flags MIST-style pseudo-labels as harmful at T = 20 segments. Would they help at T = 100?",
    "**Saudi / GCC pilot** — fine-tune HRM-Crime on non-sensitive Saudi CCTV footage (in discussion with an industry partner).",
], y=1.5, size=15, leading=1.3)
add_footer_bar(s, 17, TOTAL_SLIDES, '10. Future Work')
add_speaker_notes(s,
    "Five concrete future directions.\n\n"
    "First, and highest priority, is frame-level localisation AUC. This is "
    "the standard secondary metric on UCF-Crime and I owe it to the "
    "community.\n\n"
    "Second, adding a CLIP-based feature stream as a fourth ensemble "
    "member. VadCLIP already showed CLIP contains signal complementary to "
    "traditional CNN features. Adding it to my 3-stream ensemble is a "
    "natural next experiment.\n\n"
    "Third, ensemble distillation. The 4-model ensemble runs in 0.4 ms per "
    "video, but a single distilled student HRM would run in 0.1 ms. This "
    "would matter for very large deployments.\n\n"
    "Fourth, revisit pseudo-label fine-tuning at finer temporal "
    "granularity. My negative result was at T=20 segments. Perhaps at "
    "T=100 the pseudo-labels are less noisy and the fine-tuning helps.\n\n"
    "Fifth, and this is the practical direction I'm most excited about — "
    "an industry pilot on Saudi surveillance footage. This is currently in "
    "discussion with a company called InnovationTeam, who have expressed "
    "interest in sponsoring the publication and running a real-world "
    "pilot.")

# ─────────────────────────────────────────────────────────────────────────
# 18. PUBLICATION STATUS
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Publication Status')
add_body(s, [
    "**Submitted to MDPI Algorithms** (Q1 open-access, ISSN 1999-4893).",
    "     Manuscript ID: algorithms-4523798",
    "     Initial editorial pre-check: three constructive comments received.",
    "     Currently preparing resubmission (16 August 2026).",
    "",
    "**Revision addresses:**",
    "     •  Expanded technical detail (new Sections 4.8, 4.9, 5.5; Algorithms 1 & 2)",
    "     •  6 new 2023–2024 references + new Section 2.5 'Recent Advances'",
    "     •  Rebuilt SOTA comparison with 7 recent baselines",
    "     •  Applied nested-CV methodology throughout",
], y=1.5, size=16, leading=1.3)
add_footer_bar(s, 18, TOTAL_SLIDES, '11. Publication')
add_speaker_notes(s,
    "For context on the current state of the work: the paper has been "
    "submitted to MDPI Algorithms, a Q1 open-access journal, and received "
    "a constructive initial editorial pre-check.\n\n"
    "The editor asked for three specific improvements: more technical "
    "detail, more recent references, and comparison with recent "
    "solutions. I've addressed all three in the revision I am about to "
    "resubmit.\n\n"
    "The revised manuscript adds three new sections and two pseudocode "
    "algorithms — this is the technical-detail expansion. It adds six "
    "new 2023-2024 references and a new subsection specifically discussing "
    "recent advances. And the SOTA comparison table now has 15 rows "
    "including 7 recent baselines from 2023 and 2024.\n\n"
    "It also applies the nested-CV methodology I described earlier in the "
    "talk, which addresses a subtle methodological concern with the "
    "original submission.\n\n"
    "I expect the paper to enter formal peer review within 2-3 weeks.")

# ─────────────────────────────────────────────────────────────────────────
# 19. SUMMARY
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
add_top_accent(s)
add_title(s, 'Summary')
add_body(s, [
    "**Compact 270K-parameter HRM** — Swin windowed attention + dilated Conv1D.",
    "**Per-model top-K aggregation** replaces max; K tuned per feature stream.",
    "**Three-stream feature-diversity ensemble** exploits decorrelated blind spots.",
    "**Rank-normalised fusion** makes ensemble invariant to score scale.",
    "**Nested 5-fold CV** gives unbiased AUC = 0.9215 ± 0.02; deployed AUC = 0.9300.",
    "**+6 AUC over strongest ViT-B baseline** while using 300× fewer parameters.",
    "**Runs in <0.4 ms per video on CPU** — practical for real deployment.",
    "**Documented five negative results** to save future researchers time.",
], y=1.4, size=16, leading=1.25)
add_callout(s,
    "Prediction diversity — not model complexity — is the largest "
    "available lever for weak-supervision performance improvement on UCF-Crime.",
    x=0.8, y=6.35, w=11.7, h=0.6,
    fill=RGBColor(0xd1,0xe7,0xdd), color=ACCENT2, fontsize=15, bold=True)
add_footer_bar(s, 19, TOTAL_SLIDES, '12. Summary')
add_speaker_notes(s,
    "Let me summarise the entire thesis in one slide.\n\n"
    "I built a compact 270 thousand-parameter hierarchical model combining "
    "Swin-style windowed attention with dilated 1-D convolutions.\n\n"
    "I introduced per-model top-K aggregation, replacing the standard max "
    "with the mean of the K highest segment scores, with K tuned per "
    "feature stream.\n\n"
    "I built a three-stream feature-diversity ensemble — combined, "
    "spatial-only, temporal-only — that exploits the structurally "
    "decorrelated blind spots of models trained on different feature "
    "subsets.\n\n"
    "I used rank normalisation before averaging, making the fusion "
    "invariant to score scale.\n\n"
    "I validated using 5-fold nested cross-validation, giving an unbiased "
    "AUC of 0.9215 plus-minus 0.02, and a deployed AUC of 0.9300.\n\n"
    "This is 5-6 AUC points above the strongest 2024 ViT-B baseline, "
    "using 300 times fewer parameters. It runs in under 0.4 milliseconds "
    "per video on a single CPU core.\n\n"
    "I documented five negative results, so future researchers don't have "
    "to repeat my failed experiments.\n\n"
    "The single-sentence take-away: prediction diversity — NOT model "
    "complexity — is the largest available lever for improving weakly-"
    "supervised video anomaly detection.")

# ─────────────────────────────────────────────────────────────────────────
# 20. Q&A / Thank you
# ─────────────────────────────────────────────────────────────────────────
s = add_slide()
# Full-bleed accent for closing
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
    Inches(0), Inches(0), Inches(13.333), Inches(7.5))
bg.fill.solid(); bg.fill.fore_color.rgb = ACCENT; bg.line.fill.background()

tb = s.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12.3), Inches(3))
tf = tb.text_frame; tf.word_wrap = True; tf.margin_left = 0
p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
r = p.add_run(); r.text = 'Thank you.'
r.font.size = Pt(80); r.font.bold = True
r.font.color.rgb = RGBColor(0xff,0xff,0xff); r.font.name = 'Palatino'
p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
r = p2.add_run(); r.text = 'Questions?'
r.font.size = Pt(40); r.font.italic = True
r.font.color.rgb = RGBColor(0xdc,0xea,0xf5); r.font.name = 'Palatino'
p2.space_before = Pt(24)

tb = s.shapes.add_textbox(Inches(0.5), Inches(6.4), Inches(12.3), Inches(0.5))
tf = tb.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
r = p.add_run()
r.text = 'Eslam Medhat Fathy Habib  ·  ieslammedhat@gmail.com  ·  ORCID 0009-0007-1758-8612'
r.font.size = Pt(14); r.font.italic = True
r.font.color.rgb = RGBColor(0xdc,0xea,0xf5); r.font.name = 'Palatino'

add_speaker_notes(s,
    "Thank you for your attention.\n\n"
    "I welcome your questions.\n\n"
    "Anticipated questions I'm prepared for:\n\n"
    "1. Why not use CLIP features? — Complexity budget; CLIP would be a "
    "natural 4th ensemble stream in future work.\n\n"
    "2. Why not train on more data? — UCF-Crime is the standard benchmark; "
    "using more data would break comparability with prior work.\n\n"
    "3. Isn't tuning K on the test-set folds still test-set tuning? — "
    "Nested CV holds each fold out; hyperparameters never see the fold on "
    "which they are evaluated. A stronger protocol would carve validation "
    "from training set — flagged as limitation.\n\n"
    "4. Why should we believe the +6 AUC gap is real? — Every baseline "
    "number cites its source paper; the gap is measured on the same test "
    "set that everyone uses.\n\n"
    "5. Where's the frame-level AUC? — Not computed; frame-level "
    "annotations were not in our feature release; flagged as top future-"
    "work priority.\n\n"
    "6. What about optical flow? — Deliberately excluded to preserve the "
    "CPU-only deployment philosophy; may explain residual Shoplifting "
    "difficulty.\n\n"
    "7. Broader impact / ethics? — HRM-Crime is a decision-support tool "
    "for human operators; explicit recommendation in the paper that it "
    "must never gate consequential decisions without human review.")

prs.save(OUT)
print(f'Presentation saved: {OUT}')
print(f'{len(prs.slides)} slides.')
