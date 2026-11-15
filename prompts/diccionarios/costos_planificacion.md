## Tabla public.costos_planificacion

Plan mensual por producto. Una fila por producto y mes (fecha = primer día del mes).

| Columna | Significado |
|---|---|
| id | Registro |
| fecha | Mes (primer día). Filtrá siempre por esta columna |
| producto_id | Producto → costos_productos.id |
| plan | Plan inicial en unidades |
| sistema | Plan calculado por el sistema (en el 85% de las filas coincide con corregido) |
| corregido | Plan final ajustado a mano: es el que usa el backend para comparar |
| indice | Índice de ajuste aplicado |

Este es el plan vigente. No uses planificacion2024.
