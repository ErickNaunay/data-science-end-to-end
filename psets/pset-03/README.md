# PSet 3 — Experimentación desde la OBT

La guía vigente es `CD_PSet_3.pdf`. Esta carpeta desarrolla incrementalmente el
PSet 2; el README original del curso queda en `README_curso.md`. La integración
final en `psets/proyecto/` se hará al empaquetar el proyecto, sin duplicar datasets.

## Preparación

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Completar credenciales localmente: nunca agregarlas a git.
python -m src.datos
docker compose up -d --build
```

MLflow queda en http://localhost:5001, con SQLite como backend y artefactos en
`mlflow/artifacts`; ambos persisten en `mlflow/`, excluido de Git. El snapshot
`data/obt.parquet` tiene un manifiesto con tabla, fecha y SHA-256. No se publica.

## Orden de trabajo

1. `notebooks/01_eda.ipynb`: distribución, faltantes, IQR, Z-score, Spearman y tres hallazgos.
2. `02_features.ipynb`: volatilidad relativa y momentum normalizado por riesgo;
   comprobar disponibilidad y posteriormente aporte por ablación en CV.
3. `03_baseline_candidatos.ipynb`: código preparado en `src/experimentos.py` para
   dos bases y cuatro familias. Falta integrar la quinta familia fundacional y
   probar el LLM por prompting o justificar su inaplicabilidad.
4. `04_tuning.ipynb`: preparar los tres mejores usando solo CV; al menos 30
   configuraciones por modelo y corridas hijas. Aún no ejecutado.
5. `05_seleccion.ipynb`: guía pendiente de implementación final; comparar dos
   finalistas una sola vez en hold-out, calcular métrica de negocio, registrar
   champion/challenger y recargar el ganador en una sesión limpia.

El target es el retorno log del mes siguiente. El corte usa el mes del objetivo:
objetivos hasta diciembre de 2023 en entrenamiento; posteriores en hold-out.
La CV separa meses completos y purga un mes. Imputación y escalado se ajustan
adentro de cada Pipeline/ColumnTransformer. Se excluyen columnas del futuro y
atributos actuales como `sigue_en_sp500` de los predictores.

## Estado y límites

La estructura está preparada; no es una entrega completa de PSet 3. No se ha
elegido ganador, consumido hold-out ni inventado corridas.csv o un memo final.
Faltan quinta familia, ablación, experimento LLM, 90 configuraciones, métrica de
negocio alineada con PSet 1, selección/registro y memo de hasta 6 páginas.
Antes de entrenar, revisar ajustes retrospectivos de precios, bolsa actual,
interpolación y cobertura del universo documentados en el memo del PSet 2.

El trabajo previo de análisis permanece en la rama `draft`, en
`psets/pset-02/analisis/`. No se duplica en esta entrega: parte de Yahoo/DuckDB
y no satisface el protocolo experimental de la OBT que exige el PDF.
Los notebooks finales se entregan con Restart y Run All y salidas guardadas.

### Comprobaciones realizadas

Los notebooks 01 y 02 se ejecutaron completos con el snapshot de 87.178 filas,
con salidas y gráficos guardados. El entrenamiento elegible contiene 46.926
filas y 158 meses. Tres pruebas verifican corte por objetivo, separación de
meses e imputación ajustada solo con entrenamiento. Los notebooks 03-05
son guías de ejecución; no contienen resultados de experimentación.

MLflow se construyó en Docker. Se configura con un solo worker y límite de 1 GB para reducir
consumo. No ejecutar a la vez que Spark en el entorno de 8 GB: durante la
verificación la coexistencia de ambos provocó un OOM de Kestra.

## Verificación funcional aislada

Primero ejecuta `docker compose down` desde `../pset-02/`, sin `-v`; Snowflake
conserva las tablas. No se necesita Kestra ni Spark para ejecutar PSet 3:
la única dependencia compartida es la OBT ya materializada en Snowflake.

```bash
docker compose down
docker compose --profile verificacion build
docker compose up -d mlflow
GIT_COMMIT="$(git rev-parse HEAD)" GIT_DIRTY=true \
  docker compose --profile verificacion run --rm verificar
docker compose down
```

`src/verificar_entorno.py` consulta Snowflake, crea un snapshot nuevo, ejecuta
EDA/features y registra media, retorno cero y Ridge con CV temporal en un
experimento separado, `portafolio-verificacion-entorno`. Registra y recarga
Ridge con alias `verificacion` en `portafolio-verificacion-modelo`, y comprueba
que reproduce su RMSE de entrenamiento. No asigna champion, no elige ganador,
no utiliza el hold-out y no sustituye las 98 corridas mínimas del PDF.
La evidencia de esa prueba queda en `docs/verificacion/`.

Los notebooks 03-05 y el programa de tuning siguen siendo la preparación para
el trabajo experimental completo. Sus pendientes están en
[docs/pendientes_entrega.md](docs/pendientes_entrega.md).

## Cadencia de negocio y futura inferencia

Según PSet 1 revisado, la inferencia y propuesta de compra son mensuales; los datos se actualizan diariamente en PSet 2. El reporte de desempeño también es mensual. No se establece una frecuencia de reentrenamiento ni se implementa aquí un scheduler productivo de scoring. `preparar()` filtra targets nulos para entrenamiento: la futura inferencia necesitará conservar esas filas del mes cerrado sin usar columnas futuras. Ver [temporalidad y disponibilidad del cierre](../pset-02/docs/temporalidad_batch.md).
