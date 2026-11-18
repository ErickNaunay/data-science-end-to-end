"""Metrica de negocio del PSet 1: portafolio mensual de 10 acciones con pesos 1/vol.

Regla (PSet 1 con feedback): cada cierre de mes se eligen las n acciones elegibles con mayor
puntaje cuya volatilidad no supere el tope del cliente; pesos proporcionales a 1/vol. Solo
compras, sin apalancamiento. Se mide en retornos SIMPLES (ret_pct_mes_siguiente), que son los
que se suman entre acciones.

Costos: turnover = suma |w_nuevo - w_derivado| (compras + ventas), donde w_derivado son los
pesos del mes anterior despues de moverse con los precios. costo = turnover * costo_bps / 1e4.

Pendiente de decidir con Paul: tope de volatilidad, costo_bps y ventana de vol (vol_21d o
vol_63d). La comprobacion del tope a nivel de portafolio (covarianza historica) necesita
OBT_ACCION_DIA y queda para cuando este el snapshot diario.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def pesos_mes(g: pd.DataFrame, puntaje: str, vol: str = "vol_63d", n: int = 10,
              tope_vol: float | None = None) -> pd.Series:
    c = g[g[puntaje].notna() & (g[vol] > 0)]
    if tope_vol is not None:
        c = c[c[vol] <= tope_vol]
    c = c.nlargest(n, puntaje)
    if c.empty:
        return pd.Series(dtype=float)
    w = 1.0 / c[vol]
    return (w / w.sum()).set_axis(c["accion_key"])


def backtest(df: pd.DataFrame, puntaje: str, n: int = 10, vol: str = "vol_63d",
             tope_vol: float | None = None, costo_bps: float = 10.0,
             retorno: str = "ret_pct_mes_siguiente", rf: str = "rf_mes_siguiente") -> pd.DataFrame:
    """Serie mensual: retorno bruto, turnover, costo, retorno neto y tasa libre de riesgo."""
    if retorno not in df:                                   # snapshot anterior a F1
        df = df.assign(ret_pct_mes_siguiente=np.expm1(df["ret_log_mes_siguiente"]))
    filas, previos = [], pd.Series(dtype=float)
    for mes, g in df.sort_values("anio_mes").groupby("anio_mes"):
        w = pesos_mes(g, puntaje, vol, n, tope_vol)
        r = g.set_index("accion_key")[retorno].reindex(w.index).fillna(0.0)   # sin cotizacion: 0
        bruto = float((w * r).sum())
        todos = w.index.union(previos.index)
        turnover = float((w.reindex(todos, fill_value=0) - previos.reindex(todos, fill_value=0)).abs().sum())
        neto = bruto - turnover * costo_bps / 1e4
        tasa = float(g[rf].iloc[0]) if rf in g and g[rf].notna().any() else 0.0
        filas.append({"anio_mes": mes, "bruto": bruto, "turnover": turnover, "neto": neto,
                      "rf": tasa, "n_acciones": len(w)})   # rf_mes de la OBT ya es tasa simple aprox.
        derivado = w * (1 + r)
        previos = derivado / derivado.sum() if derivado.sum() > 0 else derivado
    return pd.DataFrame(filas).set_index("anio_mes")


def sharpe_anual(serie: pd.DataFrame, col: str = "neto") -> float:
    exceso = serie[col] - serie["rf"]
    return float(exceso.mean() / exceso.std(ddof=1) * np.sqrt(12)) if exceso.std(ddof=1) > 0 else np.nan


def drawdown_maximo(serie: pd.DataFrame, col: str = "neto") -> float:
    riqueza = (1 + serie[col]).cumprod()
    return float((riqueza / riqueza.cummax() - 1).min())


def resumen(serie: pd.DataFrame) -> dict:
    return {"sharpe_neto": sharpe_anual(serie, "neto"), "sharpe_bruto": sharpe_anual(serie, "bruto"),
            "drawdown_max": drawdown_maximo(serie), "turnover_prom": float(serie["turnover"].mean()),
            "retorno_anual_neto": float((1 + serie["neto"]).prod() ** (12 / len(serie)) - 1)}


def portafolios_aleatorios(df: pd.DataFrame, sorteos: int = 200, semilla: int = 7, **kw) -> pd.DataFrame:
    """B4: distribucion del Sharpe de portafolios de n acciones elegidas al azar cada mes."""
    rng = np.random.default_rng(semilla)
    out = []
    for s in range(sorteos):
        d = df.assign(_azar=rng.random(len(df)))
        out.append({"sorteo": s, **resumen(backtest(d, "_azar", **kw))})
    return pd.DataFrame(out)
