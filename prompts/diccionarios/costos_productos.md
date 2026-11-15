## Tabla public.costos_productos

Productos fabricados y semielaborados. Su id es el product_id de panacea_sales_v2.

| Columna | Significado |
|---|---|
| id | Producto. Igual a panacea_sales_v2.product_id |
| codigo, nombre | Código y nombre |
| categoria | PASTAS, PASTELERIA, PANADERIA, BUDINES, CUADRADOS, ALFAJORES, GALLETAS, BOLLERIA, PIZZAS, FACTURAS, MEDIALUNAS, OTROS |
| ref_id | Referencia del artículo en el sistema de caja (texto). Para el vínculo completo usá costos_productosref |
| utilidad | Utilidad objetivo en % sobre el costo |
| precio_actual | Precio de venta cargado, en ARS por unidad |
| unidad_medida | UN, GR o KG (campo viejo; ver unidad_base) |
| lote_produccion | Unidades que salen de una receta de costos_costos |
| tiempo_produccion | Minutos por lote |
| responsable | Área: Pasteleria, Pastas, Panaderia o Todos |
| is_producto | Falso para intermedios (masas) |
| habilitado | Producto activo: filtrá habilitado = true salvo que pidan históricos |
| prioridad | Orden de producción |
| producto_base_id | Masa o intermedio del que se arma → costos_productos.id |
| naturaleza | TERMINADO o SEMIELABORADO |
| unidad_base, peso_unitario_g | Unidad de stock (KG, UN, LT) y peso por unidad |
| vendible | Se vende al público |
