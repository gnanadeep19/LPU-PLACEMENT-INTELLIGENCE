"""Build the LPU Placement Intelligence capstone presentation.

Usage:
    python scripts/build_presentation.py

Outputs:
    LPU_Placement_Intelligence_Capstone_Presentation.pptx
    reports/presentation/assets/*.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "reports" / "presentation" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)
OUTPUT = ROOT / "LPU_Placement_Intelligence_Capstone_Presentation.pptx"

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
BG = RGBColor(0x0D, 0x15, 0x24)
PANEL = RGBColor(0x16, 0x22, 0x38)
PANEL_ALT = RGBColor(0x1D, 0x2B, 0x45)
STROKE = RGBColor(0x2A, 0x3A, 0x55)
ACCENT = RGBColor(0xF9, 0x73, 0x16)
ACCENT_SOFT = RGBColor(0xFD, 0xBA, 0x74)
BLUE = RGBColor(0x60, 0xA5, 0xFA)
GREEN = RGBColor(0x34, 0xD3, 0x99)
RED = RGBColor(0xF8, 0x71, 0x71)
WHITE = RGBColor(0xF8, 0xFA, 0xFC)
MUTED = RGBColor(0x9F, 0xB0, 0xC8)
DARK_TEXT = RGBColor(0x0B, 0x12, 0x20)

HEAD = "Segoe UI Semibold"
BODY = "Segoe UI"
MONO = "Consolas"

SW, SH = 13.333, 7.5
MARGIN = 0.75
CONTENT_W = SW - 2 * MARGIN

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
CHART_TEXT = "#E5EAF3"
CHART_MUTED = "#9FB0C8"
CHART_BG = "#0D1524"


def _style_axes(ax):
    ax.set_facecolor(CHART_BG)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=CHART_MUTED, labelsize=10, length=0)
    ax.grid(axis="x", color="#25344D", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)


def chart_cv_accuracy() -> Path:
    rows = [
        ("Majority baseline", 0.514, 0.008, "baseline"),
        ("Rule-based baseline", 0.769, 0.054, "baseline"),
        ("SVM (RBF)", 0.880, 0.034, "model"),
        ("K-Nearest Neighbors", 0.900, 0.036, "model"),
        ("Naive Bayes", 0.928, 0.028, "model"),
        ("Random Forest", 0.939, 0.023, "model"),
        ("Logistic Regression", 0.940, 0.026, "model"),
        ("Gradient Boosting (deployed)", 0.947, 0.030, "hero"),
        ("Decision Tree", 0.950, 0.032, "model"),
        ("AdaBoost (CV winner)", 0.959, 0.022, "winner"),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=200)
    fig.patch.set_facecolor(CHART_BG)
    _style_axes(ax)
    colors = {"baseline": "#64748B", "model": "#3B82F6", "hero": "#F97316", "winner": "#FBBF24"}
    y = range(len(rows))
    for yi, (label, mean, std, kind) in zip(y, rows):
        ax.barh(yi, mean, color=colors[kind], height=0.62, xerr=std,
                error_kw={"ecolor": "#94A3B8", "elinewidth": 1.0, "capsize": 3})
        ax.text(mean + std + 0.012, yi, f"{mean * 100:.1f}%", va="center",
                color=CHART_TEXT, fontsize=9.5, fontweight="bold")
    ax.set_yticks(list(y))
    ax.set_yticklabels([r[0] for r in rows], color=CHART_TEXT, fontsize=10)
    ax.set_xlim(0, 1.12)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xticklabels(["0%", "20%", "40%", "60%", "80%", "100%"], color=CHART_MUTED, fontsize=9)
    ax.set_xlabel("Accuracy — 3 x 5 repeated stratified cross-validation (mean ± std)",
                  color=CHART_MUTED, fontsize=9, labelpad=8)
    path = ASSETS / "cv_accuracy.png"
    fig.tight_layout()
    fig.savefig(path, facecolor=CHART_BG)
    plt.close(fig)
    return path


def chart_confusion() -> Path:
    fig, ax = plt.subplots(figsize=(4.3, 3.9), dpi=200)
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    values = [[25, 1], [1, 24]]
    labels = [["TN 25", "FP 1"], ["FN 1", "TP 24"]]
    colors = [["#1E3A5F", "#7F1D1D"], ["#7F1D1D", "#14532D"]]
    ax.imshow([[0, 1], [2, 3]], cmap="Greys", alpha=0)
    for r in range(2):
        for c in range(2):
            ax.add_patch(plt.Rectangle((c - 0.5, r - 0.5), 1, 1, color=colors[r][c]))
            ax.text(c, r, labels[r][c], ha="center", va="center", color="#FFFFFF",
                    fontsize=15, fontweight="bold")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Pred: Not Ready", "Pred: Ready"], color=CHART_TEXT, fontsize=9)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Actual: Not Ready", "Actual: Ready"], color=CHART_TEXT, fontsize=9)
    ax.tick_params(colors=CHART_MUTED, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Hold-out confusion matrix — 51 students", color=CHART_TEXT, fontsize=10, pad=10)
    path = ASSETS / "confusion_matrix.png"
    fig.tight_layout()
    fig.savefig(path, facecolor=CHART_BG)
    plt.close(fig)
    return path


def chart_importance() -> Path:
    rows = [
        ("Academic CGPA", 77.91),
        ("Active backlogs", 7.26),
        ("Certifications", 4.45),
        ("Communication", 2.87),
        ("Aptitude", 2.84),
        ("Coding / DSA", 2.44),
        ("Technical core", 1.18),
        ("Projects", 1.06),
        ("Internships", 0.0),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=200)
    fig.patch.set_facecolor(CHART_BG)
    _style_axes(ax)
    names = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    colors = ["#F97316" if v > 20 else "#3B82F6" for v in vals]
    ax.barh(names, vals, color=colors, height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + 1.2, i, f"{v:.2f}%", va="center", color=CHART_TEXT, fontsize=9)
    ax.set_xlim(0, 92)
    ax.set_xticks([0, 20, 40, 60, 80])
    ax.set_xticklabels(["0%", "20%", "40%", "60%", "80%"], color=CHART_MUTED, fontsize=9)
    ax.tick_params(axis="y", colors=CHART_TEXT, labelsize=10)
    ax.set_title("Global feature importance — deployed Gradient Boosting (Gini)",
                 color=CHART_TEXT, fontsize=10, pad=10)
    path = ASSETS / "feature_importance.png"
    fig.tight_layout()
    fig.savefig(path, facecolor=CHART_BG)
    plt.close(fig)
    return path


def chart_correlation() -> Path:
    rows = [
        ("Certifications", 0.797),
        ("Academic CGPA", 0.789),
        ("Projects", 0.786),
        ("Coding / DSA", 0.721),
        ("Aptitude", 0.714),
        ("Technical core", 0.702),
        ("Internships", 0.682),
        ("Communication", 0.640),
        ("Active backlogs", -0.226),
    ]
    fig, ax = plt.subplots(figsize=(6.2, 4.1), dpi=200)
    fig.patch.set_facecolor(CHART_BG)
    _style_axes(ax)
    names = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    colors = ["#F87171" if v < 0 else "#3B82F6" for v in vals]
    ax.barh(names, vals, color=colors, height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + (0.02 if v >= 0 else -0.02), i, f"{v:+.2f}", va="center",
                ha="left" if v >= 0 else "right", color=CHART_TEXT, fontsize=9)
    ax.axvline(0, color="#475569", linewidth=1)
    ax.set_xlim(-0.35, 0.95)
    ax.set_xticks([-0.2, 0, 0.2, 0.4, 0.6, 0.8])
    ax.tick_params(axis="y", colors=CHART_TEXT, labelsize=10)
    ax.set_title("Feature correlation with placement_ready (n = 253)",
                 color=CHART_TEXT, fontsize=10, pad=10)
    path = ASSETS / "correlation.png"
    fig.tight_layout()
    fig.savefig(path, facecolor=CHART_BG)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Shape helpers
# ---------------------------------------------------------------------------
def blank_slide(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG
    bg.line.fill.background()
    bg.shadow.inherit = False
    return slide


def rect(slide, x, y, w, h, fill=PANEL, line=None, radius=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shape.adjustments[0] = radius
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    return shape


def text(slide, x, y, w, h, value, size=14, bold=False, color=WHITE, font=BODY,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.05, margin=0.0):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = 0
    paragraph = tf.paragraphs[0]
    paragraph.alignment = align
    paragraph.line_spacing = line_spacing
    run = paragraph.add_run()
    run.text = value
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    return box


def bullets(slide, x, y, w, h, items, size=13, gap=6, color=WHITE, marker="▪",
            line_spacing=1.08):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    for index, item in enumerate(items):
        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.space_after = Pt(gap)
        paragraph.line_spacing = line_spacing
        marker_run = paragraph.add_run()
        marker_run.text = f"{marker}  "
        marker_run.font.size = Pt(size)
        marker_run.font.bold = True
        marker_run.font.color.rgb = ACCENT
        marker_run.font.name = BODY
        if isinstance(item, tuple) and len(item) == 2:
            head, tail = item
            head_run = paragraph.add_run()
            head_run.text = head
            head_run.font.size = Pt(size)
            head_run.font.bold = True
            head_run.font.color.rgb = WHITE
            head_run.font.name = BODY
            tail_run = paragraph.add_run()
            tail_run.text = tail
            tail_run.font.size = Pt(size)
            tail_run.font.color.rgb = color
            tail_run.font.name = BODY
        else:
            run = paragraph.add_run()
            run.text = item
            run.font.size = Pt(size)
            run.font.color.rgb = color
            run.font.name = BODY
    return box


def header(slide, number, eyebrow, title, component=None):
    text(slide, MARGIN, 0.34, 8.4, 0.28, eyebrow.upper(), size=10.5, bold=True,
         color=ACCENT, font=HEAD)
    text(slide, MARGIN, 0.62, 10.6, 0.55, title, size=27, bold=True, color=WHITE, font=HEAD)
    rect(slide, MARGIN, 1.24, 1.0, 0.05, fill=ACCENT)
    if component:
        chip_w = 1.85
        rect(slide, SW - MARGIN - chip_w, 0.36, chip_w, 0.3, fill=PANEL_ALT,
             line=STROKE, radius=0.5)
        text(slide, SW - MARGIN - chip_w, 0.38, chip_w, 0.26, component, size=9.5,
             bold=True, color=ACCENT_SOFT, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def footer(slide, page):
    rect(slide, MARGIN, 7.0, CONTENT_W, 0.012, fill=STROKE)
    text(slide, MARGIN, 7.08, 8.0, 0.28, "LPU Placement Intelligence  ·  End-to-End ML Capstone",
         size=9, color=MUTED)
    text(slide, SW - MARGIN - 2.0, 7.08, 2.0, 0.28, f"{page:02d}", size=9, bold=True,
         color=MUTED, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, heading, body, accent=ACCENT, size=12.5, heading_size=14):
    rect(slide, x, y, w, h, fill=PANEL, line=STROKE, radius=0.06)
    rect(slide, x, y + 0.16, 0.05, h - 0.32, fill=accent)
    text(slide, x + 0.22, y + 0.17, w - 0.38, 0.3, heading, size=heading_size, bold=True,
         color=accent, font=HEAD)
    text(slide, x + 0.22, y + 0.53, w - 0.4, h - 0.65, body, size=size, color=WHITE,
         line_spacing=1.14)


def kpi(slide, x, y, w, value, label, sub=None, color=ACCENT):
    rect(slide, x, y, w, 1.12, fill=PANEL, line=STROKE, radius=0.08)
    text(slide, x + 0.18, y + 0.12, w - 0.3, 0.45, value, size=25, bold=True, color=color, font=HEAD)
    text(slide, x + 0.18, y + 0.6, w - 0.3, 0.26, label, size=10.5, bold=True, color=WHITE)
    if sub:
        text(slide, x + 0.18, y + 0.84, w - 0.3, 0.22, sub, size=8.5, color=MUTED)


def table(slide, x, y, w, h, data, col_widths, font_size=10.5, header_size=10.5,
          highlight_rows=(), align_center_from=1):
    rows, cols = len(data), len(data[0])
    shape = slide.shapes.add_table(rows, cols, Inches(x), Inches(y), Inches(w), Inches(h))
    tbl = shape.table
    tbl.first_row = True
    tbl.horz_banding = False
    for index, width in enumerate(col_widths):
        tbl.columns[index].width = Inches(width)
    for r, row in enumerate(data):
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = ACCENT
            elif r in highlight_rows:
                cell.fill.fore_color.rgb = RGBColor(0x3A, 0x27, 0x14)
            else:
                cell.fill.fore_color.rgb = PANEL if r % 2 else PANEL_ALT
            tf = cell.text_frame
            tf.word_wrap = True
            paragraph = tf.paragraphs[0]
            paragraph.alignment = PP_ALIGN.CENTER if c >= align_center_from else PP_ALIGN.LEFT
            run = paragraph.add_run()
            run.text = str(value)
            run.font.size = Pt(header_size if r == 0 else font_size)
            run.font.bold = r == 0 or r in highlight_rows
            run.font.name = BODY
            run.font.color.rgb = DARK_TEXT if r == 0 else WHITE
    return shape


def picture(slide, path: Path, x, y, width):
    with Image.open(path) as image:
        ratio = image.height / image.width
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(width),
                                    height=Inches(width * ratio))


def notes(slide, value):
    slide.notes_slide.notes_text_frame.text = value


# ---------------------------------------------------------------------------
# Deck
# ---------------------------------------------------------------------------
def build() -> Path:
    cv_chart = chart_cv_accuracy()
    confusion_chart = chart_confusion()
    importance_chart = chart_importance()
    correlation_chart = chart_correlation()

    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)

    # ---------------- 1. Title ----------------
    slide = blank_slide(prs)
    rect(slide, 0, 0, SW, 0.12, fill=ACCENT)
    rect(slide, 9.5, 0.12, 3.83, 7.38, fill=PANEL)
    rect(slide, 9.5, 0.12, 0.06, 7.38, fill=ACCENT)

    text(slide, MARGIN, 0.95, 8.3, 0.3, "MACHINE LEARNING  ·  CAPSTONE PROJECT 2026",
         size=11, bold=True, color=ACCENT, font=HEAD)
    text(slide, MARGIN, 1.38, 8.4, 1.9,
         "LPU Placement\nIntelligence", size=48, bold=True, color=WHITE, font=HEAD,
         line_spacing=0.95)
    text(slide, MARGIN, 3.42, 8.0, 0.75,
         "Student readiness prediction, skill-gap diagnosis and a prescriptive improvement roadmap",
         size=16, color=ACCENT_SOFT, line_spacing=1.2)
    rect(slide, MARGIN, 4.35, 2.2, 0.04, fill=STROKE)

    text(slide, MARGIN, 4.6, 4.0, 0.28, "TEAM — 3 MEMBERS", size=10, bold=True, color=MUTED,
         font=HEAD)
    members = [
        ("Team Member 1", "Name · Roll No.", "Data & ML modelling"),
        ("Team Member 2", "Name · Roll No.", "Backend & deployment"),
        ("Team Member 3", "Name · Roll No.", "Frontend & explainability"),
    ]
    for index, (name, roll, role) in enumerate(members):
        y = 4.96 + index * 0.56
        rect(slide, MARGIN, y, 0.06, 0.42, fill=BLUE if index else ACCENT)
        text(slide, MARGIN + 0.18, y - 0.01, 1.95, 0.24, name, size=11.5, bold=True)
        text(slide, MARGIN + 0.18, y + 0.21, 2.1, 0.22, roll, size=9.5, color=MUTED)
        text(slide, MARGIN + 2.25, y + 0.02, 2.9, 0.3, role, size=10.5, color=ACCENT_SOFT)

    text(slide, MARGIN, 6.78, 8.0, 0.3,
         "School of Computer Science & Engineering  ·  Lovely Professional University",
         size=10.5, color=MUTED)

    text(slide, 9.95, 1.1, 3.0, 0.3, "AT A GLANCE", size=10, bold=True, color=MUTED, font=HEAD)
    highlights = [
        ("96.08%", "hold-out accuracy", ACCENT),
        ("8", "algorithms benchmarked", BLUE),
        ("4,048", "student records · 7 datasets", GREEN),
        ("11/11", "required components covered", ACCENT_SOFT),
    ]
    for index, (value, label, color) in enumerate(highlights):
        y = 1.55 + index * 1.32
        rect(slide, 9.85, y, 3.15, 1.1, fill=PANEL_ALT, line=STROKE, radius=0.08)
        text(slide, 10.02, y + 0.13, 2.8, 0.5, value, size=27, bold=True, color=color, font=HEAD)
        text(slide, 10.02, y + 0.68, 2.8, 0.3, label, size=10, color=WHITE)
    notes(slide, "Open with the one-line pitch: students find out too late that they are not "
                 "placement-ready. We built a deployed machine-learning system that scores "
                 "readiness, explains why, and prescribes what to fix. Mention the three-member "
                 "split once, then move on.")

    # ---------------- 2. Agenda ----------------
    slide = blank_slide(prs)
    header(slide, 2, "Agenda", "The 11 mandatory components, mapped to this deck")
    items = [
        ("01", "Problem Definition", "slide 03"),
        ("02", "Dataset & Data Acquisition", "slide 04"),
        ("03", "Exploratory Data Analysis", "slide 05"),
        ("04", "Preprocessing & Feature Engineering", "slide 06"),
        ("05", "Model Development & Baselines", "slide 07"),
        ("06", "Model Evaluation & Accuracy", "slides 08–10"),
        ("07", "Ensemble Learning & Optimization", "slide 11"),
        ("08", "Explainable AI (XAI)", "slide 12"),
        ("09", "ML Pipeline & Reproducibility", "slide 13"),
        ("10", "Deployment", "slides 14–15"),
        ("11", "GitHub Repository & Docs", "slide 16"),
    ]
    for index, (number, label, ref) in enumerate(items):
        column = 0 if index < 6 else 1
        row = index if index < 6 else index - 6
        x = MARGIN + column * 5.95
        y = 1.58 + row * 0.84
        rect(slide, x, y, 5.75, 0.72, fill=PANEL if column == 0 else PANEL_ALT,
             line=STROKE, radius=0.1)
        rect(slide, x, y, 0.62, 0.72, fill=ACCENT if column == 0 else BLUE, radius=0.1)
        text(slide, x, y + 0.2, 0.62, 0.3, number, size=13, bold=True, color=DARK_TEXT,
             align=PP_ALIGN.CENTER, font=HEAD)
        text(slide, x + 0.8, y + 0.14, 3.85, 0.3, label, size=12.5, bold=True)
        text(slide, x + 4.55, y + 0.2, 1.05, 0.26, ref, size=9, color=MUTED,
             align=PP_ALIGN.RIGHT)
    text(slide, 6.7 + 0.0, 6.06, 5.7, 0.5,
         "Plus: live demo, tech stack, team split, limitations and future scope.",
         size=11, color=ACCENT_SOFT)
    notes(slide, "State that every component the brief asks for is present, and point out that "
                 "evaluation gets three slides because accuracy is the part most likely to be "
                 "questioned.")

    # ---------------- 3. Problem definition ----------------
    slide = blank_slide(prs)
    header(slide, 3, "Component 1 of 11", "Problem Definition", "1 / 11")
    cards = [
        ("Real-world problem",
         "Placement preparation is reactive. Students discover their gaps only after a "
         "rejection, and advice is generic rather than profile-specific.", ACCENT),
        ("Target users & stakeholders",
         "Students preparing for campus drives, training & placement cells, faculty mentors, "
         "and recruiters screening readiness.", BLUE),
        ("ML objective",
         "Binary classification of placement readiness from nine measurable competency "
         "signals, with an explainable probability used as a ranking score.", GREEN),
    ]
    for index, (heading, body, color) in enumerate(cards):
        card(slide, MARGIN + index * 3.98, 1.55, 3.83, 1.95, heading, body, accent=color, size=12.8)
    cards2 = [
        ("Input variables (9)",
         "CGPA · coding · technical · aptitude · communication · projects · internships · "
         "certifications · active backlogs.", ACCENT),
        ("Expected output",
         "Readiness score 0–100 with a category (Ready / Nearly Ready / Needs Focus), skill-gap "
         "matrix and priority-ranked action plan.", BLUE),
        ("Success criteria",
         "≥ 90% accuracy and F1 on held-out data, beats both baselines, every prediction "
         "explained, and the whole flow usable in a browser.", GREEN),
    ]
    for index, (heading, body, color) in enumerate(cards2):
        card(slide, MARGIN + index * 3.98, 3.68, 3.83, 2.12, heading, body, accent=color, size=12.8)
    rect(slide, MARGIN, 6.05, CONTENT_W, 0.6, fill=PANEL_ALT, line=STROKE, radius=0.06)
    text(slide, MARGIN + 0.2, 6.17, CONTENT_W - 0.4, 0.4,
         "Scope discipline: the model predicts readiness from self-reported competency inputs — "
         "it does not promise a job offer, and the interface says so.",
         size=11, color=ACCENT_SOFT)
    notes(slide, "Anchor on the decision the system supports: where should a student spend the "
                 "next 30 days? Emphasise that the output is advisory and the app carries that "
                 "disclaimer visibly.")

    # ---------------- 4. Dataset ----------------
    slide = blank_slide(prs)
    header(slide, 4, "Component 2 of 11", "Dataset & Data Acquisition", "2 / 11")
    data = [
        ["#", "Dataset file", "Rows", "Source", "Role in the project"],
        ["1", "students.csv", "253", "Curated / synthetic — LPU schema", "Primary training set"],
        ["2", "college_placement_engineering.csv", "2,966", "Kaggle — Engineering Placements", "External benchmark"],
        ["3", "campus_recruitment_kaggle.csv", "215", "Kaggle — Campus Recruitment", "Secondary analysis"],
        ["4", "job_placement_features.csv", "215", "Kaggle — Job Placement", "Secondary analysis"],
        ["5", "engineering_skills_placement.csv", "99", "Kaggle — Engineering Skills", "Secondary analysis"],
        ["6", "placement_package_salary.csv", "200", "CampusX — salary benchmark", "Regression study"],
        ["7", "placement_iq_academic.csv", "100", "CampusX — IQ + CGPA", "Classification study"],
        ["", "Total", "4,048", "7 files · PII-free", "Documented in dataset/README.md"],
    ]
    table(slide, MARGIN, 1.55, 8.15, 3.95, data, [0.32, 2.55, 0.6, 2.35, 2.33],
          font_size=9, header_size=9, highlight_rows=(8,), align_center_from=2)
    rect(slide, 9.15, 1.55, 3.45, 3.95, fill=PANEL, line=STROKE, radius=0.05)
    text(slide, 9.33, 1.7, 3.1, 0.28, "PRIMARY DATASET", size=9.5, bold=True, color=ACCENT,
         font=HEAD)
    text(slide, 9.33, 2.0, 3.1, 0.3, "students.csv", size=16, bold=True, font=MONO)
    text(slide, 9.33, 2.36, 3.1, 0.9,
         "253 rows · 9 features · 1 binary target (placement_ready) · 0 missing values",
         size=10.5, color=WHITE, line_spacing=1.15)
    rect(slide, 9.33, 3.2, 3.1, 0.01, fill=STROKE)
    text(slide, 9.33, 3.3, 3.1, 0.26, "CLASS BALANCE", size=9, bold=True, color=MUTED, font=HEAD)
    text(slide, 9.33, 3.56, 3.1, 0.55, "Not ready 130  ·  Ready 123\n51% / 49% — near-balanced",
         size=10.5, color=WHITE, line_spacing=1.15)
    text(slide, 9.33, 4.2, 3.1, 0.26, "WHY THIS SET", size=9, bold=True, color=MUTED, font=HEAD)
    text(slide, 9.33, 4.45, 3.1, 0.9,
         "Every feature is actionable: a student can raise coding score or clear backlogs. "
         "Demographics are deliberately excluded.",
         size=10, color=WHITE, line_spacing=1.12)
    bullets(slide, MARGIN, 5.72, CONTENT_W, 1.1, [
        ("Acquisition: ", "public Kaggle / CampusX files for benchmarking; the primary schema mirrors LPU competency dimensions."),
        ("Audit: ", "dataset/data_audit.py produces reports/data-audit/ — 3 blocking findings were found and documented, not hidden."),
    ], size=11.5, gap=4)
    notes(slide, "Be explicit that only students.csv trains the live model, and that the six "
                 "external files are benchmarks. The audit found duplicates and missing salary "
                 "values; we recorded them and restricted use rather than merging everything.")

    # ---------------- 5. EDA ----------------
    slide = blank_slide(prs)
    header(slide, 5, "Component 3 of 11", "Exploratory Data Analysis", "3 / 11")
    picture(slide, correlation_chart, MARGIN, 1.6, 5.55)
    kpis = [("253", "rows"), ("0", "missing values"), ("2", "exact duplicates"), ("9", "features")]
    for index, (value, label) in enumerate(kpis):
        x = 6.75 + (index % 2) * 2.85
        y = 1.62 + (index // 2) * 0.86
        rect(slide, x, y, 2.7, 0.74, fill=PANEL, line=STROKE, radius=0.1)
        text(slide, x + 0.15, y + 0.1, 0.95, 0.4, value, size=18, bold=True, color=ACCENT, font=HEAD)
        text(slide, x + 1.05, y + 0.2, 1.55, 0.3, label, size=9.5, color=WHITE)
    bullets(slide, 6.75, 3.52, 5.85, 3.0, [
        ("Distributions: ", "CGPA 5.1–9.0 (mean 7.32), scores 32–97, so the data spans weak and strong profiles."),
        ("Class balance: ", "130 vs 123 — mild imbalance, handled with stratified splitting and balanced accuracy."),
        ("Correlation: ", "certifications, CGPA and projects lead; backlogs is the only negative signal."),
        ("Outliers: ", "no impossible values; extreme profiles kept because they are real edge cases."),
        ("Data-quality flags: ", "2 duplicate rows in the primary set, 1,829 in the Kaggle engineering file, 67 missing salaries."),
    ], size=11, gap=5)
    notes(slide, "Say the audit is the reason the EDA slide starts with data quality. The duplicate "
                 "in the primary set is removed before evaluation; the external dataset is not "
                 "merged, so its duplicates cannot leak into training.")

    # ---------------- 6. Preprocessing ----------------
    slide = blank_slide(prs)
    header(slide, 6, "Component 4 of 11", "Preprocessing & Feature Engineering", "4 / 11")
    steps = [
        ("01", "Schema & boundary validation",
         "Type, range and required-field checks (CGPA 0–10, scores 0–100, non-negative counts) "
         "at the API edge, so bad input never reaches the model.", ACCENT),
        ("02", "Deduplicate & clean",
         "Explicit exact-duplicate removal — 253 → 251 rows — plus missing-value checks. "
         "Duplicates are dropped by decision, not silently.", BLUE),
        ("03", "Stratified split & folds",
         "80/20 stratified hold-out and 3 × 5 repeated stratified CV, seed 42, preserving the "
         "class ratio in every fold.", GREEN),
        ("04", "Feature engineering",
         "Research pipeline adds coding_technical_mean and experience_count. The live model keeps "
         "the original nine features for explainability.", ACCENT_SOFT),
        ("05", "Scaling & encoding",
         "Not required: tree ensembles are scale-invariant, and all nine inputs are numeric. "
         "This is a deliberate choice, not an omission.", RGBColor(0xBA, 0x8F, 0xF7)),
        ("06", "Imbalance & calibration",
         "Stratified folds + balanced accuracy for selection; sigmoid calibration turns raw "
         "scores into usable probabilities.", RED),
    ]
    for index, (number, heading, body, color) in enumerate(steps):
        column = index % 2
        row = index // 2
        x = MARGIN + column * 6.0
        y = 1.55 + row * 1.74
        rect(slide, x, y, 5.85, 1.6, fill=PANEL if column == 0 else PANEL_ALT, line=STROKE,
             radius=0.05)
        text(slide, x + 0.2, y + 0.2, 0.45, 0.35, number, size=17, bold=True, color=color, font=HEAD)
        text(slide, x + 0.72, y + 0.18, 4.95, 0.3, heading, size=12.5, bold=True)
        text(slide, x + 0.72, y + 0.52, 4.95, 1.0, body, size=10.9, color=MUTED, line_spacing=1.14)
    notes(slide, "If asked why no scaler: gradient boosting splits on thresholds, so monotone "
                 "scaling cannot change the split. Say the engineered features exist in the "
                 "research XGBoost experiment and are not silently mixed into the live model.")

    # ---------------- 7. Model development ----------------
    slide = blank_slide(prs)
    header(slide, 7, "Component 5 of 11", "Model Development & Baselines", "5 / 11")
    rect(slide, MARGIN, 1.5, 3.3, 4.55, fill=PANEL_ALT, line=STROKE, radius=0.05)
    text(slide, MARGIN + 0.2, 1.65, 2.9, 0.28, "BASELINES FIRST", size=9.5, bold=True,
         color=ACCENT, font=HEAD)
    text(slide, MARGIN + 0.2, 1.98, 2.9, 1.05,
         "Majority class\n51.4% accuracy\n\nRule-based thresholds\n76.9% accuracy",
         size=12, line_spacing=1.2)
    text(slide, MARGIN + 0.2, 3.5, 2.9, 0.85,
         "Any model that cannot beat 77% is not learning anything useful.",
         size=10.5, color=ACCENT_SOFT, line_spacing=1.15)
    text(slide, MARGIN + 0.2, 4.55, 2.9, 1.1,
         "Then eight algorithms were trained under identical data, split and seed, so the "
         "comparison is fair.",
         size=10.5, color=MUTED, line_spacing=1.15)
    rect(slide, MARGIN + 0.2, 5.5, 2.9, 0.4, fill=PANEL, line=None, radius=0.15)
    text(slide, MARGIN + 0.2, 5.57, 2.9, 0.28,
         "10 models × 5 metrics = 50 scores", size=9, bold=True, color=ACCENT_SOFT,
         align=PP_ALIGN.CENTER)

    algos = [
        ("Logistic Regression", "linear reference model"),
        ("K-Nearest Neighbors", "instance-based similarity"),
        ("Support Vector Machine", "RBF kernel, margin-based"),
        ("Naive Bayes", "probabilistic baseline"),
        ("Decision Tree", "depth-limited, interpretable"),
        ("Random Forest", "bagged trees, 250 estimators"),
        ("AdaBoost", "boosted stumps, 100 estimators"),
        ("Gradient Boosting", "sequential residual fitting"),
    ]
    for index, (name, note) in enumerate(algos):
        column = index % 2
        row = index // 2
        x = 4.35 + column * 4.06
        y = 1.5 + row * 1.15
        rect(slide, x, y, 3.9, 1.0, fill=PANEL, line=STROKE, radius=0.08)
        text(slide, x + 0.16, y + 0.14, 3.6, 0.3, name, size=11.5, bold=True)
        text(slide, x + 0.16, y + 0.44, 3.6, 0.42, note, size=10, color=MUTED)
    rect(slide, MARGIN, 6.2, CONTENT_W, 0.56, fill=PANEL, line=STROKE, radius=0.06)
    text(slide, MARGIN + 0.2, 6.3, CONTENT_W - 0.4, 0.4,
         "Justification: tabular data, 251 rows, mixed monotone thresholds → tree ensembles are "
         "the correct family. Deep learning would overfit and cost explainability.",
         size=10.5, color=ACCENT_SOFT)
    notes(slide, "Spend a moment on the baselines: 51% majority and 77% rule-based. That frames "
                 "the 96% number honestly. The eight models cover linear, instance, margin, "
                 "probabilistic and ensemble families.")

    # ---------------- 8. Evaluation: CV table ----------------
    slide = blank_slide(prs)
    header(slide, 8, "Component 6 of 11", "Model Evaluation — Repeated Cross-Validation", "6 / 11")
    cv_data = [
        ["Model", "Accuracy", "Balanced acc.", "Precision", "Recall", "F1", "ROC-AUC"],
        ["Majority baseline", "51.4% ± 0.8", "50.0%", "0.0%", "0.0%", "0.0%", "0.500"],
        ["Rule-based baseline", "76.9% ± 5.4", "76.3%", "100.0%", "52.6%", "68.3%", "0.763"],
        ["SVM (RBF)", "88.0% ± 3.4", "88.0%", "89.6%", "85.8%", "87.4%", "0.955"],
        ["K-Nearest Neighbors", "90.0% ± 3.6", "90.0%", "91.4%", "88.0%", "89.5%", "0.960"],
        ["Naive Bayes", "92.8% ± 2.8", "93.0%", "87.8%", "99.2%", "93.1%", "0.991"],
        ["Random Forest", "93.9% ± 2.3", "93.9%", "92.3%", "95.6%", "93.8%", "0.991"],
        ["Logistic Regression", "94.0% ± 2.6", "94.0%", "94.8%", "92.9%", "93.8%", "0.988"],
        ["Gradient Boosting — deployed", "94.7% ± 3.0", "94.7%", "94.6%", "94.5%", "94.5%", "0.985"],
        ["Decision Tree", "95.0% ± 3.2", "94.9%", "95.2%", "94.5%", "94.7%", "0.949"],
        ["AdaBoost — CV winner", "95.9% ± 2.2", "95.9%", "95.8%", "95.9%", "95.8%", "0.995"],
    ]
    table(slide, MARGIN, 1.5, 11.3, 4.3, cv_data,
          [3.1, 1.5, 1.45, 1.25, 1.15, 1.05, 1.3], font_size=10, header_size=10,
          highlight_rows=(8, 11), align_center_from=1)
    text(slide, MARGIN, 5.95, 6.6, 0.28,
         "251 rows · 3 × 5 repeated stratified CV · mean ± std · seed 42 · duplicates removed",
         size=9.5, color=MUTED)
    rect(slide, 7.75, 5.85, 4.85, 0.85, fill=PANEL, line=STROKE, radius=0.06)
    text(slide, 7.92, 5.95, 4.55, 0.65,
         "Winner is chosen on balanced accuracy and F1 — not accuracy alone. The two best models "
         "are ensembles and sit within 1.2 points of each other.",
         size=9.5, color=ACCENT_SOFT, line_spacing=1.12)
    notes(slide, "Walk down the model column, not every cell. The story is: baselines, then a "
                 "steady climb, then a plateau around 94–96%. AdaBoost edges the CV table; "
                 "Gradient Boosting is within one standard deviation, so both are defensible.")

    # ---------------- 9. Evaluation: accuracy deep dive ----------------
    slide = blank_slide(prs)
    header(slide, 9, "Component 6 of 11", "Accuracy Deep-Dive — Deployed Model", "6 / 11")
    kpis = [
        ("96.08%", "Accuracy", "49 / 51 correct", ACCENT),
        ("96.00%", "F1-score", "precision = recall", BLUE),
        ("0.9754", "ROC-AUC", "strong separation", GREEN),
        ("2", "Errors", "1 false positive, 1 false negative", ACCENT_SOFT),
    ]
    for index, (value, label, sub, color) in enumerate(kpis):
        kpi(slide, MARGIN + index * 2.94, 1.5, 2.78, value, label, sub, color)
    picture(slide, confusion_chart, MARGIN, 2.95, 4.3)
    bullets(slide, 5.55, 2.95, 6.95, 3.9, [
        ("How the score is produced: ", "predict_proba → readiness probability → 0–100 score, then Ready (≥75), Nearly Ready (50–74), Needs Focus (<50)."),
        ("Accuracy in plain terms: ", "49 of 51 unseen students were classified correctly; both errors are one student each."),
        ("Why both errors matter: ", "a false positive creates false confidence, a false negative wastes preparation time."),
        ("Honest caveat: ", "96.08% is one stratified 80/20 split. The repeated CV number for the same model is 94.7% ± 3.0% — that range, not the single split, is the realistic estimate."),
        ("Baseline lift: ", "+44.7 points over majority class and +19.2 points over the rule-based benchmark."),
    ], size=11, gap=6)
    notes(slide, "This is the slide to slow down on. 96.08% is 49 of 51; say the counts out loud. "
                 "Then immediately volunteer the CV range so the panel does not have to ask. "
                 "Explaining accuracy via the confusion matrix is stronger than quoting a single "
                 "percentage.")

    # ---------------- 10. Error analysis & limits ----------------
    slide = blank_slide(prs)
    header(slide, 10, "Component 6 of 11", "Error Analysis, Calibration & Limitations", "6 / 11")
    rect(slide, MARGIN, 1.5, 5.55, 2.3, fill=PANEL, line=STROKE, radius=0.05)
    text(slide, MARGIN + 0.2, 1.62, 5.0, 0.28, "PROBABILITY QUALITY — SIGMOID CALIBRATION",
         size=9.5, bold=True, color=ACCENT, font=HEAD)
    cal_data = [
        ["Output", "Brier", "Log loss", "ROC-AUC"],
        ["Raw GB probability", "0.0531", "0.8161", "0.9853"],
        ["Calibrated", "0.0460", "0.1999", "0.9828"],
    ]
    table(slide, MARGIN + 0.2, 1.98, 5.15, 1.25, cal_data, [2.2, 0.95, 1.0, 1.0],
          font_size=9.5, header_size=9.5)
    text(slide, MARGIN + 0.2, 3.33, 5.15, 0.4,
         "Log loss drops 75% → the 0–100 score behaves like a probability, not just a rank.",
         size=9.5, color=MUTED)

    rect(slide, MARGIN, 3.98, 5.55, 2.7, fill=PANEL, line=STROKE, radius=0.05)
    text(slide, MARGIN + 0.2, 4.1, 5.0, 0.28, "WHAT THE ERRORS LOOK LIKE", size=9.5, bold=True,
         color=BLUE, font=HEAD)
    bullets(slide, MARGIN + 0.2, 4.45, 5.15, 2.1, [
        "Borderline profiles: students sitting exactly on a threshold are the hardest cases.",
        "CGPA dominates, so a low-CGPA student with strong projects is under-credited.",
        "Internships have almost no variance here, so their real effect cannot be learned.",
    ], size=10, gap=4, marker="–")

    rect(slide, 6.65, 1.5, 5.95, 2.95, fill=PANEL_ALT, line=STROKE, radius=0.05)
    text(slide, 6.85, 1.63, 5.5, 0.28, "LIMITATIONS WE STATE OPENLY", size=9.5, bold=True,
         color=RED, font=HEAD)
    bullets(slide, 6.85, 2.0, 5.55, 2.35, [
        ("Prototype label: ", "placement_ready is not a verified institutional outcome, so 96% is prototype accuracy, not a promise of placement."),
        ("Small sample: ", "251 distinct rows; ±3% CV spread reflects split noise, not real-world populations."),
        ("Same-source split: ", "the hold-out comes from the same dataset, so this is internal validation only."),
        ("Not yet audited: ", "subgroup fairness across branches and regions is still open."),
    ], size=10, gap=5)
    rect(slide, 6.65, 4.62, 5.95, 2.05, fill=PANEL, line=STROKE, radius=0.05)
    text(slide, 6.85, 4.74, 5.5, 0.28, "REPRODUCE THESE NUMBERS", size=9.5, bold=True,
         color=GREEN, font=HEAD)
    bullets(slide, 6.85, 5.08, 5.55, 1.5, [
        "python backend/compare_models.py → the CV table on slide 08.",
        "python backend/calibrate_model.py → the calibration row above.",
        "Artifacts and reports are regenerated, with the dataset SHA-256 recorded.",
    ], size=10, gap=4, marker="–")
    notes(slide, "Volunteering limitations earns marks. Say clearly: the number is reproducible, "
                 "the label is not yet institutionally verified. Calibration is the technical "
                 "highlight here — log loss from 0.82 to 0.20.")

    # ---------------- 11. Ensemble & optimization ----------------
    slide = blank_slide(prs)
    header(slide, 11, "Component 7 of 11", "Ensemble Learning & Hyperparameter Optimization", "7 / 11")
    rect(slide, MARGIN, 1.5, 5.55, 2.2, fill=PANEL, line=STROKE, radius=0.05)
    text(slide, MARGIN + 0.2, 1.62, 5.1, 0.28, "BAGGING — RANDOM FOREST", size=9.5, bold=True,
         color=BLUE, font=HEAD)
    text(slide, MARGIN + 0.2, 1.98, 5.1, 1.55,
         "250 trees grown independently on bootstrap samples, then averaged.\n"
         "Strength: stable, resists variance.\nLimit: parallel trees never target the residual "
         "errors.", size=11, line_spacing=1.2)

    rect(slide, 6.95, 1.5, 5.55, 2.2, fill=PANEL, line=STROKE, radius=0.05)
    text(slide, 7.15, 1.62, 5.1, 0.28, "BOOSTING — GRADIENT BOOSTING / ADABOOST", size=9.5,
         bold=True, color=ACCENT, font=HEAD)
    text(slide, 7.15, 1.98, 5.1, 1.55,
         "Trees are added sequentially; each one fits the previous ensemble's errors.\n"
         "Strength: sharper boundaries, best accuracy + F1.\nRisk: overfits small data — "
         "controlled with shallow depth.", size=11, line_spacing=1.2)

    rect(slide, MARGIN, 3.9, 5.55, 2.35, fill=PANEL_ALT, line=STROKE, radius=0.05)
    text(slide, MARGIN + 0.2, 4.02, 5.0, 0.28, "GRID SEARCH — XGBOOST RESEARCH TRACK",
         size=9.5, bold=True, color=GREEN, font=HEAD)
    bullets(slide, MARGIN + 0.2, 4.38, 5.15, 1.75, [
        ("Grid: ", "learning_rate {0.05, 0.1} × max_depth {2, 3} × n_estimators {80, 160}"),
        ("Protocol: ", "3-fold stratified CV inside the training split only; selection on balanced accuracy."),
        ("Best: ", "lr 0.05, depth 2, 160 trees → CV 0.940, hold-out 88.2% (45/51) vs 51.0% baseline."),
    ], size=9.8, gap=4, marker="–")

    rect(slide, 6.95, 3.9, 5.55, 2.35, fill=PANEL_ALT, line=STROKE, radius=0.05)
    text(slide, 7.15, 4.02, 5.0, 0.28, "SELECTION RULES THAT KEPT US HONEST", size=9.5,
         bold=True, color=ACCENT_SOFT, font=HEAD)
    bullets(slide, 7.15, 4.38, 5.15, 1.75, [
        "Winner chosen on a five-metric average, with balanced accuracy for tuning.",
        "Tuning never sees the hold-out split.",
        "Research XGBoost stays offline — it does not silently replace the deployed artifact.",
    ], size=9.8, gap=4, marker="–")
    text(slide, MARGIN, 6.45, CONTENT_W, 0.4,
         "Bagging reduces variance, boosting reduces bias — with 251 rows and hard eligibility "
         "thresholds, bias reduction won.", size=10.5, color=MUTED, align=PP_ALIGN.CENTER)
    notes(slide, "Explain the bagging vs boosting difference in one sentence each, then the grid "
                 "search protocol. The key governance point: tuning was done inside the training "
                 "split, so the hold-out stays untouched.")

    # ---------------- 12. XAI ----------------
    slide = blank_slide(prs)
    header(slide, 12, "Component 8 of 11", "Explainable AI — Why the Model Says That", "8 / 11")
    picture(slide, importance_chart, MARGIN, 1.55, 5.7)
    cards = [
        ("Global explanation", "Gini importances show CGPA dominates (77.91%), backlogs next "
         "(7.26%). The panel sees the same chart in the app.", ACCENT),
        ("Local explanation", "One-feature sensitivity and counterfactual scenarios: “if coding "
         "rises to 75, readiness moves from X to Y”.", BLUE),
        ("SHAP on demand", "TreeExplainer runs on request and is labelled in raw log-odds; it is "
         "unavailable for unsupported models instead of being faked.", GREEN),
    ]
    for index, (heading, body, color) in enumerate(cards):
        y = 1.55 + index * 1.72
        rect(slide, 6.75, y, 5.85, 1.55, fill=PANEL, line=STROKE, radius=0.05)
        rect(slide, 6.75, y + 0.16, 0.05, 1.23, fill=color)
        text(slide, 6.95, y + 0.16, 5.4, 0.3, heading, size=12, bold=True, color=color, font=HEAD)
        text(slide, 6.95, y + 0.5, 5.4, 0.95, body, size=10.5, line_spacing=1.12)
    text(slide, MARGIN, 5.85, 5.7, 0.55,
         "CGPA dominance is not just a modelling artefact — it reflects how campus shortlisting "
         "actually gates students.", size=10.5, color=ACCENT_SOFT, line_spacing=1.15)
    rect(slide, MARGIN, 6.5, 5.7, 0.02, fill=STROKE)
    notes(slide, "If asked about SHAP values in log-odds: we do not relabel them as probabilities. "
                 "The counterfactual view is the most useful part for students because it says "
                 "what to change.")

    # ---------------- 13. ML pipeline ----------------
    slide = blank_slide(prs)
    header(slide, 13, "Component 9 of 11", "Reproducible ML Pipeline", "9 / 11")
    stages = [
        ("1", "Validate", "data_audit.py + data_pipeline.py\nschema, ranges, duplicates"),
        ("2", "Preprocess", "dedupe → stratified splits\nmissing checks, engineered features"),
        ("3", "Train & evaluate", "compare_models.py\n3 × 5 CV + hold-out metrics"),
        ("4", "Register artifact", "model_registry.py\nversion + metrics + metadata"),
        ("5", "Serve", "Flask API → joblib model\npredict + explain + skill gaps"),
    ]
    for index, (number, name, body) in enumerate(stages):
        x = MARGIN + index * 2.39
        rect(slide, x, 1.6, 2.15, 1.45, fill=PANEL if index % 2 == 0 else PANEL_ALT,
             line=STROKE, radius=0.08)
        text(slide, x + 0.15, 1.7, 0.4, 0.3, number, size=11, bold=True, color=ACCENT, font=HEAD)
        text(slide, x + 0.15, 1.98, 1.85, 0.3, name, size=11.5, bold=True)
        text(slide, x + 0.15, 2.32, 1.85, 0.65, body, size=8.8, color=MUTED, line_spacing=1.1)
        if index < 4:
            arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.17),
                                           Inches(2.32), Inches(0.2), Inches(0.2))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()
            arrow.shadow.inherit = False

    cards = [
        ("Reproducibility", "Fixed seed 42, pinned requirements, dataset SHA-256 recorded, and "
         "every evaluation writes its own report JSON + Markdown.", ACCENT),
        ("Versioned artifacts", "1.0.0-gb-winner is the live model; 2.0.0-calibrated-gb is the "
         "calibrated candidate. Research models are never auto-promoted.", BLUE),
        ("Retraining on demand", "train_model.py, compare_models.py, tune_xgboost.py and "
         "auto_select_and_retrain.py rebuild and re-evaluate the pipeline end to end.", GREEN),
    ]
    for index, (heading, body, color) in enumerate(cards):
        card(slide, MARGIN + index * 3.98, 3.45, 3.83, 1.75, heading, body, accent=color, size=10.5)
    rect(slide, MARGIN, 5.55, CONTENT_W, 0.85, fill=PANEL_ALT, line=STROKE, radius=0.06)
    text(slide, MARGIN + 0.2, 5.68, CONTENT_W - 0.4, 0.6,
         "One command rebuilds evidence: reports/model-evaluation/, reports/data-audit/ and "
         "reports/teacher-brief-xgboost/ are generated, not hand-written.",
         size=10.5, color=ACCENT_SOFT, line_spacing=1.15)
    notes(slide, "Frame the pipeline as a chain of recorded decisions. Mention that the model "
                 "artifact carries its own metrics and metadata, so serving and evaluation cannot "
                 "drift apart silently.")

    # ---------------- 14. Deployment architecture ----------------
    slide = blank_slide(prs)
    header(slide, 14, "Component 10 of 11", "Deployment — Web App + REST API", "10 / 11")
    boxes = [
        ("React 18 SPA", "Vite · Recharts · Lucide\nDashboard, history, mentor views", BLUE),
        ("Nginx", "Static build + SPA fallback\n/api reverse proxy", ACCENT_SOFT),
        ("Gunicorn + Flask", "2 workers × 4 threads\nREST API, auth, CSRF", ACCENT),
        ("Gradient Boosting", "placement_model.joblib\npredict_proba + explanations", GREEN),
    ]
    for index, (name, body, color) in enumerate(boxes):
        x = MARGIN + index * 2.95
        rect(slide, x, 1.55, 2.6, 1.5, fill=PANEL, line=STROKE, radius=0.06)
        rect(slide, x, 1.55, 2.6, 0.05, fill=color)
        text(slide, x + 0.16, 1.72, 2.3, 0.3, name, size=12, bold=True, color=color, font=HEAD)
        text(slide, x + 0.16, 2.06, 2.3, 0.85, body, size=9.3, color=WHITE, line_spacing=1.15)
        if index < 3:
            arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.66),
                                           Inches(2.17), Inches(0.24), Inches(0.26))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = STROKE
            arrow.line.fill.background()
            arrow.shadow.inherit = False

    left = [
        ("Run it: ", "docker compose -f docker-compose.production.yml up --build → UI on :8080, API reached via the Nginx /api proxy."),
        ("API surface: ", "/api/predict, /api/history, /api/cohort-analytics, /api/auth/*, health & readiness probes."),
        ("Security: ", "session auth with server-enforced roles, CSRF token on state changes, cohort scoping."),
        ("Alternate entry point: ", "backend/asgi.py mounts the same app under FastAPI/uvicorn — no logic fork."),
    ]
    bullets(slide, MARGIN, 3.35, 7.4, 2.0, left, size=10.8, gap=6)
    rect(slide, MARGIN, 5.45, 7.4, 1.1, fill=PANEL, line=STROKE, radius=0.05)
    text(slide, MARGIN + 0.18, 5.53, 7.05, 0.24, "SAMPLE REQUEST — POST /api/v1/predict", size=8.5,
         bold=True, color=ACCENT, font=HEAD)
    text(slide, MARGIN + 0.18, 5.76, 7.05, 0.75,
         '{"cgpa": 8.5, "coding_score": 80, "technical_score": 75, "aptitude_score": 72,\n'
         ' "communication_score": 85, "projects": 4, "internships": 1, "certifications": 3,\n'
         ' "backlogs": 0}   →  {readiness_score, category, top_factors, skill_gaps}',
         size=8.2, color=MUTED, font=MONO, line_spacing=1.2)
    rect(slide, 8.55, 3.35, 3.95, 3.25, fill=PANEL_ALT, line=STROKE, radius=0.06)
    text(slide, 8.75, 3.47, 3.55, 0.28, "DEPLOYMENT STATUS", size=9.5, bold=True, color=ACCENT,
         font=HEAD)
    text(slide, 8.75, 3.8, 3.55, 2.6,
         "Containerized stack runs end to end and is health-check gated.\n\n"
         "Hosted URL, TLS, institutional SSO and a managed database are the remaining "
         "production steps — documented in docs/DEPLOYMENT_BASELINE.md rather than claimed.\n\n"
         "The prototype never presents its score as an official placement decision.",
         size=9.6, color=WHITE, line_spacing=1.15)
    notes(slide, "Deployment is mandatory, so lead with the runnable stack, not the caveats. "
                 "Then be precise: local/container deployment is verified; a public institutional "
                 "URL is the next step. FastAPI exists as a wrapper, not a second codebase.")

    # ---------------- 15. Demo ----------------
    slide = blank_slide(prs)
    header(slide, 15, "Component 10 of 11", "Live Demo — What the User Actually Sees", "10 / 11")
    shots = [
        ("screenshots/fig1_dashboard_top_performer.png",
         "Readiness gauge + competency matrix", "Score, confidence band and nine sliders sync live"),
        ("screenshots/fig2_skill_gap_matrix.png",
         "Skill-gap matrix", "Every gap vs benchmark, colour-coded by severity"),
        ("screenshots/fig4_influential_factors.png",
         "Influential factors", "Model importance surfaced inside the product"),
    ]
    for index, (path, title, caption) in enumerate(shots):
        x = MARGIN + index * 3.99
        image_path = ROOT / path
        rect(slide, x, 1.55, 3.83, 2.55, fill=PANEL, line=STROKE, radius=0.03)
        with Image.open(image_path) as image:
            ratio = image.height / image.width
        slide.shapes.add_picture(str(image_path), Inches(x + 0.06), Inches(1.6),
                                 width=Inches(3.71), height=Inches(3.71 * ratio))
        text(slide, x, 4.28, 3.83, 0.28, title, size=11, bold=True, color=ACCENT_SOFT)
        text(slide, x, 4.56, 3.83, 0.55, caption, size=9.2, color=MUTED, line_spacing=1.1)
    rect(slide, MARGIN, 5.35, CONTENT_W, 1.4, fill=PANEL_ALT, line=STROKE, radius=0.06)
    text(slide, MARGIN + 0.25, 5.5, 4.2, 0.3, "INTERACTION LOOP", size=9.5, bold=True,
         color=ACCENT, font=HEAD)
    steps = ["Adjust profile", "Live prediction", "See the gap", "Get 30–60 day plan", "Export report"]
    for index, step in enumerate(steps):
        x = MARGIN + 0.25 + index * 2.32
        text(slide, x, 5.82, 2.1, 0.3, step, size=10.5, bold=True)
        if index < 4:
            text(slide, x + 1.85, 5.82, 0.3, 0.3, "→", size=12, color=ACCENT)
    text(slide, MARGIN + 0.25, 6.2, 11.1, 0.4,
         "Presets (Top Performer / Average / Needs Focus / Active Backlogs) make the demo fast and "
         "repeatable in front of a panel.", size=9.8, color=MUTED)
    notes(slide, "Demo order: top-performer preset, then needs-focus, then open the gap matrix and "
                 "the roadmap. Keep it under 90 seconds. Point out that the importance chart in the "
                 "UI is the same model evidence from the XAI slide.")

    # ---------------- 16. GitHub ----------------
    slide = blank_slide(prs)
    header(slide, 16, "Component 11 of 11", "GitHub Repository & Documentation", "11 / 11")
    rect(slide, MARGIN, 1.5, 6.05, 4.95, fill=PANEL, line=STROKE, radius=0.04)
    tree = (
        "LPU-Placement-Intelligence/\n"
        "├── backend/          Flask API · ML · auth · tests\n"
        "│   ├── app.py · model.py · data_pipeline.py\n"
        "│   ├── compare_models.py · tune_xgboost.py\n"
        "│   └── placement_model.joblib (+ calibrated)\n"
        "├── frontend/         React 18 + Vite dashboard\n"
        "│   └── src/ · tests · Playwright e2e\n"
        "├── dataset/          7 CSV files + audit scripts\n"
        "├── docs/             27 design / ops / governance docs\n"
        "├── reports/          CV, calibration, XAI evidence\n"
        "├── screenshots/      demo figures used in this deck\n"
        "├── docker-compose.yml + production stack\n"
        "├── requirements-dev.txt · pyproject.toml\n"
        "└── README.md         setup · API · model card"
    )
    text(slide, MARGIN + 0.22, 1.62, 5.6, 0.28, "REPOSITORY LAYOUT", size=9.5, bold=True,
         color=ACCENT, font=HEAD)
    text(slide, MARGIN + 0.22, 1.95, 5.65, 4.3, tree, size=9.6, color=WHITE, font=MONO,
         line_spacing=1.25)

    checklist = [
        ("Source code", "backend + frontend + scripts"),
        ("Dataset info", "dataset/README.md with sources, sizes, limits"),
        ("ML pipeline", "validation → training → evaluation → registry"),
        ("Model artifacts", "versioned .joblib + retraining scripts"),
        ("Requirements", "requirements-dev.txt, research extras, npm lockfile"),
        ("README + deployment", "setup, API reference, Docker instructions"),
        ("Screenshots / demo", "five figures + demo guide"),
        ("Documentation", "architecture, XAI, auth, governance, release criteria"),
    ]
    for index, (item, detail) in enumerate(checklist):
        column = index % 2
        row = index // 2
        x = 7.05 + column * 2.85
        y = 1.5 + row * 1.24
        rect(slide, x, y, 2.7, 1.1, fill=PANEL_ALT if column else PANEL, line=STROKE, radius=0.08)
        text(slide, x + 0.14, y + 0.12, 0.3, 0.3, "✓", size=13, bold=True, color=GREEN, font=HEAD)
        text(slide, x + 0.45, y + 0.1, 2.1, 0.28, item, size=10, bold=True)
        text(slide, x + 0.45, y + 0.4, 2.1, 0.6, detail, size=8.3, color=MUTED, line_spacing=1.1)
    rect(slide, MARGIN, 6.58, CONTENT_W, 0.28, fill=None)
    text(slide, MARGIN, 6.6, CONTENT_W, 0.3,
         "CI: .github/workflows/frontend-ci.yml (lint, format, unit tests, bundle budget) · 50 test files across backend and frontend",
         size=9.5, color=MUTED)
    notes(slide, "If the panel checks the repository, the layout tree is the map. Point out that "
                 "documentation is not one README — there are 27 docs covering auth, deployment, "
                 "XAI and release criteria.")

    # ---------------- 17. Tech stack ----------------
    slide = blank_slide(prs)
    header(slide, 17, "Tech Stack", "What It Is Built With, and Why")
    stack = [
        ["Layer", "Technology", "Why this choice"],
        ["Language", "Python 3.10+ · JavaScript (ESM)", "One ML ecosystem, one UI ecosystem"],
        ["ML / data", "scikit-learn · NumPy · pandas", "Tabular ensembles, reproducible CV, mature tooling"],
        ["Explainability", "SHAP · feature importance · counterfactuals", "Local and global reasons for every score"],
        ["Backend", "Flask REST API · Gunicorn", "Small surface, easy auth/CSRF control, worker-safe"],
        ["Optional ASGI", "FastAPI / uvicorn wrapper", "Same app served through an async entry point"],
        ["Frontend", "React 18 · Vite · Recharts · Lucide", "Fast dev loop, charting, accessible components"],
        ["Data stores", "SQLite (prototype) · Supabase (migration path)", "Local demo today, managed Postgres later"],
        ["Packaging", "Docker · Docker Compose · Nginx", "Identical local and container behaviour"],
        ["Quality", "pytest · Vitest · Playwright · ESLint · Ruff", "Model, API, UI and end-to-end coverage"],
    ]
    table(slide, MARGIN, 1.55, 11.3, 4.4, stack, [1.9, 3.55, 5.85], font_size=10.2,
          header_size=10.2, align_center_from=9)
    text(slide, MARGIN, 6.15, CONTENT_W, 0.6,
         "Dependency discipline: runtime, research and migration requirements are separate files, "
         "so a demo install never drags in SHAP, XGBoost tuning or Supabase migration tooling.",
         size=10.5, color=ACCENT_SOFT, line_spacing=1.15)
    notes(slide, "Do not read the table. Name the spine: scikit-learn for the model, Flask for "
                 "serving, React for the interface, Docker for delivery, SHAP for trust.")

    # ---------------- 18. Team ----------------
    slide = blank_slide(prs)
    header(slide, 18, "Team", "Three Members, End-to-End Ownership")
    members = [
        ("Team Member 1", "Name · Roll No.", "Data & ML",
         ["Dataset audit and EDA", "Preprocessing and baselines", "8-model benchmark + tuning",
          "Calibration and evaluation reports", "Owner: reports/model-evaluation/"], ACCENT),
        ("Team Member 2", "Name · Roll No.", "Backend & Deployment",
         ["Flask REST API and validation", "Auth, roles and CSRF", "Model registry and artifacts",
          "Docker, Gunicorn, Nginx, CI", "Owner: deployment + API docs"], BLUE),
        ("Team Member 3", "Name · Roll No.", "Frontend & XAI",
         ["React dashboard and presets", "Skill-gap and roadmap views", "SHAP / factor panels",
          "Docs, screenshots, demo script", "Owner: UI evidence + demo"], GREEN),
    ]
    for index, (name, roll, role, tasks, color) in enumerate(members):
        x = MARGIN + index * 3.98
        rect(slide, x, 1.55, 3.83, 3.85, fill=PANEL, line=STROKE, radius=0.05)
        rect(slide, x, 1.55, 3.83, 0.06, fill=color)
        text(slide, x + 0.22, 1.78, 3.4, 0.3, name, size=14, bold=True, font=HEAD)
        text(slide, x + 0.22, 2.1, 3.4, 0.26, roll, size=9.5, color=MUTED)
        text(slide, x + 0.22, 2.45, 3.4, 0.3, role.upper(), size=9.5, bold=True, color=color,
             font=HEAD)
        rect(slide, x + 0.22, 2.82, 3.4, 0.012, fill=STROKE)
        bullets(slide, x + 0.22, 3.0, 3.35, 2.9, tasks, size=10.3, gap=10, marker="–")
    text(slide, MARGIN, 5.62, CONTENT_W, 0.7,
         "Placeholder names and roll numbers — replace before submission.\n"
         "Shared ownership: weekly review of reports, README and demo script.",
         size=10, color=ACCENT_SOFT, line_spacing=1.3)
    notes(slide, "Keep this to 20 seconds unless asked. Edit the three placeholder name blocks and "
                 "the role split to match the actual contributions.")

    # ---------------- 19. Conclusion ----------------
    slide = blank_slide(prs)
    header(slide, 19, "Wrap-up", "Outcome, Honest Gaps, Next Steps")
    card(slide, MARGIN, 1.55, 3.83, 2.55, "What we delivered",
         "A deployed, explainable readiness platform: 8-model benchmark, 96.08% hold-out accuracy, "
         "calibrated probabilities, skill-gap diagnosis, action roadmap, auth and Docker stack.",
         accent=GREEN, size=11.5)
    card(slide, MARGIN + 3.98, 1.55, 3.83, 2.55, "What is still prototype",
         "The label and provenance are unverified, validation is same-source, no subgroup fairness "
         "audit, and hosting/TLS/institutional SSO remain before real student use.",
         accent=RED, size=11.5)
    card(slide, MARGIN + 7.96, 1.55, 3.83, 2.55, "What comes next",
         "Verified LPU outcome data, external validation and calibration checks, resume/GitHub "
         "parsing, company-specific cutoffs, and a hosted pilot with the placement cell.",
         accent=BLUE, size=11.5)
    rect(slide, MARGIN, 4.35, CONTENT_W, 1.55, fill=PANEL_ALT, line=STROKE, radius=0.06)
    text(slide, MARGIN + 0.25, 4.49, 11.0, 0.3, "TAKEAWAY", size=9.5, bold=True, color=ACCENT,
         font=HEAD)
    text(slide, MARGIN + 0.25, 4.8, 11.1, 0.9,
         "A model is only useful when a student can act on it. The contribution here is the "
         "complete loop — prediction, explanation, prescription and a deployable service — with "
         "the limits stated as clearly as the accuracy.",
         size=12.5, line_spacing=1.18)
    notes(slide, "Close on the loop, not the percentage. One sentence on limitations, one on next "
                 "steps, then invite questions.")

    # ---------------- 20. Thank you ----------------
    slide = blank_slide(prs)
    rect(slide, 0, 0, 0.12, SH, fill=ACCENT)
    text(slide, MARGIN + 0.6, 2.0, 10.5, 0.3, "THANK YOU", size=12, bold=True, color=ACCENT,
         font=HEAD)
    text(slide, MARGIN + 0.6, 2.4, 10.5, 1.0, "Questions & discussion", size=40, bold=True,
         font=HEAD)
    text(slide, MARGIN + 0.6, 3.55, 8.6, 1.0,
         "LPU Placement Intelligence — student readiness prediction, skill-gap diagnosis and a "
         "prescriptive roadmap.", size=14, color=MUTED, line_spacing=1.25)
    for index, label in enumerate(["Reproducible evaluation", "Explainable predictions",
                                   "Deployable service"]):
        x = MARGIN + 0.6 + index * 3.5
        rect(slide, x, 4.85, 3.2, 0.7, fill=PANEL, line=STROKE, radius=0.1)
        text(slide, x, 5.02, 3.2, 0.35, label, size=10.5, bold=True, color=ACCENT_SOFT,
             align=PP_ALIGN.CENTER)
    text(slide, MARGIN + 0.6, 6.4, 10.5, 0.35,
         "Team Member 1 · Team Member 2 · Team Member 3", size=10.5, color=MUTED)
    notes(slide, "Stop here. Let the panel ask. Likely questions: why Gradient Boosting, why not "
                 "deep learning, how do you know 96% is real, what happens with a new dataset.")

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
