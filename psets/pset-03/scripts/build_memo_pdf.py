from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepInFrame,
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
DOCS = PROJECT_ROOT / "docs"
SOURCE = DOCS / "memo_tecnico.md"
OUTPUT = DOCS / "PSet3_memo_Buenaño_Peñafiel.pdf"
FIGURES = DOCS / "figures"
BENCHMARK_REPORT = DOCS / "llm_benchmark_metrics_20261118T013622Z.json"

_IMAGE_PATTERN = re.compile(
    r"!\[(?P<caption>.*?)\]\((?P<path>.*?)\)(?:\s*\{width=(?P<width>\d+)%\})?"
)


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


def _extract_eda_figures() -> None:
    notebook_path = PROJECT_ROOT / "notebooks" / "01_eda.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    FIGURES.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            image = output.get("data", {}).get("image/png")
            if image:
                outputs.setdefault(cell["id"], image)

    expected_cells = {
        "eda_distribution.png": "eda-target-distribution",
        "eda_correlation.png": "eda-correlations",
    }
    image_cells = [
        cell["id"]
        for cell in notebook["cells"]
        if any("image/png" in output.get("data", {}) for output in cell.get("outputs", []))
    ]
    if len(image_cells) < 2:
        raise ValueError(f"Expected two EDA figures in {notebook_path}")
    for name, cell_id in expected_cells.items():
        target_id = cell_id if cell_id in outputs else image_cells[
            0 if name == "eda_distribution.png" else 1
        ]
        (FIGURES / name).write_bytes(
            base64.b64decode(outputs[target_id], validate=True)
        )


def _save_cv_chart() -> None:
    baselines = pd.read_csv(DOCS / "baselines.csv")
    candidates = pd.read_csv(DOCS / "candidatos.csv")
    results = pd.concat([baselines, candidates], ignore_index=True)
    labels = {
        "naive_median": "Mediana global",
        "method_median_proxy": "Mediana condición",
        "ridge": "Ridge",
        "knn": "KNN",
        "mlp": "MLP",
        "random_forest": "Random Forest",
        "hist_gradient_boosting": "HistGradientBoosting",
    }
    results["label"] = results["family"].map(labels)
    results = results.sort_values("cv_rmse_mean", ascending=False)

    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    y = np.arange(len(results))
    ax.barh(
        y,
        results["cv_rmse_mean"],
        xerr=results["cv_rmse_std"],
        color=["#2a9d8f" if row.phase == "candidate" else "#8d99ae" for row in results.itertuples()],
        capsize=3,
    )
    ax.set_yticks(y, results["label"])
    ax.set_xlabel("RMSE CV (min), media ± desviación estándar")
    ax.set_title("Comparación agrupada por compuesto: 5 folds")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "cv_all_models.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_tuning_chart() -> None:
    tuning = pd.read_csv(DOCS / "tuning.csv")
    baseline = pd.read_csv(DOCS / "candidatos.csv").set_index("family")
    families = [
        ("random_forest", "Random Forest"),
        ("hist_gradient_boosting", "HistGradientBoosting"),
        ("mlp", "MLP"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7), sharey=True)
    colors_by_family = ["#457b9d", "#2a9d8f", "#e76f51"]
    for ax, (family, label), color in zip(axes, families, colors_by_family, strict=True):
        trials = tuning.loc[tuning["family"].eq(family)].sort_values("configuration")
        ax.scatter(
            trials["configuration"],
            trials["cv_rmse_mean"],
            color=color,
            s=20,
            alpha=0.8,
        )
        ax.axhline(
            baseline.loc[family, "cv_rmse_mean"],
            color="#333333",
            linestyle="--",
            linewidth=1,
            label="Default",
        )
        best_index = trials["cv_rmse_mean"].idxmin()
        best = trials.loc[best_index]
        ax.scatter(
            [best["configuration"]],
            [best["cv_rmse_mean"]],
            color="#d62828",
            s=30,
            zorder=3,
            label="Mejor tuning",
        )
        ax.set_title(label, fontsize=8)
        ax.set_xlabel("Configuración")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("RMSE CV (min)")
    axes[-1].legend(fontsize=6, loc="best")
    fig.suptitle("30 configuraciones por familia; línea = modelo default", y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES / "tuning_trials.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_llm_chart() -> None:
    report = json.loads(BENCHMARK_REPORT.read_text(encoding="utf-8"))
    metrics = report["metrics"]
    labels = ["Gemini", "Champion\nHistGradientBoosting", "Challenger\nRandom Forest"]
    rmse = [
        metrics["gemini_rmse_min"],
        metrics["champion_rmse_min"],
        metrics["challenger_rmse_min"],
    ]
    mae = [
        metrics["gemini_mae_min"],
        metrics["champion_mae_min"],
        metrics["challenger_mae_min"],
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.2))
    palette = ["#e76f51", "#2a9d8f", "#457b9d"]
    for ax, values, title in zip(
        axes,
        (rmse, mae),
        ("RMSE (min)", "MAE (min)"),
        strict=True,
    ):
        bars = ax.bar(labels, values, color=palette)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
        ax.tick_params(axis="x", labelsize=6)
        for bar, value in zip(bars, values, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
            )
    fig.suptitle("Misma muestra: 50 compuestos distintos del holdout", y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES / "llm_holdout_comparison.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def _prepare_figures() -> None:
    _extract_eda_figures()
    _save_cv_chart()
    _save_tuning_chart()
    _save_llm_chart()


def _image_flowable(match: re.Match, styles, doc):
    relative_path = match.group("path")
    path = (DOCS / relative_path).resolve()
    if not path.is_relative_to(DOCS.resolve()) or not path.is_file():
        raise ValueError(f"Report image is missing or outside docs: {relative_path}")
    width_fraction = int(match.group("width") or 100) / 100
    max_width = doc.width * width_fraction
    max_height = doc.height * (0.30 if width_fraction < 1 else 0.46)
    image = Image(str(path))
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    caption = Paragraph(_inline(match.group("caption")), styles["Caption"])
    return [image, caption]


def _build_story(styles, doc) -> list:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    pages: list[list] = [[]]
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line == r"\newpage":
            pages.append([])
            index += 1
            continue
        if line.startswith("!["):
            matches = []
            while index < len(lines) and lines[index].strip().startswith("!["):
                match = _IMAGE_PATTERN.fullmatch(lines[index].strip())
                if not match:
                    raise ValueError(f"Unsupported image syntax: {lines[index]}")
                matches.append(match)
                index += 1
            image_cells = [
                _image_flowable(match, styles, doc) for match in matches
            ]
            if len(image_cells) == 1 and int(matches[0].group("width") or 100) == 100:
                pages[-1].extend(image_cells[0])
            else:
                widths = [
                    doc.width * int(match.group("width") or 100) / 100
                    for match in matches
                ]
                table = Table([image_cells], colWidths=widths, hAlign="LEFT")
                table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                pages[-1].append(table)
            pages[-1].append(Spacer(1, 3))
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
            if not rows:
                continue
            column_count = len(rows[0])
            table = Table(
                rows,
                colWidths=[doc.width / column_count] * column_count,
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365d")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab7c4")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            pages[-1].extend([Spacer(1, 2), table, Spacer(1, 4)])
            continue
        if line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                item = lines[index].strip()[2:]
                items.append(ListItem(Paragraph(_inline(item), styles["MemoBody"])))
                index += 1
            pages[-1].append(
                ListFlowable(items, bulletType="bullet", leftIndent=12, bulletFontSize=5)
            )
            pages[-1].append(Spacer(1, 2))
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2)
            style = styles["MemoTitle"] if level == 1 else styles["MemoHeading"]
            pages[-1].append(Paragraph(_inline(text), style))
            index += 1
            continue

        paragraph_lines = [line]
        index += 1
        while (
            index < len(lines)
            and lines[index].strip()
            and not lines[index].strip().startswith(("#", "|", "- ", "!["))
            and lines[index].strip() != r"\newpage"
        ):
            paragraph_lines.append(lines[index].strip())
            index += 1
        pages[-1].append(
            Paragraph(_inline(" ".join(paragraph_lines)), styles["MemoBody"])
        )
        pages[-1].append(Spacer(1, 2))

    story = []
    for page_index, content in enumerate(pages):
        story.append(
            KeepInFrame(
                doc.width,
                doc.height,
                content,
                mode="shrink",
                hAlign="LEFT",
                vAlign="TOP",
            )
        )
        if page_index < len(pages) - 1:
            story.append(PageBreak())
    return story


def _header_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#5b6573"))
    canvas.drawString(18 * mm, 10 * mm, "QSRR-Predict · PSet 3")
    canvas.drawRightString(192 * mm, 10 * mm, f"Página {document.page}")
    canvas.restoreState()


def build_pdf() -> None:
    _prepare_figures()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="MemoTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17365d"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MemoHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=9.4,
            leading=11,
            textColor=colors.HexColor("#17365d"),
            spaceBefore=5,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MemoBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=8.7,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MemoTable",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=5.8,
            leading=7.1,
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Caption",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=6,
            leading=7,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#5b6573"),
            spaceAfter=2,
        )
    )

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=11 * mm,
        bottomMargin=15 * mm,
        title="Documento técnico — QSRR-Predict PSet 3",
        author="Jonatan Buenaño",
    )
    document.build(
        _build_story(styles, document),
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )
    print(f"PDF generado: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
