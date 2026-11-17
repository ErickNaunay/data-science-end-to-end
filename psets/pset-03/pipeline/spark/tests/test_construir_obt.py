"""Pruebas de construir_obt.py con datos armados a mano (no leen data/ ni Snowflake).

Verifican que la OBT sale con el grano accion x mes cerrado, que el objetivo es el retorno
del mes siguiente y que los controles detectan joins que duplican o pierden filas.

Uso, desde psets/pset-03/pipeline/ (requiere Java 17 y el grupo opcional de pyspark):
  uv sync --group dev --group pruebas-locales
  uv run python -m pytest -q spark/tests
Sin pyspark o sin Java las pruebas se saltan (skip), no fallan.
O dentro de la imagen de Spark, sin Java ni pyspark en el host (falla si faltan, no salta):
  docker compose --profile pruebas run --rm --build spark-pruebas
"""
from __future__ import annotations

import datetime as dt
import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("pyspark")
if shutil.which("java") is None:
    pytest.skip("Spark necesita Java en el PATH", allow_module_level=True)

from pyspark.sql import SparkSession  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
import construir_obt as obt_mod  # noqa: E402

# Dos sesiones por mes; enero de 2024 queda abierto (mes_cerrado = False).
# El corte por defecto es 2023-12-31: noviembre y diciembre son entrenamiento.
SESIONES = [
    (dt.date(2023, 11, 29), True, False), (dt.date(2023, 11, 30), True, True),
    (dt.date(2023, 12, 28), True, False), (dt.date(2023, 12, 29), True, True),
    (dt.date(2024, 1, 2), False, False), (dt.date(2024, 1, 3), False, False),
]
RET = {1: 0.01, 2: -0.02}   # retorno log diario constante por accion


@pytest.fixture(scope="module")
def spark():
    s = (SparkSession.builder.master("local[1]").appName("test-obt")
         .config("spark.sql.shuffle.partitions", "1").config("spark.ui.enabled", "false")
         .getOrCreate())
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


def tablas(spark, dim_accion_extra=(), fct_extra=(), quitar_mercado_mes=None):
    fechas = [(int(f.strftime("%Y%m%d")), f, f.year, f.month, f.year * 100 + f.month, cerrado, cierre,
               "entrenamiento" if f <= dt.date(2023, 12, 31) else "prueba")
              for f, cerrado, cierre in SESIONES]
    dim_f = spark.createDataFrame(fechas, "fecha_key int, fecha date, anio int, mes int, anio_mes int, "
                                          "mes_cerrado boolean, es_cierre_de_mes boolean, conjunto string")
    fct_filas = [(a, fk, RET[a], False, 0.0, RET[a], 0.0, 100.0, 1000.0, 100.0, False, False, True)
                 for a in RET for fk, *_ in fechas]
    fct = spark.createDataFrame(fct_filas + list(fct_extra),
                                "accion_key int, fecha_key int, ret_log_diario double, imputado boolean, "
                                "ret_log_apertura double, ret_log_intradia double, ret_log_nocturno double, "
                                "precio_cierre_ajustado double, volumen double, precio_cierre double, "
                                "es_retorno_extremo boolean, despues_de_tramo_excluido boolean, en_sp500 boolean")
    acciones = [(1, "AAA", "Acme", "NYSE", True, True, "N"), (2, "BBB", "Beta", "NYSE", True, False, "N")]
    dim_a = spark.createDataFrame(acciones + list(dim_accion_extra),
                                  "accion_key int, ticker string, nombre string, bolsa string, es_nyse boolean, "
                                  "sigue_en_sp500 boolean, codigo_bolsa string")
    mercado = [(fk, 0.001, 0.001, 0.0001, 5.0) for fk, *_ in fechas
               if quitar_mercado_mes is None or fk // 100 != quitar_mercado_mes]
    mkt = spark.createDataFrame(mercado, "fecha_key int, ret_log_sp500 double, ret_log_nyse_composite double, "
                                         "rf_diaria double, tasa_irx_anual_pct double")
    return {"fct_precios_diarios": fct, "dim_accion": dim_a, "dim_fecha": dim_f, "fct_mercado_diario": mkt}


def construir(spark, **kw):
    c = obt_mod.Controles()
    return obt_mod.construir(tablas(spark, **kw), c), c


def fallidos(c):
    return [nombre for nombre, _, _, ok in c.filas if not ok]


def test_datos_validos_pasan_todos_los_controles(spark):
    obt, c = construir(spark)
    assert c.todos_ok(), fallidos(c)
    assert len(c.filas) == 13
    # 2 acciones x 2 meses cerrados; enero (abierto) no entra.
    assert obt.count() == 4
    assert obt.select("accion_key", "anio_mes").distinct().count() == 4
    assert len(obt.columns) == 43


def test_objetivo_es_el_retorno_del_mes_siguiente(spark):
    obt, _ = construir(spark)
    filas = {(r.accion_key, r.anio_mes): r for r in obt.collect()}
    nov, dic = filas[(1, 202311)], filas[(1, 202312)]
    assert nov.ret_log_mes == pytest.approx(2 * RET[1])
    assert nov.ret_log_mes_siguiente == pytest.approx(dic.ret_log_mes)
    # El mes siguiente a diciembre (enero) no esta cerrado: sin objetivo.
    assert dic.ret_log_mes_siguiente is None


def test_corte_marca_entrenamiento_y_mes_que_cruza(spark):
    obt, _ = construir(spark)
    filas = {(r.accion_key, r.anio_mes): r for r in obt.collect()}
    assert {r.conjunto for r in filas.values()} == {"entrenamiento"}
    assert filas[(1, 202312)].objetivo_cruza_corte is True
    assert filas[(1, 202311)].objetivo_cruza_corte is False


def test_dimension_accion_duplicada_falla(spark):
    _, c = construir(spark, dim_accion_extra=[(1, "AAA", "Acme bis", "NYSE", True, True, "N")])
    assert not c.todos_ok()
    assert any(n.startswith("dim_accion") for n in fallidos(c))
    assert "join OBT x dim_accion conserva filas" in fallidos(c)


def test_hecho_diario_duplicado_falla(spark):
    duplicado = (1, 20231129, RET[1], False, 0.0, RET[1], 0.0, 100.0, 1000.0, 100.0, False, False, True)
    _, c = construir(spark, fct_extra=[duplicado])
    assert any(n.startswith("fct_precios_diarios") for n in fallidos(c))


def test_mes_sin_mercado_falla(spark):
    _, c = construir(spark, quitar_mercado_mes=202312)
    assert "OBT sin meses huerfanos de mercado" in fallidos(c)
