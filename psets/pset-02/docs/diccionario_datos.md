# Diccionario de datos para la entrega PSet 2

El inventario exhaustivo de las 236 columnas, clasificación de origen/creación,
porcentajes y políticas está en [calidad/README.md](calidad/README.md),
[inventario_columnas.csv](calidad/inventario_columnas.csv) y
[decisiones_por_columna.csv](calidad/decisiones_por_columna.csv).

## Gold

| Objeto | Clave/grano | Medidas y atributos |
|---|---|---|
| DIM_ACCION | accion_key, una acción/símbolo normalizado | ticker, nombre, bolsa actual, fechas de precio/membresía, disponibilidad |
| DIM_FECHA | fecha_key (AAAAMMDD), un día bursátil | fecha, año, mes, anio_mes, cierre de mes, conjunto temporal |
| DIM_MEMBRESIA_SP500 | periodo_key, un intervalo por símbolo | ticker, fecha_inicio, fecha_fin, vigente, huecos_unidos |
| FCT_PRECIOS_DIARIOS | accion_key + fecha_key | OHLC, cierre/apertura ajustados, volumen, retornos log, membresía, marcas de calidad |
| FCT_MERCADO_DIARIO | fecha_key | cierre y retorno de S&P 500 / NYSE Composite, ^IRX y tasa diaria aproximada |

`periodo_sp500_key` enlaza el hecho con GOLD.DIM_MEMBRESIA_SP500, publicada
desde Silver. Hay dos hechos y tres dimensiones Gold; DIM_FECHA es compartida.
Ver [auditoría de capas y grano](revision_capas_modelo.md).
Un ticker es una aproximación a la empresa; cambios y reutilización de símbolos
requieren revisar las equivalencias, no asumir identidad permanente.

## OBT_ACCION_MES

Grano: `accion_key` + `anio_mes` (AAAAMM), meses cerrados. Los precios están en
USD, el volumen en acciones y los retornos en logaritmos naturales salvo las
columnas de tasa libre de riesgo, aproximadas como tasas simples.

| Grupo | Columnas | Interpretación / restricción |
|---|---|---|
| Identidad | accion_key, ticker, nombre | Clave y etiquetas; no se emplean como variables numéricas |
| Bolsa | bolsa, es_nyse, bolsa_desconocida | Bolsa actual, no prueba histórica; limitar sesgo de selección |
| Tiempo | anio_mes, anio, mes, fecha_ultima_cotizacion | Última observación del mes cerrado |
| Protocolo | conjunto, objetivo_cruza_corte | Separación original por fecha; PSet 3 divide por mes del objetivo |
| Elegibilidad | cotizo_al_cierre_de_mes, en_sp500, sigue_en_sp500, elegible | sigue_en_sp500 describe el presente y no debe entrar a X histórica |
| Nivel y retorno | precio_cierre_ajustado, ret_log_mes, ret_log_21d, ret_log_252d, momentum_12_1 | Ventanas hasta la fila; momentum = retorno 252 - retorno 21 |
| Riesgo | vol_21d, vol_63d, vol_apertura_21d, drawdown_252d | Volatilidad anualizada con raíz de 252; drawdown frente a máximo de ventana |
| Intradía | intradia_prom_21d, nocturno_prom_21d | Promedios de retornos intradía/nocturnos observados |
| Liquidez | volumen_prom_21d, dolares_negociados_prom_21d | Promedios de volumen y volumen × cierre |
| Cobertura | obs_252d, dias_negociados_mes, dias_imputados_mes | Conteos; las ventanas se basan en filas, no necesariamente días consecutivos |
| Calidad | hubo_tramo_excluido_mes, hubo_retorno_extremo_mes | Marcas de exclusión de huecos largos y retornos extremos |
| Mercado actual | ret_log_sp500_mes, ret_log_nyse_composite_mes, rf_mes, tasa_irx_prom_mes_pct | Referentes del mes que termina |
| Objetivo | ret_log_mes_siguiente, exceso_ret_mes_siguiente | Valores futuros: nunca incluir en los predictores |
| Referentes futuros | ret_log_sp500_mes_siguiente, ret_log_nyse_composite_mes_siguiente, rf_mes_siguiente | Solo evaluación ex post; nunca incluir en X |

El target queda nulo si no hay mes siguiente consecutivo para la acción.
Los nulos de las features se imputan dentro de cada fold de entrenamiento en
PSet 3, no con estadísticas de toda la OBT. El detalle SQL y los tests están
en dbt/models/*/*.yml; la fórmula exacta de la OBT está en spark/jobs/.
