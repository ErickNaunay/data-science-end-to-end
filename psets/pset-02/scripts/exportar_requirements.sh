#!/usr/bin/env bash
# Regenera los requirements.txt del PSet 2 desde uv.lock (no se editan a mano).
#
# Uso, desde psets/pset-02:
#   uv lock                               # solo si cambiaste pyproject.toml
#   bash scripts/exportar_requirements.sh
#
# Produce:
#   requirements.txt          entorno local (pipeline + pruebas locales con Spark + memo)
#   kestra/requirements.txt   solo la imagen pset2-ingesta (grupo "ingesta")
# Ambos con versiones exactas (==) tomadas del mismo uv.lock.
set -euo pipefail
cd "$(dirname "$0")/.."

uv export --frozen --format requirements-txt --no-hashes --no-emit-project \
    --no-dev --group pruebas-locales --output-file requirements.txt > /dev/null
uv export --frozen --format requirements-txt --no-hashes --no-emit-project \
    --only-group ingesta --output-file kestra/requirements.txt > /dev/null

echo "OK: requirements.txt y kestra/requirements.txt regenerados desde uv.lock"
