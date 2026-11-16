# Imagen de la tarea de ingesta. Kestra la corre como contenedor (pullPolicy NEVER),
# asi que hay que construirla antes:  docker compose build ingesta
# Se conserva Python 3.12 del borrador para no cambiar el runtime al migrar.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ /app/
ENTRYPOINT []
