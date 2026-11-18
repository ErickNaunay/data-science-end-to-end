from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "docs" / "memo_tecnico.md"
OUTPUT = PROJECT_ROOT / "docs" / "PSet3_memo_Buenaño_Peñafiel.pdf"


def _inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', escaped)
    return escaped


def _table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _header_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5b6573"))
    canvas.drawString(18 * mm, 12 * mm, "QSRR-Predict · PSet 3")
    canvas.drawRightString(192 * mm, 12 * mm, f"Página {document.page}")
    canvas.restoreState()


def build_pdf() -> None:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="MemoTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17365d"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MemoHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.HexColor("#17365d"),
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MemoBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MemoTable",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.3,
            leading=9,
            spaceAfter=0,
        )
    )

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = [
                [Paragraph(_inline(cell), styles["MemoTable"]) for cell in row]
                for row in _table_rows(table_lines)
            ]
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365d")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aab7c4")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.extend([Spacer(1, 2), table, Spacer(1, 5)])
            continue
        if line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                item = lines[index].strip()[2:]
                items.append(ListItem(Paragraph(_inline(item), styles["MemoBody"])))
                index += 1
            story.append(
                ListFlowable(items, bulletType="bullet", leftIndent=14, bulletFontSize=6)
            )
            story.append(Spacer(1, 3))
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2)
            if level == 1:
                style = styles["MemoTitle"]
            else:
                style = styles["MemoHeading"]
            story.append(Paragraph(_inline(text), style))
            index += 1
            continue

        paragraph_lines = [line]
        index += 1
        while (
            index < len(lines)
            and lines[index].strip()
            and not lines[index].strip().startswith(("#", "|", "- "))
        ):
            paragraph_lines.append(lines[index].strip())
            index += 1
        story.append(Paragraph(_inline(" ".join(paragraph_lines)), styles["MemoBody"]))

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=19 * mm,
        title="Memo técnico — QSRR-Predict PSet 3",
        author="Jonatan Buenaño",
    )
    document.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    print(f"PDF generado: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
