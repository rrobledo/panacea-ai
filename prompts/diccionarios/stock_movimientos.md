## Tabla public.stock_movimientos

Libro de movimientos de stock de insumos y productos. Desde el 25/08/2026. Cada fila tiene insumo_id o producto_id, nunca los dos.

| Columna | Significado |
|---|---|
| id | Movimiento |
| insumo_id | Insumo → costos_insumos.id |
| producto_id | Producto o semielaborado → costos_productos.id |
| tipo | Insumos: RESERVA (no descuenta stock), CONSUMO (siempre negativo), AJUSTE (±). Productos: PRODUCCION (positivo), CONSUMO_INTERNO (negativo) |
| cantidad | Cantidad con signo, en la unidad del artículo |
| orden_id | Orden que lo generó → ordenes_produccion.id (vacío en AJUSTE) |
| referencia | Código de la orden o motivo del ajuste |
| fecha | Momento. Filtrá siempre por esta columna |

Para consumo real de insumos, usá tipo = 'CONSUMO' (no RESERVA).
