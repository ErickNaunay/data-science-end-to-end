"""Empaqueta la entrega del PSet 2 como pset_2/ (estructura que pide CD_PSet_2.pdf), con un
manifiesto SHA-256, sin credenciales ni artefactos locales.

Solo incluye archivos versionados en git (git ls-files): el ZIP corresponde exactamente al
commit (y al tag pset-02), sin cachés, entornos ni datos locales. Fuera de un checkout de git
(por ejemplo, al reempaquetar el ZIP extraído) recorre la carpeta con la lista de exclusiones.

Uso, desde psets/pset-02:
  python scripts/empaquetar_entrega.py
Salida: entregables/PSet2_repositorio_Gomez_Ehmig.zip (entregables/ está en .gitignore).
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / 'entregables'
OMITIR = {'.env', '.env_encoded', 'secrets', '.venv', '__pycache__', '.DS_Store', 'target', 'logs',
          'dbt_packages', '.structurizr', 'entregables', 'datos', 'salida', '.user.yml',
          '.pytest_cache'}
SUFIJOS_OMITIDOS = {'.pyc', '.p8', '.pem', '.duckdb', '.parquet'}
CREDENCIALES = {'SNOWFLAKE_PRIVATE_KEY', 'SNOWFLAKE_PASSWORD', 'SNOWFLAKE_TOKEN', 'KESTRA_CLAVE',
                'KESTRA_DB_PASSWORD'}


def listar_archivos() -> list[Path]:
    try:
        salida = subprocess.run(['git', 'ls-files', '-z', '--', '.'], cwd=RAIZ, check=True,
                                capture_output=True).stdout.decode()
        candidatos = [RAIZ / f for f in salida.split('\0') if f]
    except (OSError, subprocess.CalledProcessError):
        candidatos = sorted(RAIZ.rglob('*'))
    # Las exclusiones se aplican también a lo versionado, como segunda barrera.
    return sorted(p for p in candidatos
                  if p.is_file()
                  and not any(x in OMITIR for x in p.relative_to(RAIZ).parts)
                  and p.suffix not in SUFIJOS_OMITIDOS)


def verificar_sin_secretos(archivos: list[Path]) -> None:
    for p in archivos:
        if p.suffix in {'.py', '.yml', '.json', '.md', '.txt', '.sql', '.csv', '.example', '.log'}:
            if re.search(r'-----BEGIN (?:RSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/=]{40}',
                         p.read_text(errors='ignore')):
                raise ValueError(f'Llave privada detectada: {p.relative_to(RAIZ)}')
    # Si hay credenciales locales, impedir que sus valores aparezcan en la entrega.
    secretos = []
    if (RAIZ / '.env').exists():
        for linea in (RAIZ / '.env').read_text().splitlines():
            nombre, sep, valor = linea.partition('=')
            if sep and nombre.strip() in CREDENCIALES and valor.strip():
                secretos.append(valor.strip().encode())
    for p in archivos:
        if any(valor in p.read_bytes() for valor in secretos):
            raise ValueError(f'Valor de credencial local detectado en: {p.relative_to(RAIZ)}')


def main() -> None:
    archivos = listar_archivos()
    verificar_sin_secretos(archivos)
    SALIDA.mkdir(exist_ok=True)
    manifiesto = {str(p.relative_to(RAIZ)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in archivos}
    with zipfile.ZipFile(SALIDA / 'PSet2_repositorio_Gomez_Ehmig.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in archivos:
            z.write(p, Path('pset_2') / p.relative_to(RAIZ))
        z.writestr('MANIFEST_SHA256.json', json.dumps(manifiesto, indent=2))
    print(f'{len(archivos)} archivos incluidos; ZIP y manifiesto creados en entregables/')


if __name__ == '__main__':
    main()
