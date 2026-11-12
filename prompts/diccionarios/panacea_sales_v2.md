## Tabla public.panacea_sales_v2

Cada fila es una LÍNEA de un comprobante: un producto dentro de una venta.

| Columna | Significado |
|---|---|
| document_id | Comprobante o ticket. Un ticket tiene varias filas, una por producto. Contá tickets con COUNT(DISTINCT document_id) |
| category_id / category | Categoría del producto |
| ref_id | Referencia interna del producto (confirmar significado con el usuario antes de usarla) |
| product_id / product | Producto |
| lugar_venta_id / lugar_venta | Sucursal o canal donde se realizó la venta |
| customer_id / customer | Cliente. Las ventas de mostrador de cada sucursal se registran con un cliente genérico: 999 Carlos Paz, 0 Villa Allende, 888 Córdoba, 777 Villa General Belgrano |
| operation_date | Fecha de la venta (indexada: filtrá siempre por esta columna) |
| operation_hour | Hora de la venta (0–23) |
| operation_year / operation_month | Año y mes (índice compuesto con product_id) |
| week_of_year (texto), week_of_month, day_of_week, day_of_week_text | Atributos de calendario. Verificá con `perfil_datos` cómo está codificado day_of_week |
| count | Unidades vendidas (float: puede haber fraccionados) |
| subtotal | Importe de la línea en ARS |
