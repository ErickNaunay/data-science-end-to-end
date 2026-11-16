// Modelo C4 del pipeline del PSet 2 (Structurizr DSL).
// Ver docs/README.md: ver_diagramas.sh abre la UI (Structurizr Lite) y
// exportar_diagramas.sh genera Mermaid/PlantUML con el CLI.
workspace "Pipeline de datos del portafolio de inversiones" "PSet 2 · MSDS 6003 · Allan Paul Gómez Ehmig (00351916)" {

    model {
        asesor = person "Asesor de inversiones" "Usuario de la herramienta: lanza el backfill, revisa las ejecuciones y consume la OBT para la decisión mensual."

        yahoo = softwareSystem "Yahoo Finance" "Precios diarios OHLCV y cierre ajustado (API no oficial, vía yfinance): acciones, ^GSPC, ^NYA, ^IRX." "Externo"
        github = softwareSystem "GitHub (fuentes de referencia)" "Composición histórica del S&P 500 (chinobing) y listados de bolsa (rreichel3)." "Externo"

        pipeline = softwareSystem "Pipeline de datos del portafolio" "ELT reproducible: Fuente → Kestra → Raw → dbt → Bronze → dbt → Silver → dbt → Gold → Spark → OBT." {
            kestra = container "Kestra" "Orquestación: flows ingesta_diaria (L–V 18:30 NY, retries, recuperación), backfill_historico (por año) y transformar." "Kestra 2.0 · Docker · UI :8090"
            postgres = container "Postgres" "Estado interno de Kestra (flows, ejecuciones, colas)." "PostgreSQL 18 · Docker" "BaseDatos"
            ingesta = container "Tarea de ingesta" "extraer_cargar.py: descarga precios, composición y listados; traduce símbolos con equivalencias_tickers y carga a RAW (append-only, con lote)." "Python 3.11 · imagen pset2-ingesta"
            dbt = container "Tarea dbt" "dbt build: Bronze (staging: tipos, deduplicación), Silver (calendario NYSE, imputación de huecos cortos, retornos, membresía), Gold (dos hechos y tres dimensiones, incluida membresía histórica) y CALIDAD; tests de integridad y negocio." "dbt Core + dbt-snowflake · imagen pset2-dbt"
            spark = container "Driver Spark / tarea OBT" "construir_obt.py: lee Gold, construye acción por mes, verifica 13 controles y escribe OBT. Ejecutor 2 GB; driver 1 GB; un core total." "Spark 3.5.3 · pset2-spark · tarea efímera"
            master = container "spark-master" "Coordina los recursos del clúster; servicio persistente de Compose." "Spark 3.5.3 · RPC :7077 · UI :8081"
            worker = container "spark-worker" "Ejecuta las tareas distribuidas; ofrece 2 GB al ejecutor." "Spark 3.5.3 · pset2-spark"
            snowflake = container "Snowflake · base PORTAFOLIO" "Esquemas RAW, BRONZE, SILVER, GOLD, OBT y CALIDAD. Bodega PSET2_WH (XSMALL, autosuspensión)." "SaaS" "BaseDatos"
        }

        asesor -> kestra "Lanza el backfill y supervisa ejecuciones" "UI en localhost:8090"
        kestra -> postgres "Guarda su estado en"
        kestra -> ingesta "Ejecuta como contenedor de tarea (trigger L–V 18:30 NY; reintentos exponenciales)"
        kestra -> dbt "Ejecuta al terminar la ingesta (subflow transformar)"
        kestra -> spark "Ejecuta spark-submit tras dbt"
        ingesta -> yahoo "Descarga OHLCV diario (yfinance, por lotes con reintentos)"
        ingesta -> github "Descarga composición histórica y listados de bolsa"
        ingesta -> snowflake "Carga RAW con write_pandas (append-only + bitácora)"
        dbt -> snowflake "Transforma RAW → BRONZE → SILVER → GOLD y calcula CALIDAD.DQ_METRICAS"
        spark -> master "Solicita recursos del clúster" "spark://spark-master:7077"
        master -> worker "Asigna ejecutores"
        spark -> worker "Coordina tareas y resultados"
        worker -> snowflake "Lee y escribe particiones mediante el conector Snowflake"
        spark -> snowflake "Lee GOLD y escribe OBT.OBT_ACCION_MES y VALIDACION_OBT"
        asesor -> snowflake "Consulta la OBT y las métricas de calidad" "Snowsight"
    }

    views {
        systemContext pipeline "contexto" "Nivel 1: el pipeline, su usuario y las fuentes externas." {
            include *
            autoLayout lr
        }

        container pipeline "contenedores" "Nivel 2: servicios persistentes, tareas efímeras y Snowflake SaaS." {
            include *
            autoLayout lr
        }

        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Externo" {
                background #999999
                color #ffffff
            }
            element "BaseDatos" {
                shape Cylinder
                background #2a6a4f
                color #ffffff
            }
        }
    }
}
