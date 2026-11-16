"""Empaqueta código, diagramas, memo y evidencia sin credenciales ni artefactos locales."""
from pathlib import Path
import hashlib,json,zipfile,re
RAIZ=Path(__file__).resolve().parents[1]
SALIDA=RAIZ/'entregables';SALIDA.mkdir(exist_ok=True)
OMITIR={'.env','.env_encoded','secrets','.venv','__pycache__','.DS_Store','target','logs','dbt_packages','.structurizr','entregables','datos','salida','.user.yml'}
archivos=[]
for p in sorted(RAIZ.rglob('*')):
 if not p.is_file() or any(x in OMITIR for x in p.relative_to(RAIZ).parts):continue
 if p.suffix in {'.pyc','.p8','.pem','.duckdb','.parquet'}:continue
 archivos.append(p)
for p in archivos:
 if p.suffix in {'.py','.yml','.json','.md','.txt','.sql','.csv','.example','.log'}:
  t=p.read_text(errors='ignore')
  if re.search(r'-----BEGIN (?:RSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/=]{40}',t):
   raise ValueError(f'Llave privada detectada: {p.relative_to(RAIZ)}')
# Si hay credenciales locales, impedir que sus valores aparezcan en la entrega.
secretos=[]
if (RAIZ/'.env').exists():
 for linea in (RAIZ/'.env').read_text().splitlines():
  nombre,sep,valor=linea.partition('=')
  if sep and nombre.strip() in {'SNOWFLAKE_PRIVATE_KEY','SNOWFLAKE_PASSWORD','SNOWFLAKE_TOKEN','KESTRA_CLAVE','KESTRA_DB_PASSWORD'} and valor.strip():
   secretos.append(valor.strip().encode())
for p in archivos:
 if any(valor in p.read_bytes() for valor in secretos):
  raise ValueError(f'Valor de credencial local detectado en: {p.relative_to(RAIZ)}')
manifest={str(p.relative_to(RAIZ)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos}
with zipfile.ZipFile(SALIDA/'PSet2_repositorio_Gomez_Ehmig.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in archivos:z.write(p,Path('pset_2')/p.relative_to(RAIZ))
 z.writestr('MANIFEST_SHA256.json',json.dumps(manifest,indent=2))
print(f'{len(archivos)} archivos incluidos; ZIP y manifiesto creados en entregables/')
