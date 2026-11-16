"""Preparación común y CV temporal por mes completo, con purga del horizonte objetivo."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
TARGET='ret_log_mes_siguiente'
BASE=['ret_log_mes','ret_log_21d','ret_log_252d','momentum_12_1','vol_21d','vol_63d','vol_apertura_21d','intradia_prom_21d','nocturno_prom_21d','drawdown_252d','volumen_prom_21d','dolares_negociados_prom_21d','obs_252d','dias_negociados_mes','ret_log_sp500_mes','ret_log_nyse_composite_mes','rf_mes']
FEATURES=BASE+['vol_relativa','momentum_por_riesgo']
def preparar(df):
    d=df.copy().sort_values(['anio_mes','accion_key']).reset_index(drop=True)
    for c in BASE+[TARGET]: d[c]=pd.to_numeric(d[c],errors='coerce')
    d['vol_relativa']=d.vol_21d/d.vol_63d.replace(0,np.nan)
    d['momentum_por_riesgo']=d.momentum_12_1/d.vol_63d.replace(0,np.nan)
    d[FEATURES]=d[FEATURES].replace([np.inf,-np.inf],np.nan).astype(float)
    d=d[d.elegible.fillna(False) & d[TARGET].notna()].copy()
    # No usar atributos actuales (sigue_en_sp500, bolsa) como predictores ni columnas del futuro.
    d['mes_objetivo']=pd.PeriodIndex(d.anio_mes.astype(str),freq='M')+1
    return d.reset_index(drop=True)
def dividir(d,corte='2023-12'):
    limite=pd.Period(corte,freq='M')
    # Objetivos que terminan antes de 2024: diciembre 2023 no entra al entrenamiento.
    return d[d.mes_objetivo<=limite].copy(),d[d.mes_objetivo>limite].copy()
def pliegues(d,n_splits=5):
    meses=np.sort(d.anio_mes.unique())
    for tr,va in TimeSeriesSplit(n_splits=n_splits,gap=1).split(meses):
        it=np.flatnonzero(d.anio_mes.isin(meses[tr])); iv=np.flatnonzero(d.anio_mes.isin(meses[va]))
        yield it,iv

def crear_pipeline(modelo):
    num=Pipeline([('imputar',SimpleImputer(strategy='median',keep_empty_features=True)),('escalar',StandardScaler())])
    return Pipeline([('preparar',ColumnTransformer([('numericas',num,FEATURES)],remainder='drop')),('modelo',modelo)])
