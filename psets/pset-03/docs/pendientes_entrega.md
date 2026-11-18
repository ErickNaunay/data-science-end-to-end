# PSet 3: requisitos y estado

| Requisito del PDF | Estado |
|---|---|
| EDA de OBT con estadísticas, faltantes, IQR, Z-score, correlación y 3 hallazgos | Notebook 01 ejecutado; resultados en hallazgos_eda.csv |
| Dos features, una ligada a EDA | Notebook 02 ejecutado; aporte predictivo por ablación pendiente |
| Pipeline + ColumnTransformer, ajuste solo en train | Implementado y probado |
| División única y CV pertinente | Temporal por mes con purga de un mes; hold-out reservado |
| MLflow con backend y artifact store | Docker Compose, SQLite y volumen persistente |
| Dos líneas base | Ambas ejecutadas en verificación funcional; confirmar correspondencia de la segunda con PSet 1 |
| Cinco familias por defecto | Cuatro implementadas; familia fundacional pendiente |
| Prueba por prompting | Pendiente experimento o justificación de inaplicabilidad |
| Tres mejores × 30 configuraciones | Infraestructura de ParameterSampler/nested runs; no ejecutada |
| Ganador y segundo, hold-out una vez | Pendiente; no hay selección inventada |
| Métrica de negocio | Alinear coste/retorno y restricciones con PSet 1 antes de selección |
| Champion / challenger y recarga exacta | Pendiente implementación y ejecución final |
| docs/corridas.csv | Se genera con mlflow.search_runs tras tuning; aún no existe evidencia |
| Memo hasta 6 páginas | Pendiente hasta disponer de experimentos reales |

Las salidas 01-02 corresponden al snapshot con manifiesto local data/obt.json.
El hash y origen se imprimen en los notebooks. No consumir prueba para decidir
features ni hiperparámetros. HistGradientBoosting desactiva early stopping
aleatorio interno como adaptación al protocolo temporal; documentar esa
excepción a hiperparámetros por defecto en el memo experimental.
