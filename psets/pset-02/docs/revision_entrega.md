# Revisión desde «Documento técnico» hasta la rúbrica

Guía: `../CD_PSet_2.pdf`, páginas 3 a 5, leídas y revisadas visualmente. Checkout: rama `proyecto`. Esta revisión comprueba documentación, configuración y empaquetado; no es una nueva ejecución end-to-end ni asigna una calificación.

## Documento técnico

Archivo: `PSet2_memo_Gomez_Ehmig.pdf`. Cumple el patrón `PSet2_memo_<apellido_1>_<apellido_2>.pdf`. Contiene **seis páginas técnicas y tres anexos**, nueve páginas físicas. El límite de seis excluye expresamente los anexos. No se añade portada separada. Describe la implementación y sus decisiones, sin dedicar secciones a definiciones teóricas de herramientas.

| Sección exigida | Ubicación en el memo | Evidencia / contenido |
|---|---|---|
| 1. Arquitectura | Página 1; anexos A–C | Flujo Fuente → Kestra → RAW → dbt → Bronze → Silver → Gold → Spark → OBT; Compose, Snowflake SaaS y diagramas Structurizr |
| 2. Ingesta | Página 2 | Fuentes y granos, carga append-only, cron y zona, ventana reciente, retries y backfill; diferencia entre ejecución exitosa y cobertura |
| 3. Data Quality | Página 3 | Tabla problema/evidencia/acción/justificación, porcentajes RAW y decisiones; inventario completo en `calidad/` |
| 4. Transformaciones y modelado | Página 4 | Bronze/staging, Silver, dos hechos y tres dimensiones Gold; diagrama, grano y tests de negocio |
| 5. Spark y OBT | Página 5 | Entradas Gold, acción-mes, 43 columnas, 13 controles, escritura y uso estrella/OBT |
| 6. Batch vs. streaming | Página 6 | Datos diarios y decisión mensual; SLA no establecido, condiciones futuras para streaming sin implementarlo |
| 7. Limitaciones | Página 6 y notas en secciones 2–5 | Cobertura, atributos actuales, revisiones, interpolación, cierre mensual, atomicidad y memoria |

Las limitaciones se mantienen visibles: 1.615 fechas generan advertencia de cobertura; los checks de precisión son plausibilidad, no una validación con proveedor independiente. No se afirma que el dataset garantice información point-in-time. La futura inferencia y el reporte de compra no se presentan como servicios productivos ya implementados.

## Repositorio y reproducción

La guía muestra `pset_2/` con `docker-compose.yml`, `.env.example`, `README.md`, `kestra/`, `dbt/`, `spark/` y `docs/`. El checkout conserva `psets/pset-02/` para respetar la organización del curso; el ZIP exporta exactamente la raíz `pset_2/`. Las carpetas adicionales `scripts/` y `pruebas_locales/` son auxiliares.

El README cubre variables, generación de llaves, setup SQL, secretos, build, arranque, publicación de flows, backfill, dbt/Spark manuales y verificación. Los seeds necesarios están incluidos; no se requiere copiar análisis de PSet 3 ni de draft para ejecutar el pipeline.

Se eliminaron contraseñas predeterminadas de `.env.example`, Compose, el publicador de flows y el ejemplo curl. Las claves deben definirse localmente. `.env`, `.env_encoded`, `secrets/` y llaves privadas se excluyen del ZIP y de Git. El cambio no rota credenciales del entorno existente. La configuración Compose se validó sin imprimir su contenido expandido ni iniciar servicios.

**Cierre de versionado solicitado por el usuario:** esta entrega se incorpora a Git en la rama `proyecto` mediante el commit de consolidación de PSet 2 y preparación de PSet 3. Verificar su identificador con `git log -1 --oneline`. La observación anterior sobre archivos no rastreados describía el estado previo al commit. La publicación remota sigue pendiente: no se hizo push ni tag. La guía recibida no prescribe un tag concreto.

## Entregables y evidencia existente

| Entregable | Archivo / evidencia | Estado y alcance |
|---|---|---|
| Repositorio | Código, README y `../entregables/PSet2_repositorio_Gomez_Ehmig.zip` | Paquete local preparado; publicación remota pendiente |
| Documento | `PSet2_memo_Gomez_Ehmig.pdf` | 6 páginas técnicas + 3 anexos |
| Arquitectura | `arquitectura.dot/png/svg`, `structurizr/workspace.dsl`, `structurizr/export/` | Fuentes editables y diagramas incluidos |
| Snowflake | `corrida/conteos_por_capa.csv`, `corrida/auditoria_capas_modelo.json`, `corrida/auditoria_obt.json` | RAW, Bronze, Silver, Gold y OBT verificados en ejecuciones previas |
| Kestra | `corrida/kestra_ejecucion_aislada.json`, memo sección 2 y `cumplimiento.md` | Corrida aislada SUCCESS; backfill y retry tienen evidencia histórica, no se repitieron hoy |
| dbt | `corrida/run_results_gold.json` | 14 modelos, 2 seeds, 82 tests: 81 tests pass y 1 warn; 97 resultados correctos y 0 errores en total |
| Spark | `corrida/spark_obt_actualizada.log`, `corrida/auditoria_obt.json` | 87.178 filas, 43 columnas, 58.628 elegibles; 13/13 controles; cero diferencias de claves con Gold |

No confundir la fecha de una revisión documental con la fecha de las pruebas. Cada JSON conserva su timestamp; las evidencias históricas y las últimas verificaciones se distinguen en `cumplimiento.md`.

## Rúbrica: trazabilidad, no calificación

`../rubrica.md` y `../README_curso.md` conservan la variante original del repositorio (cuatro criterios, DuckDB y limpieza Python). No son la rúbrica controlante de esta entrega. Se aplica la guía `CD_PSet_2.pdf` indicada por el usuario, con siete criterios ponderados, Snowflake y limpieza dbt; las diferencias ya están registradas en `../disclaimer.txt`.

| Criterio oficial | Peso | Evidencia principal |
|---|---:|---|
| Kestra, ingesta y orquestación para Raw | 15% | Memo 2; flows y bitácora RAW |
| Calidad y limpieza de datos | 20% | Memo 3; diagnóstico RAW y políticas por columna |
| dbt y arquitectura Bronze/Silver/Gold | 15% | Memo 4; DAG `source()`/`ref()` y auditoría de capas |
| Star schema | 15% | Diagrama dimensional; hechos, dimensiones, grano y tests |
| Spark y OBT | 15% | Memo 5; código Spark y verificación Snowflake |
| Infraestructura y reproducibilidad | 10% | Compose, README, variables, scripts y ZIP; publicación remota pendiente |
| Documento técnico y decisiones de arquitectura | 10% | Memo de seis páginas, anexos y decisiones justificadas |
| **Total** | **100%** | La nota corresponde al evaluador |

## Cierre de esta revisión

Se verifican páginas y secciones, renderizado del memo, sintaxis de scripts modificados, configuración Compose, estructura del ZIP, hashes de su manifiesto y exclusión de credenciales locales. No se vuelve a levantar Docker ni se ejecutan cargas en Snowflake por cambios de documentación y empaquetado.
