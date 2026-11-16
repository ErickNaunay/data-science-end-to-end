-- objetos; query_id=01c87072-0004-e92b-0000-7b7d0019dc16
SELECT table_schema,table_name,table_type FROM information_schema.tables WHERE table_schema IN ('RAW','BRONZE','SILVER','GOLD') ORDER BY 1,2;

-- DIM_ACCION; query_id=01c87072-0004-e92c-0000-7b7d001a363a
SELECT COUNT(*) filas, COUNT(DISTINCT accion_key) claves_unicas,COUNT_IF(accion_key IS NULL) claves_nulas FROM GOLD.DIM_ACCION;

-- DIM_FECHA; query_id=01c87072-0004-e93d-0000-7b7d001a4022
SELECT COUNT(*) filas, COUNT(DISTINCT fecha_key) claves_unicas,COUNT_IF(fecha_key IS NULL) claves_nulas FROM GOLD.DIM_FECHA;

-- DIM_MEMBRESIA_SP500; query_id=01c87072-0004-e937-0000-7b7d0019fc3e
SELECT COUNT(*) filas, COUNT(DISTINCT periodo_key) claves_unicas,COUNT_IF(periodo_key IS NULL) claves_nulas FROM GOLD.DIM_MEMBRESIA_SP500;

-- FCT_PRECIOS_DIARIOS; query_id=01c87072-0004-e92b-0000-7b7d0019dc1a
SELECT COUNT(*) filas, COUNT(DISTINCT accion_key,fecha_key) claves_unicas,COUNT_IF(accion_key IS NULL OR fecha_key IS NULL) claves_nulas FROM GOLD.FCT_PRECIOS_DIARIOS;

-- FCT_MERCADO_DIARIO; query_id=01c87072-0004-e92c-0000-7b7d001a363e
SELECT COUNT(*) filas, COUNT(DISTINCT fecha_key) claves_unicas,COUNT_IF(fecha_key IS NULL) claves_nulas FROM GOLD.FCT_MERCADO_DIARIO;

-- joins_precios; query_id=01c87072-0004-e91a-0000-7b7d001a261e
SELECT COUNT(*) filas_join,COUNT_IF(a.accion_key IS NULL) accion_huerfana,COUNT_IF(d.fecha_key IS NULL) fecha_huerfana,COUNT_IF(p.periodo_sp500_key IS NOT NULL AND m.periodo_key IS NULL) periodo_huerfano,COUNT_IF(p.en_sp500<>(p.periodo_sp500_key IS NOT NULL)) membresia_inconsistente,COUNT_IF(m.periodo_key IS NOT NULL AND (m.ticker<>a.ticker OR d.fecha<m.fecha_inicio OR d.fecha>COALESCE(m.fecha_fin,'9999-12-31'::DATE))) periodo_fuera_intervalo,COUNT_IF(NOT p.en_sp500) filas_fuera_sp500,COUNT_IF(p.imputado) filas_imputadas,MIN(d.fecha) desde,MAX(d.fecha) hasta FROM GOLD.FCT_PRECIOS_DIARIOS p LEFT JOIN GOLD.DIM_ACCION a ON p.accion_key=a.accion_key LEFT JOIN GOLD.DIM_FECHA d ON p.fecha_key=d.fecha_key LEFT JOIN GOLD.DIM_MEMBRESIA_SP500 m ON p.periodo_sp500_key=m.periodo_key;

-- join_mercado; query_id=01c87072-0004-e92c-0000-7b7d001a3642
SELECT COUNT(*) filas_join,COUNT_IF(d.fecha_key IS NULL) fecha_huerfana FROM GOLD.FCT_MERCADO_DIARIO m LEFT JOIN GOLD.DIM_FECHA d ON m.fecha_key=d.fecha_key;

-- conservacion_silver; query_id=01c87072-0004-e92b-0000-7b7d0019dc1e
SELECT (SELECT COUNT(*) FROM SILVER.SLV_PRECIOS_ACCIONES) precios_silver,(SELECT COUNT(*) FROM GOLD.FCT_PRECIOS_DIARIOS) precios_gold,(SELECT COUNT(*) FROM SILVER.SLV_MERCADO_DIARIO) mercado_silver,(SELECT COUNT(*) FROM GOLD.FCT_MERCADO_DIARIO) mercado_gold;

-- solapes_membresia; query_id=01c87072-0004-e93d-0000-7b7d001a4026
SELECT COUNT(*) pares_solapados FROM GOLD.DIM_MEMBRESIA_SP500 a JOIN GOLD.DIM_MEMBRESIA_SP500 b ON a.ticker=b.ticker AND a.periodo_key<b.periodo_key AND a.fecha_inicio<=COALESCE(b.fecha_fin,'9999-12-31'::DATE) AND b.fecha_inicio<=COALESCE(a.fecha_fin,'9999-12-31'::DATE);

-- restricciones_gold; query_id=01c87072-0004-e91a-0000-7b7d001a2622
SELECT table_name,constraint_type FROM information_schema.table_constraints WHERE table_schema='GOLD' ORDER BY 1,2;

-- atributos_temporales; query_id=01c87072-0004-e91a-0000-7b7d001a2626
SELECT COUNT_IF(codigo_bolsa IS NULL) bolsa_desconocida,COUNT(*) acciones FROM GOLD.DIM_ACCION;

-- join_hechos_por_fecha; query_id=01c87072-0004-e937-0000-7b7d0019fc42
SELECT COUNT(*) filas_join FROM GOLD.FCT_PRECIOS_DIARIOS p JOIN GOLD.FCT_MERCADO_DIARIO m ON p.fecha_key=m.fecha_key;