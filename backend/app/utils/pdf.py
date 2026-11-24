"""PDF generation using ReportLab (formal, printable layouts)."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings

NAVY = colors.HexColor("#16243d")
INDIGO = colors.HexColor("#4338ca")
LIGHT = colors.HexColor("#eef2f7")


def _styles():
    base = getSampleStyleSheet()
    return {
        "institution": ParagraphStyle("inst", parent=base["Title"], fontSize=18, textColor=NAVY, spaceAfter=2),
        "subtitle": ParagraphStyle("sub", parent=base["Normal"], fontSize=10, textColor=colors.HexColor("#5b6472"), alignment=TA_CENTER),
        "heading": ParagraphStyle("head", parent=base["Heading2"], fontSize=14, textColor=INDIGO, alignment=TA_CENTER, spaceBefore=8, spaceAfter=8),
        "normal": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, leading=13, textColor=NAVY),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#5b6472")),
    }


def _table(data: list[list[Any]], widths: list[float] | None = None) -> Table:
    table = Table(data, colWidths=widths, hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _header(story: list, styles: dict, title: str) -> None:
    story.append(Paragraph(settings.institution_name, styles["institution"]))
    story.append(Paragraph(settings.institution_address, styles["subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Paragraph(title, styles["heading"]))


def render_hall_ticket(payload: dict[str, Any]) -> bytes:
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Hall Ticket", author=settings.institution_name,
    )
    story: list = []
    _header(story, styles, "EXAMINATION HALL TICKET")
    info = [
        ["Student Name", payload["student_name"], "Roll Number", payload["roll_number"]],
        ["Branch", payload.get("branch", "-"), "Semester", str(payload.get("semester", "-"))],
        ["Academic Year", payload.get("academic_year", "-"), "Examination", payload.get("examination", "-")],
        ["Ticket Number", payload["ticket_number"], "Issue Date", str(payload.get("issue_date", "-"))],
    ]
    story.append(_table(info, [32 * mm, 58 * mm, 32 * mm, 58 * mm]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Registered Subjects", styles["normal"]))
    story.append(Spacer(1, 2 * mm))
    rows = [["Code", "Subject", "Date", "Time", "Session / Venue"]]
    for item in payload.get("subjects", []):
        rows.append([
            item.get("code", "-"), item.get("name", "-"), str(item.get("date", "-")),
            f"{item.get('start_time', '-')} - {item.get('end_time', '-')}",
            f"{item.get('session', '-')} / {item.get('venue', '-')}",
        ])
    story.append(_table(rows, [22 * mm, 58 * mm, 24 * mm, 34 * mm, 42 * mm]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "Instructions: Bring a valid photo ID and this hall ticket. Reach the venue 30 minutes before the scheduled time. "
        "Electronic devices are not permitted. This document is valid only for the examinations listed above.",
        styles["small"],
    ))
    doc.build(story)
    return buf.getvalue()


def render_certificate(payload: dict[str, Any]) -> bytes:
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Semester Certificate", author=settings.institution_name,
    )
    story: list = []
    _header(story, styles, "SEMESTER RESULT CERTIFICATE")
    story.append(Paragraph(
        f"This is to certify that <b>{payload['student_name']}</b>, bearing roll number "
        f"<b>{payload['roll_number']}</b>, of the <b>{payload.get('branch', '-')}</b> branch, "
        f"has appeared for the <b>{payload.get('examination', 'examination')}</b> for "
        f"Semester <b>{payload['semester']}</b>, Academic Year <b>{payload.get('academic_year', '-')}</b>.",
        styles["normal"],
    ))
    story.append(Spacer(1, 5 * mm))
    rows = [["Code", "Subject", "Credits", "Marks", "Grade", "Status"]]
    for item in payload.get("subjects", []):
        rows.append([
            item.get("code", "-"), item.get("name", "-"), str(item.get("credits", "-")),
            str(item.get("marks", "-")), item.get("grade", "-"), item.get("status", "-"),
        ])
    story.append(_table(rows, [22 * mm, 62 * mm, 18 * mm, 24 * mm, 20 * mm, 34 * mm]))
    story.append(Spacer(1, 6 * mm))
    summary = [
        ["Semester SGPA (this semester)", str(payload.get("sgpa", "-"))],
        ["Current CGPA (all completed semesters)", str(payload.get("cgpa", "-"))],
        ["Issue Date", str(payload.get("issue_date", "-"))],
        ["Verification Reference", str(payload.get("verification_reference", "-"))],
    ]
    story.append(_table(summary, [95 * mm, 85 * mm]))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Authorized Signatory", styles["small"]))
    doc.build(story)
    return buf.getvalue()


def render_timetable(payload: dict[str, Any]) -> bytes:
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Examination Timetable", author=settings.institution_name,
    )
    story: list = []
    _header(story, styles, payload.get("title", "EXAMINATION TIMETABLE"))
    rows = [["Date", "Time", "Session", "Code", "Subject", "Venue"]]
    for item in payload.get("rows", []):
        rows.append([
            str(item.get("date", "-")), f"{item.get('start_time', '-')} - {item.get('end_time', '-')}",
            item.get("session", "-"), item.get("code", "-"), item.get("name", "-"), item.get("venue", "-"),
        ])
    story.append(_table(rows, [26 * mm, 34 * mm, 22 * mm, 22 * mm, 52 * mm, 30 * mm]))
    doc.build(story)
    return buf.getvalue()
