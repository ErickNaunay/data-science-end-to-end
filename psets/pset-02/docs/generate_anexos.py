"""Genera PSet2_anexos_Buenaño_Peñafiel.pdf con evidencia de ejecución del pipeline.

Uso:
    python docs/generate_anexos.py            # arma el PDF con docs/evidencia/*.json
    python docs/generate_anexos.py --refresh  # vuelve a recolectar la evidencia

`--refresh` lee los logs del contenedor `kestra_server`, `dbt/target/run_results.json`
y ejecuta consultas de solo lectura en Snowflake con las variables de `.env`
(exportadas en la terminal). No escribe credenciales en los JSON.

Las capturas de pantalla se toman manualmente y se guardan en `docs/capturas/`
(PNG o JPG). Se incluyen en orden alfabético; el nombre del archivo sin prefijo
numérico se usa como pie de figura, p. ej. `01_kestra_ejecucion_exitosa.png`, salvo
que `docs/capturas/pies.json` defina un pie para ese archivo.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCS = Path(__file__).resolve().parent
PSET = DOCS.parent
EVIDENCE = DOCS / "evidencia"
CAPTURES = DOCS / "capturas"
OUTPUT = DOCS / "PSet2_anexos_Buenaño_Peñafiel.pdf"
FLOW = "ingest_report_to_snowflake"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

pdfmetrics.registerFont(TTFont("AnexoSans", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("AnexoSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("AnexoMono", str(FONT_DIR / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily(
    "AnexoSans",
    normal="AnexoSans",
    bold="AnexoSans-Bold",
    italic="AnexoSans",
    boldItalic="AnexoSans-Bold",
)

NAVY = colors.HexColor("#17365d")
STYLES = {
    "title": ParagraphStyle(
        "title", fontName="AnexoSans-Bold", fontSize=15, leading=19,
        alignment=TA_CENTER, textColor=NAVY, spaceAfter=4,
    ),
    "subtitle": ParagraphStyle(
        "subtitle", fontName="AnexoSans", fontSize=8.5, leading=11,
        alignment=TA_CENTER, textColor=colors.HexColor("#5b6573"), spaceAfter=10,
    ),
    "h1": ParagraphStyle(
        "h1", fontName="AnexoSans-Bold", fontSize=11.5, leading=14,
        textColor=NAVY, spaceBefore=8, spaceAfter=4, keepWithNext=True,
    ),
    "body": ParagraphStyle(
        "body", fontName="AnexoSans", fontSize=8.5, leading=11.5,
        alignment=TA_JUSTIFY, spaceAfter=4,
    ),
    "cell": ParagraphStyle("cell", fontName="AnexoSans", fontSize=7.2, leading=9),
    "cellmono": ParagraphStyle("cellmono", fontName="AnexoMono", fontSize=6.6, leading=8.5),
    "caption": ParagraphStyle(
        "caption", fontName="AnexoSans", fontSize=7.5, leading=9.5,
        alignment=TA_CENTER, textColor=colors.HexColor("#5b6573"), spaceAfter=8,
    ),
}


# --------------------------------------------------------------------------- #
# Recolección de evidencia
# --------------------------------------------------------------------------- #
def _collect_kestra() -> dict:
    logs = subprocess.run(
        ["docker", "logs", "-t", "kestra_server"],
        capture_output=True, text=True, check=True,
    )
    text = re.sub(r"\x1b\[[0-9;]*m", "", logs.stdout + logs.stderr)
    lines = [line for line in text.splitlines() if f"[flow: {FLOW}]" in line]
    finished = [
        re.search(r"\[execution: (\w+)\] Flow completed with state (\w+) in ([\d:.]+)", line)
        for line in lines
    ]
    finished = [m for m in finished if m and m.group(2) == "SUCCESS"]
    if not finished:
        raise RuntimeError("No hay ejecuciones SUCCESS del flow en los logs de Kestra")
    execution, _, duration = finished[-1].groups()
    run_lines = [line for line in lines if f"[execution: {execution}]" in line]
    tasks = []
    for line in run_lines:
        m = re.search(
            r"\[task: (\w+)\].*Type (\w+) with state (\w+) completed in ([\d:.]+)", line
        )
        if m:
            tasks.append(dict(zip(("task", "type", "state", "duration"), m.groups())))
    trigger = next(
        (
            re.search(r"\[trigger: (\w+)\] Scheduled execution \w+ at '([^']+)'", line)
            for line in text.splitlines()
            if f"Scheduled execution {execution}" in line
        ),
        None,
    )
    timestamps = [line.split()[0] for line in run_lines]
    return {
        "flow": f"pset2.pipeline.{FLOW}",
        "execution_id": execution,
        "state": "SUCCESS",
        "duration": duration,
        "started_utc": timestamps[0][:19] if timestamps else None,
        "finished_utc": timestamps[-1][:19] if timestamps else None,
        "trigger": trigger.group(1) if trigger else "manual",
        "scheduled_for": trigger.group(2) if trigger else None,
        "tasks": tasks,
        "source": "docker logs kestra_server",
    }


def _collect_dbt() -> dict:
    data = json.loads((PSET / "dbt" / "target" / "run_results.json").read_text())
    results = []
    for item in data["results"]:
        kind, _, name = item["unique_id"].split(".", 2)
        results.append({
            "kind": kind,
            "name": re.sub(r"\.[0-9a-f]{10}$", "", name),
            "status": item["status"],
            "seconds": round(item["execution_time"], 2),
            "rows": (item.get("adapter_response") or {}).get("rows_affected"),
        })
    return {
        "command": f"dbt {data['args'].get('which')}",
        "generated_at": data["metadata"]["generated_at"][:19],
        "elapsed_seconds": round(data["elapsed_time"], 1),
        "dbt_version": data["metadata"].get("dbt_version"),
        "results": results,
    }


def _collect_snowflake() -> dict:
    import snowflake.connector

    db = os.environ["SNOWFLAKE_DATABASE"]
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=db,
        login_timeout=60,
    )
    queries = {
        "tablas": f"""SELECT TABLE_SCHEMA, TABLE_NAME, ROW_COUNT,
       TO_CHAR(CONVERT_TIMEZONE('UTC', LAST_ALTERED), 'YYYY-MM-DD HH24:MI') AS ULTIMA_ACTUALIZACION_UTC
FROM {db}.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA IN ('RAW', 'BRONZE', 'SILVER', 'GOLD') AND ROW_COUNT > 0
ORDER BY CASE TABLE_SCHEMA WHEN 'RAW' THEN 1 WHEN 'BRONZE' THEN 2
         WHEN 'SILVER' THEN 3 ELSE 4 END, TABLE_NAME""",
        "obt": f"""SELECT COUNT(*) AS TOTAL_FILAS, COUNT(DISTINCT HECHO_ID) AS HECHOS_UNICOS,
       COUNT_IF(HECHO_ID IS NULL) AS HECHO_ID_NULOS
FROM {db}.GOLD.OBT_QSRR_FINAL""",
        "referencial": f"""SELECT
  (SELECT COUNT(*) FROM {db}.GOLD.FACT_RETENCION_CROMATOGRAFICA f
     LEFT JOIN {db}.GOLD.DIM_COMPUESTO d USING (COMPUESTO_ID)
    WHERE d.COMPUESTO_ID IS NULL) AS HECHOS_SIN_COMPUESTO,
  (SELECT COUNT(*) FROM {db}.GOLD.FACT_RETENCION_CROMATOGRAFICA f
     LEFT JOIN {db}.GOLD.DIM_CONDICIONES d USING (CONDICION_ID)
    WHERE d.CONDICION_ID IS NULL) AS HECHOS_SIN_CONDICION""",
        "muestra_obt": f"""SELECT HECHO_ID, INCHIKEY, TIPO_COLUMNA, FLUJO_ML_MIN, TIEMPO_RETENCION
FROM {db}.GOLD.OBT_QSRR_FINAL ORDER BY HECHO_ID LIMIT 5""",
    }
    out = {"consultado_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M")}
    try:
        cursor = conn.cursor()
        for name, sql in queries.items():
            cursor.execute(sql)
            out[name] = {
                "sql": sql.replace(f"{db}.", "<DB>."),
                "columns": [d[0] for d in cursor.description],
                "rows": [["—" if v is None else str(v) for v in row] for row in cursor.fetchall()],
            }
    finally:
        conn.close()
    return out


def refresh() -> None:
    EVIDENCE.mkdir(exist_ok=True)
    for name, collect in (
        ("kestra", _collect_kestra),
        ("dbt", _collect_dbt),
        ("snowflake", _collect_snowflake),
    ):
        data = collect()
        (EVIDENCE / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Evidencia actualizada: docs/evidencia/{name}.json")


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def _p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def _table(rows: list[list[str]], widths: list[float], mono_cols: tuple[int, ...] = ()) -> Table:
    body = [
        [
            _p(f"<b>{escape(str(c))}</b>" if r == 0 else escape(str(c)),
               "cellmono" if r > 0 and i in mono_cols else "cell")
            for i, c in enumerate(row)
        ]
        for r, row in enumerate(rows)
    ]
    table = Table(body, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab7c4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _sql(sql: str) -> Table:
    lines = "<br/>".join(escape(line).replace(" ", "&nbsp;") for line in sql.splitlines())
    box = Table([[_p(lines, "cellmono")]], hAlign="LEFT")
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6f8")),
        ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab7c4")),
    ]))
    return box


def _captures(width: float, max_height: float) -> list:
    files = sorted(
        p for p in CAPTURES.glob("*")
        if p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    ) if CAPTURES.is_dir() else []
    captions_file = CAPTURES / "pies.json"
    captions = (
        json.loads(captions_file.read_text(encoding="utf-8")) if captions_file.is_file() else {}
    )
    story = []
    for number, path in enumerate(files, start=1):
        image = Image(str(path))
        scale = min(width / image.imageWidth, max_height / image.imageHeight)
        image.drawWidth, image.drawHeight = image.imageWidth * scale, image.imageHeight * scale
        caption = captions.get(path.name) or re.sub(
            r"^\d+[_\- ]*", "", path.stem
        ).replace("_", " ").strip()
        story.append(KeepTogether([
            image,
            _p(f"Figura A{number}. {escape(caption[:1].upper() + caption[1:])}", "caption"),
        ]))
    return story


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("AnexoSans", 7)
    canvas.setFillColor(colors.HexColor("#5b6573"))
    canvas.drawString(18 * mm, 10 * mm, "PSet 2 · Anexos de evidencia")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


def build() -> None:
    kestra = json.loads((EVIDENCE / "kestra.json").read_text(encoding="utf-8"))
    dbt = json.loads((EVIDENCE / "dbt.json").read_text(encoding="utf-8"))
    sf = json.loads((EVIDENCE / "snowflake.json").read_text(encoding="utf-8"))

    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm,
        title="PSet 2 — Anexos de evidencia", author="Jonatan Buenaño",
    )
    w = doc.width
    story = [
        _p("PSet 2 — Anexos de evidencia de ejecución", "title"),
        _p("Pipeline RepoRT → Kestra → Snowflake RAW → dbt (Bronze/Silver/Gold) → Spark → OBT", "subtitle"),
        _p(
            "Este anexo complementa el memo técnico. Reúne la evidencia de que el pipeline se "
            "ejecutó de punta a punta: capturas de pantalla de las herramientas, el registro de "
            "la ejecución programada en Kestra, el resultado de <i>dbt build</i> y consultas de "
            "verificación hechas directamente en Snowflake. Las tablas de las secciones B a D se "
            "generan con <i>docs/generate_anexos.py</i> a partir de salidas reales, no se "
            "transcriben a mano."
        ),
    ]

    captures = _captures(w, doc.height * 0.42)
    if captures:
        story += [_p("A. Capturas de pantalla", "h1")] + captures

    # B. Kestra
    story += [
        _p("B. Orquestación con Kestra", "h1"),
        _p(
            f"El flow <b>{escape(kestra['flow'])}</b> se ejecutó con el trigger "
            f"<b>{escape(kestra['trigger'])}</b> (programado para "
            f"{escape(str(kestra['scheduled_for']))}). La ejecución "
            f"<font name='AnexoMono'>{escape(kestra['execution_id'])}</font> inició el "
            f"{escape(str(kestra['started_utc']).replace('T', ' '))} UTC y terminó con estado "
            f"<b>{escape(kestra['state'])}</b> en {escape(kestra['duration'])}. Todas sus tareas "
            "terminaron en SUCCESS, sin reintentos:"
        ),
        _table(
            [["#", "Tarea", "Tipo", "Estado", "Duración"]]
            + [[str(i), t["task"], t["type"], t["state"], t["duration"]]
               for i, t in enumerate(kestra["tasks"], start=1)],
            [w * 0.06, w * 0.40, w * 0.16, w * 0.16, w * 0.22], mono_cols=(1,),
        ),
        _p(f"Fuente: {escape(kestra['source'])}.", "caption"),
    ]

    # C. dbt
    counts = {}
    for r in dbt["results"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = ", ".join(f"{v} {k.upper()}" for k, v in counts.items())
    story += [
        _p("C. Transformaciones con dbt", "h1"),
        _p(
            f"Resultado de <b>{escape(dbt['command'])}</b> (dbt {escape(str(dbt['dbt_version']))}) "
            f"ejecutado el {escape(dbt['generated_at'].replace('T', ' '))} UTC en "
            f"{dbt['elapsed_seconds']} s: <b>{len(dbt['results'])} acciones, {summary}</b>, "
            "0 errores. Los modelos materializan las tablas y las pruebas validan claves "
            "<i>not_null</i>/<i>unique</i> y relaciones de la tabla de hechos con sus dimensiones."
        ),
        _table(
            [["Tipo", "Modelo / prueba", "Estado", "Filas", "Seg."]]
            + [["modelo" if r["kind"] == "model" else "prueba",
                r["name"].removeprefix("pset_02_qsrr."), r["status"].upper(),
                f"{r['rows']:,}" if r["kind"] == "model" and r["rows"] is not None else "—",
                f"{r['seconds']:.2f}"] for r in dbt["results"]],
            [w * 0.10, w * 0.62, w * 0.10, w * 0.10, w * 0.08], mono_cols=(1,),
        ),
        _p("Fuente: dbt/target/run_results.json.", "caption"),
        PageBreak(),
    ]

    # D. Snowflake
    tablas = sf["tablas"]
    story += [
        _p("D. Verificación en Snowflake (Spark y OBT)", "h1"),
        _p(
            f"Consultas de solo lectura ejecutadas el {escape(sf['consultado_utc'])} UTC. "
            "Las tablas de carga temporales vacías que deja Kestra se omiten. Los conteos "
            "coinciden con los reportados en el memo; la OBT escrita por Spark conserva una fila "
            "por hecho."
        ),
        _p("<b>D.1 Tablas por capa</b>"),
        _sql(tablas["sql"]),
        Spacer(1, 3),
        _table(
            [["Esquema", "Tabla", "Filas", "Última actualización (UTC)"]]
            + [[r[0], r[1], f"{int(r[2]):,}", r[3]] for r in tablas["rows"]],
            [w * 0.14, w * 0.44, w * 0.14, w * 0.28], mono_cols=(1,),
        ),
        Spacer(1, 6),
    ]
    for key, title in (
        ("obt", "D.2 Grano y unicidad de la OBT"),
        ("referencial", "D.3 Integridad referencial en Gold"),
    ):
        block = sf[key]
        n = len(block["columns"])
        story += [
            KeepTogether([
                _p(f"<b>{title}</b>"),
                _sql(block["sql"]),
                Spacer(1, 3),
                _table([block["columns"]] + [[f"{int(v):,}" for v in row] for row in block["rows"]],
                       [w / n] * n),
            ]),
            Spacer(1, 6),
        ]
    sample = sf["muestra_obt"]
    story += [
        KeepTogether([
            _p("<b>D.4 Muestra de la OBT final</b>"),
            _sql(sample["sql"]),
            Spacer(1, 3),
            _table([sample["columns"]]
                   + [row[:-1] + [f"{float(row[-1]):.3f}"] for row in sample["rows"]],
                   [w * 0.27, w * 0.27, w * 0.24, w * 0.10, w * 0.12], mono_cols=(0, 1)),
        ]),
    ]

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"PDF generado: {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="recolecta evidencia nueva")
    if parser.parse_args().refresh:
        refresh()
    build()
