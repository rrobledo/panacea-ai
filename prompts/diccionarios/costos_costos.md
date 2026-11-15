## Tabla public.costos_costos

Receta del motor viejo: cuánto de cada insumo lleva un lote del producto. El backend la sigue usando para costos y órdenes, mientras pasa al grafo de procesos.

| Columna | Significado |
|---|---|
| id | Registro |
| producto_id | Producto → costos_productos.id |
| insumo_id | Insumo → costos_insumos.id |
| cantidad | Cantidad por lote, en la unidad de medida del insumo |

Costo de materia prima (misma fórmula que el backend):
- costo del lote = SUM(costos_insumos.precio / costos_insumos.cantidad × costos_costos.cantidad)
- costo unitario = costo del lote / costos_productos.lote_produccion
- margen % = (precio de venta / costo unitario − 1) × 100

Aclará siempre que es costo de materia prima a precios de hoy, sin mano de obra ni gastos.
