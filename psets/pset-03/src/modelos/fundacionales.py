"""M8-M10: modelos fundacionales en zero-shot (fase pesada, una vez; resultado en artefactos/).

Contexto: los ultimos `contexto` retornos log diarios hasta el cierre del mes t (dias
observados). Pronostico: 21 dias; el retorno del mes es la suma de las medianas diarias y la
dispersion de los cuantiles da una medida de incertidumbre. Los modelos normalizan cada
ventana por su cuenta (escalado por instancia, al estilo RevIN), asi que no se ajusta ningun
escalador con datos futuros.

Riesgos documentados en docs/diseno_experimental.md:
  - Contaminacion: si el corpus de preentrenamiento incluye precios posteriores a 2023, el
    hold-out no es fuera de muestra para ese modelo. Revisar la ficha de cada modelo.
  - Latencia: se mide (ms por serie) y se registra en MLflow. Con rebalanceo mensual no es un
    cuello de botella; la destilacion solo vale la pena si se despliega en linea (PSet 4).
Paquetes (fuera del lock, chocan entre si): chronos-forecasting; timesfm; uni2ts (Moirai).
Instalar cada uno en su propio entorno o en Colab con !pip.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from ..entorno import dispositivo

CUANTILES = (0.1, 0.5, 0.9)


class Chronos:
    """amazon/chronos-bolt-small por defecto (rapido en CPU, mps y T4)."""

    def __init__(self, modelo: str = "amazon/chronos-bolt-small", contexto: int = 512, h: int = 21):
        from chronos import BaseChronosPipeline
        import torch
        disp = dispositivo()
        self.nombre, self.contexto, self.h = modelo, contexto, h
        self.pipe = BaseChronosPipeline.from_pretrained(
            modelo, device_map=disp, torch_dtype=torch.float32 if disp != "cuda" else torch.bfloat16)

    def pronosticar(self, ventanas: list[np.ndarray]) -> np.ndarray:
        import torch
        ctx = [torch.tensor(v[-self.contexto:], dtype=torch.float32) for v in ventanas]
        q, _ = self.pipe.predict_quantiles(ctx, prediction_length=self.h, quantile_levels=list(CUANTILES))
        return q.float().cpu().numpy()                      # (series, h, cuantiles)


class TimesFM:
    """Adaptador pendiente: la API de timesfm cambia entre 1.x y 2.x; se completa al instalarlo."""

    def __init__(self, *a, **k):
        raise NotImplementedError("Completar con la version instalada de timesfm (plan M9)")


class Moirai:
    """Adaptador pendiente (uni2ts, plan M10)."""

    def __init__(self, *a, **k):
        raise NotImplementedError("Completar con la version instalada de uni2ts (plan M10)")


def pronosticos_mensuales(modelo, diaria: pd.DataFrame, origenes: pd.DataFrame, lote: int = 256) -> pd.DataFrame:
    """Una fila por (accion_key, anio_mes): pronostico del mes (suma de cuantiles diarios),
    ancho 10-90 y latencia por serie. Solo usa retornos con fecha <= fecha_origen."""
    diaria = diaria[~diaria["imputado"].astype(bool)].sort_values(["accion_key", "fecha"])
    series = {k: (g["fecha"].to_numpy(), g["ret_log_diario"].to_numpy(dtype=float))
              for k, g in diaria.groupby("accion_key")}
    claves, ventanas = [], []
    for o in origenes.itertuples():
        f, r = series.get(o.accion_key, (None, None))
        if f is None:
            continue
        v = r[(f <= np.datetime64(o.fecha_origen)) & np.isfinite(r)]
        if len(v) >= 64:
            claves.append((o.accion_key, o.anio_mes))
            ventanas.append(v)
    filas, t0 = [], time.perf_counter()
    for i in range(0, len(ventanas), lote):
        q = modelo.pronosticar(ventanas[i:i + lote]).sum(axis=1)          # suma de 21 dias
        for (k, m), fila in zip(claves[i:i + lote], q):
            filas.append({"accion_key": k, "anio_mes": m, "pred": fila[1], "ancho_10_90": fila[2] - fila[0]})
    ms = 1000 * (time.perf_counter() - t0) / max(len(ventanas), 1)
    out = pd.DataFrame(filas)
    out.attrs["latencia_ms_por_serie"] = ms
    return out
