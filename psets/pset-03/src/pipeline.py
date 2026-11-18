"""Preparación común y CV temporal por mes completo, con purga del horizonte objetivo.

Catálogo de columnas de las dos OBT (pipeline/spark/jobs/construir_obt.py) y qué entra como
predictor. Fuente única: src/modelos/tabulares.py importa FEATURES_OBT de aquí.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit

TARGET = 'ret_log_mes_siguiente'

# --- OBT_ACCION_MES (75 columnas): 43 del PSet 2 + 32 de F1 (PSet 3) -----------------------
OBT_MES_PSET2 = [
    'accion_key', 'ticker', 'nombre', 'bolsa', 'es_nyse', 'bolsa_desconocida', 'anio_mes', 'anio', 'mes',
    'conjunto', 'objetivo_cruza_corte', 'fecha_ultima_cotizacion', 'cotizo_al_cierre_de_mes', 'en_sp500',
    'sigue_en_sp500', 'elegible', 'precio_cierre_ajustado', 'ret_log_mes', 'ret_log_21d', 'ret_log_252d',
    'momentum_12_1', 'vol_21d', 'vol_63d', 'vol_apertura_21d', 'intradia_prom_21d', 'nocturno_prom_21d',
    'drawdown_252d', 'volumen_prom_21d', 'dolares_negociados_prom_21d', 'obs_252d', 'dias_negociados_mes',
    'dias_imputados_mes', 'hubo_tramo_excluido_mes', 'hubo_retorno_extremo_mes', 'ret_log_sp500_mes',
    'ret_log_nyse_composite_mes', 'rf_mes', 'tasa_irx_prom_mes_pct', 'ret_log_mes_siguiente',
    'exceso_ret_mes_siguiente', 'ret_log_sp500_mes_siguiente', 'ret_log_nyse_composite_mes_siguiente',
    'rf_mes_siguiente',
]
OBT_MES_F1 = [
    'ret_pct_mes', 'ret_log_mes_lag1', 'ret_pct_mes_lag1', 'ret_log_mes_lag2', 'ret_pct_mes_lag2',
    'ret_log_mes_lag3', 'ret_pct_mes_lag3', 'intradia_log_mes', 'intradia_pct_mes', 'nocturno_log_mes',
    'nocturno_pct_mes', 'intradia_pct_prom_21d', 'nocturno_pct_prom_21d', 'vol_intradia_21d',
    'rango_log_hl_mes', 'rango_pct_hl_mes', 'cambio_rango_log_hl_mes', 'cambio_rango_pct_hl_mes',
    'rango_log_hl_prom_21d', 'rango_pct_hl_prom_21d', 'rango_log_hl_prom_63d', 'rango_pct_hl_prom_63d',
    'cambio_rango_log_hl_21_63', 'cambio_rango_pct_hl_21_63', 'vol_parkinson_21d', 'vol_garman_klass_21d',
    'beta_252d', 'exceso_sp500_log_mes', 'exceso_sp500_pct_mes', 'volumen_relativo_log_21_252',
    'volumen_relativo_pct_21_252', 'ret_pct_mes_siguiente',
]
OBT_MES = OBT_MES_PSET2 + OBT_MES_F1

# --- OBT_ACCION_DIA (33 columnas, nueva en F1): una fila por fila de GOLD.FCT_PRECIOS_DIARIOS ---
OBT_DIA = [
    'accion_key', 'ticker', 'fecha', 'anio_mes', 'conjunto', 'mes_cerrado', 'en_sp500', 'imputado',
    'despues_de_tramo_excluido', 'es_retorno_extremo',
    'precio_apertura', 'precio_maximo', 'precio_minimo', 'precio_cierre',
    'precio_apertura_ajustado', 'precio_maximo_ajustado', 'precio_minimo_ajustado', 'precio_cierre_ajustado',
    'volumen',
    'dif_cierre_ajustado', 'ret_pct_diario', 'ret_log_diario',
    'dif_apertura_ajustada', 'ret_pct_apertura', 'ret_log_apertura',
    'ret_pct_intradia', 'ret_log_intradia', 'ret_pct_nocturno', 'ret_log_nocturno',
    'rango_pct_hl', 'rango_log_hl', 'ret_log_sp500', 'rf_diaria',
]

# --- Predictores --------------------------------------------------------------------------
# PSet 2 (17): sin cambios.
BASE = ['ret_log_mes', 'ret_log_21d', 'ret_log_252d', 'momentum_12_1', 'vol_21d', 'vol_63d',
        'vol_apertura_21d', 'intradia_prom_21d', 'nocturno_prom_21d', 'drawdown_252d', 'volumen_prom_21d',
        'dolares_negociados_prom_21d', 'obs_252d', 'dias_negociados_mes', 'ret_log_sp500_mes',
        'ret_log_nyse_composite_mes', 'rf_mes']
# F1 (16): la version en logaritmo de cada variable nueva. La version en % es la misma variable
# con otra escala (prueba test_porcentaje_y_logaritmo_son_la_misma_variable): usar las dos
# duplica informacion casi colineal, asi que el % queda para EDA y la regla de negocio.
F1_LOG = ['ret_log_mes_lag1', 'ret_log_mes_lag2', 'ret_log_mes_lag3',
          'vol_intradia_21d', 'vol_parkinson_21d', 'vol_garman_klass_21d',
          'intradia_log_mes', 'nocturno_log_mes',
          'rango_log_hl_mes', 'rango_log_hl_prom_21d', 'rango_log_hl_prom_63d',
          'cambio_rango_log_hl_mes', 'cambio_rango_log_hl_21_63',
          'beta_252d', 'exceso_sp500_log_mes', 'volumen_relativo_log_21_252']
F1_PCT = ['ret_pct_mes', 'ret_pct_mes_lag1', 'ret_pct_mes_lag2', 'ret_pct_mes_lag3',
          'intradia_pct_mes', 'nocturno_pct_mes', 'intradia_pct_prom_21d', 'nocturno_pct_prom_21d',
          'rango_pct_hl_mes', 'rango_pct_hl_prom_21d', 'rango_pct_hl_prom_63d',
          'cambio_rango_pct_hl_mes', 'cambio_rango_pct_hl_21_63',
          'exceso_sp500_pct_mes', 'volumen_relativo_pct_21_252']
FEATURES_OBT = BASE + F1_LOG                         # 33 columnas tal como vienen de la OBT
DERIVADAS = ['vol_relativa', 'momentum_por_riesgo']  # se calculan en preparar()
FEATURES = FEATURES_OBT + DERIVADAS                  # 35

# Nunca predictores: el futuro (objetivo y mercado del mes siguiente) y atributos de hoy que
# no se conocian en el mes (sigue_en_sp500, bolsa actual, ultima cotizacion).
FUGA = ['ret_log_mes_siguiente', 'ret_pct_mes_siguiente', 'exceso_ret_mes_siguiente',
        'ret_log_sp500_mes_siguiente', 'ret_log_nyse_composite_mes_siguiente', 'rf_mes_siguiente',
        'sigue_en_sp500', 'bolsa', 'es_nyse', 'bolsa_desconocida', 'fecha_ultima_cotizacion']


# Acciones fuera del analisis (H19): la semilla equivalencias_tickers une BMS (Bemis) con AMCR (Amcor) como
# si fuera un cambio de simbolo, pero fue una adquisicion. AMCR 2012-2014 queda en el S&P 500 con barras de
# solo cierre (rango maximo-minimo 0, volumen casi nulo) y deja predictores 0/0. Se quitan las dos.
EXCLUIDAS = ('BMS', 'AMCR')


def faltan_columnas(df, esperadas=OBT_MES):
    return [c for c in esperadas if c not in df.columns]


def preparar(df):
    falta = faltan_columnas(df, FEATURES_OBT + [TARGET, 'elegible', 'anio_mes', 'accion_key'])
    if falta:
        raise KeyError(f'El snapshot no tiene {len(falta)} columnas de F1 ({falta[:3]}...): '
                       'regenerarlo con "uv run python -m src.datos" tras reconstruir la OBT.')
    d = df.copy().sort_values(['anio_mes', 'accion_key']).reset_index(drop=True)
    num = [c for c in FEATURES_OBT + F1_PCT + [TARGET, 'ret_pct_mes_siguiente'] if c in d]
    for c in num:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d['vol_relativa'] = d.vol_21d / d.vol_63d.replace(0, np.nan)
    d['momentum_por_riesgo'] = d.momentum_12_1 / d.vol_63d.replace(0, np.nan)
    d[FEATURES] = d[FEATURES].replace([np.inf, -np.inf], np.nan).astype(float)
    d = d[d.elegible.fillna(False).astype(bool) & d[TARGET].notna()].copy()
    if 'ticker' in d:
        d = d[~d.ticker.astype(str).str.upper().isin(EXCLUIDAS)]
    d['mes_objetivo'] = pd.PeriodIndex(d.anio_mes.astype(str), freq='M') + 1
    return d.reset_index(drop=True)


def interpolar_huecos(d, columnas=FEATURES):
    """Interpola linealmente, por accion y en orden de mes, solo los huecos intermedios (con un valor
    observado antes y otro despues). Los nulos al inicio o al final de la historia quedan nulos y los
    imputa la mediana del Pipeline, ajustada en cada pliegue. Se aplica a cada lado del corte por separado
    (ver dividir), asi que un hueco del entrenamiento nunca se rellena con un mes del hold-out."""
    columnas = [c for c in columnas if c in d]
    if not columnas or 'accion_key' not in d or 'anio_mes' not in d or not d[columnas].isna().any().any():
        return d
    d = d.sort_values(['accion_key', 'anio_mes'])
    d[columnas] = d.groupby('accion_key', sort=False)[columnas].transform(
        lambda s: s.interpolate(method='linear', limit_area='inside'))
    return d.sort_values(['anio_mes', 'accion_key'])


def dividir(d, corte='2023-12'):
    limite = pd.Period(corte, freq='M')
    # Objetivos que terminan antes de 2024: diciembre 2023 no entra al entrenamiento.
    # El corte se hace antes de interpolar: cada lado solo usa sus propios meses.
    return (interpolar_huecos(d[d.mes_objetivo <= limite].copy()),
            interpolar_huecos(d[d.mes_objetivo > limite].copy()))


def pliegues(d, n_splits=5):
    meses = np.sort(d.anio_mes.unique())
    for tr, va in TimeSeriesSplit(n_splits=n_splits, gap=1).split(meses):
        it = np.flatnonzero(d.anio_mes.isin(meses[tr])); iv = np.flatnonzero(d.anio_mes.isin(meses[va]))
        yield it, iv


def crear_pipeline(modelo, features=FEATURES):
    num = Pipeline([('imputar', SimpleImputer(strategy='median', keep_empty_features=True)),
                    ('escalar', StandardScaler())])
    return Pipeline([('preparar', ColumnTransformer([('numericas', num, list(features))], remainder='drop')),
                     ('modelo', modelo)])
