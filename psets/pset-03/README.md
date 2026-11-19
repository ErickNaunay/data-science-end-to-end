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
- **Proxy técnico disponible ahora:** se evalúa la regla del intervalo del 95%
  contra un evento químico independiente del modelo: dos compuestos cuya
  retención real difiere ≤ 0,5 min en la misma condición. Se reportan recall
  (error más costoso: no alertar), precisión y tasa de alertas. En el holdout,
  el champion alerta el 99,1% de esos pares, pero marca el 91% de todos los
  pares (precisión 20% frente a una tasa base de 18,7%). Con RMSE 2,3 min la
  alerta todavía no discrimina. RepoRT no incluye resolución ni ancho de pico:
  es un proxy, no una coelución confirmada (`docs/reglas_alerta.csv`).
- **Meta del PSet 1:** RMSE ≤ 0,5 min y R² ≥ 0,90. El champion obtiene RMSE
  2,329 y R² 0,828 en el holdout; la meta no se alcanza.
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
- `notebooks/`: EDA, features (ablación y prueba de no fuga), líneas base y
  candidatos, tuning, selección y reproducción limpia del champion.
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
- `docs/llm_benchmark_metrics_20261118T013622Z.json` y
  `docs/llm_benchmark_predictions_20261118T013622Z.csv`: benchmark zero-shot
  de Gemini 3.5 Flash-Lite en 50 compuestos, comparado con los modelos
  champion/challenger sobre la misma muestra.
- `docs/memo_tecnico.md`, `docs/PSet3_memo_Buenaño_Peñafiel.pdf` (6 páginas,
  límite de la rúbrica) y `docs/PSet3_anexo_Buenaño_Peñafiel.pdf` (evidencia de
  MLflow). Ambos PDF se generan con `python scripts/build_memo_pdf.py`, que
  falla si el cuerpo supera 6 páginas.

## Reproducir

1. Configura tus credenciales propias de Snowflake en `psets/pset-02/.env` o
   copia `.env.example` a `.env` en este directorio. No subas archivos `.env`.
2. Instala los paquetes de `requirements.txt` en un entorno Python 3.11.
3. Levanta MLflow con `docker compose up -d --build`. En Codespaces, abre
   **Ports**, localiza el puerto `5000` y selecciona **Open in Browser** para
   ver el experimento y los modelos registrados.
4. Ejecuta los notebooks en orden, con **Restart** y luego **Run All**:
   `01_eda.ipynb`, `02_features.ipynb`, `03_baseline_candidatos.ipynb`,
   `04_tuning.ipynb`, `05_seleccion.ipynb` y `06_reproducir_champion.ipynb`.
   Los notebooks 03, 04 y 05 reutilizan las corridas `FINISHED` de MLflow con
   el mismo nombre, fase, familia y hash de muestra (columna
   `reused_from_mlflow`), de modo que **Restart + Run All** no duplica
   evidencia. En un servidor MLflow vacío, el mismo código entrena y registra
   todo. `06_reproducir_champion.ipynb` es el notebook limpio: carga
   `models:/qsrr-predict-modelo@champion` y comprueba que reproduce exactamente
   el RMSE/MAE del holdout registrado.
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

La celda de monitoreo de `05_seleccion.ipynb` calcula PSI y faltantes para una muestra
reproducible de 20.000 filas de entrenamiento y 20.000 de holdout. El CSV
resultante es una comparación offline dentro de RepoRT, no una evaluación
temporal ni una alarma de producción. En operación, PSI y faltantes se calculan en
cada lote de moléculas nuevas (al menos semanal). RMSE, MAE y cobertura
requieren el tiempo real que mide el laboratorio al inyectar: se registran el
día de la corrida y se recalculan al acumular 30 compuestos medidos o cada mes.
Si el RMSE supera 3,09 min (CV + 2σ) o la cobertura cae bajo 90%, se revisa o
reentrena el modelo.

Las ejecuciones registran tabla(s) de origen, hora de extracción, SHA-256 del
snapshot, semilla, métricas y duración. Los artefactos y modelos quedan en el
volumen Docker de MLflow. Antes de interpretar los resultados se debe confirmar
que Snowflake contiene la OBT de PSet 2 y que hay suficientes registros C18 con
SMILES válidos.

El benchmark zero-shot de Gemini 3.5 Flash-Lite se ejecutó en 50 compuestos
distintos del holdout. El prompt envió únicamente SMILES y condiciones
cromatográficas, no el tiempo de retención real ni identificadores. Gemini
obtuvo RMSE 5,344 min y MAE 4,528 min; en la misma muestra, el champion logró
RMSE 2,064 min y MAE 1,302 min, y el challenger RMSE 2,103 min y MAE 1,360 min.
Es una comparación exploratoria pequeña, no evidencia independiente: Gemini
puede haber visto RepoRT durante su preentrenamiento. La reducción del 30% de
corridas sigue siendo una hipótesis de negocio y el proxy de pares cercanos no
representa coelusión confirmada.
