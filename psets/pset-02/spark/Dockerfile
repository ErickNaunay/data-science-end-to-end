# Imagen de Spark para el maestro, el trabajador y el job de la OBT. Incluye el conector
# de Snowflake para Spark y su driver JDBC (todos los nodos los necesitan).
#   docker compose build spark-master
# 3.1.9 es la ultima version del conector publicada para Scala 2.12 (la de Spark 3.5.x);
# las 3.2.x son solo para Scala 2.13. Si cambia, ajustala con --build-arg.
ARG SPARK_IMAGE=apache/spark:3.5.3-python3
FROM ${SPARK_IMAGE}

ARG SPARK_SNOWFLAKE_VERSION=3.1.9
ARG SNOWFLAKE_JDBC_VERSION=3.28.0

ADD --chmod=644 https://repo1.maven.org/maven2/net/snowflake/spark-snowflake_2.12/${SPARK_SNOWFLAKE_VERSION}/spark-snowflake_2.12-${SPARK_SNOWFLAKE_VERSION}.jar /opt/spark/jars/
ADD --chmod=644 https://repo1.maven.org/maven2/net/snowflake/snowflake-jdbc/${SNOWFLAKE_JDBC_VERSION}/snowflake-jdbc-${SNOWFLAKE_JDBC_VERSION}.jar /opt/spark/jars/

COPY jobs/ /opt/jobs/
WORKDIR /opt/jobs
