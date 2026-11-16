"""Genera docs/PSet2_memo_Gomez_Ehmig.pdf (6 paginas tecnicas + anexos) y
docs/PSet2_memo_fuente.txt (texto plano del mismo memo, solo salida).

Las cifras se leen de la evidencia en docs/corrida/ y docs/calidad/; el texto se edita aqui.
Uso, desde psets/pset-02:
  uv run python scripts/generar_memo.py
"""
from pathlib import Path
import csv,json
from xml.sax.saxutils import escape
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,NextPageTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
R=Path(__file__).resolve().parents[1]; D=R/'docs'; E=D/'corrida'
metrics={r['metrica']:float(r['valor']) for r in csv.DictReader((E/'dq_metricas.csv').open())}
counts={r['t']:int(r['filas']) for r in csv.DictReader((E/'conteos_por_capa.csv').open())}
build_evidence=E/('run_results_gold.json' if (E/'run_results_gold.json').exists() else 'run_results.json')
build_results=json.loads(build_evidence.read_text())['results']
passed=sum(r['status'] in ('success','pass') for r in build_results)
warned=sum(r['status']=='warn' for r in build_results)
failed=sum(r['status'] in ('fail','error') for r in build_results)
tests_count=sum(r['unique_id'].startswith('test.') for r in build_results)
models_count=sum(r['unique_id'].startswith('model.') for r in build_results)
valid=list(csv.DictReader((E/'validacion_obt.csv').open())); states=json.loads((E/'kestra_estados.json').read_text())
style=getSampleStyleSheet(); style.add(ParagraphStyle(name='TitleX',fontName='Helvetica-Bold',fontSize=21,leading=25,textColor=colors.HexColor('#17384D'),spaceAfter=14)); style.add(ParagraphStyle(name='BodyX',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=9)); style.add(ParagraphStyle(name='SmallX',fontName='Helvetica',fontSize=8,leading=10,spaceAfter=6)); style.add(ParagraphStyle(name='HeadX',fontName='Helvetica-Bold',fontSize=13,leading=17,textColor=colors.HexColor('#17384D'),spaceBefore=10,spaceAfter=8))
story=[]; plain=[]
def n(x):return f'{int(x):,}'.replace(',','.')
def p(text,sty='BodyX'):
 story.append(Paragraph(text.replace("&", "&amp;"),style[sty])); plain.append(text)
def title(text): p(text,'TitleX')
def h(text): p(text,'HeadX')
def table(headers,rows,widths):
 data=[[Paragraph(escape(str(x)),style['SmallX']) for x in row] for row in [headers]+rows]
 t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT'); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7F0F5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#17384D')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D5DEE3')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),6)])); story.append(t); story.append(Spacer(1,10)); plain.append('\n'.join(' | '.join(str(v) for v in row) for row in [headers]+rows))
def page():story.append(PageBreak())
def flow():
 d=Drawing(480,285)
 def box(x,y,w,label,fill='#E7F0F5',size=9):
  d.add(Rect(x,y,w,28,rx=3,ry=3,fillColor=colors.HexColor(fill),strokeColor=colors.HexColor('#668394')))
  d.add(String(x+w/2,y+10,label,fontName='Helvetica',fontSize=size,textAnchor='middle'))
 def arrow(x1,y1,x2,y2):
  d.add(Line(x1,y1,x2,y2,strokeColor=colors.HexColor('#526775')))
  if x2>x1:d.add(Polygon([x2-5,y2-3,x2-5,y2+3,x2,y2],fillColor=colors.HexColor('#526775')))
  else:d.add(Polygon([x2-3,y2+5,x2+3,y2+5,x2,y2],fillColor=colors.HexColor('#526775')))
 for x,label in [(5,'Yahoo Finance'),(165,'Composición histórica'),(325,'Listados de bolsa')]:box(x,252,150,label)
 d.add(Rect(5,5,230,225,fillColor=None,strokeColor=colors.HexColor('#17384D')))
 d.add(String(120,215,'Docker Compose local',fontName='Helvetica-Bold',fontSize=10,textAnchor='middle'))
 box(15,175,210,'Kestra: schedule / flows / retry')
 box(15,138,210,'Postgres: estado de Kestra','#F5F7F8')
 box(15,97,210,'Tarea Python: ingesta')
 box(15,56,210,'Tarea dbt Core: SQL + tests')
 box(15,15,210,'Spark: driver + master + worker')
 d.add(Rect(280,5,195,225,fillColor=None,strokeColor=colors.HexColor('#17384D')))
 d.add(String(378,215,'Snowflake: PORTAFOLIO',fontName='Helvetica-Bold',fontSize=10,textAnchor='middle'))
 for y,label in [(175,'RAW'),(138,'BRONZE / staging'),(97,'SILVER'),(56,'GOLD / star schema'),(15,'OBT + validación')]:box(290,y,175,label)
 for y in [175,138,97]:arrow(378,y,378,y-9)
 arrow(80,252,80,230);arrow(240,252,160,230);arrow(400,252,220,230)
 arrow(225,111,290,189);arrow(225,70,290,152);arrow(225,29,290,29)
 d.add(String(252,119,'carga',fontSize=8,textAnchor='middle'))
 d.add(String(253,77,'SQL',fontSize=8,textAnchor='middle'))
 d.add(String(253,18,'escribe',fontSize=7,textAnchor='middle'))
 d.add(Line(290,70,225,41,strokeColor=colors.HexColor('#526775')))
 d.add(Polygon([225,41,230,46,232,41],fillColor=colors.HexColor('#526775')))
 d.add(String(253,53,'lee Gold',fontSize=7,textAnchor='middle'))
 return d

title('PSet 2 | Pipeline de datos end-to-end')
p('Allan Paul Gómez Ehmig · 00351916<br/>MSDS 6003 · USFQ · Verificación: 15 de noviembre de 2026 (Ecuador)','SmallX')
h('1. Arquitectura')
p('El pipeline prepara datos para la decisión mensual de un asesor de inversiones: seleccionar acciones del S&P 500 vinculadas a la NYSE. La aprobación del inversionista y el entrenamiento de modelos quedan fuera de este PSet. El resultado es una OBT de acción por mes, junto con el star schema que permite auditar sus insumos.')
story.append(flow())
p('Figura 1. Infraestructura implementada y flujo de datos. Kestra orquesta ingesta, dbt y Spark. dbt ejecuta las tres transiciones RAW-Bronze-Silver-Gold. Los anexos A-C incorporan el flujo detallado y las vistas C4 de contexto y contenedores, generadas desde docs/structurizr/workspace.dsl.','SmallX')
p('Docker Compose mantiene Kestra, Postgres y Spark maestro/trabajador. Kestra ejecuta tres imágenes de tarea: ingesta en Python, dbt Core y el driver Spark. Postgres conserva el estado del orquestador; los datos analíticos residen en Snowflake, base PORTAFOLIO, esquemas RAW, BRONZE, SILVER, GOLD, CALIDAD y OBT.')
p('La autenticación de Snowflake usa un usuario de servicio y llave privada. Las credenciales llegan por variables de entorno o secretos de Kestra; no forman parte del repositorio. El checkout usa psets/pset-02/; el ZIP exporta pset_2/, como indica la guía.')
page(); title('2. Ingesta')
table(['Fuente','Grano / uso'],[['Yahoo Finance (yfinance)','OHLCV por símbolo y fecha; ^GSPC, ^NYA y ^IRX como referentes.'],['chinobing/historical_sp500_constituents','Foto fechada de la lista de miembros; incluye empresas que salieron del índice.'],['rreichel3/US-Stock-Symbols','Símbolo por snapshot del listado actual; no prueba la bolsa histórica.'],['Seeds versionados','Calendario NYSE y equivalencias de símbolos.']],[190,290])
p('La extracción normaliza punto, barra y guion en los símbolos y traduce cambios de ticker mediante un seed. RAW conserva cargas append-only con LOTE_ID e INGESTA_TS (precio por símbolo-fecha-lote; fotos y listados por lote); una recarga aumenta las filas crudas, pero Bronze conserva la versión más reciente por clave. Esto permite repetir una ventana sin duplicar el hecho analítico.')
p('Frente al PSet 1 se añadieron chinobing (composición histórica, que el PSet 1 exigía sin nombrar fuente) y rreichel3 (bolsa); el respaldo de Kaggle no hizo falta.','SmallX')
h('Trigger y frecuencia de ejecución')
p('El trigger cierre_nyse usa cron 30 18 * * 1-5 y zona America/New_York: lunes a viernes a las 18:30, después del cierre habitual. El cron no excluye feriados bursátiles. ingesta_diaria consulta desde fecha menos 11 días naturales hasta fecha, ambos inclusive; los lunes carga también composición y listados. recoverMissedSchedules=ALL configura la recuperación de horarios perdidos al reiniciar Kestra. Se verificó por API, no mediante un disparo del reloj en su horario real.')
h('Manejo de errores y retries')
p('Python descarga grupos de 100 símbolos y realiza hasta tres intentos ante excepciones. Registra OK, SIN_DATOS o ERROR en RAW.INGESTA_LOG. Si más del 10 % de los grupos agota sus intentos, la tarea falla; SIN_DATOS no dispara por sí solo ese fallo. Por eso una ejecución exitosa no garantiza cobertura completa.')
p('Kestra reintenta la tarea diaria con espera exponencial desde 2 min, tope 30 min y maxAttempts=4. En transformar, dbt configura maxAttempts=2 con espera constante de 1 min; Spark, maxAttempts=2 y 2 min. Si persiste el error, el flow registra ERROR. El subflow se espera y propaga el fallo (wait y transmitFailed); si dbt falla, Spark no comienza. Se revisan logs de Kestra y la bitácora RAW para decidir la recuperación.')
h('Backfill de datos históricos')
p('backfill_historico se lanza por UI o API, sin trigger periódico, con anio_desde y anio_hasta (2010-2026 por defecto). Un bucle shell carga cada año y solo al finalizar ejecuta transformar una vez. Configura espera exponencial desde 5 min, tope 1 h y maxAttempts=3. El retry repite toda la tarea, no solo el año fallido. Para reanudar manualmente, se consulta el último año en los logs y se fija anio_desde a ese año. RAW conserva lo ya cargado; Bronze deduplica por clave, evitando duplicar el hecho analítico.')
h('Evidencia operativa')
p('Backfill histórico SUCCESS 3Fp8GRgzmNcyj7Xnd5GJf5; retry fallido 7LTsUVocdrwvwyhQxiiC4H. Últimas corridas (15-nov-2026, imágenes en Python 3.11): ingesta_diaria 5mNgM5uCz2x5OjKgoFPdgs recargó once días (RAW +5.050 filas, Gold sin cambios: deduplicación comprobada); transformar 4OsR2Nj3JNW42qJGrvNj1, ya con forward-fill, SUCCESS.','SmallX')
p(f'Última construcción dbt: {passed} resultados correctos, {warned} advertencia(s) y {failed} errores ({models_count} modelos, 2 seeds, {tests_count} tests). Evidencia en docs/corrida/: kestra_transformar_4OsR2Nj3.txt y {build_evidence.name}. La frescura aprobó cuatro fuentes; no garantiza cobertura.','SmallX')
page(); title('3. Data Quality')
p('scripts/diagnosticar_calidad.py consulta RAW antes de la limpieza dbt y perfila por separado las capas posteriores: 22 tablas, 236 columnas. Guarda inventario, porcentajes por columna, decisiones, SQL y query IDs en docs/calidad/. RAW ya contiene el tipado de ingesta; el diagnóstico no escribe ni imputa datos. La tabla cubre las cuatro dimensiones: completitud, precisión, consistencia y validez.')
perfil={(r['tabla'],r['columna']):r for r in csv.DictReader((D/'calidad/perfil_columnas.csv').open())}
problemas=list(csv.DictReader((D/'calidad/problemas_raw.csv').open()))
def tasa(v):
 v=float(v); s=f'{v:.2f}' if v>=0.01 or v==0 else f'{v:.6f}'.rstrip('0')
 return s.replace('.',',')
def problema(inicio):return next(r for r in problemas if r['problema'].startswith(inicio))
def evidencia(r):return f"{n(r['afectados'])}/{n(r['denominador'])} ({tasa(r['porcentaje'])} %)"
open_raw=perfil[('RAW.PRECIOS_DIARIOS','OPEN')]
flags=[perfil[('RAW.LISTADOS_BOLSA',c)] for c in ['ES_ETF','ES_PRUEBA']]
raw_tab=next(r for r in csv.DictReader((D/'calidad/perfil_tablas.csv').open()) if r['tabla']=='RAW.PRECIOS_DIARIOS')
por_fecha=D/'calidad/outliers_mad_por_fecha.csv'
top_fechas=list(csv.DictReader(por_fecha.open()))[:3] if por_fecha.exists() else []
eventos=('Días con más acciones marcadas: '+', '.join(f"{r['fecha']} ({r['acciones_marcadas']})" for r in top_fechas)+'; detalle en calidad/outliers_mad_*.csv') if top_fechas else 'Detalle en calidad/'
max_faltantes=max(float(perfil[('RAW.PRECIOS_DIARIOS',c)]['faltantes_pct']) for c in ['OPEN','HIGH','LOW','CLOSE','ADJ_CLOSE','VOLUME'])
mad=next((r for r in problemas if r['problema'].startswith('Retornos con z-score robusto')),None);iqr=problema('Retornos fuera');huecos=problema('Sesiones sin fila');sin_datos=problema('Símbolos sin precios');fotos=problema('Fotos de composición')
DIM={'completitud':'Completitud','precision':'Precisión','consistencia':'Consistencia','validez':'Validez'}
table(['Dimensión','Problema / evidencia RAW','Acción en dbt','Justificación'],[
 ['Completitud',f"ES_ETF / ES_PRUEBA: {tasa(flags[0]['faltantes_pct'])} % / {tasa(flags[1]['faltantes_pct'])} % faltantes en {n(flags[0]['filas'])} filas.",'Bronze conserva NULL; convierte solo Y/N conocidos.','El JSON no aporta los flags. Se corrigió el reemplazo implícito por false.'],
 ['Validez',f"OPEN inválido: {n(open_raw['invalidos'])}/{n(open_raw['filas'])} ({tasa(open_raw['invalidos_pct'])} %). Máximo de faltantes por columna OHLCV: {tasa(max_faltantes)} %.",'Silver excluye observaciones inválidas; conserva RAW.','Un precio no positivo impide log-precios. No confundir filas presentes con cobertura completa.'],
 ['Consistencia (unicidad)',f"Reingestas: {tasa(raw_tab['redundantes_pct'])} % de filas de precios redundantes.",'Bronze elige última ingesta/lote por clave.','RAW append-only conserva auditoría; no duplicar hechos.'],
 ([DIM[mad['dimension']],'Retornos atípicos, z-score robusto (MAD) > 3,5 por acción: '+evidencia(mad)+'. Con 1,5 IQR: '+evidencia(iqr)+'.','Marcar, sin borrado ni winsorización automática; cotejar con eventos reales.','Criterio del PSet 1. '+eventos+'.'] if mad else
  [DIM[iqr['dimension']],'Retornos atípicos (1,5 IQR por acción): '+evidencia(iqr)+'.','Revisar, sin borrado ni winsorización automática.','Colas financieras reales pueden ser atípicas; IQR no prueba error.']),
 [DIM[huecos['dimension']],'Sesiones sin fila, entre primera y última cotización: '+evidencia(huecos)+'.','Silver: grilla NYSE; forward-fill en huecos cortos, excluir largos.','No inventar historias de empresas sin precios. Denominador: sesiones esperadas en vida observada.'],
 [DIM[sin_datos['dimension']],'Solicitudes SIN_DATOS: '+evidencia(sin_datos)+'.','Conservar bitácora y limitación de cobertura.','0 % de nulos en precios recibidos no significa que Yahoo respondió a todo.'],
 [DIM[fotos['dimension']],'Fotos con menos de 495 símbolos: '+evidencia(fotos)+'.','No completar miembros sin fuente verificable.','Métrica RAW; difiere de Bronze tras normalizar/deduplicar símbolos.']],[62,170,118,130])
p('Staging/Bronze se genera con dbt: tipos, normalización, claves y deduplicación. Silver continúa la limpieza: rellena hacia adelante (forward-fill, como fija el PSet 1) log-cierre y log-apertura ajustados en huecos internos de hasta cinco sesiones, con marca; no imputa OHLC original ni volumen. Huecos largos se excluyen y el retorno al reanudar queda nulo. ^IRX usa el último valor observado. El snapshot registra 0 % de días imputados.')
p('Precisión: coherencia OHLC y retornos son pruebas de plausibilidad, no contraste oficial. El valor imputado no usa precios futuros; solo el largo del hueco (imputar o excluir) mira el siguiente día observado. La construcción dbt actual conserva la advertencia de cobertura: 1.615 fechas con menos de 400 miembros con precio. Los flags desconocidos de listados permanecen NULL. Verificación con eventos reales: los días con más outliers MAD son de marzo de 2020 (COVID-19) y abril de 2025 (aranceles de EE. UU.), y casos como GL, PCG, OXY y FISV corresponden a noticias documentadas. El diagnóstico usa solo sesiones consecutivas: una acción fuera del índice puede tener años sin datos, y Silver tampoco convierte ese salto en retorno.','SmallX')
page(); title('4. Transformaciones y modelado')
p('Bronze es staging: tipos, normalización y deduplicación. Silver integra calendario, membresía, precios válidos y retornos. Gold publica dos hechos diarios y tres dimensiones. Precios se relaciona con acción, fecha y membresía; mercado comparte fecha. Todas las dimensiones de consumo están en Gold. source() y ref() ordenan el DAG sin dependencias inversas entre capas.')
img=Image(str(D/'modelo_dimensional.png')); ratio=img.imageHeight/img.imageWidth; img.drawWidth=480; img.drawHeight=480*ratio; story.append(img)
p('Figura 2. Modelo dimensional Gold: dos estrellas comparten fecha. La membresía histórica también es una dimensión Gold; su clave es opcional fuera del índice. PK/FK lógicas, verificadas con dbt. Fuente: docs/modelo_dimensional.dot.','SmallX')
table(['Objeto','Grano','Filas'],[['DIM_ACCION','Un símbolo normalizado (proxy de acción)',n(counts['GOLD.DIM_ACCION'])],['DIM_FECHA','Un día bursátil',n(counts['GOLD.DIM_FECHA'])],['DIM_MEMBRESIA_SP500','Un intervalo por símbolo',n(counts['GOLD.DIM_MEMBRESIA_SP500'])],['FCT_PRECIOS_DIARIOS','Una acción por día bursátil',n(counts['GOLD.FCT_PRECIOS_DIARIOS'])],['FCT_MERCADO_DIARIO','Un día bursátil',n(counts['GOLD.FCT_MERCADO_DIARIO'])]],[175,220,85])
p('Precios tiene grano acción-fecha en sesiones conservadas. Los tests not_null, unique y relationships verifican claves; los tests de negocio impiden intervalos solapados, fechas fuera de vigencia y membresías de otra acción. Los joins conservan filas. DIM_ACCION tiene bolsa actual, no historia SCD2. Silver une 11 huecos de membresía hasta siete días: hipótesis de omisión. No sumar precios ni retornos entre acciones.')
page(); title('5. Spark y OBT')
p('Spark lee cuatro de las cinco tablas Gold (los dos hechos, DIM_ACCION y DIM_FECHA) mediante el conector Snowflake, calcula ventanas históricas por acción y selecciona una fila por mes cerrado. Añade el resumen mensual, referentes de mercado y atributos de acción, y escribe OBT.OBT_ACCION_MES y OBT.VALIDACION_OBT en Snowflake.')
table(['Resultado','Valor verificado'],[['Filas de la OBT',n(counts['OBT.OBT_ACCION_MES'])],['Columnas','43'],['Filas elegibles','58.628'],['Controles de joins y grano',f"{sum(r['ok'].lower() == 'true' for r in valid)} de {len(valid)} correctos"],['Clave de la OBT','accion_key + anio_mes'],['Objetivo','ret_log_mes_siguiente; nulo sin mes consecutivo']],[230,250])
p('Los controles verifican unicidad de dimensiones, hechos y mercado mensual; conservación de filas al unir hechos con fechas, cierres con resúmenes, mercado y atributos; cobertura de todos los meses en mercado y unicidad/conteo final de la OBT. Si un control falla, se guarda la validación y no se sobrescribe la OBT anterior; esto no garantiza atomicidad ante fallos durante la escritura.')
p('Las features incluyen retorno del mes, momentum 12-1, volatilidades de 21 y 63 observaciones, drawdown, volumen y liquidez. La elegibilidad exige membresía, NYSE o bolsa desconocida marcada, cotización al cierre, 200 retornos no nulos en 252 filas y 15 filas diarias en el mes (incluyen imputadas si existen). Las volatilidades excluyen días imputados. Las ventanas basadas en filas requieren cautela después de huecos excluidos: no equivalen siempre a días consecutivos.')
p('El objetivo es el retorno log del mes siguiente, acorde con el rebalanceo mensual. El corte del PSet 1 es 2023-12-31: DIM_FECHA.conjunto marca entrenamiento hasta esa fecha y prueba desde enero de 2024 (variable fecha_corte de dbt; FECHA_CORTE_ENTRENAMIENTO lo cambia sin tocar código, porque el corte está sujeto a cambios). objetivo_cruza_corte marca el mes cuyo target invade prueba. PSet 3 debe dividir por fecha del objetivo y excluir columnas de futuro de X; que la OBT contenga target y referentes futuros no los convierte en predictores válidos.')
h('Cuándo usar cada representación')
p('El star schema sirve para auditoría, reportes de cobertura y consultas por acción/fecha sin repetir atributos. La OBT sirve para construir matrices de entrenamiento y evaluación con una unidad de decisión mensual. Las cinco tablas Gold bastan para este uso: la membresía ya está resuelta en el hecho. No añadir dimensiones sin uso y fuente histórica fiable. La OBT repite atributos para facilitar ML; Gold conserva el detalle diario. Detalle: docs/revision_obt.md.')
page(); title('6. Batch vs. streaming')
p('PSet 1 revisado con feedback (14-nov-2026, secciones 3.1, 3.3 y 3.5) plantea apoyo al asesor, con revisión y aprobación del inversionista. No es trading de alta frecuencia ni ejecución automática de órdenes. El horizonte de un mes se igualó al periodo de rebalanceo, según el feedback del PSet 1.')
table(['Proceso','Frecuencia / alcance'],[['Datos y OBT','Batch L-V 18:30 Nueva York; el cron incluye feriados. Datos diarios, OBT de grano mensual.'],['Inferencia y propuesta de compra','Mensual: ranking, 10 acciones, pesos, riesgo y cambios; revisión del asesor y aprobación del cliente.'],['Reporte de desempeño','Mensual: Sharpe y drawdown frente a índices.'],['Reentrenamiento','Frecuencia no fijada en PSet 1; experimentos offline. No confundir con inferencia.']],[155,325])
p('Se consumen cierres diarios y se decide mensualmente: procesar por lotes permite validar y reintentar antes de la revisión, con latencia de horas. PSet 1 no fija una hora límite. La inferencia y publicación mensual son el diseño de negocio; PSet 2 implementa datos, no un scheduler de scoring ni el reporte de compra.')
p('El código reconoce mes cerrado al recibir datos de un mes posterior: no garantiza recomendar antes de la primera apertura del mes. Para ello habría que detectar el cierre con el calendario completo y validar disponibilidad. El target es el mes calendario siguiente (21 sesiones es aproximado); la compra debe usar un precio posterior a la disponibilidad del reporte. Detalle y fuentes: docs/temporalidad_batch.md.')
p('Streaming se justificaría si el caso cambiara a alertas intradía de riesgo que exigieran actuar en segundos o minutos. Requeriría fuente intradía, procesamiento continuo con estado, eventos tardíos/duplicados, serving y control de latencia. No exige trading de alta frecuencia; sí una decisión que no pueda esperar al lote. Una recomendación diaria aún podría resolverse con batch diario.')
h('7. Limitaciones')
p('Persisten cobertura incompleta, bolsa actual sin historia SCD2, equivalencias por verificar y revisiones de precios ajustados. La composición histórica reduce, pero no elimina, sesgos. La regla que excluye huecos largos conoce el día de reanudación; en inferencia en tiempo real habría que aplicarla con retraso. La precisión se evalúa por plausibilidad, no con cotizaciones oficiales; ^IRX se aproxima como tasa diaria simple.')
p('Las incidencias de memoria y sus soluciones están en docs/cumplimiento.md: ejecutor Spark 2 GB, driver 1 GB y un core; ejecutar PSet 2 y PSet 3 separadamente. README.md documenta configuración y ejecución; docs/corrida/ conserva evidencia. El ZIP excluye credenciales, datos completos y cachés. El versionado y la publicación se registran en docs/revision_entrega.md.')
p('Fuentes: CD_PSet_2.pdf; PSet1_memo_Gomez_Ehmig_v2 (psets/pset-01/feedback/, revisión 14-nov-2026); código kestra/, dbt/, spark/; evidencia docs/corrida/; calidad docs/calidad/README.md. Datos: Yahoo/yfinance, github.com/chinobing/historical_sp500_constituents, github.com/rreichel3/US-Stock-Symbols; calendario: github.com/rsheftel/pandas_market_calendars. Equivalencias: seed local, no fuente externa independiente.','SmallX')

# Anexos de arquitectura: fuera del cuerpo tecnico de seis paginas.
story.append(NextPageTemplate('anexo')); page()
for i,(heading,path,caption,key) in enumerate([
 ('Anexo A. Flujo implementado',D/'arquitectura_vertical.png','Fuente → Kestra → RAW → dbt → BRONZE → dbt → SILVER → dbt → GOLD → Spark → OBT. Las flechas punteadas distinguen dependencias de control y calidad. Versión vertical de docs/arquitectura.dot (mismo contenido que docs/arquitectura.png), para que se lea impresa.',None),
 ('Anexo B. C4 - contexto',D/'structurizr/export/structurizr-contexto.png','Modelo de contexto exportado del workspace.dsl validado con Structurizr. El sistema agrupa el pipeline local y su almacenamiento analítico SaaS.',D/'structurizr/export/structurizr-contexto-key.png'),
 ('Anexo C. C4 - contenedores',D/'structurizr/export/structurizr-contenedores.png','Servicios persistentes: Kestra, Postgres, maestro y trabajador Spark. Tareas efímeras: ingesta, dbt y driver Spark. Snowflake es SaaS externo a Docker. El driver coordina el clúster; los ejecutores procesan las particiones.',D/'structurizr/export/structurizr-contenedores-key.png')
]):
 if i:page()
 title(heading)
 im=Image(str(path));scale=min(1100/im.imageWidth,610/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;story.append(im);story.append(Spacer(1,16));p(caption)
 if key:
  im=Image(str(key));scale=min(230/im.imageWidth,100/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;story.append(im)

def footer(c,doc):
 width,height=c._pagesize
 c.setStrokeColor(colors.HexColor('#D5DEE3')); c.line(42,40,width-42,40); c.setFont('Helvetica',8); c.setFillColor(colors.HexColor('#526775')); c.drawString(42,27,'PSet 2 · Portafolio de inversiones · Gómez Ehmig'); c.drawRightString(width-42,27,str(doc.page) if doc.page<=6 else 'Anexo '+str(doc.page-6))
doc=BaseDocTemplate(str(D/'PSet2_memo_Gomez_Ehmig.pdf'),pagesize=(595,842),title='PSet 2 - Pipeline de datos',author='Allan Paul Gómez Ehmig')
doc.addPageTemplates([
 PageTemplate(id='memo',frames=[Frame(57,52,480,748,leftPadding=6,rightPadding=6,topPadding=6,bottomPadding=6)],onPage=footer,pagesize=(595,842)),
 PageTemplate(id='anexo',frames=[Frame(36,52,1118,748)],onPage=footer,pagesize=(1190,842))])
doc.build(story)
(D/'PSet2_memo_fuente.txt').write_text('\n\n'.join(plain))
print('Memo generado: cuerpo tecnico y anexos')
