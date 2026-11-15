## Tabla public.productos_fabricados

Lo fabricado al cerrar cada orden, con el desperdicio. Existe desde el 07/09/2026.

| Columna | Significado |
|---|---|
| id | Registro |
| orden_id | Orden → ordenes_produccion.id |
| producto_id | Producto → costos_productos.id |
| cantidad_fabricada | Unidades buenas |
| ubicacion_id | Dónde quedó lo fabricado |
| cantidad_desperdicio | Unidades descartadas |
| ubicacion_desperdicio_id | Dónde quedó el desperdicio |
| motivo_desperdicio | Texto libre |
| fecha | Momento del registro. Filtrá siempre por esta columna |

Hoy el desperdicio no se está cargando: cantidad_desperdicio vale 0 en todas las filas (relevado el 14/11/2026). No informes una merma de 0%: decí que el dato no se registra. Cuando se cargue, merma % = SUM(cantidad_desperdicio) / SUM(cantidad_fabricada + cantidad_desperdicio). Antes de septiembre de 2026 no hay registros.
