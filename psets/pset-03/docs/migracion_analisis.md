# Migración de `analisis/` y del plan desde la rama `draft`

Fecha: 2026-11-15. Origen: `origin/draft` (`7ce9444`), `psets/pset-02/analisis/` y
`psets/pset-02/plan.txt` (versión local con J10 e I4 cerrados).

| Qué | Antes | Después |
|---|---|---|
| Scripts y listas | `draft:psets/pset-02/analisis/` (6 `.py`, 1 `.md`, 5 CSV en `listas/`) | `proyecto:psets/pset-03/analisis/`; las listas y el `.md` son idénticos a draft |
| Instrucciones de uso de los `.py` | `Uso, desde psets/pset-02/: python analisis/...` y `pip install ...` | `Uso, desde psets/pset-03/ (uv sync --group analisis): uv run python analisis/...` |
| Destino de la semilla en `equivalencias_tickers.py` | `AQUI.parent / "dbt"/"seeds"` y `/"kestra"/"scripts"` (dentro de pset-02) | `AQUI.parent.parent / "pset-02"`, para seguir alimentando el pipeline del PSet 2 sin crear carpetas en pset-03 |
| Dependencias | `analisis/requirements.txt` y `pyproject.toml` de draft (Python >=3.12, pandas>=3) | Grupo `analisis` en `pset-03/pyproject.toml` (Python 3.11, pandas<3 del proyecto): duckdb>=2,<3, pandas-market-calendars, statsmodels, xgboost, yfinance; `analisis/requirements.txt` no se copia |
| `uv.lock` | sin el análisis | +20 paquetes del grupo `analisis`; ninguna versión existente cambia; `requirements.txt` (runner) sin cambios |
| `.gitignore` | sin reglas de `analisis/` | `analisis/*.duckdb`, `analisis/*.duckdb.bak`, `analisis/*.log` |
| README | "permanece en la rama `draft` ... No se duplica" | apunta a `analisis/`, aclara que es exploratorio y no reemplaza el protocolo de la OBT |
| Plan | `draft:psets/pset-02/plan.txt` | `psets/pset-03/plan.txt` con una cabecera de 3 líneas sobre su origen; el resto sin cambios |

Las cachés `universo.duckdb`, `yahoo.duckdb` y `yahoo_v69_terminal.duckdb.bak` no se
versionan; se regeneran con `construir_listas.py`, `equivalencias_tickers.py` y
`traer_yahoo.py`, o se copian a mano desde la carpeta local de `draft`.
