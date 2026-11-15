## Tabla public.ordenes_produccion_producto_linea

Productos que pide cada orden.

| Columna | Significado |
|---|---|
| id | Línea |
| orden_id | Orden → ordenes_produccion.id |
| producto_id | Producto → costos_productos.id |
| cantidad_planeada | Unidades a producir |
| programacion_id | Fila de costos_programacion de la que salió (vacío en órdenes anteriores a la migración 0026) |
| masa_kg, bollos, gramaje_g | Kilos de masa, cantidad de bollos y peso del bollo crudo en gramos |
