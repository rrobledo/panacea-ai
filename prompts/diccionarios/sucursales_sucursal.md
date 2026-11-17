## Tabla public.sucursales_sucursal

Sucursales del sistema de pedidos y remitos (no son los lugares de venta de panacea_sales_v2).

| id | nombre | tipo | Lugar de venta |
|---|---|---|---|
| 1 | Centro Producción (Fábrica) | FABRICA | no vende al público |
| 2 | Villa Allende | SUCURSAL | 1 Villa Allende |
| 3 | Carlos Paz (9 de Julio 355) | SUCURSAL | 2 Carlos Paz |
| 4 | Carlos Paz (San Martín) | SUCURSAL | 2 Carlos Paz |
| 5 | Villa General Belgrano | SUCURSAL | 4 Villa General Belgrano |

Columnas: id, nombre, tipo (FABRICA o SUCURSAL), activa. Las dos sucursales de Carlos Paz venden como un solo lugar en panacea_sales_v2: no se pueden separar sus ventas.
