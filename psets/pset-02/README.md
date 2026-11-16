# PSet 2: Pipeline de datos del portafolio de inversiones

Allan Paul Gómez Ehmig · 00351916 · MSDS 6003 Fundamentos de Ciencia de Datos (USFQ)

Pipeline ELT reproducible para el proyecto del PSet 1 (Idea 3: portafolio de acciones del S&P 500 que cotizan en la NYSE, con rebalanceo mensual):

```
Fuente → Kestra → Raw → dbt → Bronze → dbt → Silver → dbt → Gold → Spark → OBT   (Snowflake)
```

- **Fuentes** (públicas, sin credenciales): precios diarios de Yahoo Finance (`yfinance`) para las acciones que alguna vez estuvieron en el S&P 500 y para `^GSPC`, `^NYA` e `^IRX`; composición histórica del S&P 500 ([chinobing/historical_sp500_constituents](https://github.com/chinobing/historical_sp500_constituents), actualizada a diario); bolsa de cada símbolo ([rreichel3/US-Stock-Symbols](https://github.com/rreichel3/US-Stock-Symbols), listas de Nasdaq actualizadas cada noche).
- **Destino**: Snowflake, base `PORTAFOLIO`, con un esquema por capa: `RAW`, `BRONZE`, `SILVER`, `GOLD`, `OBT` y `CALIDAD`.
- **Documento técnico**: [memo técnico de seis páginas más tres anexos](docs/PSet2_memo_Gomez_Ehmig.pdf). Diagramas: [arquitectura](docs/arquitectura.png) y [modelo dimensional](docs/modelo_dimensional.png), además de C4 [contexto](docs/structurizr/export/structurizr-contexto.png) y [contenedores](docs/structurizr/export/structurizr-contenedores.png).
- Diferencias con la guía del repositorio del curso (`README_curso.md`): ver [`disclaimer.txt`](disclaimer.txt).

## Estructura

```
pset-02/
├── docker-compose.yml        Kestra + Postgres, Spark (maestro y trabajador), imágenes de tareas
├── .env.example              variables necesarias (copiar como .env; .env no se sube)
├── README.md
├── disclaimer.txt
├── scripts/preparar_env.sh   arma los secretos de Kestra a partir de .env
├── kestra/
│   ├── Dockerfile, requirements.txt   imagen pset2-ingesta
│   ├── scripts/extraer_cargar.py      extracción y carga a RAW (modos diario e histórico)
│   ├── flows/                         ingesta_diaria, backfill_historico, transformar
│   ├── sql/snowflake_setup.sql        bodega, base, esquemas, rol, usuario y tablas RAW
│   └── subir_flows.sh                 crea o actualiza los flows por la API de Kestra
├── dbt/                      proyecto dbt (Bronze, Silver, Gold, CALIDAD) + seeds + tests; imagen pset2-dbt
├── spark/                    imagen pset2-spark (con el conector de Snowflake) y jobs/construir_obt.py
├── docs/                     memo, diagramas y fuentes de los diagramas (.dot)
└── pruebas_locales/          prueba del código con DuckDB y Spark local, sin Snowflake
```

## Requisitos

- Docker con Docker Compose v2.24 o superior.
- Una cuenta de Snowflake (la prueba gratuita de 30 días sirve: https://signup.snowflake.com/).
- `openssl` para generar el par de llaves.

## Cómo correr el pipeline

Todos los comandos se corren desde `psets/pset-02/` en este checkout, o desde `pset_2/` al extraer el ZIP de entrega. El ZIP usa el nombre de carpeta indicado por la guía; ambas rutas contienen el mismo pipeline.

### 1. Variables de entorno

```bash
cp .env.example .env
```

Completa `SNOWFLAKE_ACCOUNT` con el identificador de tu cuenta (Snowsight → menú de la cuenta → *Account* → *Account identifier*, formato `ORGANIZACION-CUENTA`). Los nombres de objetos Snowflake ya coinciden con lo que crea el paso 3. Completa también `KESTRA_CLAVE` y `KESTRA_DB_PASSWORD` con claves propias; no tienen valor por defecto. Usa valores alfanuméricos sin espacios en este archivo y no lo publiques.

### 2. Par de llaves para el usuario de servicio

El usuario del pipeline es de tipo `SERVICE`: no usa contraseña, se autentica con un par de llaves.

```bash
mkdir -p secrets
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out secrets/snowflake_llave.p8 -nocrypt
openssl rsa -in secrets/snowflake_llave.p8 -pubout -out secrets/snowflake_llave.pub
grep -v -- '-----' secrets/snowflake_llave.pub | tr -d '\n'; echo   # llave pública en una línea
```

`secrets/` está en `.gitignore`: la llave privada nunca se sube.

### 3. Objetos en Snowflake

En Snowsight, abre una hoja de trabajo SQL, pega [`kestra/sql/snowflake_setup.sql`](kestra/sql/snowflake_setup.sql), reemplaza `<LLAVE_PUBLICA>` con la línea del paso anterior y ejecútalo completo con el rol `ACCOUNTADMIN`. Crea la bodega `PSET2_WH` (XSMALL, se suspende a los 60 s), la base `PORTAFOLIO` con sus seis esquemas, el rol `PSET2_ROL`, el usuario `PSET2_SERVICIO` y las tablas de `RAW`.

### 4. Secretos para Kestra

```bash
bash scripts/preparar_env.sh
```

Copia la llave privada a `SNOWFLAKE_PRIVATE_KEY` en `.env` (para dbt, Spark y la ingesta) y crea `.env_encoded`, donde cada variable va como `SECRET_<NOMBRE>` en base64; así lee Kestra los secretos con `{{ secret('...') }}`. Ninguno de los dos archivos se sube.

### 5. Infraestructura

```bash
docker compose --profile herramientas build    # imágenes pset2-ingesta, pset2-dbt y pset2-spark
docker compose up -d                           # postgres, kestra, spark-master y spark-worker
```

- Kestra: http://localhost:8090 (usuario y clave de `.env`: `KESTRA_USUARIO` y `KESTRA_CLAVE`).
- Spark: http://localhost:8081

Si la construcción de `pset2-spark` falla al descargar el conector de Maven, cambia las versiones con `--build-arg SPARK_SNOWFLAKE_VERSION=... --build-arg SNOWFLAKE_JDBC_VERSION=...`.

### 6. Flows de Kestra

```bash
bash kestra/subir_flows.sh
```

Crea (o actualiza) tres flows en el namespace `usfq.portafolio`:

| Flow | Qué hace | Cuándo corre |
|---|---|---|
| `backfill_historico` | Carga `RAW` año por año (inputs `anio_desde` y `anio_hasta`, por defecto 2010 a 2026) y al final llama a `transformar` | A mano, una vez |
| `ingesta_diaria` | Carga los últimos ~7 días hábiles (los lunes, también composición y listados) y llama a `transformar` | Lunes a viernes, 18:30 hora de Nueva York |
| `transformar` | `dbt build` (modelos y tests) y después el job de Spark que escribe la OBT | Lo llaman los otros dos |

### 7. Primera carga (backfill)

En la UI de Kestra: *Flows* → `usfq.portafolio.backfill_historico` → *Execute*. O por API:

```bash
curl --user TU_USUARIO_KESTRA -X POST \
  http://localhost:8090/api/v1/main/executions/usfq.portafolio/backfill_historico \
  -F anio_desde=2010 -F anio_hasta=2026
```

En el ejemplo de API reemplaza `TU_USUARIO_KESTRA` por el usuario configurado; curl solicita su contraseña sin incluirla en el comando.

Al terminar, `RAW` tiene el histórico y `transformar` ya construyó Bronze, Silver, Gold, `CALIDAD.DQ_METRICAS` y `OBT.OBT_ACCION_MES`. Desde ahí, `ingesta_diaria` corre sola. Para reprocesar un día puntual, ejecuta `ingesta_diaria` con el input `fecha`; para un rango de días programados que se perdieron, usa *Triggers* → `cierre_nyse` → *Backfill executions*.

### 8. Correr dbt o Spark a mano (opcional)

```bash
docker compose --profile herramientas run --rm dbt dbt build --target snowflake
docker compose --profile herramientas run --rm dbt dbt source freshness --target snowflake
docker compose --profile herramientas run --rm spark-job
```

### 9. Verificar en Snowflake

```sql
select * from PORTAFOLIO.CALIDAD.DQ_METRICAS order by dimension, metrica;
select * from PORTAFOLIO.OBT.VALIDACION_OBT;
select conjunto, count(*), count_if(elegible) from PORTAFOLIO.OBT.OBT_ACCION_MES group by 1;
```

## Probar el código sin Snowflake

`pruebas_locales/` carga en DuckDB una muestra real pequeña: la composición completa del S&P 500, ORCL, UBER y VST, y VTI y QQQ como sustitutos de los índices. Con eso corre el mismo proyecto dbt (target `local`) y el job de Spark en modo local. Sirve solo para verificar el código; no son los datos del proyecto.

```bash
pip install dbt-duckdb duckdb pandas pyarrow "pyspark==3.5.3"   # requiere Java 17
python pruebas_locales/cargar_muestra.py
(cd dbt && DBT_PROFILES_DIR=. dbt build --target local --vars '{exigir_tasa_libre_riesgo: false, fecha_inicio: "2016-11-14"}')
python pruebas_locales/probar_spark_local.py
```

Resultado histórico de la muestra del borrador, antes de añadir la dimensión Gold de membresía: `PASS=89 WARN=1 ERROR=0` (la advertencia es `assert_cobertura_sp500_por_dia`, porque la muestra solo tiene 3 acciones). Como la muestra empieza en 2016, hay que pasar `fecha_inicio: "2016-11-14"` en `--vars`. Spark imprime 11 controles `[OK]` y escribe la OBT con 330 filas.

### Alcance de la migración

El análisis y entrenamiento de modelos se organizan en `../pset-03/`;
los antecedentes permanecen en la rama `draft`, en `psets/pset-02/analisis/`.
Los seeds necesarios ya están incluidos. El calendario se regenera con
`scripts/generar_calendario_nyse.py`; el generador de equivalencias permanece
como referencia en `draft/psets/pset-02/analisis/equivalencias_tickers.py`.
No es necesario ejecutarlo para usar los seeds transferidos.

`scripts/` y `pruebas_locales/` complementan la estructura del PDF.
Para instalar las dependencias locales, usa un entorno virtual y
`pip install -r requirements.txt`. Las imágenes tienen dependencias propias.
Consulta [el registro de migración](docs/migracion.md).
La muestra local de DuckDB indicada arriba es evidencia histórica del borrador. Las ejecuciones reales posteriores de dbt y Spark contra Snowflake desde esta rama están documentadas en `docs/corrida/` y `docs/cumplimiento.md`.

## Batch o streaming

El pipeline actualiza datos por lotes L–V a las 18:30 de Nueva York (el cron incluye feriados). La inferencia, la propuesta de compra y el reporte de desempeño son mensuales según PSet 1 revisado; no se establece una frecuencia de reentrenamiento. El negocio requiere preparación en horas antes de la revisión mensual, no trading de alta frecuencia. El cierre mensual actual se reconoce cuando llegan datos del mes siguiente: no garantiza una propuesta antes de la primera apertura. Ver [temporalidad, evidencia y brechas](docs/temporalidad_batch.md) y la sección 6 del memo.

## Seguridad

No se sube ninguna contraseña, token, llave ni dato: `.env`, `.env_encoded`, `secrets/`, `*.p8`, los artefactos de dbt y las bases de prueba están en `.gitignore`. Las credenciales llegan a los contenedores como variables de entorno (desde `.env`) o como secretos de Kestra (desde `.env_encoded`).

## Verificación y entregables (15 de noviembre de 2026)

La revisión contra el PDF y las incidencias están en [docs/cumplimiento.md](docs/cumplimiento.md).
Las métricas reales se exportaron desde Snowflake a `docs/corrida/`. dbt build:
97 correctos, 1 advertencia de cobertura, 0 errores en el build Gold actual
(14 modelos, 2 seeds, 82 tests); source freshness previo: 4/4.
La OBT tiene 87.178 filas, 43 columnas y 13 controles correctos. El memo conserva
las limitaciones de cobertura, precisión y disponibilidad temporal.

Evita ejecutar simultáneamente los dos entornos Kestra, Spark y MLflow en una
máquina con 8 GB asignados a Docker. Se observó un OOM de Kestra con esa carga.
Completa PSet 2 antes de levantar MLflow de PSet 3, o asigna más memoria según
el consumo observado. Un contenedor que termina no garantiza que el orquestador
haya recibido su estado final: consultar ambos al recuperar una caída.

Pruebas unitarias de la ingesta:

```bash
python -m unittest discover -s kestra/tests -v
```

Regenerar evidencia y memo (requiere credenciales configuradas y `reportlab`):

```bash
python scripts/exportar_metricas.py
python scripts/generar_memo.py
```

El exportador acepta variables del entorno o `.env` local. La primera prueba reutilizó las credenciales de draft; la ejecución aislada usó
configuración local ignorada por Git en este checkout. Los JSON dbt de evidencia contienen estados, no credenciales.

### Ejecución aislada

Antes de verificar, baja el entorno PSet 3 (`docker compose down` desde su
carpeta) y otros laboratorios activos. Desde PSet 2:

```bash
docker compose down          # conserva volúmenes; no usar -v
docker compose --profile herramientas build
docker compose up -d
bash kestra/subir_flows.sh
# Ejecutar ingesta_diaria en Kestra y esperar SUCCESS, incluido transformar.
python scripts/verificar_snowflake.py
python scripts/exportar_metricas.py
docker compose down          # luego puede verificarse PSet 3
```

Spark usa 2 GB de heap para el ejecutor, 1 GB para el driver y un core total.
El trabajador debe ofrecer al menos 2 GB. El perfil manual y Kestra usan
los mismos límites. El resultado final se comprueba con SELECT en Snowflake,
no solo por el estado de un contenedor.

Para armar el paquete de entrega (excluye secretos, bases y artefactos locales):

```bash
python scripts/empaquetar_entrega.py
```

La configuración local de esta revisión se preparó en `.env` y `.env_encoded`
con permisos 0600; ambos están ignorados por Git y por el empaquetador. No se
incluye la configuración privada en el ZIP ni en los documentos.

## Trazabilidad de la cadena y reproducibilidad

| Tramo exigido | Implementación |
|---|---|
| Fuente → Kestra → RAW | `ingesta_diaria` / `backfill_historico` ejecutan `kestra/scripts/extraer_cargar.py`; carga append-only con bitácora |
| RAW → dbt → Bronze | `dbt/models/bronze/`, fuentes RAW declaradas con `source()`; normalización y deduplicación |
| Bronze → dbt → Silver | `dbt/models/silver/`, dependencias `ref()`; calendario, precios, membresía y mercado |
| Silver → dbt → Gold | `dbt/models/gold/`; tres dimensiones y dos hechos |
| Gold → Spark → OBT | `spark/jobs/construir_obt.py`; cuatro tablas Gold, 13 controles y escritura en Snowflake |

Las tres apariciones de dbt son etapas lógicas del mismo `dbt build`: el DAG
ordena modelos y tests. No se necesitan tres servicios dbt. `transformar`
ejecuta primero dbt y después Spark, propagando fallos. CALIDAD es transversal
a RAW/Bronze/Silver/Gold; Postgres almacena el estado de Kestra, no datos analíticos.

La ejecución aislada previa terminó SUCCESS con 87.178 filas y 11 controles OK.
La revisión de arquitectura añade `docker compose config --quiet`, `dbt parse`
y validación Structurizr: ver `docs/corrida/verificacion_arquitectura.json`.
Se corrigió el envío de `FECHA_CORTE_ENTRENAMIENTO` a Spark en Kestra; el valor
por defecto sigue siendo 2023-12-31. Para aplicar un cambio de configuración,
regenerar secretos, recrear Kestra y volver a publicar los flows.

Reproducible significa repetir el procedimiento con una cuenta, permisos y
credenciales propios siguiendo los pasos 1-9. No se realizó un nuevo bootstrap
completo en una cuenta vacía durante esta revisión. Yahoo y las ramas de GitHub
son mutables y algunas dependencias Python usan rangos: no se garantiza igualdad
bit a bit ni los mismos conteos en otra fecha. Para reconstruir exactamente un
snapshot harían falta los insumos originales y dependencias bloqueadas.

Los diagramas C4 se generan desde una única fuente (`docs/structurizr/workspace.dsl`);
los anexos A-C del memo contienen flujo, contexto y contenedores. Para regenerarlos:

```bash
bash docs/structurizr/exportar_diagramas.sh
dot -Tpng -Gdpi=170 docs/arquitectura.dot -o docs/arquitectura.png
dot -Tsvg docs/arquitectura.dot -o docs/arquitectura.svg
python scripts/generar_memo.py
python scripts/empaquetar_entrega.py
```

## Diagnóstico previo a limpieza y decisiones por columna

[Informe completo de calidad](docs/calidad/README.md): 22 tablas, 236 columnas,
con inventario de origen/creación, faltantes, inválidos, inconsistencias, anomalías
y decisiones por columna. Distingue RAW previo a limpieza de perfiles posteriores.

```bash
python scripts/diagnosticar_calidad.py
python scripts/generar_informe_calidad.py
```

El primer script hace solo SELECT y conserva SQL/query IDs. No transforma datos.
La limpieza es dbt: staging/Bronze normaliza, tipa y deduplica; Silver aplica
calendario, tratamiento de huecos y marcas. Se corrigieron ES_ETF/ES_PRUEBA:
los valores desconocidos permanecen NULL en Bronze. Silver admite desconocidos
sin afirmar que son falsos. La reconstrucción dbt terminó PASS=89 WARN=1 ERROR=0.

Porcentajes de RAW no deben sustituirse por métricas post-limpieza. La evidencia
de esta revisión está en docs/calidad/; docs/corrida/run_results.json conserva
la ejecución anterior y docs/calidad/dbt_validacion.json resume la nueva.

## Revisión de capas y modelo dimensional

[Auditoría detallada](docs/revision_capas_modelo.md): no se encontraron ciclos ni
dependencias inversas entre capas. Gold contiene **dos hechos diarios** y tres
dimensiones; DIM_FECHA es conformada. Las claves/granos y los joins se verificaron
en Snowflake sin duplicados, huérfanos ni pérdida de filas.

La excepción anterior quedó corregida: periodo_sp500_key apunta ahora a
GOLD.DIM_MEMBRESIA_SP500, publicada con dbt desde Silver. Todos los joins de
consumo del hecho se resuelven dentro de Gold. Las claves son lógicas validadas
con tests, no PK/FK DDL. Nuevas pruebas verifican vigencia, solapes y correspondencia
de acción/fecha. Evidencia: docs/corrida/run_results_gold.json.

```bash
python scripts/auditar_capas_modelo.py
```

### Revisión del requisito 5: OBT

El grano, los 13 controles de joins, el uso de cada tabla Gold y la decisión sobre dimensiones adicionales están en [docs/revision_obt.md](docs/revision_obt.md). `scripts/auditar_obt.py` verifica en Snowflake igualdad de claves contra Gold y mide almacenamiento; la evidencia queda en `docs/corrida/auditoria_obt.json`.

## Revisión de entrega contra la guía

[docs/revision_entrega.md](docs/revision_entrega.md) relaciona las siete secciones del memo, los entregables y los pesos de la rúbrica con su evidencia. El memo tiene seis páginas técnicas y tres anexos. Para generar el paquete: `python scripts/empaquetar_entrega.py`. El ZIP incluye `pset_2/` y `MANIFEST_SHA256.json`; no reemplaza publicar los archivos en el repositorio Git solicitado por el curso.

La guía controlante es `CD_PSet_2.pdf`. `README_curso.md` y `rubrica.md` son referencias originales de otra variante de la tarea; sus cuatro criterios no sustituyen los siete criterios ponderados del PDF. Ver `disclaimer.txt` y la matriz de revisión.
