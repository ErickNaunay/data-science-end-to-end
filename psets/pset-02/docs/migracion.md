# Migración draft → proyecto — 2026-11-15

Referencia: `../CD_PSet_2.pdf`. Se transfieren Compose, Kestra, dbt (modelos,
seeds y tests), Spark, diagramas, utilitarios y pruebas locales. El README
original del curso se conserva en `README_curso.md` y la rúbrica no cambia.
El origen y su plan.txt con cambios locales se conservan sin modificaciones.

Se excluyen analisis/ (reservado para PSet 3), credenciales, llaves, entornos,
cachés, bases locales, artefactos dbt y métricas docs/corrida/ del borrador.
Se excluyen pyproject.toml y uv.lock porque mezclan dependencias del análisis
con el pipeline. requirements.txt declara dependencias locales del PSet 2;
no es una exportación del lock ni garantiza el mismo entorno del borrador.
Los SHA-256 originales figuran en migracion_origen.sha256; README, docs/README,
Dockerfile de Kestra, dbt_project y Compose tienen ajustes documentales.

## Correspondencia con el PDF y siguientes verificaciones

| Requisito | Archivos | Pendiente operativo |
|---|---|---|
| Arquitectura | Compose y diagramas docs/ | Construir y levantar contenedores |
| Ingesta Raw | kestra/ | Correr backfill, diaria y retries |
| Calidad y limpieza | dbt Bronze (staging), Silver, CALIDAD | dbt build y métricas |
| Star schema | Gold y diagrama dimensional | Validar grano y relaciones |
| OBT | spark/jobs/construir_obt.py | Ejecutar en Snowflake y revisar controles |
| Batch vs streaming | README | Incorporar justificación al memo |
| Memo hasta 6 páginas | Diagramas disponibles | Elaborar con evidencia real |

Orden: configurar entorno local según README; construir infraestructura;
preparar Snowflake; cargar flows; ejecutar backfill, dbt y Spark; exportar
métricas a docs/corrida/; elaborar memo. No se transfieren resultados de draft
como evidencia de ejecución en proyecto. Quedan pendientes las pruebas pytest
propuestas en J9 del plan y la comprobación de punta a punta de J10.

No se ejecutaron cargas ni cambios en Snowflake. No se hicieron commits,
push ni tags. proyecto estaba un commit detrás de la referencia local
origin/proyecto (solo afecta PSet 1); no se sincronizó ni consultó el remoto.

## Verificación realizada

- PDF idéntico al origen y manifiesto SHA-256 de los 81 archivos transferidos.
- Sintaxis Python (AST) y shell (`bash -n`) válida.
- `docker compose --profile herramientas config --quiet` válido con .env.example.
- `git diff --check` sin errores.
- Sin archivos de credenciales, llaves privadas ni bases locales transferidos.

Estas comprobaciones no sustituyen la ejecución de Kestra, dbt y Spark.

## Revisión posterior

La verificación operativa inicial pendiente se abordó el 15 de noviembre de
2026. Consultar `cumplimiento.md` y `corrida/` para resultados actuales; los
apartados anteriores describen únicamente el momento de la copia inicial.

## Cambio de entorno: uv por carpeta y Python 3.11 (2026-11-15)

Decisión de Paul, según el acuerdo de trabajo ("entornos con uv, un proyecto
independiente por carpeta") y la CI del curso (`python-version: "3.11"`).

| | Antes | Después |
|---|---|---|
| Entorno pset-02 | `requirements.txt` escrito a mano, rangos `>=,<`, sin lock | `pyproject.toml` + `uv.lock` (solo pipeline; `requires-python ==3.11.*`) |
| Imagen de ingesta | `kestra/requirements.txt` a mano | Exportado del mismo lock, grupo `ingesta`, versiones `==` |
| Entorno pset-03 | `requirements.txt` a mano | `pyproject.toml` + `uv.lock` propios; `requirements.txt` exportado |
| Python de las imágenes | `python:3.12-slim` (Kestra, MLflow, runner) | `python:3.11-slim` |
| duckdb local | `>=1,<2` | `>=2,<3`: un mismo formato de archivo en todas las máquinas |
| Instrucciones | `pip install -r requirements.txt` | `uv sync` y `uv run ...` |

Los `requirements.txt` se regeneran con `bash scripts/exportar_requirements.sh`
(pset-02) y `bash exportar_requirements.sh` (pset-03). La objeción de la copia
inicial —que el lock del borrador mezclaba el análisis con el pipeline— se resuelve
con un proyecto por carpeta: pset-02 ya no incluye dependencias de modelado.

Verificado con Python 3.11.17: `uv sync`, `pytest` (3 pruebas en pset-02 y 3 en
pset-03), imports de la imagen de ingesta (yfinance 1.8.0, pandas 2.3.3) y
`dbt --version` (dbt-core 1.12.7, igual que la imagen). Pendiente: reconstruir las
imágenes en la Mac (`docker compose build`) y una corrida corta de cada flow.

Ajuste posterior (mismo día): `pyspark==3.5.3` pasó de las dependencias principales al
grupo opcional `pruebas-locales`. Antes, `uv sync` descargaba ~317 MB de pyspark aunque la
corrida real usa Spark dentro de la imagen `pset2-spark`; ahora `uv sync --group dev` no lo
instala y `uv sync --group dev --group pruebas-locales` lo agrega para `pruebas_locales/`.
Las versiones de los 101 paquetes del lock no cambiaron; `requirements.txt` local sigue
incluyendo pyspark y `kestra/requirements.txt` no cambió.

Ajuste posterior (mismo día): `kestra/Dockerfile` usa la caché de pip de BuildKit.
Antes: `RUN pip install --no-cache-dir -r requirements.txt` (un build cortado volvía a
descargar todo). Después: `RUN --mount=type=cache,target=/root/.cache/pip pip install -r
requirements.txt` (los reintentos reutilizan lo descargado; la imagen no crece).

Ajuste posterior (mismo día): `kestra/subir_flows.sh` fallaba en macOS con "Define
KESTRA_CLAVE en .env" aunque la clave existía. Antes: `source <(grep ... .env)`, que el bash
3.2 de macOS no lee. Después: un bucle `while read ... export`, compatible con bash 3.2.
