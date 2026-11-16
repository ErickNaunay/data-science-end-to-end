-- Silver de precios de acciones: una fila por accion y dia bursatil de la NYSE, desde su
-- primera hasta su ultima cotizacion, con faltantes detectados e imputados.
--
-- 1. Deteccion: la grilla accion x calendario NYSE muestra los dias en que la accion
--    deberia tener precio. Falta un dia si no hay fila o si el precio no es valido (nulo,
--    no positivo o maximo < minimo).
-- 2. Imputacion (huecos de hasta max_hueco_imputable dias): interpolacion lineal del
--    log-precio entre el ultimo dia observado y el siguiente, para el cierre ajustado y la
--    apertura ajustada. La comparación con ruido y Kalman pertenece al análisis de PSet 3;
--    aquí no se afirma superioridad sin evidencia. Usa un vecino posterior: auditar
--    disponibilidad temporal antes de emplear las features en entrenamiento.
-- 3. Huecos mas largos: no se imputan y esos dias no pasan a Silver; el retorno del dia
--    siguiente queda nulo, para no unir dos dias lejanos en un solo retorno.
-- 4. Banderas: imputado, retorno extremo (se marca, no se borra: puede ser real), cierre
--    fuera del rango del dia, volumen cero.
-- La apertura ajustada = apertura * cierre ajustado / cierre: Yahoo no ajusta la apertura
-- por splits ni dividendos.
with validos as (
    select
        p.ticker,
        p.fecha,
        p.precio_apertura,
        p.precio_maximo,
        p.precio_minimo,
        p.precio_cierre,
        p.precio_cierre_ajustado,
        p.precio_apertura * p.precio_cierre_ajustado / p.precio_cierre as precio_apertura_ajustado,
        p.volumen,
        p.lote_id,
        p.ingesta_ts
    from {{ ref('brz_precios_diarios') }} as p
    where not p.es_indice
      and p.precio_cierre_ajustado > 0
      and p.precio_cierre > 0
      and p.precio_apertura > 0
      and p.precio_maximo > 0
      and p.precio_minimo > 0
      and p.precio_maximo >= p.precio_minimo
),

vida as (
    select ticker, min(fecha) as primera, max(fecha) as ultima
    from validos
    group by ticker
),

grilla as (
    select v.ticker, c.fecha, c.orden_bursatil
    from vida as v
    inner join {{ ref('slv_calendario_nyse') }} as c
        on c.fecha between v.primera and v.ultima
),

con_obs as (
    select
        g.ticker,
        g.fecha,
        g.orden_bursatil,
        o.precio_apertura,
        o.precio_maximo,
        o.precio_minimo,
        o.precio_cierre,
        o.precio_cierre_ajustado,
        o.volumen,
        o.lote_id,
        o.ingesta_ts,
        ln(o.precio_cierre_ajustado)    as lp_cierre,
        ln(o.precio_apertura_ajustado)  as lp_apertura,
        case when o.ticker is not null then g.orden_bursatil end as orden_obs
    from grilla as g
    left join validos as o
        on g.ticker = o.ticker and g.fecha = o.fecha
),

grupos as (
    -- grupo_ant: cuantos dias observados hay hasta hoy (incluido); todos los dias de un
    -- hueco comparten el grupo del ultimo dia observado. grupo_sig: lo mismo hacia atras.
    select
        *,
        count(orden_obs) over (partition by ticker order by orden_bursatil
                               rows between unbounded preceding and current row) as grupo_ant,
        count(orden_obs) over (partition by ticker order by orden_bursatil desc
                               rows between unbounded preceding and current row) as grupo_sig
    from con_obs
),

vecinos as (
    select
        *,
        max(orden_obs)   over (partition by ticker, grupo_ant) as orden_ant,
        max(lp_cierre)   over (partition by ticker, grupo_ant) as lp_cierre_ant,
        max(lp_apertura) over (partition by ticker, grupo_ant) as lp_apertura_ant,
        min(orden_obs)   over (partition by ticker, grupo_sig) as orden_sig,
        max(lp_cierre)   over (partition by ticker, grupo_sig) as lp_cierre_sig,
        max(lp_apertura) over (partition by ticker, grupo_sig) as lp_apertura_sig
    from grupos
),

imputada as (
    select
        *,
        orden_obs is null                                          as imputado,
        orden_sig - orden_ant - 1                                  as largo_hueco,
        case
            when orden_obs is not null then lp_cierre
            when orden_sig - orden_ant - 1 <= {{ var('max_hueco_imputable') }}
                then lp_cierre_ant + (lp_cierre_sig - lp_cierre_ant)
                     * (orden_bursatil - orden_ant) / (orden_sig - orden_ant)
        end                                                        as lp_cierre_final,
        case
            when orden_obs is not null then lp_apertura
            when orden_sig - orden_ant - 1 <= {{ var('max_hueco_imputable') }}
                then lp_apertura_ant + (lp_apertura_sig - lp_apertura_ant)
                     * (orden_bursatil - orden_ant) / (orden_sig - orden_ant)
        end                                                        as lp_apertura_final
    from vecinos
),

con_retornos as (
    select
        *,
        lp_cierre_final - lag(lp_cierre_final) over (partition by ticker order by orden_bursatil)   as ret_log_diario,
        lp_apertura_final - lag(lp_apertura_final) over (partition by ticker order by orden_bursatil) as ret_log_apertura,
        lp_apertura_final - lag(lp_cierre_final) over (partition by ticker order by orden_bursatil)   as ret_log_nocturno,
        lag(lp_cierre_final) over (partition by ticker order by orden_bursatil) is null
            and orden_bursatil > min(orden_bursatil) over (partition by ticker)                       as despues_de_tramo_excluido
    from imputada
)

select
    ticker,
    fecha,
    precio_apertura,
    precio_maximo,
    precio_minimo,
    precio_cierre,
    exp(lp_cierre_final)                                              as precio_cierre_ajustado,
    exp(lp_apertura_final)                                            as precio_apertura_ajustado,
    volumen,
    ret_log_diario,
    ret_log_apertura,
    lp_cierre_final - lp_apertura_final                               as ret_log_intradia,
    ret_log_nocturno,
    imputado,
    case when imputado then largo_hueco end                           as largo_hueco_imputado,
    despues_de_tramo_excluido,
    coalesce(abs(ret_log_diario) > {{ var('umbral_retorno_extremo') }}, false) as es_retorno_extremo,
    coalesce(precio_cierre > precio_maximo * 1.001 or precio_cierre < precio_minimo * 0.999, false)
                                                                      as cierre_fuera_de_rango,
    coalesce(volumen = 0, false)                                      as volumen_cero,
    lote_id,
    ingesta_ts
from con_retornos
where lp_cierre_final is not null
  and lp_apertura_final is not null
