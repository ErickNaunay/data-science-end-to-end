---
title: "PSet 3 — Modelos para el portafolio S&P 500 ∩ NYSE"
subtitle: "MSDS 6003 · Allan Paul Gómez Ehmig (00351916) · 18 de noviembre de 2026"
---

**Problema.** Para cada acción del S&P 500 que cotiza en la NYSE, al cierre de cada mes *t* se pronostica `ret_log_mes_siguiente`, el retorno logarítmico del mes *t+1*. Con ese pronóstico se arma un portafolio de 10 acciones ponderadas por 1/volatilidad. Los datos vienen de la OBT `PORTAFOLIO_P3.OBT.OBT_ACCION_MES` de Snowflake: 87.178 filas, snapshot `sha256 c3568917…`, que cada corrida registra en MLflow. Repositorio: `VirtualZen/data-science-end-to-end`, rama `work`, carpeta `psets/pset-03`.

**Resultado en una línea.** Ningún modelo supera a la media histórica (B1) en el MAE de forma que se distinga de la variación entre pliegues. El champion, LightGBM ajustado, obtiene un Sharpe neto de 0,87 en el hold-out, frente a 0,68 del universo con igual ponderación (B5). Ese resultado es para confirmar: su IC es prácticamente cero. Una regla manual, B3 (comprar cada mes las 10 acciones con mejor retorno medio histórico del universo común), logra el mejor Sharpe neto en CV (0,585) sin tecnología y queda como estrategia contingente.

# 1. EDA

| Hallazgo | Evidencia | Consecuencia en el modelo |
|---|---|---|
| Target con colas gruesas | Curtosis en exceso 9,6; asimetría −1,02; 1,27 % con \|z\| ≥ 3 (normal: 0,27 %) | Métrica técnica **MAE**; no se borran extremos; se prueban pérdidas L1 y Huber en el tuning |
| Buena parte de la varianza es común al mes | El mes explica el **34,5 %** de la varianza del target | Validación por meses completos, nunca por filas; IC de Spearman por mes como métrica del ranking; feature `dispersion_mes` |
| Señal débil para ordenar acciones | IC medio dentro del mes ≤ 0,021; 0 de 28 variables con \|t\| ≥ 2 | Se esperan mejoras modestas; modelos regularizados; se exige que la mejora supere la desviación entre pliegues |
| Predictores redundantes | 23 pares con \|ρ\| > 0,9; 4 combinaciones lineales exactas (rango 29 de 33) | Ridge sin 4 redundantes (`FEATURES_LINEALES`); `SelectKBest` dentro del Pipeline |
| Riesgo heterogéneo | `vol_63d` anual: p10 0,148, p90 0,413 | Escalado dentro del Pipeline; ponderación 1/vol y topes de volatilidad en la regla de negocio |
| Faltantes | 0 de 33 predictores con nulos tras excluir BMS y AMCR | Interpolación por acción a cada lado del corte; mediana en el Pipeline para extremos |

BMS y AMCR se excluyen (hallazgo H19): el pipeline trata la compra de Bemis por Amcor como un cambio de símbolo, lo que deja 109 filas con barras de solo cierre. Las figuras del EDA (distribución, boxplots y correlación) están en el anexo A.

# 2. Features

Se usan las 33 variables numéricas de la OBT y dos derivadas, todas conocidas al cierre de *t*:

- **`dispersion_mes`:** desviación estándar transversal de `ret_log_mes` en el mes *t*. Usa solo filas del mismo mes y se calcula antes de filtrar por target.
- **`mes_calendario_obj`:** mes calendario de *t+1*, que se conoce de antemano. Va como one-hot con categorías fijas (enero como referencia) y `handle_unknown='error'`.

**Evidencia (ablación con los 7 pliegues):** con las dos derivadas, el MAE de LightGBM baja 0,0012 y mejora en **7 de 7 ventanas**; el de Ridge baja 0,0014 (5 de 7). Otras cuatro candidatas no mejoraron y se descartaron: `vol_relativa`, `momentum_por_riesgo`, `ret_idiosincratico_mes` y `regimen_vol` (anexo A3).

**Sin fuga.** Quedan fuera de X los niveles de precio ajustado, que dependen de dividendos posteriores a *t*, y `sigue_en_sp500`, que describe el presente. Las pruebas `tests/test_pipeline.py` (`test_dispersion_solo_usa_el_mes`, `test_mes_calendario_del_objetivo`, `test_interpolacion_no_cruza_el_corte`, `test_imputador_no_ve_prueba`) y `tests/test_diseno.py` (`test_fuga_se_detecta` y otras) pasan: 28 de 28.

# 3. Preparación y validación

**División temporal.** Entrenamiento: objetivos hasta 2023-12, **46.851 filas**. Hold-out: objetivos de 2024-01 a 2026-10, **11.326 filas y 34 meses**, evaluado una sola vez. Imputación, escalado, one-hot y selección viven en el `Pipeline` (`src/pipeline.py`) y se ajustan en cada pliegue.

**CV.** `TimeSeriesSplit` sobre meses únicos: 7 pliegues de 12 meses, ventana expansiva y `gap=1` mes, porque las ventanas de 21 a 252 días se solapan. Se valida 2017–2023: 84 meses. Fechas de corte en `docs/cortes_cv.csv`.

| Esquema (LightGBM L1) | MAE CV | Filas de validación con su mes en el entrenamiento |
|---|---|---|
| **TimeSeriesSplit por meses (oficial)** | 0,0651 ± 0,0177 | 0 % |
| TimeSeriesSplit por filas | 0,0670 ± 0,0139 | 3,3 % |
| KFold(5) aleatorio | 0,0476 ± 0,0004 | 100 % |
| GroupKFold por acción | 0,0475 ± 0,0022 | 100 % |

Los esquemas no temporales dan un MAE un 27 % más bajo porque entrenan con el mismo mes que validan. Es justamente la fuga que el EDA anticipaba.

**Métricas.**

- **Técnica (decide): MAE.** RMSE, R² frente al random walk, acierto direccional y el IC de Spearman por mes se registran como informativas.
- **Negocio: Sharpe neto anualizado del portafolio top-10.**
  - Cada mes se toman las 10 acciones con mayor pronóstico, ponderadas por 1/`vol_63d`.
  - Tope relativo: se excluye el 20 % más volátil del mes.
  - Tope de portafolio: 1,35 × la volatilidad del S&P 500 (covarianza de 63 días). El exceso va a efectivo, que rinde la tasa libre de riesgo.
  - Costo de 15 pb por US\$ negociado. Todo en US\$.

# 4. Diseño experimental

El experimento `portafolio-inversiones` del servidor MLflow (Docker, `localhost:5001`) tiene **142 corridas**, exportadas en `docs/corridas.csv`:

| Fase | Corridas |
|---|---|
| Líneas base | B1 media, B2 random walk sin deriva, B3 random walk con deriva por acción |
| Referencias de negocio (familia N/A) | B4 azar (mediana de 200 sorteos), B5 universo con igual ponderación, índices S&P 500 y NYSE |
| Candidatos | 8, uno por modelo, de 5 familias más 3 fundacionales |
| Tuning | 3 corridas padre × 30 hijas = 90 configuraciones |
| Final | 2: champion y challenger en el hold-out |

Las corridas fallidas o duplicadas no se borraron; tienen el tag `fase=descartada` y su `motivo`:

- una prueba de TimesFM con 500 filas;
- una prueba previa al pipeline final;
- registros repetidos de B1, B2 y B5;
- un tuning de XGBoost que falló porque dos procesos paralelos compartían un archivo temporal, junto con sus corridas hijas. Se corrigió y se repitió.

**Qué registra cada corrida:**

- **Tags:** `fase`, `familia`, `modelo`, `git_commit` y `git_dirty`.
- **Parámetros:** los hiperparámetros, la semilla 42 y el sha256 de los datos.
- **Métricas:** MAE, RMSE y demás por pliegue, más su media, desviación y valor en entrenamiento; IC, ICIR y t; Sharpe neto y bruto, drawdown, turnover y tiempos.
- **Artefactos:** las predicciones por pliegue, el modelo serializado con `skops` y su firma, y un ejemplo de predicción para verificar la recarga.

![Comparación de candidatos y líneas base en la interfaz de MLflow, ordenados por `mae_cv_media`.](mlflow_comparacion.png){width=100%}

# 5. Resultados

Candidatos con sus hiperparámetros por defecto, salvo la semilla. Los fundacionales se usan sin ajuste (zero-shot) con un contexto de 512 días hábiles, por eso su columna "Entrena" dice "—". LLM por prompting no aplica: conoce los precios posteriores a su fecha de corte y no hay forma de aislar esa fuga.

| Modelo | Familia | MAE entrena | MAE CV (± desv.) | Brecha | Learning rate | Entrena (s) | Sharpe neto CV |
|---|---|---|---|---|---|---|---|
| B1 media | línea base | 0,0529 | **0,0641** ± 0,0165 | 0,011 | — | 0,8 | — |
| B2 RW sin deriva | línea base | 0,0539 | 0,0647 ± 0,0159 | 0,011 | — | 0,7 | — |
| B3 RW con deriva | línea base | 0,0527 | 0,0652 ± 0,0159 | 0,013 | — | 0,1 | **0,585** |
| M8 Chronos-Bolt | fundacional | 0,0550 | 0,0670 ± 0,0175 | 0,012 | — | — | 0,568 |
| M4 Ridge | lineal | 0,0513 | 0,0681 ± 0,0200 | 0,017 | — | 1,5 | 0,197 |
| M9 TimesFM 2.5 | fundacional | 0,0578 | 0,0687 ± 0,0171 | 0,011 | — | — | 0,457 |
| M10 Moirai 2.0 | fundacional | 0,0563 | 0,0693 ± 0,0192 | 0,013 | — | — | 0,430 |
| M3 LightGBM | boosting | 0,0387 | 0,0706 ± 0,0223 | 0,032 | 0,1 | 13,4 | 0,440 |
| M3b XGBoost | boosting | 0,0300 | 0,0732 ± 0,0202 | 0,043 | 0,3 | 7,6 | 0,490 |
| M2 Random Forest | bagging | 0,0149 | 0,0757 ± 0,0247 | 0,061 | — | 206,0 | 0,201 |
| M5 MLP | red neuronal | 0,0449 | 0,0896 ± 0,0189 | 0,045 | 0,001 | 16,2 | 0,285 |

*Referencias de negocio en CV: B5 0,544; B4 (azar) 0,344.*

![MAE de CV y Sharpe neto de todos los modelos, por defecto y ajustados.](resultados_modelos.png){width=100%}

**Lectura.**

- Por defecto, **ningún candidato le gana a B1**.
- Los árboles sobreajustan: el random forest tiene una brecha de 0,061 entre entrenamiento y CV.
- Los fundacionales sin ajuste quedan cerca de B1 y Chronos es el mejor de ellos. En el negocio, solo B3 y Chronos superan a B5.

# 6. Tuning

Se ajustan los 3 mejores modelos con hiperparámetros: Ridge, LightGBM y XGBoost (`src/tuning.py`).

**Método.** Optuna con muestreador TPE (semilla 42) y 30 configuraciones por modelo. Cada configuración es una corrida hija de MLflow y se evalúa con los mismos 7 pliegues, minimizando el MAE de CV. Se eligió TPE porque con 30 configuraciones en 9 dimensiones una rejilla no cabe y el azar desperdicia pruebas. Además, TPE maneja en un solo espacio escalas logarítmicas, enteros y categorías.

**Espacio de búsqueda:**

| Hiperparámetro | Rango | Escala |
|---|---|---|
| `learning_rate` | 0,005–0,2 | log |
| `n_estimators` | 50–1000 | log |
| `num_leaves` (LightGBM) | 4–128 | log |
| `max_depth` (XGBoost) | 2–8 | lineal |
| `min_child_samples` (LightGBM) | 20–2000 | log |
| `min_child_weight` (XGBoost) | 1–500 | log |
| `subsample` | 0,5–1 | lineal |
| `colsample` | 0,3–1 | lineal |
| `reg_lambda` | 10⁻³–100 | log |
| Pérdida | L2, L1 o Huber | categórica |
| `alpha` de Ridge | 10⁻³–10⁵ | log |
| `k` de `SelectKBest` (todos) | 10, 20, 30 o todas | categórica |
| Rango transversal (todos) | sí o no | categórica |

| Modelo | MAE por defecto | MAE ajustado (± desv.) | Mejora | ¿Supera la desviación? | Mejor configuración | Sharpe neto CV |
|---|---|---|---|---|---|---|
| LightGBM | 0,0706 | **0,0636** ± 0,0163 | 0,0070 | no (0,022) | 63 árboles, lr 0,021, pérdida L1, `reg_lambda` 97, k = 10 | 0,302 |
| Ridge | 0,0681 | **0,0636** ± 0,0161 | 0,0045 | no (0,020) | `alpha` 47.651, todas las features, rango transversal | 0,421 |
| XGBoost | 0,0732 | 0,0640 ± 0,0169 | 0,0092 | no (0,020) | 51 árboles, lr 0,016, profundidad 3, pseudo-Huber, k = 10 | 0,266 |

![Historia de las tres búsquedas: MAE de CV por configuración y mejor acumulado.](tuning_historia.png){width=88%}

**Lectura.**

- Optuna empuja hacia **modelos casi constantes**: pocos árboles, tasas de aprendizaje bajas, regularización alta y, en Ridge, un `alpha` de 47.651.
- Los tres ajustados quedan apenas debajo de B1, por menos de 0,0006. Eso es unas 30 veces menos que la desviación entre pliegues, así que en la práctica **empatan con la media**.
- Ninguna mejora frente a la versión por defecto supera la desviación entre pliegues, así que, según el criterio del PDF, no cuentan como mejora.

# 7. Decisión

| | Champion | Challenger |
|---|---|---|
| Modelo | M3 LightGBM ajustado | M4 Ridge ajustado |
| Corrida de tuning (`run_id`) | `f7596a565f8a458492057238f245cf89` | `75f75a7030154008a54e502bf2e4d18b` |
| Corrida `final` en el hold-out | `50f2d7b9f44048d79506ce8d65ac4c87` | `a07387177c294fe8acd7e0fc1bf911b0` |
| Registro `portafolio-inversiones-modelo` | **versión 1, alias `champion`** | versión 2, alias `challenger` |
| MAE CV | 0,06355 ± 0,0163 | 0,06361 ± 0,0161 |
| **MAE hold-out** | 0,0673 | **0,0635** |
| Acierto direccional / IC hold-out | 50,0 % / −0,001 | 54,5 % / −0,009 |
| **Sharpe neto hold-out** | **0,87** | −0,02 |
| Drawdown / retorno anual neto | −11,5 % / 15,9 % | −17,2 % / 3,1 % |
| Entrena (CV) / inferencia | 8,9 s / 0,0045 ms por fila | 5,8 s / 0,0033 ms por fila |

*Referencias en el hold-out: MAE de B1 0,0634; Sharpe de B5 0,68 y del S&P 500 (precio) 1,10.*

![Hold-out: MAE (izquierda) y Sharpe neto (derecha) frente a las referencias. El eje del MAE no empieza en cero.](holdout.png){width=92%}

**Por qué gana LightGBM.**

- Tiene el menor MAE de CV, la regla fijada antes de abrir el hold-out. La diferencia con Ridge es de **0,00006**, frente a una desviación entre pliegues de 0,016: gana en 2 de 7 años y el t pareado es 0,07. **Es un empate técnico.**
- En el hold-out, Ridge tiene mejor MAE y LightGBM mejor Sharpe. No se cambió la elección después de verlo, para no convertir el hold-out en un segundo conjunto de validación.

**Costo y explicabilidad.** Los dos son baratos de entrenar y de usar. Ridge se explica directo con sus coeficientes. LightGBM, con la importancia por ganancia. En ambos domina `dispersion_mes`, que es igual para todas las acciones del mes: el modelo aprende sobre todo el nivel del mes siguiente y no qué acción rinde más que otra, lo que es coherente con un IC cercano a cero.

**Reproducibilidad.** `06_champion.ipynb` recarga `models:/portafolio-inversiones-modelo@champion` en un kernel limpio y reproduce el MAE del hold-out: 0,0673399888, idéntico al registrado.

**Recomendación.** Registrar el champion como referencia, pero **no usarlo todavía para invertir**. Su ventaja en el Sharpe del hold-out no aparece en CV (0,30) ni tiene respaldo en el IC.

**Implicaciones de negocio.**

- **Para el asesor, el valor sigue estando en la disciplina del proceso**, no en la predicción: rebalanceo mensual en fecha fija, topes de volatilidad acordados con el cliente, 15 pb por US\$ negociado y aprobación del cliente antes de cada cambio. Ningún modelo aporta todavía una señal de selección que justifique su costo de operación (pipeline, Snowflake, servidor de modelos y monitoreo).
- **Estrategia contingente sin tecnología.** Es la regla de B3: cada mes, el asesor ordena las acciones del universo común S&P 500 ∩ NYSE por su retorno medio histórico, toma las 10 mejores y aplica la misma ponderación 1/vol con los mismos topes. Se arma en una hoja de cálculo con precios públicos, sin modelo ni infraestructura.
  - En CV obtuvo el mejor Sharpe neto de todo el experimento: **0,585**, frente a 0,544 de B5 y 0,568 del mejor candidato (Chronos).
  - Sirve como **plan de contingencia** si el pipeline o el modelo fallan: Kestra o Snowflake caídos, o un modelo degradado.
  - También es la **vara mínima de negocio**: un modelo solo justifica su costo si la supera con un margen mayor que la variación entre pliegues.
  - Su Sharpe en el hold-out queda por medir en el PSet 4.
- **Frente al índice.** En el hold-out, comprar el S&P 500 completo (Sharpe 1,10) le gana a toda estrategia restringida a la NYSE: el universo común deja fuera a las grandes tecnológicas que cotizan en NASDAQ. Para un cliente que solo busca retorno ajustado por riesgo, un fondo indexado es la alternativa de menor costo. El servicio se justifica por el control de volatilidad y la personalización, no por superar al índice.
- **Operación recomendada.** Hasta que un modelo supere a B3 y B5 con margen claro, se opera con la regla contingente o con el universo de igual ponderación. El champion corre en paralelo sin decidir compras, y se registra mes a mes su pronóstico y su desempeño para decidir con evidencia fuera de muestra.

# 8. Limitaciones

- **Señal débil.** El EDA ya mostraba un IC de 0,02 como máximo. Con 84 meses de validación, la desviación entre pliegues (≈ 0,016) es más de 25 veces mayor que las diferencias entre los mejores modelos. Ninguna selección es estadísticamente distinguible.
- **Múltiples comparaciones.** Se evaluaron 8 candidatos, 3 líneas base y 90 configuraciones sobre los mismos 84 meses, así que el mejor resultado de CV está sesgado hacia arriba. El hold-out, abierto una sola vez, lo confirma: el MAE del champion empeora de 0,0636 a 0,0673.
- **Contaminación de los fundacionales.** Chronos, TimesFM y Moirai se preentrenaron con series públicas que pueden incluir precios del periodo de validación. Por eso se reportan, pero no son candidatos al registro: tampoco son un `Pipeline` reentrenable.
- **Universo con sesgo de supervivencia.** El filtro NYSE refleja la bolsa actual (H11, 20,8 % de símbolos sin precios). Además, las fusiones se tratan como cambio de símbolo, lo que excluyó a BMS y AMCR (H16, H19).
- **Hold-out alcista.** 2024–2026 fue un periodo muy alcista: el S&P 500 tuvo un Sharpe de 1,10. El tope de volatilidad y el efectivo penalizan a todos los portafolios frente al índice.
- **Alcance.** Quedan para el PSet 4:
  - ARIMA-GARCH (M1) y los híbridos con MLP y LSTM (M6, M7);
  - el ensamble por rangos;
  - las pruebas Diebold-Mariano y Wilcoxon con ajuste de Holm, ya implementadas en `src/evaluacion.py`;
  - un target de ranking relativo, que ataca directamente el problema del efecto común del mes.

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Anexos

**A1. EDA: distribución del target y boxplots de atípicos.**

![](eda_target_distribucion.png){width=80%}

![](eda_atipicos_boxplots.png){width=85%}

**A2. EDA: correlación de Spearman entre predictores.**

![](eda_correlacion_spearman.png){width=75%}

**A3. Ablación de features (ΔMAE por configuración, 7 pliegues).**

![](features_ablacion.png){width=85%}

**A4. Pliegues de la validación temporal.**

![](validacion_pliegues.png){width=85%}

**A5. Brecha entre entrenamiento y CV de los candidatos.**

![](candidatos_brecha.png){width=80%}

**A6. Importancia de hiperparámetros en el tuning de LightGBM (Optuna).**

![](tuning_M3_lightgbm_importancia.png){width=70%}

**A7. Líneas base y referencias de negocio (valor acumulado).**

![](lineas_base_negocio.png){width=85%}

**A8. Cómo reproducir.**

- **Requisitos:** MLflow con `docker compose up -d mlflow`, y Kestra y Spark apagados. Credenciales de Snowflake en `.env` (ver `.env.example`).
- **Notebooks**, en orden: `01_eda`, `02_features`, `03_preparacion_validacion`, `03_baseline_candidatos`, `04_tuning`, `05_seleccion` y `06_champion`.
- **Fundacionales:** `src/modelos/fundacionales.py` (comandos en el README).
- **Tuning:** `python -m src.tuning --modelo <m> --trials 30`.
- **Pruebas:** `pytest tests`.
