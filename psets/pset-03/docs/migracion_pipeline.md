# Copia del pipeline del PSet 2 en `pipeline/`

Fecha: 2026-11-16. Rama `work` (`6f4c141`). Motivo: el PSet 3 necesita volver a correr
el pipeline completo con posibles cambios, y `psets/pset-02/` ya se entregó (tag
`pset-02`), así que no se modifica.

## Qué se copió

Desde `psets/pset-02/` se copiaron 74 archivos versionados a `psets/pset-03/pipeline/`:
`dbt/`, `kestra/`, `spark/`, `scripts/`, `pruebas_locales/`, `docker-compose.yml`,
`pyproject.toml`, `uv.lock`, `requirements.txt`, `.env.example` y `.gitignore`.

No se copiaron, porque son entregables del PSet 2: `docs/` (evidencias, memo, diagramas),
`CD_PSet_2.pdf`, `README_curso.md`, `rubrica.md`, `disclaimer.txt`,
`scripts/generar_memo.py` y `scripts/empaquetar_entrega.py`. Se agregaron
`docs/corrida/.gitkeep` y `docs/calidad/.gitkeep` porque los scripts escriben ahí.

## Antes y después

| Qué | Antes (`psets/pset-02`) | Después (`psets/pset-03/pipeline`) |
|---|---|---|
| Base de Snowflake (valores por defecto, `.env.example`, `snowflake_setup.sql`) | `PORTAFOLIO` | `PORTAFOLIO_P3` |
| Bodega, rol, usuario y llave | `PSET2_WH`, `PSET2_ROL`, `PSET2_SERVICIO` | sin cambio |
| Proyecto de Compose | `name: pset2` | `name: pset3-pipeline` (volúmenes de Postgres y Kestra propios) |
| Imágenes (compose y `containerImage` de los flows) | `pset2-ingesta`, `pset2-dbt`, `pset2-spark` | `pset3-ingesta`, `pset3-dbt`, `pset3-spark` |
| Red de Docker (compose y `networkMode` de `transformar`) | `pset2_red` | `pset3_red` |
| `QUERY_TAG`, `application` de Snowflake, `appName` de Spark, User-Agent | `pset2_*` / `pset2-*` | `pset3_*` / `pset3-*` |
| Nombre del proyecto uv | `pset-02-pipeline` | `pset-03-pipeline`; `uv.lock` y los tres `requirements.txt` con las mismas versiones |
| Líneas `Uso, desde ...` | `psets/pset-02/` | `psets/pset-03/pipeline/` |
| README | README completo del PSet 2 | README corto con lo que cambia; remite a `../../pset-02/README.md` |
| Etiqueta `pset` de los tres flows (y de sus ejecuciones) | `"2"` | `"3"` |
| Namespace de Kestra | `usfq.portafolio` | sin cambio |

## Corrección: fecha del trigger en `ingesta_diaria` (2026-11-17)

La primera ejecución programada en la copia (`1LkyGFQko1nP8uqG4rXaLn`, 16-nov 18:30 de Nueva
York) falló: `extraer_cargar.py diario: error: argument --fecha: invalid fromisoformat value:
'2026-11-16T18:30:00.000000-05:00'`. En Pebble el filtro `| date(...)` solo se aplicaba a
`execution.startDate`, así que `trigger.date` llegaba con hora y zona.

| Antes | Después |
|---|---|
| `{{ inputs.fecha ?? (trigger.date ?? execution.startDate \| date('yyyy-MM-dd')) }}` | `{{ inputs.fecha ?? ((trigger.date ?? execution.startDate) \| date('yyyy-MM-dd', timeZone='America/New_York')) }}` |

El mismo error está en `psets/pset-02/kestra/flows/ingesta_diaria.yml`, que no se corrige
porque ya se entregó; las ejecuciones manuales con el input `fecha` y el backfill no lo tienen.

## Avisos por correo (2026-11-17)

Comprobación previa: la ejecución manual `7SXMpaCiw1t6nUUFgcu7wc` de `ingesta_diaria`,
lanzada sin el input `fecha` (misma expresión que usa el trigger), terminó en `SUCCESS`
con la corrección de la fecha y la etiqueta `pset: 3`.

| Archivo | Antes | Después |
|---|---|---|
| `kestra/flows/avisos.yml` | no existía | flow `usfq.avisos.avisos`: trigger de tipo Flow sobre `usfq.portafolio` (estados SUCCESS, WARNING, FAILED, KILLED; excluye `transformar`, que corre como subflow) y tarea `io.kestra.plugin.email.MailExecution` por Gmail; asunto con `Success` o `Fail` al inicio |
| `kestra/subir_flows.sh` | subía 3 flows; si Kestra rechazaba uno, salía sin mensaje (`curl -sf`) | sube también `avisos.yml` y muestra el código HTTP y el mensaje de Kestra si rechaza un flow |
| `scripts/preparar_env.sh` | codificaba `SNOWFLAKE_*` y `FECHA_*` | también `AVISO_*` |
| `.env.example` | sin avisos | `AVISO_CORREO` y `AVISO_CLAVE_APP` vacíos |

El correo y la contraseña de aplicación solo van en `.env` y `.env_encoded`, que no se suben.
Está en un namespace propio para que sus ejecuciones no lo vuelvan a disparar.

## Pruebas de Spark dentro de la imagen (2026-11-17)

Las 6 pruebas de `spark/tests/test_construir_obt.py` se saltaban en el entorno uv porque
`pyspark` está en el grupo opcional `pruebas-locales` (~317 MB) y piden Java 17.

| Archivo | Antes | Después |
|---|---|---|
| `spark/Dockerfile` | una etapa; jars con `ADD <url de Maven>` | etapas `base` (jars), `pruebas` (pytest 8.3.5, `jobs/`, `tests/`) y `runtime` (`jobs/`); jars con `RUN` + cache de BuildKit y pytest con cache de pip |
| `spark/descargar_jars.py` | no existía | baja los dos jars al cache (`/var/cache/spark-jars`) y los copia a `/opt/spark/jars`; reusa lo ya bajado |
| `spark/.dockerignore` | no existía | excluye `__pycache__/`, `.pytest_cache/`, `*.pyc` |
| `docker-compose.yml` | `spark-master` con `build: ./spark` | `target: runtime`; servicio nuevo `spark-pruebas` (perfil `pruebas`, `target: pruebas`, 2 GB) |
| `spark/tests/test_construir_obt.py` | solo uso con uv | docstring con el comando de Docker |

Primera corrida: falló con `TypeError: 'type' object is not subscriptable` en
`descargar_jars.py`, porque la imagen `apache/spark:3.5.3-python3` trae Python 3.8
(`list[str]` requiere 3.9). Se agregó `from __future__ import annotations` y se fijó
pytest 8.3.5 (pytest 8.4+ ya no soporta 3.8).

Segunda corrida: las 6 pruebas dieron `JAVA_GATEWAY_EXITED` por
`UnknownHostException` del nombre del contenedor, porque el servicio tenía
`network_mode: none`. Se quitó esa opción y la etapa `pruebas` fija
`SPARK_LOCAL_IP=127.0.0.1` y `SPARK_LOCAL_HOSTNAME=localhost`.

El contenedor de pruebas verifica que `pyspark` y `java` existen antes de pytest y muestra
los motivos de cualquier skip (`-rs`), para que un resultado verde signifique que se probó.

## Cambios fuera de `pipeline/`

| Archivo | Antes | Después |
|---|---|---|
| `src/datos.py` | `TABLA='PORTAFOLIO.OBT.OBT_ACCION_MES'` | `tabla()` usa `SNOWFLAKE_DATABASE`, por defecto `PORTAFOLIO_P3` |
| `.env.example` | sin `SNOWFLAKE_DATABASE` | `SNOWFLAKE_DATABASE=PORTAFOLIO_P3` |
| `analisis/equivalencias_tickers.py` | escribía la semilla en `../pset-02/dbt/seeds` y `../pset-02/kestra/scripts` | la escribe en `pipeline/dbt/seeds` y `pipeline/kestra/scripts` |
| `.dockerignore` | sin `pipeline/` ni `analisis/` | los excluye del contexto de la imagen de MLflow |
| `pyproject.toml` | pytest sin `testpaths` | `testpaths = ["tests"]` |
| `docs/separacion_alcance.json` | fuente `OBT.OBT_ACCION_MES`; escrituras en Snowflake: "Ninguna" | fuente `PORTAFOLIO_P3.OBT.OBT_ACCION_MES`; notebooks y `src/` no escriben, `pipeline/` escribe solo en `PORTAFOLIO_P3` (se conserva el valor anterior en `antes`) |
| `README.md`, Verificación funcional aislada | "la única dependencia compartida es la OBT ya materializada en Snowflake" | los notebooks solo leen la OBT de `PORTAFOLIO_P3`; `pipeline/` solo hace falta para reconstruirla |
| `README.md` | "docker compose down desde `../pset-02/`" | desde `pipeline/`; nota sobre la copia y `PORTAFOLIO_P3` |

## Consecuencia para el snapshot

`data/obt.parquet` y los notebooks actuales provienen de `PORTAFOLIO.OBT.OBT_ACCION_MES`
(sha256 `f66dd033…`). Al correr el pipeline copiado y luego `uv run python -m src.datos`,
el snapshot pasará a `PORTAFOLIO_P3.OBT.OBT_ACCION_MES` y el manifiesto lo registrará.

## Verificación

- `uv lock` en `pipeline/`: mismas versiones que `pset-02` (salvo el nombre del proyecto).
- `uv run pytest` en `pipeline/`: 3 pasan y 1 se salta (Spark sin pyspark/Java).
- `uv run pytest` en `pset-03`: 3 pasan.
- `docker compose config` con `.env.example` y claves de prueba: válido.
- `git grep` de secretos: solo nombres de variables en `scripts/preparar_env.sh`.
