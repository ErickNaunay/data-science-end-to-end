# Memo técnico — PSet 3: experimentación y selección de modelo

**Proyecto:** QSRR-Predict · **Autor:** Jonatan Buenaño · **Fecha:** 15 de noviembre de 2026

## Resumen ejecutivo

Se construyó un flujo reproducible para predecir el tiempo de retención (minutos) de observaciones C18 de RepoRT, aprovechando la OBT del PSet 2 almacenada en Snowflake. La instantánea contiene 152.586 observaciones y 96.482 compuestos; todos los registros incluidos en el modelado tienen SMILES válidos. La partición se hizo por InChIKey para evitar que un compuesto aparezca a la vez en entrenamiento y prueba.

HistGradientBoosting es el champion registrado (RMSE de holdout: **2,329 min**; MAE: **1,529 min**). Random Forest es challenger (RMSE: **2,506 min**; MAE: **1,633 min**). Su modelo final utiliza `max_samples=4096` por árbol para poder serializarse en el Codespace; se volvió a evaluar esa variante con CV agrupada y se registró el ajuste. Los resultados no demuestran ahorro experimental, coelusión real ni generalización a un laboratorio distinto.

## Datos, alcance y preparación

La consulta recupera la OBT `GOLD.OBT_QSRR_FINAL`, une SMILES de `RAW.RAW_REPORT_DATA` por InChIKey y filtra C18 con tiempo de retención positivo. La instantánea, leída el 14 de noviembre de 2026, tiene SHA-256 `0c366b465f7b56e6b5873132279f7a3152532f0a035186c776f491c01a628210`. Se observaron 28 tipos de columna, 12 fases móviles y 75 condiciones cromatográficas. El flujo falta en 4,35% de las filas de desarrollo y el nombre del compuesto falta en 53,38%; por ello, el nombre se excluyó como predictor y el flujo se imputa dentro del pipeline.

La mediana de retención en desarrollo es 10,34 min (IQR: 9,71 min; rango: 0,005–49,97 min). No se eliminaron automáticamente observaciones atípicas. El split agrupado deja **122.370** observaciones de entrenamiento y **30.216** de holdout. La selección de candidatos y el tuning usan solo una muestra estratificada de **12.000 compuestos completos** de entrenamiento (19.406 observaciones, semilla 42); el holdout permaneció apartado de la selección.

Las 16 variables derivadas combinan nueve descriptores RDKit, seis proporciones de composición de fase móvil y el flujo. El escalado y la imputación se ajustan dentro de cada fold. En la muestra de desarrollo, las asociaciones monotónicas más fuertes con el target fueron flujo (Spearman −0,705), logP (0,590), donadores H (−0,491) y anillos aromáticos (0,497). Son asociaciones exploratorias, no evidencia causal.

## Comparación de modelos

Se usaron cinco folds agrupados por InChIKey para las dos líneas base y las cinco familias candidatas.

| Modelo | RMSE CV (min) | MAE CV (min) |
|---|---:|---:|
| Mediana global (base ingenua) | 5,828 | 4,875 |
| Mediana por condición cromatográfica (proxy) | 3,765 | 2,584 |
| Ridge | 3,176 | 2,278 |
| KNN | 3,064 | 1,935 |
| MLP | 2,764 | 1,846 |
| Random Forest | 2,683 | 1,723 |
| HistGradientBoosting | 2,604 | 1,693 |

Se ajustaron 30 configuraciones por familia para las tres mejores candidatas, para un total de **90 trials** registrados en MLflow. Los mejores RMSE de tuning fueron 2,573 para Random Forest, 2,592 para HistGradientBoosting y 2,754 para MLP. Para hacer viable el artefacto final de Random Forest, cada árbol se entrenó con 4.096 filas extraídas de toda la partición de entrenamiento. La variante se volvió a medir con GroupKFold: RMSE **2,593 ± 0,216 min**. La media queda prácticamente empatada con HistGradientBoosting (**2,592 ± 0,250 min**); la diferencia de 0,0015 min es mucho menor que la variabilidad entre folds y no se interpreta como una superioridad estadística concluyente. Se eligió HistGradientBoosting como champion por la menor media de CV.

| Modelo final | RMSE train completo | RMSE holdout | MAE holdout | Estado MLflow |
|---|---:|---:|---:|---|
| HistGradientBoosting (champion) | 2,070 | 2,329 | 1,529 | Registrado; alias `champion` |
| Random Forest, `max_samples=4096` (challenger) | 2,303 | 2,506 | 1,633 | Registrado; alias `challenger` |

El holdout se utilizó para reportar desempeño, no para escoger el champion. El intervalo pairwise de 95% se calibró con predicciones OOF de la muestra de entrenamiento: el radio estimado fue 9,079 min. En 61.742 pares de holdout, la cobertura observada fue 95,7%, el proxy de recall fue 96,6% y la tasa de alerta 91,2%. Esa tasa de alerta es muy alta para una herramienta operativa: el resultado es un análisis exploratorio que requiere recalibración y validación de laboratorio. Los pares “cercanos” se definen solo por diferencia temporal; RepoRT no confirma coelusión, resolución ni ancho de pico.

## Valor de negocio, límites y monitoreo

La reducción del 30% de corridas sigue siendo una **hipótesis**, no un ahorro medido. El KPI propuesto para un piloto es `(corridas actuales − corridas asistidas) / corridas actuales × 100`, comparando métodos con el mismo criterio de aceptación; como métrica complementaria se registrarán los mL de solvente por método validado. No existen en esta entrega registros locales del número de ensayos ni del consumo de solvente para calcularlos.

La validación se limita a RepoRT C18. No se dispone de corridas de control de un laboratorio local, así que no se afirma transferencia a otras columnas, equipos o gradientes. Antes del uso operativo se debe comparar el RMSE local con el de RepoRT en un protocolo de calibración acordado con el laboratorio. Como plan de monitoreo, se propone revisar la distribución de descriptores y condiciones por cada lote nuevo; el desempeño (RMSE/MAE y cobertura del intervalo) solo se medirá cuando se reciban los tiempos reales de retención. Esta entrega no afirma tener un sistema de monitoreo productivo ni labels de coelusión confirmada.

Como demostración offline, se compararon 20.000 observaciones de entrenamiento y 20.000 de holdout. Las 16 features presentaron PSI menor que 0,01 (máximo: 0,0080) y la diferencia absoluta máxima en la fracción de faltantes fue 0,0036. Estos valores describen únicamente la comparación aleatoria dentro de RepoRT y no acreditan estabilidad temporal ni generalización a un laboratorio.

**Benchmark LLM:** se autorizó una comparación zero-shot de hasta 50 compuestos del holdout con Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`). El prompt contiene SMILES y condiciones cromatográficas, pero excluye el tiempo de retención real y los identificadores. La clave `GEMINI_API_KEY` aún no está configurada en el entorno, por lo que no se han realizado llamadas ni se reportan métricas del LLM. Al ejecutarlo, se registrarán RMSE/MAE junto a champion y challenger en MLflow. Por ser un modelo preentrenado, puede haber solapamiento con RepoRT en sus datos de entrenamiento; el resultado sería exploratorio, no una comparación independiente.

## Reproducibilidad y artefactos

El tracking corre con MLflow 2.22.0 en el contenedor Docker del PSet 3, disponible localmente en `http://localhost:5000` mediante el port forwarding de Codespaces. El Model Registry tiene aliases `champion` y `challenger`; el modelo champion se volvió a cargar y reprodujo exactamente su RMSE de holdout. Los notebooks y tablas de resultados están en `notebooks/` y `docs/`; `corridas.csv` conserva el historial, incluidos intentos fallidos, para trazabilidad.

Para repetir el flujo se requieren Python 3.11, las dependencias de `requirements.txt`, acceso autorizado a Snowflake y variables de entorno propias; no se incluyen credenciales. La instantánea Parquet y el split local están excluidos de Git, por lo que un evaluador necesita acceso a las tablas Snowflake para recrearlos. El benchmark Gemini se ejecuta con `python scripts/run_llm_benchmark.py` después de configurar `GEMINI_API_KEY` como secreto local.
