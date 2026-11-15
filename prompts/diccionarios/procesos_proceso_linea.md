## Tabla public.procesos_proceso_linea

Entradas y salidas de cada versión de proceso. Cada fila tiene insumo_id o producto_id, nunca los dos.

| Columna | Significado |
|---|---|
| id | Línea |
| proceso_id | Versión del proceso → procesos_proceso.id |
| rol | ENTRADA, SALIDA (en uso), COPRODUCTO, RESIDUO |
| insumo_id, producto_id | Artículo → costos_insumos.id o costos_productos.id |
| cantidad, unidad | Cantidad por lote de referencia |
| gramaje_g | Peso del bollo crudo en las salidas por unidad |
| porcentaje_panadero | % sobre el total de harinas |
| merma_pct, rendimiento_pct | Merma y rendimiento esperados en % |
| minutos_directos, minutos_maquina | Tiempo de operario y de máquina |
| criterio_reparto | Cómo se reparte el costo entre salidas (PESO) |
| orden | Orden de la línea |

Usala para rendimiento y merma esperados. Para costo de materia prima, el backend todavía usa costos_costos.
