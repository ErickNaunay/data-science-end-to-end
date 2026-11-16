# Ejecución aislada — 15 de noviembre de 2026 (Ecuador)

Resultado: **OK**, con PSet 2 apagado. Snapshot nuevo de Snowflake: 87.178 filas y 43 columnas. EDA y features ejecutados completos; 46.926 filas de entrenamiento y 11.360 de hold-out reservado, sin evaluar.

Se ejecutaron media, retorno cero y Ridge con validación temporal. MLflow guardó métricas, modelos y artefactos. Ridge se registró como `portafolio-verificacion-modelo`, versión 1, alias `verificacion`; su recarga reprodujo RMSE de entrenamiento 0,0814376930970281. Esto verifica persistencia, no selecciona un ganador.

`resultado.json` identifica snapshot, versiones y las tres corridas válidas; `resultados.csv` contiene sus métricas. `corridas.csv` conserva también el intento fallido de serialización: se corrigió autorizando explícitamente `numpy.dtype` para el modelo propio y usando columnas float. No se cuenta ese intento como resultado válido.

`docker_aislado.jsonl` muestra únicamente MLflow de PSet 3; el runner efímero ya había terminado. `docker_final.jsonl` está vacío: no quedan contenedores ejecutándose. Se conservaron los datos locales de MLflow y las tablas Snowflake.

La prueba no completa las cinco familias, las 90 configuraciones, la selección final, champion/challenger ni el memo experimental. Ver `../pendientes_entrega.md`.
