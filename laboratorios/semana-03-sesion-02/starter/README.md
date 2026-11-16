# Semana 3, Sesión 2: correr la ingesta localmente con uv

`ingest_data.py` descarga tres meses de viajes de taxi de Nueva York (enero a marzo de 2023, TLC) y carga los primeros
300.000 viajes de cada mes en la tabla `viajes_taxi` de Postgres (900.000 filas en total). Estos pasos lo corren en tu
máquina con uv, sin construir la imagen de Docker. Lo único que corre en Docker es Postgres.

Todos los comandos se ejecutan **desde esta carpeta** (`laboratorios/semana-03-sesion-02/starter`).

## 1. Preparar el ambiente (una vez)

```bash
unset VIRTUAL_ENV      # evita el aviso de uv si tienes otro .venv activo
uv sync
```

- `uv sync` crea `.venv` con Python 3.14 y las dependencias de `pyproject.toml`: pandas, pyarrow, requests,
  sqlalchemy y psycopg2-binary.
- SQLAlchemy está fijado a `>=2.0.30,<2.1`. En la 2.1 una URL `postgresql://` usa el driver `psycopg` (v3) y el script
  usa `psycopg2`, así que fallaría con `No module named 'psycopg'`.

## 2. Levantar Postgres

```bash
docker run -d --name pg-database \
  -e POSTGRES_USER=taxi_user \
  -e POSTGRES_PASSWORD=taxi_pass \
  -e POSTGRES_DB=taxi_db \
  -p 5432:5432 \
  -v datos_postgres:/var/lib/postgresql/data \
  postgres:13
```

- Son los mismos valores que el servicio `pg-database` del `docker-compose.yml` de la guía.
- Si ya creaste ese `docker-compose.yml` en la carpeta de la sesión, puedes usar en su lugar
  `docker compose up -d pg-database` desde esa carpeta.
- Si el puerto 5432 está ocupado, cambia `-p 5432:5432` por `-p 5433:5432` y usa `PG_PORT=5433` en el paso siguiente.

## 3. Correr la ingesta

```bash
PG_HOST=localhost \
PG_PORT=5432 \
PG_DATABASE=taxi_db \
PG_USER=taxi_user \
PG_PASSWORD=taxi_pass \
PG_TABLE=viajes_taxi \
uv run python ingest_data.py
```

- El script reintenta la conexión hasta 10 veces, cada 3 segundos, mientras Postgres termina de arrancar.
- Descarga los tres parquet en `/tmp/datos_taxis` (si ya existen, no los vuelve a bajar) y los carga en bloques de
  100.000 filas. Necesita internet, y tarda uno o dos minutos.
- Salida final esperada: `Ingesta completa: 900,000 filas en total, tabla 'viajes_taxi', meses 2023-01, 2023-02, 2023-03.`
- Cada ejecución reemplaza la tabla `viajes_taxi` desde cero, así que se puede repetir sin duplicar filas.

## 4. Verificar

```bash
docker exec pg-database psql -U taxi_user -d taxi_db \
  -c "SELECT mes_origen, COUNT(*) FROM viajes_taxi GROUP BY mes_origen ORDER BY mes_origen;"
```

Debe mostrar 300.000 filas para cada mes (`2023-01`, `2023-02` y `2023-03`).

## 5. Limpiar

```bash
docker rm -f pg-database          # detiene y borra el contenedor
docker volume rm datos_postgres   # borra los datos cargados
rm -rf /tmp/datos_taxis           # borra los parquet descargados
```

## Notas

- Localmente corre con Python 3.14 y las versiones más recientes de las librerías. La imagen de Docker de la guía usa
  Python 3.11 y las versiones fijas de `requirements.txt`.
- El `Dockerfile` y el `requirements.txt` de esta carpeta no cambian: son los que usa Docker Compose y Terraform.
