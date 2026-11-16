"""Infraestructura experimental; solo usa entrenamiento y CV, nunca hold-out."""
import os, subprocess, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import cross_validate, ParameterSampler
from sklearn.metrics import root_mean_squared_error
from .pipeline import crear_pipeline, pliegues, FEATURES, TARGET
ROOT=Path(__file__).resolve().parents[1]
SEMILLA=7

def candidatos():
    return {'dummy_media':DummyRegressor(), 'regla_cero':DummyRegressor(strategy='constant',constant=0),
            'ridge':Ridge(), 'random_forest':RandomForestRegressor(random_state=SEMILLA),
            'boosting':HistGradientBoostingRegressor(random_state=SEMILLA,early_stopping=False),
            'mlp':MLPRegressor(random_state=SEMILLA)}

def registrar(nombre,modelo,train,meta,fase,nested=False):
    import mlflow
    from mlflow.models import infer_signature
    mlflow.set_tracking_uri(os.environ.get('MLFLOW_TRACKING_URI','http://localhost:5001'))
    mlflow.set_experiment(os.environ.get('MLFLOW_EXPERIMENT_NAME','portafolio-inversiones'))
    X,y=train[FEATURES],train[TARGET]; pipe=crear_pipeline(clone(modelo)); inicio=time.perf_counter()
    with mlflow.start_run(run_name=nombre,nested=nested) as run:
        scores=cross_validate(pipe,X,y,cv=list(pliegues(train)),scoring='neg_root_mean_squared_error',return_train_score=True,n_jobs=1,error_score='raise')
        pipe.fit(X,y); segundos=time.perf_counter()-inicio
        cv=-scores['test_score']; ent=-scores['train_score']
        metricas={'rmse_train_cv':float(ent.mean()),'rmse_cv_media':float(cv.mean()),'rmse_cv_std':float(cv.std(ddof=1)),'brecha':float(cv.mean()-ent.mean()),'segundos_entrenamiento':segundos,'rmse_train_final':root_mean_squared_error(y,pipe.predict(X))}
        mlflow.log_params({**{k:str(v) for k,v in modelo.get_params().items()},'semilla':SEMILLA,'tabla':meta['tabla'],'snapshot':meta['snapshot_utc'],'sha256':meta['sha256'],'corte':meta['corte']})
        try:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
        except (FileNotFoundError,subprocess.CalledProcessError):
            commit=os.environ.get('GIT_COMMIT','sin_commit_registrado')
            dirty=os.environ.get('GIT_DIRTY','true')=='true'
        mlflow.set_tags({'fase':fase,'familia':nombre,'git_commit':commit,'git_dirty':str(dirty)})
        for source in sorted((ROOT/'src').glob('*.py')):
            mlflow.log_artifact(str(source),artifact_path='codigo')
        mlflow.log_artifact(str(ROOT/'requirements.txt'),artifact_path='codigo')
        mlflow.log_dict(meta,'snapshot.json')
        mlflow.log_metrics(metricas); mlflow.log_dict({'rmse_cv':cv.tolist()},'pliegues.json')
        info=mlflow.sklearn.log_model(pipe,name='pipeline',skops_trusted_types=['numpy.dtype'],signature=infer_signature(X.iloc[:5],pipe.predict(X.iloc[:5])),input_example=X.iloc[:5])
        return {'modelo':nombre,'run_id':run.info.run_id,'model_uri':info.model_uri,**metricas}

def evaluar_candidatos(train,meta):
    filas=[registrar(n,m,train,meta,'baseline' if n in ['dummy_media','regla_cero'] else 'candidato') for n,m in candidatos().items()]
    df=pd.DataFrame(filas); df.to_csv(ROOT/'docs/candidatos.csv',index=False)
    # Faltan la quinta familia fundacional y el experimento/justificación del LLM.
    return df

def ajustar(train,meta,mejores,n_iter=30):
    import mlflow
    if len(set(mejores))!=3 or n_iter<30: raise ValueError('La guía exige 3 modelos y >=30 configuraciones cada uno')
    espacios={'ridge':{'alpha':loguniform(1e-4,1e4)},
              'random_forest':{'n_estimators':randint(100,501),'max_depth':randint(3,25),'min_samples_leaf':randint(1,30)},
              'boosting':{'learning_rate':loguniform(.01,.3),'max_leaf_nodes':randint(8,65),'l2_regularization':loguniform(1e-5,10)},
              'mlp':{'alpha':loguniform(1e-6,1),'learning_rate_init':loguniform(1e-4,1e-2),'hidden_layer_sizes':[(32,),(64,),(64,32),(128,64)]}}
    mlflow.set_tracking_uri(os.environ.get('MLFLOW_TRACKING_URI','http://localhost:5001')); mlflow.set_experiment(os.environ.get('MLFLOW_EXPERIMENT_NAME','portafolio-inversiones'))
    filas=[]
    for nombre in mejores:
        if nombre not in espacios: raise ValueError(f'Definir espacio de búsqueda para {nombre}')
        with mlflow.start_run(run_name='tuning_'+nombre):
            mlflow.set_tag('fase','tuning_padre')
            for cfg in ParameterSampler(espacios[nombre],n_iter=n_iter,random_state=SEMILLA):
                filas.append(registrar(nombre,candidatos()[nombre].set_params(**cfg),train,meta,'tuning',nested=True))
    df=pd.DataFrame(filas); df.to_csv(ROOT/'docs/tuning.csv',index=False)
    exp=mlflow.get_experiment_by_name(os.environ.get('MLFLOW_EXPERIMENT_NAME','portafolio-inversiones'))
    mlflow.search_runs([exp.experiment_id]).to_csv(ROOT/'docs/corridas.csv',index=False)
    return df
