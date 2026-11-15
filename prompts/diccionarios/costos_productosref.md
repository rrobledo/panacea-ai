## Tabla public.costos_productosref

Vínculo entre un producto fabricado y sus artículos del sistema de caja (uno por sucursal).

| Columna | Significado |
|---|---|
| id | Registro |
| producto_id | Producto → costos_productos.id |
| ref_id | Artículo del sistema de caja (texto) → articulos_final.idarticulo (castear a entero) |
| unidad_conversion | Unidades del artículo por unidad del producto |
