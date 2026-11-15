## Tabla public.costos_programacion

Plan y producción diaria por producto. Es la serie más larga del área (desde abril de 2024).

| Columna | Significado |
|---|---|
| id | Registro. Lo referencia ordenes_produccion_producto_linea.programacion_id |
| fecha | Día. Filtrá siempre por esta columna. Hay filas futuras: es el plan cargado por adelantado |
| producto_id | Producto → costos_productos.id |
| producto_nombre | Nombre del producto al momento de cargar |
| responsable | Quién lo produce: Todos o el nombre de un panadero |
| plan | Unidades planificadas para el día |
| prod | Unidades producidas (vacío si todavía no se cargó) |

Hay una fila por producto y día aunque ese día no se planifique nada (plan y prod vacíos): sumá con COALESCE y no cuentes filas como días de producción.

Cumplimiento = SUM(COALESCE(prod, 0)) / SUM(plan) sobre días pasados con plan > 0. Lo vendido sale de panacea_sales_v2 con product_id = producto_id.
