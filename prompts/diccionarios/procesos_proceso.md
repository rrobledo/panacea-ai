## Tabla public.procesos_proceso

Recetas del grafo de procesos (motor nuevo). Cada fila es una versión; la vigente tiene vigente_hasta vacío.

| Columna | Significado |
|---|---|
| id | Versión del proceso. La referencian procesos_proceso_linea y ordenes_produccion.proceso_id |
| codigo | Identificador lógico, igual en todas sus versiones |
| version | Número de versión |
| nombre | Nombre |
| tipo | ELABORACION (único en uso), DIVISION, TRANSFORMACION, FRACCIONAMIENTO |
| responsable | Área |
| lote_referencia, lote_unidad | Tamaño de lote al que refieren las cantidades (ej. 10 KG) |
| lote_minimo, lote_multiplo | Restricciones de tamaño de lote |
| minutos_setup | Minutos de preparación por lote |
| vigente_desde, vigente_hasta | Vigencia de la versión |
