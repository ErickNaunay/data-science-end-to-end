# Separación de responsabilidades

PSet 2 termina cuando la OBT está escrita y validada en Snowflake. Contiene
infraestructura, ingesta, calidad, dbt, esquema dimensional, Spark, diccionario,
diagramas y memo. No contiene notebooks de modelado, sklearn, ARIMA, redes,
MLflow, tuning ni selección de modelos.

Las columnas de retorno, volatilidad y target en Spark sí pertenecen a PSet 2:
son parte de la OBT que la guía exige preparar para la etapa siguiente.
La elegibilidad y el indicador de corte describen cómo interpretar el dataset;
no entrenan ni seleccionan un modelo.

PSet 3 lee la OBT mediante SELECT. Allí viven EDA, las features experimentales
(volatilidad relativa y momentum normalizado), Pipeline/ColumnTransformer,
CV, modelos, tuning, tracking y registro. No reconstruye RAW, dbt ni Gold.
Los análisis previos de Yahoo/DuckDB permanecen en draft como antecedentes;
no se duplican como ruta activa de la entrega.

Los resultados de tests de PSet 3 se retiraron del acta JSON de PSet 2 y se
conservan en PSet 3. Las referencias documentales a la etapa siguiente y las
limitaciones de disponibilidad temporal se mantienen porque explican la OBT.
`separacion_alcance.json` recoge la inspección de imports y notebooks.
