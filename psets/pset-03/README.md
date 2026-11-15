# PSet 3 — Experimentación y selección del modelo

Este PSet parte de la OBT creada en [PSet 2](../pset-02/README.md) y registra
los experimentos en MLflow. El objetivo es predecir el tiempo de retención
cromatográfica (`TIEMPO_RETENCION`) para registros de columnas C18 de RepoRT.

## Alcance y métricas

- **Métrica técnica:** RMSE en minutos, calculado de la misma forma para todos
  los modelos.
- **Regla de alerta:** intervalo de predicción del 95% para la diferencia entre
  los tiempos de retención predichos de dos compuestos. El intervalo se
  calibrará con predicciones fuera de pliegue del conjunto de entrenamiento;
  no se fijará una tolerancia arbitraria en minutos.
- **KPI de negocio para un piloto:** porcentaje de reducción de corridas por
  método validado, comparando el proceso actual con el asistido por el modelo:
  `(corridas actuales - corridas asistidas) / corridas actuales * 100`. La
  comparación debe mantener el mismo criterio de aceptación cromatográfica.
  Como métrica complementaria se registrarán los mL de solvente por método
  validado.
- **Proxy técnico disponible ahora:** recall de pares con posible elución
  cercana, priorizando no omitir un riesgo. RepoRT no incluye etiquetas
  confirmadas de coelución ni resolución/ancho de pico; por ello, este resultado
  no es una tasa real de coelución ni sustituye el KPI del piloto.
- La reducción del 30% de corridas y solvente es una **hipótesis de negocio**.
  No se reportará como ahorro medido: faltan el número histórico de corridas y
  registros de consumo de solvente por método.
- No hay datos locales de laboratorio en este repositorio. La validación del
  modelo se limitará a RepoRT C18; no se afirmará generalización a otros
  equipos, columnas o laboratorios.

El pipeline de PSet 2 conserva la instantánea amplia de RepoRT. En este PSet,
el subconjunto C18 se selecciona para el modelado. Los descriptores moleculares
se derivan de SMILES de Raw y las variables de método se leen de la OBT; la
conexión no imprime ni registra credenciales.

## Componentes

- `docker-compose.yml`: servidor de tracking MLflow con SQLite persistente,
  Model Registry y almacenamiento de artefactos.
- `notebooks/`: EDA, features, líneas base y candidatos, tuning y selección.
- `src/datos.py`: extracción de OBT/SMILES, filtro C18 y huella reproducible.
- `src/pipeline.py`: features de inferencia, preprocesamiento y validación.
- `src/experiments.py`: CV agrupada, tuning anidado y registro reproducible.
- `src/business_metrics.py`: intervalo pairwise y métricas proxy de cercanía temporal.
- `src/monitoring.py`: PSI y proporción de valores faltantes para comparar
  distribuciones de features sin usar etiquetas.
- `src/llm_benchmark.py` y `scripts/run_llm_benchmark.py`: benchmark zero-shot
  con Gemini y comparación con champion/challenger en el holdout.
- `src/splits.py`: holdout único, persistido y sin fuga por compuesto.
- `docs/corridas.csv`: historial completo de las ejecuciones, incluidos intentos
  fallidos que se conservan para trazabilidad.
- `docs/feature_drift_holdout.csv`: demostración offline de deriva entre
  muestras de entrenamiento y holdout; no representa monitoreo productivo.
- `docs/memo_tecnico.md` y `docs/memo_tecnico.pdf`: memo de resultados y límites
  del experimento.

## Reproducir

1. Configura tus credenciales propias de Snowflake en `psets/pset-02/.env` o
   copia `.env.example` a `.env` en este directorio. No subas archivos `.env`.
2. Instala los paquetes de `requirements.txt` en un entorno Python 3.11.
3. Levanta MLflow con `docker compose up -d --build`. En Codespaces, abre
   **Ports**, localiza el puerto `5000` y selecciona **Open in Browser** para
   ver el experimento y los modelos registrados.
4. Ejecuta los notebooks en orden, con **Restart** y luego **Run All**:
   `01_eda.ipynb`, `02_features.ipynb`, `03_baseline_candidatos.ipynb`,
   `04_tuning.ipynb` y `05_seleccion.ipynb`.
5. El tuning evaluará al menos 30 configuraciones para cada uno de los tres
   mejores candidatos. El conjunto de prueba se reserva para comparar al final
   al ganador y al segundo mejor.

El holdout se crea primero sobre todos los registros válidos y agrupa por
InChIKey. La selección de candidatos y el tuning usan solo una muestra de hasta
12.000 compuestos completos de la partición de entrenamiento, estratificada
por quintiles de la mediana de retención (semilla 42). El RF final conserva la
mejor configuración de tuning, pero limita cada árbol a `max_samples=4096` para
que el artefacto pueda serializarse en el Codespace. Esta variante se reevaluó
con GroupKFold en la muestra de entrenamiento y se registró explícitamente en
MLflow; no se confunde su CV con el tuning original. HistGradientBoosting y
Random Forest se reentrenan con la partición completa de entrenamiento, se
evalúan una vez en el holdout completo y quedan como champion/challenger según
la CV comparable. El intento anterior sin ese límite, que terminó `KILLED`, se
conserva en MLflow y se identifica aparte en `seleccion_final.csv`. Los modelos
finales se registran antes de la calibración OOF del intervalo pairwise, hecha
con pliegues agrupados en la muestra de entrenamiento.

La última celda de `05_seleccion.ipynb` calcula PSI y faltantes para una muestra
reproducible de 20.000 filas de entrenamiento y 20.000 de holdout. El CSV
resultante es una comparación offline dentro de RepoRT, no una evaluación
temporal ni una alarma de producción. En operación, el reporte se calcularía
por cada lote nuevo y se mediría RMSE/MAE cuando estén disponibles las
retenciones reales.

Las ejecuciones registran tabla(s) de origen, hora de extracción, SHA-256 del
snapshot, semilla, métricas y duración. Los artefactos y modelos quedan en el
volumen Docker de MLflow. Antes de interpretar los resultados se debe confirmar
que Snowflake contiene la OBT de PSet 2 y que hay suficientes registros C18 con
SMILES válidos.

El benchmark no convierte la reducción del 30% en un resultado medido. Tampoco
reporta el proxy de pares temporalmente cercanos como coelusión confirmada. La
prueba con Gemini 3.5 Flash-Lite está autorizada para hasta 50 compuestos
distintos del holdout. El prompt solo incluye SMILES y condiciones
cromatográficas, nunca el tiempo de retención real ni identificadores. Para
ejecutarla, configura `GEMINI_API_KEY` localmente o en el secreto del Codespace
y corre `python scripts/run_llm_benchmark.py`; la clave no debe ir al repositorio.
En este entorno la clave todavía no está configurada, así que no se han enviado
observaciones ni se reportan métricas LLM. El benchmark zero-shot también puede
tener solapamiento con datos de entrenamiento del proveedor y no equivale a una
validación independiente.
