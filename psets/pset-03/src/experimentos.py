"""Registro de corridas en MLflow (seccion 4 de CD_PSet_3.pdf). Solo usa entrenamiento y CV, nunca hold-out.

Cada corrida registra, en el experimento "portafolio-inversiones":
- Parametros: hiperparametros del modelo, semilla (42) y la regla de negocio (topes y costo).
- Datos: tabla de origen, fecha del snapshot, fecha de corte y SHA-256 de la OBT mensual y de la diaria.
- Metricas: todas las de validar() en entrenamiento y CV (promedio y desviacion), brecha, segundos,
  IC de Spearman por mes y la metrica de negocio (Sharpe neto, drawdown, retorno, turnover, % invertido).
- Tags: fase (baseline, candidato, tuning, final), familia, modelo, commit de Git y si habia cambios sin commit.
- Artefactos: el Pipeline (mlflow.sklearn.log_model) con firma y ejemplo de entrada, el codigo de src/,
  requirements.txt, los manifiestos de los snapshots, el MAE por pliegue y las predicciones fuera de muestra.

Uso (con MLflow levantado; ver README):
    uv run --group modelos python -m src.experimentos --modelos B1_media
    uv run --group modelos python -m src.experimentos --verificar <run_id>    # recarga en sesion limpia
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import cross_validate, ParameterSampler
from sklearn.metrics import mean_absolute_error
from .entorno import SEMILLA
from .pipeline import crear_pipeline, pliegues, resumir_cv, PUNTAJES, FEATURES, TARGET
from .evaluacion import ic_por_mes, resumen_ic
from .negocio import REGLA, RiesgoDiario, metrica_negocio

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTO = 'portafolio-inversiones'
CONSERVAR = ['accion_key', 'anio_mes', 'vol_63d', 'ret_pct_mes_siguiente', 'rf_mes_siguiente']


def _lightgbm():
    from lightgbm import LGBMRegressor          # grupo "modelos" de pyproject.toml
    return LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=200, subsample=0.8,
                         subsample_freq=1, colsample_bytree=0.8, objective='l1', random_state=SEMILLA, verbose=-1)


# Modelos tabulares con su familia (tag "familia") y su nombre (tag "modelo"). Toda lista tiene >= 2 lineas base.
CATALOGO = {
    'B1_media':         ('linea_base',   lambda: DummyRegressor()),
    'B2_rw_cero':       ('linea_base',   lambda: DummyRegressor(strategy='constant', constant=0.0)),
    'M2_random_forest': ('arboles',      lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=50,
                                                                       max_features=0.5, n_jobs=-1, random_state=SEMILLA)),
    'M3_lightgbm':      ('boosting',     _lightgbm),
    'M4_ridge':         ('lineal',       lambda: Ridge(alpha=10.0)),
    'M5_mlp':           ('red_neuronal', lambda: MLPRegressor(hidden_layer_sizes=(64, 32), early_stopping=True,
                                                              random_state=SEMILLA)),
}


def candidatos():
    return {n: f() for n, (_, f) in CATALOGO.items()}


def _git():
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        sucio = bool(subprocess.check_output(['git', 'status', '--porcelain', '--', '.'], cwd=ROOT, text=True).strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        commit, sucio = os.environ.get('GIT_COMMIT', 'sin_commit_registrado'), os.environ.get('GIT_DIRTY', 'true') == 'true'
    return commit, sucio


def _tipos_confiables(pipe):
    """Tipos que skops debe aceptar al guardar y recargar el Pipeline (los genera este mismo codigo)."""
    import skops.io as sio
    return sorted(set(sio.get_untrusted_types(data=sio.dumps(pipe))) | {'numpy.dtype'})


def _mlflow():
    import mlflow
    mlflow.set_tracking_uri(os.environ.get('MLFLOW_TRACKING_URI', 'http://localhost:5001'))
    mlflow.set_experiment(os.environ.get('MLFLOW_EXPERIMENT_NAME', EXPERIMENTO))
    return mlflow


def registrar(nombre, train, meta, fase, modelo=None, riesgo=None, meta_dia=None, nested=False):
    """Una corrida: CV temporal, metricas, IC, metrica de negocio, ajuste final y registro completo."""
    mlflow = _mlflow()
    from mlflow.models import infer_signature
    familia = CATALOGO[nombre][0] if nombre in CATALOGO else 'otro'
    modelo = CATALOGO[nombre][1]() if modelo is None else modelo
    X, y = train[FEATURES], train[TARGET]
    cv = pliegues(train)
    pipe = crear_pipeline(clone(modelo))
    inicio = time.perf_counter()
    with mlflow.start_run(run_name=nombre, nested=nested) as run:
        scores = cross_validate(pipe, X, y, cv=cv, scoring=PUNTAJES, return_train_score=True,
                                return_estimator=True, n_jobs=1, error_score='raise')
        partes = []
        for k, ((_, iv), est) in enumerate(zip(cv, scores['estimator'])):
            v = train.iloc[iv]
            partes.append(v[[c for c in CONSERVAR if c in v]].assign(pliegue=k, pred=est.predict(v[FEATURES]),
                                                                     real=v[TARGET].values))
        pred = pd.concat(partes, ignore_index=True)
        pipe.fit(X, y)
        segundos = time.perf_counter() - inicio
        todas = resumir_cv(scores); mae_pliegues = todas.pop('mae_pliegues')
        ic = resumen_ic(ic_por_mes(pred))
        # Una prediccion constante no ordena acciones: la regla elegiria por el orden de las filas. Su
        # referencia de negocio es B4 (portafolios al azar), no esta corrida.
        ordena = bool(pred.groupby('anio_mes').pred.nunique().max() > 1)
        negocio = metrica_negocio(pred, riesgo=riesgo) if ordena else {}
        metricas = {**todas, 'brecha_mae': todas['mae_cv_media'] - todas['mae_train_cv'],
                    'segundos_entrenamiento': segundos, 'mae_train_final': mean_absolute_error(y, pipe.predict(X)),
                    **{k: v for k, v in ic.items() if isinstance(v, (int, float))},
                    **{f'negocio_{k}': v for k, v in negocio.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}}
        metricas = {k: float(v) for k, v in metricas.items() if v is not None and np.isfinite(v)}
        commit, sucio = _git()
        mlflow.log_params({**{k: str(v) for k, v in modelo.get_params().items()}, 'semilla': SEMILLA,
                           'tabla': meta['tabla'], 'snapshot': meta['snapshot_utc'], 'sha256': meta['sha256'],
                           'corte': meta.get('corte', '2023-12'), 'filas_entrenamiento': len(train),
                           'pliegues': f'TimeSeriesSplit({len(cv)}, test_size=12 meses, gap=1)',
                           'sha256_dia': (meta_dia or {}).get('sha256', 'sin_datos_diarios'),
                           'snapshot_dia': (meta_dia or {}).get('snapshot_utc', 'sin_datos_diarios'),
                           **{f'regla_{k}': str(v) for k, v in REGLA.items()},
                           'tope_portafolio_aplicado': str(riesgo is not None),
                           'metrica_negocio': 'calculada' if ordena else 'no_aplica_prediccion_constante'})
        mlflow.set_tags({'fase': fase, 'familia': familia, 'modelo': nombre, 'git_commit': commit,
                         'git_dirty': str(sucio)})
        mlflow.log_metrics(metricas)
        for fuente in sorted((ROOT / 'src').rglob('*.py')):
            mlflow.log_artifact(str(fuente), artifact_path='codigo/' + str(fuente.parent.relative_to(ROOT)))
        if (ROOT / 'requirements.txt').exists():
            mlflow.log_artifact(str(ROOT / 'requirements.txt'), artifact_path='codigo')
        mlflow.log_dict(meta, 'datos/snapshot_mes.json')
        if meta_dia:
            mlflow.log_dict(meta_dia, 'datos/snapshot_dia.json')
        mlflow.log_dict({'mae_cv': mae_pliegues}, 'pliegues.json')
        pred.to_csv(ROOT / 'mlflow_predicciones_tmp.csv', index=False)
        mlflow.log_artifact(str(ROOT / 'mlflow_predicciones_tmp.csv'), artifact_path='predicciones_cv')
        (ROOT / 'mlflow_predicciones_tmp.csv').unlink()
        ejemplo = X.iloc[:5]
        mlflow.log_dict({'X': ejemplo.to_dict(orient='list'), 'pred': pipe.predict(ejemplo).tolist()},
                        'verificacion/ejemplo_prediccion.json')
        info = mlflow.sklearn.log_model(pipe, name='pipeline', skops_trusted_types=_tipos_confiables(pipe),
                                        signature=infer_signature(ejemplo, pipe.predict(ejemplo)), input_example=ejemplo)
        return {'modelo': nombre, 'familia': familia, 'fase': fase, 'run_id': run.info.run_id,
                'model_uri': info.model_uri, 'git_dirty': sucio, **metricas}


def verificar(run_id):
    """Recarga el Pipeline registrado (en un proceso nuevo) y compara con las predicciones guardadas."""
    mlflow = _mlflow()
    modelo = mlflow.sklearn.load_model(f'runs:/{run_id}/pipeline')
    guardado = mlflow.artifacts.load_dict(f'runs:/{run_id}/verificacion/ejemplo_prediccion.json')
    X = pd.DataFrame(guardado['X'])[FEATURES]
    nuevo = modelo.predict(X)
    igual = bool(np.allclose(nuevo, guardado['pred'], rtol=0, atol=1e-12))
    print(json.dumps({'run_id': run_id, 'recarga_ok': igual, 'max_diferencia': float(np.max(np.abs(nuevo - guardado['pred'])))}))
    return igual


def datos_para_registro():
    from .datos import cargar
    from .pipeline import preparar, dividir
    obt, meta = cargar()
    train, _ = dividir(preparar(obt))
    riesgo = meta_dia = None
    if (ROOT / 'data/obt_dia.parquet').exists():
        dia, meta_dia = cargar(grano='dia')
        riesgo = RiesgoDiario(dia)
    return train.reset_index(drop=True), meta, riesgo, meta_dia


def evaluar_candidatos(train, meta, riesgo=None, meta_dia=None, nombres=None):
    nombres = list(CATALOGO) if nombres is None else nombres
    filas = [registrar(n, train, meta, 'baseline' if CATALOGO[n][0] == 'linea_base' else 'candidato',
                       riesgo=riesgo, meta_dia=meta_dia) for n in nombres]
    df = pd.DataFrame(filas); df.to_csv(ROOT / 'docs/candidatos.csv', index=False)
    return df

def ajustar(train,meta,mejores,n_iter=30):
    import mlflow
    if len(set(mejores))!=3 or n_iter<30: raise ValueError('La guía exige 3 modelos y >=30 configuraciones cada uno')
    espacios={'M4_ridge':{'alpha':loguniform(1e-4,1e4)},
              'M2_random_forest':{'n_estimators':randint(100,501),'max_depth':randint(3,25),'min_samples_leaf':randint(1,200)},
              'M3_lightgbm':{'learning_rate':loguniform(.01,.3),'num_leaves':randint(8,65),'min_child_samples':randint(50,500),'reg_lambda':loguniform(1e-5,10)},
              'M5_mlp':{'alpha':loguniform(1e-6,1),'learning_rate_init':loguniform(1e-4,1e-2),'hidden_layer_sizes':[(32,),(64,),(64,32),(128,64)]}}
    mlflow=_mlflow()
    filas=[]
    for nombre in mejores:
        if nombre not in espacios: raise ValueError(f'Definir espacio de búsqueda para {nombre}')
        with mlflow.start_run(run_name='tuning_'+nombre):
            mlflow.set_tag('fase','tuning_padre')
            for cfg in ParameterSampler(espacios[nombre],n_iter=n_iter,random_state=SEMILLA):
                filas.append(registrar(nombre,train,meta,'tuning',modelo=candidatos()[nombre].set_params(**cfg),nested=True))
    df=pd.DataFrame(filas); df.to_csv(ROOT/'docs/tuning.csv',index=False)
    exp=mlflow.get_experiment_by_name(os.environ.get('MLFLOW_EXPERIMENT_NAME',EXPERIMENTO))
    mlflow.search_runs([exp.experiment_id]).to_csv(ROOT/'docs/corridas.csv',index=False)
    return df


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Registra corridas en MLflow o verifica una recarga.')
    ap.add_argument('--modelos', help='nombres de CATALOGO separados por coma (por defecto, todos)')
    ap.add_argument('--verificar', metavar='RUN_ID', help='recarga el Pipeline de esa corrida y compara')
    a = ap.parse_args()
    if a.verificar:
        sys.exit(0 if verificar(a.verificar) else 1)
    train, meta, riesgo, meta_dia = datos_para_registro()
    nombres = a.modelos.split(',') if a.modelos else None
    df = evaluar_candidatos(train, meta, riesgo, meta_dia, nombres)
    cols = ['modelo', 'familia', 'fase', 'run_id', 'mae_cv_media', 'ic_media', 'negocio_sharpe_neto', 'git_dirty']
    print(df[[c for c in cols if c in df]].to_string(index=False))
