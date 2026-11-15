## Tabla public.panacea_sales_v2 (vista de producción)

Ventas por producto. Cada fila es una línea de ticket. Este perfil no ve tickets ni clientes.

| Columna | Significado |
|---|---|
| product_id, product | Producto. product_id = costos_productos.id |
| category | Categoría de venta |
| lugar_venta_id, lugar_venta | Sucursal: 0 Dietética, 1 Villa Allende, 2 Carlos Paz, 3 Córdoba, 4 Villa General Belgrano |
| operation_date | Fecha de la venta. Filtrá siempre por esta columna |
| operation_year, operation_month | Año y mes (índice con product_id) |
| count | Unidades vendidas |
| subtotal | Importe en ARS |

Vendido por producto y mes = SUM(count) agrupado por product_id, operation_year, operation_month.
