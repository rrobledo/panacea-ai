## Tabla public.pedidos_pedido_detalle

Productos de cada pedido o remito.

| Columna | Significado |
|---|---|
| id | Línea |
| pedido_id | Pedido → pedidos_pedido.id |
| producto_id | Producto → costos_productos.id (es el product_id de panacea_sales_v2 cuando el artículo de caja está vinculado) |
| cantidad_pedida | Unidades pedidas (0 en los remitos sin pedido previo) |
| cantidad_entregada | Unidades enviadas en el remito: es la cantidad que cuenta como enviada |
| observaciones | Texto libre |
| fecha_creacion | Alta de la línea |
