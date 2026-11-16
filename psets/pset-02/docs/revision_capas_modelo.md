# Revisión de capas, esquema dimensional y granularidad — PSet 2

La revisión combina el SQL actual con consultas de solo lectura a Snowflake. Evidencia reproducible: `scripts/auditar_capas_modelo.py`, `corrida/auditoria_capas_modelo.json` y sus consultas SQL con query IDs.

## Dictamen

- No se encontraron ciclos ni dependencias de transformación que retrocedan desde Gold hacia Silver/Bronze o desde Silver hacia Bronze. Gold se construye con Silver y dimensiones Gold; Bronze parte de RAW/seeds; Silver parte de Bronze/Silver/seeds.
- **Gold tiene dos hechos**, no uno. `FCT_PRECIOS_DIARIOS` forma el núcleo estrella con `DIM_ACCION` y `DIM_FECHA`; `FCT_MERCADO_DIARIO` comparte `DIM_FECHA`. El conjunto puede describirse como dos estrellas con dimensión conformada o una constelación de hechos.
- **Excepción corregida:** `FCT_PRECIOS_DIARIOS.periodo_sp500_key` ahora referencia `GOLD.DIM_MEMBRESIA_SP500`. La dimensión se construye con `ref()` desde Silver; la consulta del star schema ya no necesita acceder a Silver.
- Tener un solo hecho no exime de modelar dimensiones. Una estrella puede tener precisamente un hecho rodeado por sus dimensiones. Además, la guía del PSet 2 exige Gold con star schema.
- Las claves son **lógicas**: no hay restricciones PK/FK declaradas en `information_schema.table_constraints` de Gold. La integridad se verifica con dbt y consultas; no se atribuye protección física a esos rótulos del diagrama.

Referencia conceptual: [Kimball: Star Schemas](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/star-schema-olap-cube/) y [dimensiones conformadas](https://www.kimballgroup.com/1997/08/a-dimensional-modeling-manifesto/).

## Qué contiene cada capa y qué hace

| Capa | Objetos y grano | Transformaciones / responsabilidad |
|---|---|---|
| RAW | `PRECIOS_DIARIOS`: símbolo-fecha por carga; `COMPOSICION_SP500`: foto con lista de símbolos por carga; `LISTADOS_BOLSA`: símbolo-bolsa por carga; `INGESTA_LOG`: solicitud por símbolo-lote | Python extrae, convierte fechas, selecciona campos, asigna fuente/lote/timestamp y carga append-only. No imputa precios ni calcula features. No es una copia byte a byte de los archivos originales. |
| Bronze / staging | Tres vistas `BRZ_PRECIOS_DIARIOS`, `BRZ_COMPOSICION_SP500`, `BRZ_LISTADOS_BOLSA`; dos tablas seed `CALENDARIO_NYSE`, `EQUIVALENCIAS_TICKERS` | dbt tipa/renombra, normaliza símbolos, deduplica, explota listas, aplica equivalencias temporales y filtra instrumentos fuera del alcance. Flags ETF/prueba desconocidos permanecen NULL. Las vistas son una materialización válida; no son snapshots independientes. |
| Silver | Cinco tablas: `SLV_CALENDARIO_NYSE`, `SLV_PRECIOS_ACCIONES`, `SLV_MERCADO_DIARIO`, `SLV_MEMBRESIA_SP500`, `SLV_ACCIONES` | dbt integra referencias, establece calendario/grillas, limpia precios inválidos, interpola huecos cortos, marca calidad, deriva retornos y membresías, y consolida atributos de acciones. No hay entrenamiento de modelos. |
| Gold | Cinco tablas: tres dimensiones y dos hechos | dbt crea claves analíticas, atributos de calendario y medidas de consulta. Los hechos se mantienen diarios; Gold no mezcla registros diarios y mensuales en la misma tabla. |
| CALIDAD | `DQ_METRICAS` | Capa transversal de observación: puede leer RAW, Bronze, Silver y Gold. No es un eslabón obligatorio entre Silver y Gold ni una fuente de los hechos. |
| OBT | `OBT_ACCION_MES` y `VALIDACION_OBT` | Spark consume cuatro tablas Gold (los dos hechos, DIM_ACCION y DIM_FECHA), agrega ventanas/resúmenes mensuales y crea objetivos/elegibilidad. El grano mensual es distinto y se mantiene separado del hecho diario. |

Los seeds son referencias versionadas, no tablas derivadas de Gold. Que Bronze los use no implica una dependencia inversa. La traducción de símbolos y el filtrado de instrumentos en Bronze son decisiones de staging relativamente amplias; no violan la guía, pero deben documentarse para no presentar Bronze como una copia literal de RAW.

## Transformaciones por tabla Silver

| Tabla | Grano | Transformaciones |
|---|---|---|
| `SLV_CALENDARIO_NYSE` | Día bursátil | Seed NYSE acotado desde 2010 hasta la última fecha de precios; orden bursátil y media jornada. |
| `SLV_PRECIOS_ACCIONES` | Símbolo normalizado y sesión conservada | Descarta observaciones OHLC inválidas, crea grilla durante la vida observada, interpola log-cierre/log-apertura ajustados hasta cinco sesiones, excluye huecos largos, calcula retornos y banderas. No imputa volumen ni OHLC originales. |
| `SLV_MERCADO_DIARIO` | Día bursátil | Pivota ^GSPC/^NYA/^IRX, calcula retornos, rellena ^IRX hacia adelante, deriva tasa diaria aproximada. |
| `SLV_MEMBRESIA_SP500` | Intervalo de membresía por símbolo | Normaliza continuidad de fotos, crea fecha_inicio/fecha_fin, une huecos hasta siete días y genera periodo_key; vigente tiene fecha_fin nula. |
| `SLV_ACCIONES` | Símbolo normalizado | Une universo de membresías y precios con listado actual; resume fechas, períodos y cobertura. Conserva atributos desconocidos. |

## Hechos y dimensiones de Gold

| Objeto | Grano de negocio | Clave lógica | Filas verificadas |
|---|---|---|---:|
| `DIM_ACCION` | Símbolo normalizado que representa una acción del universo | `accion_key = MD5(ticker)`; ticker también único | 1.130 |
| `DIM_FECHA` | Día bursátil NYSE del período cargado | `fecha_key = AAAAMMDD`; fecha única | 4.243 |
| `DIM_MEMBRESIA_SP500` | Intervalo de membresía por símbolo | `periodo_key`; ticker no es único entre intervalos | 1.179 |
| `FCT_PRECIOS_DIARIOS` | Observación de una acción/símbolo en una sesión conservada, real o imputada | `(accion_key, fecha_key)` | 1.831.427 |
| `FCT_MERCADO_DIARIO` | Observación conjunta de los referentes de mercado en una sesión | `fecha_key` | 4.243 |

### Hecho principal: precios diarios

- Medidas: apertura, máximo, mínimo, cierre, cierre/apertura ajustados, volumen y retornos log diarios/intradía/nocturnos.
- Contexto: dimensiones acción, fecha y membresía histórica, todas en Gold. Los indicadores `en_sp500`, `imputado`, `es_retorno_extremo`, etc. describen la observación; no alteran su grano.
- `periodo_sp500_key` puede ser NULL fuera de membresía. Hay **44.673 filas fuera del S&P 500** y no son huérfanas: el hecho conserva historia para ventanas; la elegibilidad se decide después.
- Fecha mínima/máxima: **2010-01-04 a 2026-11-13**. No es una grilla densa de toda acción por todo día: no incluye acciones sin precios ni sesiones excluidas por huecos largos. En este snapshot hay cero filas imputadas.
- La acción se identifica por símbolo normalizado, no por un identificador legal permanente. Equivalencias y reutilización de ticker limitan la equivalencia “símbolo = empresa”.

### Hecho de mercado

Contiene cierres/retornos de ^GSPC y ^NYA, tasa ^IRX, marca de relleno y tasa libre de riesgo aproximada. Los referentes son columnas de una observación por fecha, no filas con mezcla de granularidades. No requiere `DIM_ACCION` porque un índice no es una acción del universo. Una dimensión adicional de referente sería útil si se decide remodelar a `(fecha, referente)`; no es necesaria para este diseño fijo.

### Dimensiones

`DIM_ACCION` contiene nombre, bolsa/código actuales y resúmenes de cobertura/membresía. Es una dimensión reconstruida con estado actual, **no SCD tipo 2**. Hay **439 de 1.130 símbolos con bolsa desconocida**. No representa la bolsa histórica y atributos como `sigue_en_sp500` o `ultima_fecha_precio` no son predictores point-in-time válidos sin tratamiento adicional.

`DIM_FECHA` incluye año, trimestre, mes, orden/día bursátil, cierre de mes y conjunto de entrenamiento/prueba. `mes_cerrado` se basa en que el mes sea anterior al máximo mes cargado, no directamente en la fecha actual: en un backfill que termine en un mes histórico completo, ese último mes seguirá excluido como cierre. Es una limitación de la regla, no una violación de grano. `conjunto` es configuración analítica, no un atributo intrínseco del calendario.

## Controles ejecutados

| Control | Resultado |
|---|---|
| Claves únicas y no nulas de las tres dimensiones | 0 duplicadas, 0 nulas |
| Unicidad acción-fecha en precios | 1.831.427 filas = 1.831.427 claves |
| Unicidad fecha en mercado | 4.243 filas = 4.243 claves |
| FK de acción/fecha sin dimensión | 0 huérfanas |
| periodo_sp500_key no nulo sin intervalo | 0 huérfanas |
| Período incompatible con ticker o fecha del hecho | 0 |
| Indicador en_sp500 incompatible con periodo_key | 0 |
| Intervalos de membresía superpuestos por ticker | 0 |
| Join de precios con dimensiones e intervalo | Conserva las 1.831.427 filas |
| Join mercado-fecha | Conserva las 4.243 filas |
| Filas Silver → Gold de ambos hechos | Sin pérdida ni incremento |
| Join de ambos hechos por fecha | 1.831.427 filas; mercado se repite por acción |

El último join es cardinalmente válido N:1, pero **no autoriza sumar retornos/tasas de mercado por acción**: se multiplicaría el valor por el número de acciones. Para comparar agregados, resumir cada hecho al grano común y unir después.

## Aditividad de las medidas

- Precios, tasas y volatilidades no deben sumarse entre acciones ni a través del tiempo.
- Retornos log pueden sumarse a través de períodos consecutivos de la misma serie bajo sus supuestos; no entre acciones para obtener el retorno de un portafolio.
- Volumen puede sumarse a lo largo del tiempo para el mismo instrumento; entre instrumentos son unidades distintas y no mide valor económico agregado. Usar una medida monetaria definida si ese es el objetivo.
- Banderas de calidad pueden contarse bajo un denominador claro, no interpretarse como medidas financieras.

## Implementación del requisito 4 y pruebas de negocio

La dimensión `GOLD.DIM_MEMBRESIA_SP500` ya está implementada y materializada, con 1.179 intervalos. `fct_precios_diarios` la utiliza mediante `ref('dim_membresia_sp500')`; su test `relationships` también referencia esa dimensión. No se cambia el grano del hecho ni la definición de los intervalos de Silver. El hecho conserva 1.831.427 filas.

| Regla | Prueba dbt | Motivo de negocio |
|---|---|---|
| PK de dimensiones no nulas y únicas | not_null / unique | Un join muchos-a-uno no puede multiplicar precios |
| Una fila por acción-fecha | combinacion_unica | Evitar duplicar observaciones y retornos |
| FKs del hecho a dimensiones Gold | relationships | Evitar precios sin acción, fecha o membresía identificable |
| Membresía de la misma acción y válida para la fecha | assert_membresia_gold_coherente | Una FK existente puede corresponder a otra acción/período |
| Vigencia abierta coherente, fechas ordenadas, sin solapes | assert_intervalos_gold_validos | No asignar dos membresías al mismo día ni fechas imposibles |
| Coherencia OHLC | assert_ohlc_coherente | Evitar medidas incompatibles del mismo día |
| Imputación solo en huecos cortos | assert_imputacion_solo_huecos_cortos | No inventar historias durante ausencias prolongadas |
| Cobertura del universo histórico | assert_cobertura_sp500_por_dia | Visibilizar falta de miembros con precios, aun si el esquema es íntegro |

`fecha_fin` y `periodo_sp500_key` admiten NULL cuando tienen significado: intervalo vigente y observación fuera del índice, respectivamente. No se agrega not_null indiscriminadamente. `ticker` en la dimensión de membresía tampoco es único: puede tener varios intervalos.

Resultado real: **14 modelos + 2 seeds + 82 tests = 98 resultados; 97 correctos, 1 advertencia, 0 errores**. La advertencia conserva las 1.615 fechas con cobertura inferior a 400 miembros. No se ocultó ni se redujo la severidad para aprobar la entrega.

Evidencia del nuevo build: `corrida/run_results_gold.json`. Auditoría de relaciones y grano: `corrida/auditoria_capas_modelo.json`. La construcción dbt sí escribió las tablas Gold; el script de auditoría posterior solo hizo SELECT. La revisión posterior del requisito 5 ejecuta Spark sobre este Gold y documenta su resultado en `revision_obt.md` y `corrida/auditoria_obt.json`.
