# Temporalidad del negocio y procesamiento batch

## Base documental y alcance de la verificación

Se contrastaron la propuesta local `../../pset-01/plantilla-documento-propuesta.md` (secciones 1, 3 y alcance del MVP), su README y el [memo corregido del PSet 1 en Drive](https://docs.google.com/document/d/1fg_2qYlfVj_7QgxStuleMbVpNCAj5NqB/edit), revisión 2026-11-14, guardado en la carpeta feedback. Se consultaron el contenido y el registro de cambios de esa versión. El registro identifica el ajuste H (horizonte igual al rebalanceo) como **decisión del autor**; no se atribuye al profesor una exigencia de 21 sesiones exactas. No se localizó una evaluación independiente del profesor en los archivos listados: la evidencia del feedback es la versión revisada y su registro.

El caso es apoyo al asesor, con revisión humana y aprobación del inversionista. No es trading de alta frecuencia, no ejecuta órdenes automáticamente y no necesita reaccionar a cada transacción de mercado.

## Frecuencias distintas

| Proceso | Frecuencia y salida | Estado / fundamento |
|---|---|---|
| Generación y consumo de datos | Se consumen barras OHLCV diarias e índices/tasa diarios; las operaciones subyacentes ocurren durante la sesión | El proyecto trabaja con cierres, no con ticks |
| Ingesta y transformación | Batch L–V a las 18:30 America/New_York; RAW → dbt → Gold → Spark → OBT | Implementado en Kestra; cron incluye feriados; referencia de composición y listados se refresca los lunes |
| Actualización de OBT | Se reconstruye con el pipeline diario; grano acción × mes cerrado | Reconstruir datos no ejecuta un modelo ni implica recomendaciones diarias |
| Inferencia del modelo | Una vez por ciclo mensual, sobre el mes recién cerrado, para estimar retornos del mes siguiente | Cadencia derivada del producto mensual de PSet 1; el scheduler productivo de inferencia aún no está implementado en PSet 2 |
| Propuesta / reporte para compra | Mensual: ranking, 10 acciones, pesos, volatilidad y cambios frente al portafolio anterior | MVP corregido; el asesor revisa y el inversionista aprueba antes de ejecutar en el bróker |
| Reporte de desempeño | Mensual: Sharpe y drawdown frente a índices y referencia aleatoria | Explícito en el proceso de negocio de PSet 1; distinto del reporte previo a la compra |
| Entrenamiento y reentrenamiento | Experimentos offline; no se fija frecuencia operativa en PSet 1 | No confundir con inferencia mensual. Una revisión mensual del desempeño puede decidir si procede reentrenar; sería una política futura, no una obligación ya establecida |

La propuesta mensual no obliga a operar cada mes: se respeta el umbral mínimo de cambio y la aprobación. Un informe técnico diario de calidad o frescura tampoco constituye una recomendación diaria de compra.

## Justificación de batch y latencia

Aunque el mercado genera eventos intradía, el insumo elegido se resume por sesión y la decisión se toma cada mes. Procesar después del cierre permite validar cobertura, deduplicar revisiones, ejecutar tests y reconstruir ventanas de manera reproducible antes de la revisión del asesor. La latencia requerida se mide en horas dentro del ciclo de preparación mensual, no en milisegundos. Streaming no aporta valor al objetivo actual: aumentaría operación continua, gestión de estado y tratamiento de eventos fuera de orden sin cambiar la frecuencia de decisión.

PSet 1 no establece una hora límite ni un SLA numérico para entregar la recomendación. Se propone como contrato operativo futuro: generar la propuesta después de completar y validar los datos del mes, antes de la revisión mensual acordada; si faltan datos o falla calidad, bloquear la publicación y reintentar. No afirmar que cualquier retraso de un día es irrelevante: junto al cierre mensual sí puede cambiar la fecha efectiva de compra.

## Temporalidad realmente implementada y brecha de despliegue

`SILVER.SLV_CALENDARIO_NYSE` termina en la última fecha con precios. `GOLD.DIM_FECHA` marca `mes_cerrado` cuando `anio_mes < max(anio_mes)`. Por ello, el último mes cargado nunca se considera cerrado, incluso si su última sesión ya terminó. Spark filtra por esa bandera.

En el estado verificado, Gold llega al 2026-11-13 y la OBT hasta 202610. Octubre aparece cuando se carga la primera sesión de noviembre, no necesariamente en el batch de la última sesión de octubre. En general, la OBT del mes previo queda disponible después del primer batch con precios del mes nuevo, sujeto a disponibilidad y calidad. No se garantiza entrega antes de la primera apertura del nuevo mes.

Para un despliegue que deba recomendar antes de esa apertura, hay que determinar el cierre con el calendario NYSE completo (no solo la fecha máxima observada), comprobar disponibilidad de la última sesión y activar inferencia únicamente después de los controles. Esa modificación no se implementa en esta revisión documental. La inferencia debe admitir filas del mes cerrado cuyo target futuro sea nulo: el filtrado `TARGET.notna()` de `pset-03/src/pipeline.py::preparar` pertenece al entrenamiento y no sirve como preparación de scoring productivo.

PSet 1 llama al horizonte “1 mes (21 días hábiles)”. Spark implementa **el mes calendario siguiente con sesiones NYSE**, cuyo número de sesiones varía; 21 es una aproximación, no una constante del target. Además, un backtest no debe simular compra al cierre ya usado para construir features: deberá aplicar el precio ejecutable posterior a la disponibilidad del reporte y contemplar aprobación, spread y comisiones. Esta es una brecha de evaluación/despliegue que debe resolverse antes de declarar resultados operativos, no una razón para usar streaming.

## Qué cambio justificaría streaming

Sería otro requisito de negocio: por ejemplo, alertar al asesor durante la sesión ante una ruptura del límite de riesgo que deba revisarse en segundos o minutos y donde esperar al batch produzca una pérdida medible. No hace falta convertirse en trading de alta frecuencia para justificar alertas oportunas, pero sí demostrar una decisión accionable y un SLA incompatible con el lote. Pasar a una recomendación diaria seguiría pudiendo resolverse por batch diario.

Ese cambio requeriría una fuente intradía con disponibilidad y permisos adecuados, ingestión de eventos, procesamiento continuo por tiempo de evento, manejo de duplicados y eventos tardíos, estado y recuperación, features temporales compatibles, serving del modelo, monitoreo de latencia y un procedimiento humano de respuesta. Gold y los lotes históricos seguirían sirviendo para conciliación, auditoría y entrenamiento. Un cambio de herramienta por sí solo no justifica esa arquitectura.

## Alcance de esta revisión

Se revisó código y documentación; no se volvió a ejecutar el pipeline ni se alteraron datos, SQL de transformación o triggers. Se corrigieron comentarios que confundían fecha de observación con fecha de rebalanceo y que afirmaban que un día de latencia nunca afectaba la decisión. La evidencia de la ejecución previa de Spark sigue vigente y está en `corrida/auditoria_obt.json`.
