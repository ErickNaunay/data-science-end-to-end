"""Busqueda de hiperparametros con Optuna (TPE + poda por ventana) registrada en MLflow.

Por que Optuna y no BayesSearchCV: poda (MedianPruner) ventana a ventana, espacios
condicionales y graficas de optimizacion para el memo. Objetivo: IC medio de Spearman en las
ventanas walk-forward de tuning (a maximizar). Cada trial es una corrida hija de MLflow.

Presupuesto (docs/diseno_experimental.md): 3 modelos x 30 trials (el minimo del PSet) en las 3
ultimas ventanas (2021-2023), con poda tras la primera. El hold-out no se toca.
"""
from __future__ import annotations

import time

import numpy as np

from .entorno import SEMILLA

ESPACIOS = {
    "M3c_lightgbm": lambda t: {
        "n_estimators": t.suggest_int("n_estimators", 100, 1500, log=True),
        "learning_rate": t.suggest_float("learning_rate", 5e-3, 0.2, log=True),
        "num_leaves": t.suggest_int("num_leaves", 8, 128, log=True),
        "min_child_samples": t.suggest_int("min_child_samples", 50, 2000, log=True),
        "subsample": t.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": t.suggest_float("colsample_bytree", 0.3, 1.0),
        "reg_lambda": t.suggest_float("reg_lambda", 1e-3, 100, log=True)},
    "M3_xgboost": lambda t: {
        "n_estimators": t.suggest_int("n_estimators", 100, 1500, log=True),
        "learning_rate": t.suggest_float("learning_rate", 5e-3, 0.2, log=True),
        "max_depth": t.suggest_int("max_depth", 2, 8),
        "min_child_weight": t.suggest_float("min_child_weight", 1, 500, log=True),
        "subsample": t.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": t.suggest_float("colsample_bytree", 0.3, 1.0),
        "reg_lambda": t.suggest_float("reg_lambda", 1e-3, 100, log=True)},
    "M2_random_forest": lambda t: {
        "n_estimators": t.suggest_int("n_estimators", 100, 600, log=True),
        "max_depth": t.suggest_int("max_depth", 3, 20),
        "min_samples_leaf": t.suggest_int("min_samples_leaf", 20, 2000, log=True),
        "max_features": t.suggest_float("max_features", 0.1, 1.0)},
    "M4_ridge": lambda t: {"alpha": t.suggest_float("alpha", 1e-3, 1e4, log=True)},
    "M5_mlp": lambda t: {
        "hidden_layer_sizes": (t.suggest_int("n1", 16, 256, log=True), t.suggest_int("n2", 8, 128, log=True)),
        "alpha": t.suggest_float("alpha", 1e-6, 1e-1, log=True),
        "learning_rate_init": t.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True)},
}
# Comun a todos: cuantas variables deja el filtro (SelectKBest) y si se usa rango transversal.
PREPARACION = lambda t: {"k": t.suggest_categorical("k", [10, 20, "all"]),
                         "transversal": t.suggest_categorical("transversal", [True, False])}


def estudiar(nombre: str, base, panel, ventanas, objetivo, n_trials: int = 30, registrar=None,
             features=None):
    """base: estimador sin ajustar; ventanas: lista de (idx_ent, idx_val);
    objetivo(pipeline, ent, val) -> IC medio de la ventana. registrar(trial, metricas) opcional (MLflow)."""
    import optuna
    from sklearn.base import clone
    from .modelos.tabulares import FEATURES_F1, crear_pipeline
    features = features or FEATURES_F1

    def f(trial):
        params, prep = ESPACIOS[nombre](trial), PREPARACION(trial)
        valores, t0 = [], time.perf_counter()
        for paso, (it, iv) in enumerate(ventanas):
            pipe = crear_pipeline(clone(base).set_params(**params), features=features, **prep)
            valores.append(objetivo(pipe, panel.iloc[it], panel.iloc[iv]))
            trial.report(float(np.mean(valores)), paso)
            if trial.should_prune():
                raise optuna.TrialPruned()
        m = {"ic_media": float(np.mean(valores)), "ic_desv": float(np.std(valores, ddof=1)) if len(valores) > 1 else 0.0,
             "segundos": time.perf_counter() - t0}
        if registrar:
            registrar(trial, {**params, **prep}, m)
        return m["ic_media"]

    estudio = optuna.create_study(study_name=nombre, direction="maximize",
                                  sampler=optuna.samplers.TPESampler(seed=SEMILLA),
                                  pruner=optuna.pruners.MedianPruner(n_startup_trials=8, n_warmup_steps=0))
    estudio.optimize(f, n_trials=n_trials, gc_after_trial=True)
    return estudio
