"""Snapshot reproducible de OBT; las credenciales se leen del entorno o .env local."""
import argparse, base64, hashlib, json, os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
RAIZ=Path(__file__).resolve().parents[1]
TABLA='PORTAFOLIO.OBT.OBT_ACCION_MES'
def exportar(destino=None):
    import snowflake.connector
    if (RAIZ/'.env').exists():
        from dotenv import load_dotenv
        load_dotenv(RAIZ/'.env')
    destino=Path(destino or RAIZ/'data/obt.parquet'); destino.parent.mkdir(parents=True,exist_ok=True)
    with snowflake.connector.connect(account=os.environ['SNOWFLAKE_ACCOUNT'],user=os.environ['SNOWFLAKE_USER'],private_key=base64.b64decode(os.environ['SNOWFLAKE_PRIVATE_KEY']),role=os.environ.get('SNOWFLAKE_ROLE','PSET2_ROL'),warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE','PSET2_WH')) as con:
        with con.cursor() as cur:
            cur.execute(f'SELECT * FROM {TABLA} ORDER BY ACCION_KEY, ANIO_MES')
            df=pd.DataFrame(cur.fetchall(),columns=[c[0].lower() for c in cur.description])
    df.to_parquet(destino,index=False)
    meta={'tabla':TABLA,'snapshot_utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(destino.read_bytes()).hexdigest(),'filas':len(df),'columnas':list(df),'corte':'2023-12-31'}
    destino.with_suffix('.json').write_text(json.dumps(meta,indent=2)); return meta

def cargar(ruta=None):
    ruta=Path(ruta or RAIZ/'data/obt.parquet')
    meta=json.loads(ruta.with_suffix('.json').read_text())
    if hashlib.sha256(ruta.read_bytes()).hexdigest()!=meta['sha256']: raise ValueError('Snapshot modificado; regenerar su procedencia')
    df=pd.read_parquet(ruta)
    if df.duplicated(['accion_key','anio_mes']).any(): raise ValueError('OBT duplicada')
    return df,meta
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--salida'); a=p.parse_args(); print(json.dumps(exportar(a.salida),indent=2))
