"""
draft_ppt.py — PowerPoint generation tool for SovereignForge

Generates a fully formatted .pptx presentation from structured data.
Used for board presentations, project summaries, inspection reports.
"""
import sys
import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False


# ── Color palette (industrial / MRPL style) ─────────────────────────────────
DARK_BLUE  = RGBColor(0x00, 0x33, 0x66)  if PPTX_AVAILABLE else None
MID_BLUE   = RGBColor(0x00, 0x5B, 0x99)  if PPTX_AVAILABLE else None
ACCENT_ORG = RGBColor(0xFF, 0x6B, 0x35)  if PPTX_AVAILABLE else None
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)  if PPTX_AVAILABLE else None
LIGHT_GRAY = RGBColor(0xF0, 0xF0, 0xF5)  if PPTX_AVAILABLE else None
TEXT_DARK  = RGBColor(0x1A, 0x1A, 0x2E)  if PPTX_AVAILABLE else None
GREEN_OK   = RGBColor(0x00, 0x87, 0x5F)  if PPTX_AVAILABLE else None
RED_RISK   = RGBColor(0xC0, 0x39, 0x2B)  if PPTX_AVAILABLE else None
AMBER      = RGBColor(0xE6, 0x7E, 0x22)  if PPTX_AVAILABLE else None


def _set_bg(slide, color: RGBColor):
    """Fill slide background with a solid color."""
    from pptx.oxml.ns import qn
    from lxml import etree
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_textbox(slide, text, left, top, width, height,
                 font_size=18, bold=False, color=None, align=PP_ALIGN.LEFT,
                 wrap=True, font_name="Calibri"):
    if not PPTX_AVAILABLE:
        return
    from pptx.util import Inches, Pt
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.name = font_name
    if color:
        run.font.color.rgb = color
    return txBox


def _add_rect(slide, left, top, width, height, fill_color, line_color=None):
    from pptx.util import Inches
    from pptx.oxml.ns import qn
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
    else:
        shape.line.fill.background()
    return shape


def _make_title_slide(prs, title: str, subtitle: str, date_str: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _set_bg(slide, DARK_BLUE)

    # Top accent bar
    _add_rect(slide, 0, 0, 10, 0.08, ACCENT_ORG)

    # Logo text placeholder
    _add_textbox(slide, "🛡 SovereignForge", 0.4, 0.2, 4, 0.5,
                 font_size=14, bold=True, color=ACCENT_ORG)

    # Main title
    _add_textbox(slide, title, 0.6, 1.6, 8.8, 2.0,
                 font_size=36, bold=True, color=WHITE,
                 align=PP_ALIGN.LEFT)

    # Separator line
    _add_rect(slide, 0.6, 3.5, 3.5, 0.05, ACCENT_ORG)

    # Subtitle
    _add_textbox(slide, subtitle, 0.6, 3.7, 8.8, 0.8,
                 font_size=18, bold=False, color=RGBColor(0xCC, 0xDD, 0xEE),
                 align=PP_ALIGN.LEFT)

    # Date
    _add_textbox(slide, date_str, 0.6, 4.5, 8.8, 0.4,
                 font_size=13, color=RGBColor(0xAA, 0xBB, 0xCC))

    # Bottom bar
    _add_rect(slide, 0, 6.9, 10, 0.2, MID_BLUE)
    _add_textbox(slide, "CONFIDENTIAL — FOR INTERNAL USE ONLY", 0, 7.0, 10, 0.2,
                 font_size=9, color=RGBColor(0x88, 0xAA, 0xCC),
                 align=PP_ALIGN.CENTER)


def _make_agenda_slide(prs, sections: list):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, LIGHT_GRAY)
    _add_rect(slide, 0, 0, 10, 0.08, ACCENT_ORG)
    _add_textbox(slide, "AGENDA", 0.5, 0.3, 9, 0.6,
                 font_size=28, bold=True, color=DARK_BLUE)
    _add_rect(slide, 0.5, 0.95, 3, 0.04, ACCENT_ORG)

    for i, section in enumerate(sections):
        y = 1.2 + i * 0.72
        _add_rect(slide, 0.5, y, 0.45, 0.45, DARK_BLUE)
        _add_textbox(slide, str(i + 1), 0.5, y + 0.02, 0.45, 0.45,
                     font_size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        _add_textbox(slide, section, 1.1, y + 0.04, 8, 0.45,
                     font_size=16, color=TEXT_DARK)


def _make_summary_slide(prs, title: str, summary: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, WHITE)
    _add_rect(slide, 0, 0, 10, 1.0, DARK_BLUE)
    _add_textbox(slide, title, 0.4, 0.2, 9.2, 0.6,
                 font_size=24, bold=True, color=WHITE)
    # Summary box
    _add_rect(slide, 0.4, 1.2, 9.2, 3.8, LIGHT_GRAY)
    _add_textbox(slide, summary, 0.7, 1.4, 8.6, 3.4,
                 font_size=15, color=TEXT_DARK, wrap=True)
    _add_rect(slide, 0, 6.9, 10, 0.2, DARK_BLUE)


def _make_findings_slide(prs, title: str, items: list, item_color=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, WHITE)
    _add_rect(slide, 0, 0, 10, 1.0, DARK_BLUE)
    _add_textbox(slide, title, 0.4, 0.2, 9.2, 0.6,
                 font_size=24, bold=True, color=WHITE)

    color = item_color or TEXT_DARK
    bullet = "▶"

    for i, item in enumerate(items[:6]):  # max 6 bullets
        y = 1.2 + i * 0.9
        _add_rect(slide, 0.4, y + 0.12, 0.04, 0.45, color)
        _add_textbox(slide, f"{bullet}  {item}", 0.55, y, 8.8, 0.8,
                     font_size=14, color=TEXT_DARK, wrap=True)

    _add_rect(slide, 0, 6.9, 10, 0.2, DARK_BLUE)


def _make_risk_matrix_slide(prs, risks: list):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, WHITE)
    _add_rect(slide, 0, 0, 10, 1.0, DARK_BLUE)
    _add_textbox(slide, "Risk Assessment", 0.4, 0.2, 9.2, 0.6,
                 font_size=24, bold=True, color=WHITE)

    risk_colors = {"HIGH": RED_RISK, "MEDIUM": AMBER, "LOW": GREEN_OK}
    y = 1.2
    for risk in risks[:5]:
        level = "HIGH" if any(w in risk.upper() for w in ["HIGH", "CRITICAL", "SEVERE", "FIRE", "EXPLOSION"]) \
               else "MEDIUM" if any(w in risk.upper() for w in ["MEDIUM", "MODERATE", "MODERATE"]) \
               else "LOW"
        rc = risk_colors.get(level, AMBER)
        _add_rect(slide, 0.4, y, 1.2, 0.55, rc)
        _add_textbox(slide, level, 0.4, y + 0.1, 1.2, 0.35,
                     font_size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        _add_textbox(slide, risk, 1.75, y + 0.05, 7.8, 0.5,
                     font_size=13, color=TEXT_DARK, wrap=True)
        y += 0.75

    _add_rect(slide, 0, 6.9, 10, 0.2, DARK_BLUE)


def _make_recommendations_slide(prs, recommendations: list):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, WHITE)
    _add_rect(slide, 0, 0, 10, 1.0, MID_BLUE)
    _add_textbox(slide, "Recommendations & Next Steps", 0.4, 0.2, 9.2, 0.6,
                 font_size=24, bold=True, color=WHITE)

    for i, rec in enumerate(recommendations[:6]):
        y = 1.2 + i * 0.88
        _add_rect(slide, 0.4, y + 0.1, 0.5, 0.5, ACCENT_ORG)
        _add_textbox(slide, f"R{i+1}", 0.4, y + 0.1, 0.5, 0.5,
                     font_size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        _add_textbox(slide, rec, 1.05, y + 0.08, 8.5, 0.72,
                     font_size=14, color=TEXT_DARK, wrap=True)

    _add_rect(slide, 0, 6.9, 10, 0.2, MID_BLUE)


def _make_closing_slide(prs, prepared_by: str = "SovereignForge AI Agent"):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, DARK_BLUE)
    _add_rect(slide, 0, 0, 10, 0.08, ACCENT_ORG)
    _add_textbox(slide, "Thank You", 1, 1.8, 8, 1.2,
                 font_size=48, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    _add_rect(slide, 2, 3.2, 6, 0.06, ACCENT_ORG)
    _add_textbox(slide, "Generated by SovereignForge — 100% On-Premise AI",
                 0.5, 3.5, 9, 0.6,
                 font_size=16, color=RGBColor(0xCC, 0xDD, 0xEE),
                 align=PP_ALIGN.CENTER)
    _add_textbox(slide, f"Prepared by: {prepared_by}", 0.5, 4.3, 9, 0.4,
                 font_size=13, color=RGBColor(0xAA, 0xBB, 0xCC),
                 align=PP_ALIGN.CENTER)
    _add_textbox(slide, "CONFIDENTIAL — No data left the premises during generation.",
                 0.5, 5.5, 9, 0.4, font_size=11,
                 color=RGBColor(0x66, 0x88, 0xAA), align=PP_ALIGN.CENTER)
    _add_rect(slide, 0, 6.9, 10, 0.2, MID_BLUE)


async def run_draft_ppt(
    extracted_data: dict,
    title: str = "Executive Report",
    subtitle: str = "AI-Generated Presentation",
    document_type: str = "inspection_report",
    prepared_by: str = "SovereignForge AI Agent",
) -> dict:
    """
    Generate a formatted PowerPoint presentation.

    Args:
        extracted_data: dict with keys: summary, findings, risks, recommendations
        title: Presentation title
        subtitle: Subtitle text
        document_type: Type of presentation (for naming)
        prepared_by: Author line on closing slide

    Returns:
        {"success": bool, "file_path": str, "filename": str, "slides": int, "error": str|None}
    """
    if not PPTX_AVAILABLE:
        return {
            "success": False, "file_path": "", "filename": "",
            "slides": 0, "error": "python-pptx not installed. Run: pip install python-pptx"
        }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _build_pptx,
                                        extracted_data, title, subtitle,
                                        document_type, prepared_by)
    return result


def _build_pptx(extracted_data: dict, title: str, subtitle: str,
                document_type: str, prepared_by: str) -> dict:
    try:
        prs = Presentation()
        prs.slide_width  = Inches(10)
        prs.slide_height = Inches(7.5)

        summary = extracted_data.get("summary", "")
        findings = extracted_data.get("findings", [])
        risks = extracted_data.get("risks", [])
        recommendations = extracted_data.get("recommendations", [])
        date_str = datetime.now().strftime("%B %d, %Y")

        # Build agenda
        sections = []
        if summary:         sections.append("Executive Summary")
        if findings:        sections.append("Key Findings")
        if risks:           sections.append("Risk Assessment")
        if recommendations: sections.append("Recommendations")

        # Slides
        _make_title_slide(prs, title, subtitle, date_str)
        if sections:
            _make_agenda_slide(prs, sections)
        if summary:
            _make_summary_slide(prs, "Executive Summary", summary)
        if findings:
            _make_findings_slide(prs, "Key Findings", findings, MID_BLUE)
        if risks:
            _make_risk_matrix_slide(prs, risks)
        if recommendations:
            _make_recommendations_slide(prs, recommendations)
        _make_closing_slide(prs, prepared_by)

        # Save
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_type = document_type.replace(" ", "_").lower()
        filename = f"{safe_type}_{ts}.pptx"
        file_path = os.path.join(OUTPUT_DIR, filename)
        prs.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "filename": filename,
            "slides": len(prs.slides),
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": "",
            "filename": "",
            "slides": 0,
            "error": str(e),
        }
