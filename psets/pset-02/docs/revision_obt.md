# OBT con Spark: grano, joins y decisión de diseño

## Esquema existente y entradas

Gold es una constelación de dos estrellas: precios y mercado comparten fecha. No es una tabla de hechos aislada. El diagrama editable y sus imágenes están en `modelo_dimensional.dot`, `.svg` y `.png`; los diagramas C4 de ejecución están en `structurizr/`.

| Objeto Gold | Grano | Aporte a Spark |
|---|---|---|
| FCT_PRECIOS_DIARIOS | Acción × sesión bursátil conservada | Precios, retornos, volumen, membresía vigente y banderas de calidad |
| DIM_FECHA | Día bursátil | Fecha, mes, mes cerrado, cierre del mes y corte de entrenamiento |
| DIM_ACCION | Símbolo normalizado | Identificación, nombre y bolsa actual; no es SCD2 |
| FCT_MERCADO_DIARIO | Día bursátil | Retornos S&P 500, NYSE Composite y aproximación libre de riesgo ^IRX |
| DIM_MEMBRESIA_SP500 | Intervalo de pertenencia por símbolo | Auditoría histórica mediante periodo_sp500_key; no requiere otro join en Spark porque el hecho ya resuelve en_sp500 por fecha |

Unir únicamente el hecho de precios sería insuficiente: faltan atributos del calendario, identificación y referentes del mercado. Las cuatro entradas directas satisfacen esos usos. No unir el hecho de mercado a cada acción antes de resumirlo: se repetirían sus retornos. Spark lo agrega por mes de forma independiente y después lo une muchos-a-uno.

## Grano y transformación

`OBT.OBT_ACCION_MES` tiene una fila por `(accion_key, anio_mes)` para cada mes **cerrado con observaciones conservadas**. Se selecciona la última cotización disponible de esa acción en el mes; no se presupone que sea el cierre bursátil oficial. `cotizo_al_cierre_de_mes` distingue ambos casos. No se crean filas para meses sin precios ni para el mes abierto.

La reducción de sesiones diarias a acciones-mes es una agregación intencionada. La referencia de conservación es el conjunto distinto de acción-mes cerrado de Gold, no el número de filas del hecho diario. Los joins posteriores deben conservar exactamente esa referencia. `elegible` es una bandera, no un filtro que elimine observaciones de la OBT.

Spark calcula ventanas de 21/63/252 filas históricas, resumen mensual, momentum 12-1, volatilidad, drawdown y liquidez; agrega referentes mensuales y crea el retorno del mes siguiente como objetivo solo si el siguiente mes de la acción es consecutivo. Las volatilidades excluyen filas imputadas; las ventanas basadas en filas no siempre representan sesiones consecutivas tras huecos excluidos.

Las 43 columnas incluyen identificadores, predictores, banderas de elegibilidad/calidad, objetivo y referentes futuros. El consumidor de PSet 3 selecciona explícitamente predictores y separa por fecha del objetivo: las columnas `*_siguiente`, `sigue_en_sp500` y el identificador de conjunto no deben entrar por accidente en X. Bolsa/nombre son atributos actuales y los precios ajustados pueden revisarse retrospectivamente: la OBT no constituye una garantía point-in-time.

## Controles ejecutables

`construir_obt.py` ejecuta 13 controles antes de escribir:

- Unicidad de DIM_ACCION, DIM_FECHA, FCT_MERCADO_DIARIO y FCT_PRECIOS_DIARIOS.
- Conservación de filas en precios × fecha y mercado × fecha.
- Conservación de cierres × resumen mensual.
- Unicidad del mercado mensual y ausencia de meses de OBT sin mercado.
- Conservación de OBT × mercado y OBT × acción.
- Unicidad final acción-mes y conservación del número de cierres.

La prueba de cobertura usa un anti-join sobre la clave mensual: no confunde una medida legítimamente nula con una relación ausente. Unicidad y conteos se complementan: un left join conserva filas aunque no encuentre correspondencia.

Si falla un control, se persiste VALIDACION_OBT y se termina sin reemplazar la OBT. Las dos escrituras finales usan overwrite y no forman una transacción conjunta; un fallo de escritura puede requerir repetir el job. El contrato exige Gold estable durante la ejecución; no ejecutar dbt simultáneamente.

`scripts/auditar_obt.py` verifica después en Snowflake unicidad, ausencia de claves nulas, igualdad del número de observaciones y **equivalencia de conjuntos de claves** contra Gold mediante full outer join. Conserva SQL, query IDs, fecha UTC y almacenamiento en `corrida/auditoria_obt.json`. Esto comprueba también la tabla efectivamente almacenada, no solo el DataFrame previo.

## Cuándo usar estrella y cuándo OBT

| Uso | Representación | Motivo |
|---|---|---|
| Auditoría de sesiones, membresía, huecos y procedencia | Gold | Conserva detalle y relaciones verificadas por dbt |
| Reportes por acción/fecha o nuevas agregaciones | Gold | Dimensiones reutilizables; mercado no repetido por acción |
| Entrenamiento, validación temporal e inferencia mensual | OBT | Una fila por unidad de decisión y predictores ya integrados |
| Retornos agregados de mercado | Hecho de mercado o deduplicación por mes | En OBT el mismo retorno mensual aparece en muchas acciones; no sumarlo entre acciones |

## ¿Añadir más tablas?

No se necesitan más tablas para los predictores y el objetivo actuales. Conservar DIM_MEMBRESIA_SP500 permite una estrella autónoma y trazabilidad de intervalos; volver a unirla en Spark sería redundante.

| Candidato | Añadir solo si… | Requisito antes de implementarlo |
|---|---|---|
| Dimensión sector/industria | Se usan exposiciones sectoriales, reportes o predictores sectoriales | Fuente con vigencias históricas, claves y pruebas de solapes; no atribuir el sector actual a toda la historia |
| Historial de bolsa o identidad de instrumento | Se necesita universo NYSE point-in-time o resolver reutilización de símbolos | Identificador estable y fuente temporal; ticker es hoy un proxy imperfecto |
| Hecho de eventos corporativos | Se explican dividendos/splits o retornos totales de forma explícita | Fecha efectiva y de disponibilidad; validar que no duplique ajustes ya incorporados |
| Dimensión índice + hecho largo de cotizaciones de índice | Se amplía el conjunto de índices o se compara dinámicamente | El formato ancho actual con tres referentes fijos basta para el alcance actual |

Una tabla pequeña sin uso consume poco espacio pero aumenta mantenimiento, joins y pruebas. Una tabla históricamente útil puede justificar ese coste. La decisión no depende solo del número de tablas. Gold conserva detalle y OBT intercambia repetición por comodidad de consumo; no son sustitutos.

El almacenamiento medido en INFORMATION_SCHEMA.TABLES.BYTES describe objetos actuales, no la capacidad restante de la cuenta ni todo el coste de retención, Time Travel o staging. No se ha proporcionado una cuota contractual para afirmar cuántos bytes quedan disponibles. La memoria del ejecutor Spark (2 GB) y del driver (1 GB) son restricciones de cómputo distintas del almacenamiento en Snowflake. No se borran datos para añadir dimensiones hipotéticas.

## Reproducción de esta comprobación

Desde psets/pset-02, con `.env` local y Gold construido:

```sh
docker compose build spark-master
docker compose up -d spark-master spark-worker
docker compose --profile herramientas run --rm spark-job
python scripts/verificar_snowflake.py
python scripts/exportar_metricas.py
python scripts/auditar_obt.py
docker compose down
```

Esta revisión ejecuta Spark sobre Gold actualizado; no constituye una nueva ejecución completa Fuente → Kestra ni un entrenamiento de PSet 3. Las evidencias previas de esas etapas se conservan por separado.

## Resultado de la ejecución verificada

Verificación UTC: 2026-11-16T01:37:10.419129+00:00. Spark terminó con código 0 y escribió ambas tablas en Snowflake.

- 87.178 filas y 87.178 claves distintas; 58.628 elegibles; 43 columnas.
- 13 de 13 controles correctos; cero claves nulas y cero diferencias con el conjunto acción-mes cerrado de Gold.
- Meses 201001 a 202610; 620 objetivos nulos (se conservan, no se imputan).
- Contrato estático con PSet 3 verificado: 17 predictores base, objetivo, claves y elegibilidad presentes; PSet 3 deriva dos ratios adicionales.

| Tabla | Filas | Bytes actuales | MiB |
|---|---:|---:|---:|
| GOLD.DIM_ACCION | 1,130 | 75,264 | 0.0718 |
| GOLD.DIM_FECHA | 4,243 | 56,320 | 0.0537 |
| GOLD.DIM_MEMBRESIA_SP500 | 1,179 | 53,760 | 0.0513 |
| GOLD.FCT_MERCADO_DIARIO | 4,243 | 139,264 | 0.1328 |
| GOLD.FCT_PRECIOS_DIARIOS | 1,831,427 | 122,323,456 | 116.6567 |
| OBT.OBT_ACCION_MES | 87,178 | 12,291,072 | 11.7217 |
| OBT.VALIDACION_OBT | 13 | 1,536 | 0.0015 |

Gold total: 116.97 MiB. Sus tres dimensiones: 181 KiB. OBT: 11.72 MiB. Son granos distintos: su tamaño menor no demuestra que desnormalizar reduzca almacenamiento; la OBT resume días a meses. No se observa una razón de tamaño para retirar estas dimensiones pequeñas.

El volumen local mostraba aproximadamente 1,2 TiB libres durante la revisión (`df -h .`); no representa la cuota interna de Docker ni capacidad disponible de Snowflake. Se apagaron los servicios Spark al terminar, preservando volúmenes. Log de ejecución: `corrida/spark_obt_actualizada.log`; evidencia SQL: `corrida/auditoria_obt.json`.
