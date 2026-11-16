# Migración draft → proyecto — 2026-11-15

Referencia: `../CD_PSet_2.pdf`. Se transfieren Compose, Kestra, dbt (modelos,
seeds y tests), Spark, diagramas, utilitarios y pruebas locales. El README
original del curso se conserva en `README_curso.md` y la rúbrica no cambia.
El origen y su plan.txt con cambios locales se conservan sin modificaciones.

Se excluyen analisis/ (reservado para PSet 3), credenciales, llaves, entornos,
cachés, bases locales, artefactos dbt y métricas docs/corrida/ del borrador.
Se excluyen pyproject.toml y uv.lock porque mezclan dependencias del análisis
con el pipeline. requirements.txt declara dependencias locales del PSet 2;
no es una exportación del lock ni garantiza el mismo entorno del borrador.
Los SHA-256 originales figuran en migracion_origen.sha256; README, docs/README,
Dockerfile de Kestra, dbt_project y Compose tienen ajustes documentales.

## Correspondencia con el PDF y siguientes verificaciones

| Requisito | Archivos | Pendiente operativo |
|---|---|---|
| Arquitectura | Compose y diagramas docs/ | Construir y levantar contenedores |
| Ingesta Raw | kestra/ | Correr backfill, diaria y retries |
| Calidad y limpieza | dbt Bronze (staging), Silver, CALIDAD | dbt build y métricas |
| Star schema | Gold y diagrama dimensional | Validar grano y relaciones |
| OBT | spark/jobs/construir_obt.py | Ejecutar en Snowflake y revisar controles |
| Batch vs streaming | README | Incorporar justificación al memo |
| Memo hasta 6 páginas | Diagramas disponibles | Elaborar con evidencia real |

Orden: configurar entorno local según README; construir infraestructura;
preparar Snowflake; cargar flows; ejecutar backfill, dbt y Spark; exportar
métricas a docs/corrida/; elaborar memo. No se transfieren resultados de draft
como evidencia de ejecución en proyecto. Quedan pendientes las pruebas pytest
propuestas en J9 del plan y la comprobación de punta a punta de J10.

No se ejecutaron cargas ni cambios en Snowflake. No se hicieron commits,
push ni tags. proyecto estaba un commit detrás de la referencia local
origin/proyecto (solo afecta PSet 1); no se sincronizó ni consultó el remoto.

## Verificación realizada

- PDF idéntico al origen y manifiesto SHA-256 de los 81 archivos transferidos.
- Sintaxis Python (AST) y shell (`bash -n`) válida.
- `docker compose --profile herramientas config --quiet` válido con .env.example.
- `git diff --check` sin errores.
- Sin archivos de credenciales, llaves privadas ni bases locales transferidos.

Estas comprobaciones no sustituyen la ejecución de Kestra, dbt y Spark.

## Revisión posterior

La verificación operativa inicial pendiente se abordó el 15 de noviembre de
2026. Consultar `cumplimiento.md` y `corrida/` para resultados actuales; los
apartados anteriores describen únicamente el momento de la copia inicial.
