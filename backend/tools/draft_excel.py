"""
draft_excel.py — Excel spreadsheet generation tool for SovereignForge

Generates formatted .xlsx workbooks from structured data.
Used for engineering calculations, inspection data, budget tables, risk registers.
"""
import sys
import asyncio
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR

try:
    import openpyxl
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, numbers
    )
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, Reference
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# ── Theme colours ─────────────────────────────────────────────────────────────
DARK_BLUE = "00336600"   # for openpyxl these are ARGB strings
HDR_BLUE  = "FF003366"
MID_BLUE  = "FF005B99"
ACCENT    = "FFFF6B35"
WHITE     = "FFFFFFFF"
LIGHT_BG  = "FFF0F0F5"
GREEN_OK  = "FF00875F"
AMBER     = "FFE67E22"
RED_RISK  = "FFC0392B"
GRAY_ROW  = "FFE8ECF0"


def _hdr_fill(color=HDR_BLUE):
    return PatternFill("solid", fgColor=color)

def _row_fill(color=LIGHT_BG):
    return PatternFill("solid", fgColor=color)

def _alt_fill():
    return PatternFill("solid", fgColor=GRAY_ROW)

def _thin_border():
    side = Side(style="thin", color="FFCCCCCC")
    return Border(left=side, right=side, top=side, bottom=side)

def _hdr_font(size=11):
    return Font(name="Calibri", bold=True, color=WHITE, size=size)

def _body_font(size=10, bold=False):
    return Font(name="Calibri", bold=bold, size=size)

def _center():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def _left():
    return Alignment(horizontal="left", vertical="center", wrap_text=True)


def _style_header_row(ws, row_num, cols, height=22):
    ws.row_dimensions[row_num].height = height
    for col in range(1, cols + 1):
        cell = ws.cell(row=row_num, column=col)
        cell.fill   = _hdr_fill()
        cell.font   = _hdr_font()
        cell.alignment = _center()
        cell.border = _thin_border()


def _add_cover_sheet(wb, title, subtitle, date_str):
    ws = wb.active
    ws.title = "Cover"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["C"].width = 25

    # Banner rows
    for r in range(1, 5):
        ws.row_dimensions[r].height = 18
        for c in range(1, 4):
            ws.cell(r, c).fill = _hdr_fill(HDR_BLUE)

    # Title
    ws.row_dimensions[5].height = 50
    tc = ws.cell(5, 2, title)
    tc.font = Font(name="Calibri", bold=True, size=22, color=WHITE)
    tc.fill = _hdr_fill(HDR_BLUE)
    tc.alignment = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[6].height = 8
    ws.cell(6, 2).fill = _hdr_fill(ACCENT)

    ws.row_dimensions[7].height = 28
    sc = ws.cell(7, 2, subtitle)
    sc.font = Font(name="Calibri", size=14, color="FF003366")
    sc.alignment = _left()

    ws.row_dimensions[8].height = 20
    dc = ws.cell(8, 2, f"Generated: {date_str}  |  SovereignForge AI — 100% On-Premise")
    dc.font = Font(name="Calibri", size=10, color="FF555555", italic=True)
    dc.alignment = _left()

    for r in range(9, 12):
        ws.row_dimensions[r].height = 14


def _add_findings_sheet(wb, findings, sheet_name="Findings"):
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False
    headers = ["#", "Finding Description", "Location / Component", "Severity", "Status"]
    col_widths = [5, 55, 25, 14, 14]

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Title row
    ws.row_dimensions[1].height = 24
    t = ws.cell(1, 1, sheet_name.upper())
    t.font = Font(name="Calibri", bold=True, size=14, color=WHITE)
    t.fill = _hdr_fill(HDR_BLUE)
    t.alignment = _left()
    ws.merge_cells("A1:E1")

    # Header row
    ws.row_dimensions[2].height = 20
    for c, h in enumerate(headers, 1):
        ws.cell(2, c, h)
    _style_header_row(ws, 2, len(headers))

    # Data rows
    severity_map = {
        "high": ("HIGH", RED_RISK), "critical": ("CRITICAL", RED_RISK),
        "medium": ("MEDIUM", AMBER), "moderate": ("MEDIUM", AMBER),
        "low": ("LOW", GREEN_OK),
    }
    for i, finding in enumerate(findings, 1):
        r = i + 2
        ws.row_dimensions[r].height = 30
        fill = _row_fill() if i % 2 == 0 else _alt_fill()

        # Auto-detect severity from text
        lower = finding.lower()
        sev_key = next((k for k in severity_map if k in lower), "medium")
        sev_label, sev_color = severity_map[sev_key]

        cells_data = [
            (1, str(i)),
            (2, finding),
            (3, "Field Inspection"),
            (4, sev_label),
            (5, "Open"),
        ]
        for col, val in cells_data:
            cell = ws.cell(r, col, val)
            cell.fill = fill
            cell.font = _body_font()
            cell.border = _thin_border()
            cell.alignment = _left() if col == 2 else _center()
            if col == 4:
                cell.fill = PatternFill("solid", fgColor=sev_color)
                cell.font = Font(name="Calibri", bold=True, size=10, color=WHITE)


def _add_risk_register_sheet(wb, risks):
    ws = wb.create_sheet("Risk Register")
    ws.sheet_view.showGridLines = False
    headers = ["#", "Risk Description", "Category", "Likelihood", "Impact", "Risk Level", "Mitigation"]
    col_widths = [5, 48, 18, 13, 12, 13, 40]

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.row_dimensions[1].height = 24
    t = ws.cell(1, 1, "RISK REGISTER")
    t.font = Font(name="Calibri", bold=True, size=14, color=WHITE)
    t.fill = _hdr_fill(HDR_BLUE)
    t.alignment = _left()
    ws.merge_cells("A1:G1")

    ws.row_dimensions[2].height = 20
    for c, h in enumerate(headers, 1):
        ws.cell(2, c, h)
    _style_header_row(ws, 2, len(headers))

    level_map = {
        "fire": ("HIGH", RED_RISK, "Immediate shutdown protocol"),
        "explosion": ("HIGH", RED_RISK, "Evacuation and emergency response"),
        "leak": ("HIGH", RED_RISK, "Isolate and repair within 24h"),
        "corrosion": ("MEDIUM", AMBER, "Schedule maintenance within 30 days"),
        "pressure": ("HIGH", RED_RISK, "Reduce operating pressure; inspect"),
        "compliance": ("MEDIUM", AMBER, "Engage regulatory team"),
        "default": ("MEDIUM", AMBER, "Monitor and schedule review"),
    }

    for i, risk in enumerate(risks, 1):
        r = i + 2
        ws.row_dimensions[r].height = 35
        lower = risk.lower()
        lkey = next((k for k in level_map if k != "default" and k in lower), "default")
        level, color, mitigation = level_map[lkey]
        category = "Safety" if level == "HIGH" else "Operational"

        data = [
            (1, str(i)),
            (2, risk),
            (3, category),
            (4, "3"),
            (5, "4" if level == "HIGH" else "2"),
            (6, level),
            (7, mitigation),
        ]
        alt = _row_fill() if i % 2 == 0 else _alt_fill()
        for col, val in data:
            cell = ws.cell(r, col, val)
            cell.font = _body_font()
            cell.border = _thin_border()
            cell.alignment = _left() if col in (2, 7) else _center()
            cell.fill = alt
            if col == 6:
                cell.fill = PatternFill("solid", fgColor=color)
                cell.font = Font(name="Calibri", bold=True, size=10, color=WHITE)


def _add_action_plan_sheet(wb, recommendations):
    ws = wb.create_sheet("Action Plan")
    ws.sheet_view.showGridLines = False
    headers = ["#", "Action / Recommendation", "Owner", "Priority", "Target Date", "Status"]
    col_widths = [5, 55, 20, 13, 16, 14]

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.row_dimensions[1].height = 24
    t = ws.cell(1, 1, "ACTION PLAN")
    t.font = Font(name="Calibri", bold=True, size=14, color=WHITE)
    t.fill = _hdr_fill(MID_BLUE)
    t.alignment = _left()
    ws.merge_cells("A1:F1")

    ws.row_dimensions[2].height = 20
    for c, h in enumerate(headers, 1):
        ws.cell(2, c, h)
    _style_header_row(ws, 2, len(headers), )

    from datetime import timedelta
    today = datetime.now()
    priorities = ["IMMEDIATE", "HIGH", "MEDIUM", "LOW"]

    for i, rec in enumerate(recommendations, 1):
        r = i + 2
        ws.row_dimensions[r].height = 32
        days_offset = (i - 1) * 7 + 7
        target = (today + timedelta(days=days_offset)).strftime("%Y-%m-%d")
        priority = priorities[min(i - 1, len(priorities) - 1)]
        p_color = RED_RISK if priority == "IMMEDIATE" else AMBER if priority == "HIGH" else GREEN_OK

        data = [
            (1, f"A{i:02d}"),
            (2, rec),
            (3, "Maintenance Dept."),
            (4, priority),
            (5, target),
            (6, "Pending"),
        ]
        alt = _row_fill() if i % 2 == 0 else _alt_fill()
        for col, val in data:
            cell = ws.cell(r, col, val)
            cell.font = _body_font()
            cell.border = _thin_border()
            cell.alignment = _left() if col == 2 else _center()
            cell.fill = alt
            if col == 4:
                cell.fill = PatternFill("solid", fgColor=p_color)
                cell.font = Font(name="Calibri", bold=True, size=9, color=WHITE)


async def run_draft_excel(
    extracted_data: dict,
    title: str = "Inspection Data Report",
    document_type: str = "inspection_data",
) -> dict:
    """
    Generate a formatted Excel workbook with multiple sheets.

    Returns:
        {"success": bool, "file_path": str, "filename": str, "sheets": int, "error": str|None}
    """
    if not OPENPYXL_AVAILABLE:
        return {
            "success": False, "file_path": "", "filename": "",
            "sheets": 0, "error": "openpyxl not installed. Run: pip install openpyxl"
        }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_xlsx, extracted_data, title, document_type)


def _build_xlsx(extracted_data: dict, title: str, document_type: str) -> dict:
    try:
        wb = openpyxl.Workbook()
        date_str = datetime.now().strftime("%B %d, %Y")
        subtitle = f"Prepared by SovereignForge AI Agent  |  {document_type.replace('_', ' ').title()}"

        summary         = extracted_data.get("summary", "")
        findings        = extracted_data.get("findings", [])
        risks           = extracted_data.get("risks", [])
        recommendations = extracted_data.get("recommendations", [])

        _add_cover_sheet(wb, title, subtitle, date_str)
        if findings:        _add_findings_sheet(wb, findings)
        if risks:           _add_risk_register_sheet(wb, risks)
        if recommendations: _add_action_plan_sheet(wb, recommendations)

        # Save
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_type = document_type.replace(" ", "_").lower()
        filename = f"{safe_type}_{ts}.xlsx"
        file_path = os.path.join(OUTPUT_DIR, filename)
        wb.save(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "filename": filename,
            "sheets": len(wb.sheetnames),
            "error": None,
        }
    except Exception as e:
        return {"success": False, "file_path": "", "filename": "", "sheets": 0, "error": str(e)}
