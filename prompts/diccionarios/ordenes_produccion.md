## Tabla public.ordenes_produccion

Órdenes de producción. Existen desde el 07/09/2026.

| Columna | Significado |
|---|---|
| id | Orden. La referencian las líneas, productos_fabricados y stock_movimientos |
| codigo | Código único de la orden |
| fecha_fabricacion | Día de producción. Filtrá siempre por esta columna |
| responsable | Área o persona (hoy siempre Todos) |
| estado | ASIGNADA, EN_PRODUCCION, FINALIZADA (también puede haber CANCELADA) |
| fecha_creacion, fecha_en_produccion, fecha_finalizada, fecha_cancelada | Momento de cada cambio de estado |
| proceso_id, proceso_version | Receta del grafo de procesos con la que se emitió → procesos_proceso.id (vacío en órdenes viejas) |
| masa_requerida | Kilos de masa que pedían los productos de la orden |
| lote_producido | Kilos efectivamente amasados (redondeado a lote) |
| masa_desde_stock | Kilos tomados de masa ya hecha |

Sobrante de masa = lote_producido − masa_requerida.
