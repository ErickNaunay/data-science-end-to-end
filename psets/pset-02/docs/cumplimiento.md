# Revisión de cumplimiento — PSet 2

**Requisito 6 revisado:** batch diario para datos; inferencia, propuesta de compra y reporte de desempeño mensuales según PSet 1 corregido en Drive. Reentrenamiento sin cadencia fijada. Se documentan el reconocimiento tardío del mes cerrado, el horizonte calendario y los cambios que justificarían streaming en `temporalidad_batch.md`. Esta revisión es documental; no repite las ejecuciones previas.

**Estado actual del requisito 5:** Spark ejecutado sobre Gold actualizado: 87.178 filas,
43 columnas, 58.628 elegibles y 13/13 controles OK. Verificación independiente en
Snowflake: cero diferencias de claves respecto de Gold. Evidencia: `corrida/auditoria_obt.json`
y `revision_obt.md`. Diagrama C4 y memo actualizados; entorno Spark apagado sin borrar volúmenes.

**Estado actual del requisito 4:** excepción Gold-Silver corregida mediante
GOLD.DIM_MEMBRESIA_SP500. Build actual: 97 correctos, 1 advertencia, 0 errores
(14 modelos, 2 seeds, 82 tests). Las secciones cronológicas anteriores conservan
la evidencia y limitaciones de los estados previos.

Fecha local: 15 de noviembre de 2026, America/Guayaquil.
Guía controlante: `../CD_PSet_2.pdf`. Checkout: rama `proyecto`.
No se realizaron commits, push ni tags.

| Requisito del PDF | Evidencia | Resultado |
|---|---|---|
| Arquitectura Snowflake, Kestra, dbt y Spark | Compose, tres imágenes construidas, diagramas | Implementado y construido |
| Ingesta sin intervención diaria | Schedule L–V 18:30 Nueva York; ventana reciente; subflow | Tarea de ingesta real SUCCESS; ver estados de ejecución |
| Errores, retries y backfill | Flows + historial de Kestra | Backfill histórico SUCCESS y RETRYING observados en el entorno |
| Datos originales en RAW | conteos_por_capa.csv e ingesta_resumen.csv | Consultados en Snowflake |
| Completitud, precisión, consistencia y validez | dq_metricas.csv, 22 métricas | Medidas; precisión mediante plausibilidad, sin fuente oficial de contraste |
| Limpieza con dbt / staging | Bronze y Silver | Ejecutada; decisiones explicadas en memo |
| Gold star schema y grano | Modelos y modelo_dimensional.png | 1.831.427 hechos acción-día |
| source(), ref() y tests de negocio | run_results_gold.json | 97 correctos, 1 advertencia, 0 errores; 82 tests en total |
| OBT con Spark, almacenada en Snowflake | validacion_obt.csv y obt_resumen.csv | 87.178 filas; 43 columnas; 13/13 controles correctos |
| Uso de star schema frente a OBT | Memo, sección 5 | Explicado |
| Batch frente a streaming | Memo, sección 6 | Justificado; no se implementó streaming |
| Documento técnico hasta 6 páginas | PSet2_memo_Gomez_Ehmig.pdf | 6 páginas, métricas reales y limitaciones |
| Repositorio reproducible | README, requisitos, fuentes y scripts | Configuración y pruebas verificadas; credenciales excluidas |

## Evidencia nueva y evidencia histórica

- Se construyeron las imágenes desde este checkout; dbt build y freshness se
  ejecutaron con el proyecto montado desde `proyecto`.
- dbt: 13 modelos + 2 seeds + 75 tests = 90 resultados. La advertencia contiene
  1.615 fechas con menos de 400 miembros con precio. No equivale a 90 tests.
- Frescura: cuatro fuentes PASS. Se verifica timestamp de ingesta, no cobertura.
- Backfill `3Fp8GRgzmNcyj7Xnd5GJf5`: SUCCESS histórico del entorno, no una nueva
  descarga completa ejecutada durante esta revisión. Transformación histórica
  `2067SpW43MXTGuzDQpd8Rm`: SUCCESS. Retry histórico
  `7LTsUVocdrwvwyhQxiiC4H`: FAILED → RETRYING → FAILED.
- Ingesta nueva `47NA7QQfKxmUvkHq60Bw0H`: extracción SUCCESS. Su transformación
  `7dSIMLkpyO1qhLmaQmnups`: dbt SUCCESS; Spark terminó en Docker con salida 0,
  escribió 87.178 filas, 58.628 elegibles y 43 columnas, con 11 controles OK.

## Incidencia de infraestructura

Docker dispone de 7,65 GB. Al levantar MLflow mientras Spark y dos entornos
Kestra estaban activos, `pset2-kestra-1` terminó por OOM (salida 137).
Se detuvo MLflow, se reinició Kestra y se solicitó cancelar la ejecución huérfana.
No se alteraron registros a SUCCESS manualmente. El contenedor de Spark ya
había terminado, pero el orquestador no recibió su cierre.

La nueva ejecución `AI4MasNsvewHdZx50NTmp` se inició para verificar el cierre
normal. Su estado final se conserva en `corrida/kestra_estados.json` y en el
apartado de cierre que se añade al terminar la revisión.

La recuperación usa las operaciones documentadas de [Kestra](https://kestra.io/docs/ui/executions).
Una operación Force Run solo se empleó tras confirmar que el contenedor
anterior ya había finalizado. No ejecutar cargas concurrentes deliberadamente.

## Limitaciones sustantivas

- 20,9363% de símbolos históricos sin precios y 12,7629% de días miembro sin
  precio: no afirmar universo histórico completo ni ausencia de supervivencia.
- 39,485% de fotos con menos de 495 símbolos, mínimo 444.
- Bolsa actual, cambios de ticker parcialmente verificados y ajustes de precios
  retrospectivos limitan la interpretación point-in-time.
- Interpolación con un vecino posterior: auditar disponibilidad antes de usarla
  en entrenamiento. El snapshot actual registra 0% imputado.
- Ventanas Spark basadas en filas no aseguran días consecutivos tras huecos.
- No se verificó una ejecución disparada por el reloj en su horario real; se
  verificó la configuración del trigger y ejecución por API del mismo flow.

## Pruebas complementarias

Tres pruebas unitarias de ingesta pasan: normalización, frontera temporal de
cambio de símbolo e inclusión de una empresa que sale del índice en backfill.
Estas pruebas no sustituyen los controles de negocio de dbt ni los joins de Spark.

### Retiro de registros huérfanos

Tras confirmar salida 0 del contenedor Spark, se archivaron los estados y tareas
de las dos ejecuciones afectadas en `corrida/incidencia_oom.json`. Se retiraron
únicamente esos dos registros de ejecución con la API de Kestra, conservando
logs, métricas y archivos (`deleteLogs=false`, `deleteMetrics=false`,
`deleteStorage=false`), para liberar la concurrencia de futuras ejecuciones.
La ejecución nueva y su subflow se desencolaron; no se alteró su resultado.

## Nueva ejecución aislada solicitada

Se apagaron los entornos starter/Kestra, Structurizr y PSet 3. Se recrearon
los cuatro servicios de PSet 2 desde proyecto conservando volúmenes.
El inventario está en `corrida/docker_aislado.jsonl`.

El análisis del intento anterior encontró SparkOutOfMemoryError al escribir:
el ejecutor de 1 GB por defecto resultó insuficiente. Se configura ahora
`--executor-memory 2g --driver-memory 1g`, un core por ejecutor y un core
total para evitar dos tareas simultáneas compitiendo por el heap.
Este ajuste está tanto en el flow como en la ejecución manual de Compose.
Las interrupciones deliberadas para reiniciar el entorno quedan KILLED;
no se consideran ejecuciones exitosas.

## Cierre de la ejecución aislada

- Ingesta `1LHXSfcznOJ6wf9DocpwSJ`: SUCCESS, incluidas extracción y transformación.
- Subflow `1tqie4tbsFGz6w8rvEsNEf`: SUCCESS, dbt y Spark SUCCESS.
- La ejecución no necesitó Force Run ni cambios manuales de estado.
- Tras el ajuste del ejecutor se completó la escritura en Snowflake.
- Se repitió source freshness: cuatro fuentes PASS.
- Evidencia: `kestra_ejecucion_aislada.json`, `kestra_transformacion_aislada.json`,
  `verificacion_snowflake.json` y CSV actualizados.
- PSet 2 se baja sin borrar volúmenes antes de iniciar PSet 3.

## Contraste del memo con la implementación

Revisión documental sobre el checkout `proyecto` y las evidencias conservadas,
sin volver a ejecutar servicios ni consultar Snowflake. Se contrastaron la guía,
los flows, el SQL de Silver, la configuración dbt, el job Spark y los resultados.

| Afirmación | Evidencia local | Conclusión |
|---|---|---|
| Ingesta y transformación aisladas SUCCESS | corrida/kestra_ejecucion_aislada.json; kestra_transformacion_aislada.json | Confirmada |
| 89 resultados correctos y una advertencia | corrida/run_results.json | 15 modelos/seeds exitosos + 74 tests PASS + 1 test WARN; 1.615 fechas |
| Cuatro fuentes frescas | corrida/sources.json | Cuatro PASS; no implica cobertura completa |
| 87.178 filas, 43 columnas, 58.628 elegibles, 13 controles | corrida/verificacion_snowflake.json | Coincide con el memo |
| Métricas de calidad y conteos Gold | corrida/dq_metricas.csv; conteos_por_capa.csv | Coinciden con las tablas del memo |
| Horario y retries | kestra/flows/ingesta_diaria.yml; backfill_historico.yml | Configurados; prueba por API, sin observar disparo programado |
| Limpieza de precios | dbt/models/silver/slv_precios_acciones.sql | Precisado filtro de nulos/no positivos y máximo menor que mínimo; cierre fuera de rango se marca |
| Membresía histórica | dbt/models/silver/slv_membresia_sp500.sql; dbt/dbt_project.yml | Añadida decisión: 11 huecos unidos, tolerancia de 7 días naturales y riesgo asociado |
| Elegibilidad OBT | spark/jobs/construir_obt.py | Precisado: 200 retornos no nulos en 252 filas y 15 filas mensuales; no necesariamente días observados consecutivos |
| Máximo seis páginas y diagramas | PDF regenerado y seis páginas renderizadas | Cumple extensión; revisión visual sin cortes |

Se aclaró también que las métricas combinan capas previas y posteriores a la
limpieza. Existe diagnóstico de RAW/Bronze, pero no se aporta una ejecución
independiente del diagnóstico anterior a las transformaciones. La precisión
sigue evaluada por plausibilidad, sin contraste con una fuente oficial.
El backfill completo citado es histórico, no una nueva descarga completa de
este checkout. Estas limitaciones impiden presentar la revisión como prueba
de cobertura total o de todos los escenarios operativos.

Se actualizó el generador, el texto fuente y el PDF; no se modificó el pipeline.

## Arquitectura y reproducibilidad

Se verificó la cadena completa a partir del manifest generado con `dbt parse`
(dbt 1.12.7), Compose y el código de ingesta/Spark. Las cuatro entradas Gold
resuelven sus dependencias Silver y RAW/seeds. Los seeds de equivalencias
incluidos en ingesta y dbt son idénticos. El parse termina correctamente con
advertencias de deprecación de la ubicación de `freshness`; no son fallos de datos.

Se corrigió FECHA_CORTE_ENTRENAMIENTO en el entorno de la tarea Spark de Kestra,
que antes dependía del valor por defecto aunque dbt recibiera otro corte.
La corrida previa usó el valor por defecto; no se repitió aquí la carga completa.

Structurizr validado y regenerado: driver, maestro y trabajador separados,
tareas efímeras y SaaS identificados. DOT explicita cada etapa dbt y CALIDAD
transversal. Memo: seis páginas de cuerpo + tres anexos (permitidos por la guía),
con flujo completo y ambas vistas C4, sin sustituir el modelo dimensional.
La reconstrucción de una cuenta vacía y la igualdad exacta de snapshots no están
certificadas; las fuentes son mutables y las dependencias no están bloqueadas
por completo. Evidencia: corrida/verificacion_arquitectura.json.

Prueba adicional: YAML del flow válido, mismo secreto de corte en ambas tareas y
lectura de corte alternativo 2022-12-31 por Spark (MES_CORTE=202212), sin iniciar
sesión Spark ni acceder a Snowflake. Los contenedores de validación fueron efímeros.

## Explicación de trigger, errores y backfill

La página 2 del memo contiene tres apartados explícitos contrastados con los
flows y extraer_cargar.py: cron y zona horaria, recuperación de horarios perdidos,
retries de Python/Kestra/dbt/Spark, propagación de fallos y backfill por año.
Se aclara que el cron no excluye feriados, SIN_DATOS no implica fallo y el retry
del backfill repite toda la tarea; la reanudación por año requiere anio_desde.
La edición es documental; conserva seis páginas de cuerpo y tres anexos.

## Calidad previa a limpieza por columna

Se ejecutó scripts/diagnosticar_calidad.py sobre Snowflake: 21 tablas/230 columnas.
Las cuatro tablas RAW tienen perfil completo de nulos/vacíos; reglas aplicables
de dominio, contradicciones, volumen cero, revisiones de precios, sesiones
ausentes e IQR por acción. Se incluyen SQL y query IDs en docs/calidad/.
Los datos de capas posteriores están separados; no sustituyen el diagnóstico RAW.

Se corrigió en dbt la conversión de ES_ETF/ES_PRUEBA desconocidos a false:
Bronze ahora conserva NULL y Silver conserva el listado salvo prueba conocida.
Se reconstruyeron los 13 modelos y 2 seeds: 75 tests, PASS=89 WARN=1 ERROR=0.
Gold conserva 1.831.427 hechos diarios; OBT no se recalculó en esta revisión
de calidad, conserva la ejecución Spark previa. Su estructura y entradas Gold
no cambian por esta corrección de flags del listado. No se afirma nueva corrida
completa de Kestra/Spark.

El diagnóstico final confirmó 100% de nulos en ambos flags RAW y Bronze,
y tasas entre 0 y 100 para las 230 columnas. Las pruebas de precisión son
plausibilidad; no se cuenta con cotizaciones oficiales independientes. Los
porcentajes sin regla defendible se etiquetan No evaluado, nunca cero.

La página 3 del memo presenta ahora evidencia RAW con denominadores explícitos;
las decisiones detalladas, fuentes complementarias y cada columna están en
docs/calidad/README.md y decisiones_por_columna.csv. Se mantienen seis páginas
de cuerpo y tres anexos.

## Auditoría de capas y estrella

La revisión del SQL actual y consultas nuevas en Snowflake se conserva en
corrida/auditoria_capas_modelo.json y .sql. No hay ciclos ni dependencias
inversas de transformación. Gold contiene dos hechos, no uno: precios
acción-fecha y referentes por fecha, compartiendo DIM_FECHA.

No hay duplicados, claves nulas/huérfanas, solapes de membresía ni pérdida
de filas Silver-Gold o en los joins dimensionales. Existe una excepción de
consumo: periodo_sp500_key apunta a SILVER.SLV_MEMBRESIA_SP500. El núcleo
estrella es válido, pero no es un mart completamente autocontenido. Se
documentó la alternativa de una dimensión de membresía Gold, sin implementarla
ni declarar una tabla inexistente. PK/FK del diagrama son lógicas, no DDL.

La página 4 y el diagrama reflejan este matiz. El detalle de cada capa, grano,
dimensiones, aditividad y limitaciones está en revision_capas_modelo.md.

## Cierre del requisito 4: Gold autocontenido

Se publicó DIM_MEMBRESIA_SP500 desde Silver y se cambiaron el join del hecho
y su prueba relationships para usar Gold. Se añadieron not_null/unique de
la dimensión y dos controles de negocio: coherencia de membresía del hecho
y validez/no solape de intervalos. El grano acción-fecha no cambió.

El build real concluyó PASS=97 WARN=1 ERROR=0 TOTAL=98: 14 modelos, 2 seeds,
82 tests. La advertencia permanece en cobertura (1.615 fechas). Evidencia
nueva: corrida/run_results_gold.json y auditoria_capas_modelo.json. El perfil
actual contiene 22 tablas y 236 columnas. Diagrama, C4 y memo actualizados.
