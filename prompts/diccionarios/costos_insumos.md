## Tabla public.costos_insumos

Insumos (materias primas y envases) con su precio de referencia.

| Columna | Significado |
|---|---|
| id | Insumo. Lo referencian costos_costos, procesos_proceso_linea, ordenes_produccion_insumo_linea, stock_movimientos y compras_compra_detalle |
| codigo, nombre | Código y nombre |
| unidad_medida | GR, KG, ML, LT o UN |
| cantidad | Cantidad de referencia del precio, en unidad_medida (ej. 1000 GR) |
| precio | Precio en ARS de esa cantidad de referencia |

Precio por unidad de medida = precio / cantidad. Es el precio cargado hoy: no hay historial de precios.
