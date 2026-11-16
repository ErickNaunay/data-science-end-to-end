# docs/ — diagramas y evidencias del PSet 2

## Qué hay aquí

[Calidad por tabla y columna](calidad/README.md): diagnóstico RAW, perfil de todas
las capas, inventario, políticas de limpieza y fuentes. SQL y query IDs adjuntos.

| Elemento | Qué es | Cómo se generó |
|---|---|---|
| `arquitectura.png` / `.svg` / `.dot` | Flujo del pipeline y arquitectura medallón (Raw→Bronze→Silver→Gold→OBT) | A mano en DOT, renderizado con Graphviz |
| `modelo_dimensional.png` / `.svg` / `.dot` | Star schema de Gold (modelo de datos) | A mano en DOT, renderizado con Graphviz |
| `structurizr/workspace.dsl` | Modelo C4 del pipeline: vistas de contexto y de contenedores | Structurizr DSL |
| `structurizr/export/` | Exportes del modelo C4: Mermaid, PlantUML y PNG claro con leyenda | `structurizr/exportar_diagramas.sh` |
| `corrida/*.csv` | Evidencias consultadas en Snowflake durante la verificación de proyecto (métricas de calidad, validación de la OBT, conteos) | `scripts/exportar_metricas.py` |
| `PSet2_memo_Gomez_Ehmig.pdf` | Documento técnico de seis páginas + tres anexos | — |

El cuerpo del memo incluye el resumen de infraestructura y el modelo dimensional.
Los anexos A-C incluyen los diagramas completos: `arquitectura.png` explica el
flujo y la arquitectura medallón, y los de Structurizr documentan la arquitectura con
el modelo C4 (contexto y contenedores). El modelo dimensional no es un diagrama C4
(es un modelo de datos), así que no tiene versión Structurizr.

## Actualizar los diagramas de Structurizr

1. Editar `structurizr/workspace.dsl` (modelo y vistas en un solo archivo).
2. Verlos en vivo (requiere Docker; se abre en http://localhost:8080/workspace/1):

   ```bash
   bash docs/structurizr/ver_diagramas.sh
   ```

   La UI recarga al guardar el `.dsl` y exporta PNG/SVG con leyenda desde cada
   diagrama (casilla Download; el tema se cambia con el enlace Light/Dark).

3. Regenerar los exportes de `structurizr/export/` (Mermaid y PlantUML como texto
   comparable en git, más los PNG claros con leyenda que van al memo):

   ```bash
   bash docs/structurizr/exportar_diagramas.sh
   ```

   Se valida el DSL y se regeneran también workspace.json y los exportes de texto.
   Se fija Structurizr a 2026.05.22-noble. El exportador no renderiza PNG; el script los produce pasando el
   PlantUML por `plantuml/plantuml` con `PLANTUML_LIMIT_SIZE` ampliado para que
   no recorte los diagramas anchos.

## Actualizar los diagramas de Graphviz

Editar el `.dot` correspondiente y regenerar (requiere Graphviz):

```bash
cd docs
dot -Tpng -Gdpi=170 arquitectura.dot -o arquitectura.png && dot -Tsvg arquitectura.dot -o arquitectura.svg
dot -Tpng -Gdpi=170 modelo_dimensional.dot -o modelo_dimensional.png && dot -Tsvg modelo_dimensional.dot -o modelo_dimensional.svg
```

## Actualizar las evidencias de la corrida

Con el pipeline ya corrido en Snowflake y el `.env` configurado (desde `psets/pset-02/`):

```bash
python scripts/exportar_metricas.py
```

Reescribe los CSV de `corrida/` con lo que haya en Snowflake en ese momento.

- `revision_obt.md`: grano mensual, conservación de joins, uso de Gold/OBT y criterios de ampliación.
- `corrida/auditoria_obt.json`: verificación independiente de claves en Snowflake y bytes por tabla.

- `temporalidad_batch.md`: PSet 1 revisado, cadencia de datos/modelo/reportes, latencia real, brechas de despliegue y justificación de batch.

- `revision_entrega.md`: documento técnico, estructura del repositorio, entregables y pesos oficiales de la rúbrica; publicación remota pendiente.
