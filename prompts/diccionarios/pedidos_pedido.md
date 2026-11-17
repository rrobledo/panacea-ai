## Tabla public.pedidos_pedido

Pedidos de clientes y envíos (remitos) de la fábrica a las sucursales. Módulo Pedidos de panacea-produccion-backend: desde la migración 0033 reúne pedidos y remitos.

| Columna | Significado |
|---|---|
| id | Pedido. Lo referencia pedidos_pedido_detalle.pedido_id |
| tipo | SUCURSAL (envío entre sucursales: es el remito) o CLIENTE (venta mayorista) |
| es_remito | true = remito cargado directo, sin pedido previo (cantidad_pedida queda en 0) |
| origen_sucursal_id | Sucursal que envía → sucursales_sucursal.id (casi siempre 1, la fábrica) |
| sucursal_id | Sucursal que recibe → sucursales_sucursal.id |
| cliente_id | Cliente mayorista (solo en tipo CLIENTE) |
| estado | PENDIENTE, EN_PREPARACION, PREPARADO, LISTO_PARA_ENTREGA, ENTREGADO, CANCELADO |
| fecha_carga | Alta del pedido |
| fecha_entrega | Fecha de entrega programada (está en todos, aunque no se haya despachado) |
| fecha_en_preparacion, fecha_preparado | Avance en la fábrica |
| fecha_listo_para_entrega | Emisión del remito: desde acá la mercadería cuenta como enviada |
| fecha_entregado | Recepción confirmada (casi nunca se marca) |
| fecha_cancelado, fecha_facturado, factura_referencia | Cancelación y facturación |
| vendedor, observaciones | Texto libre |

Reglas:
- Un remito a sucursal es tipo = 'SUCURSAL', estado <> 'CANCELADO', con fecha_listo_para_entrega. Contalo por esa fecha y con pedidos_pedido_detalle.cantidad_entregada. No uses estado = 'ENTREGADO': la mayoría de los envíos queda en LISTO_PARA_ENTREGA.
- Las fechas son timestamptz: para agrupar por día usá (fecha_listo_para_entrega AT TIME ZONE 'America/Argentina/Cordoba')::date.
- Sucursal → lugar de venta: 2 → Villa Allende (lugar 1); 3 y 4 → Carlos Paz (lugar 2); 5 → Villa General Belgrano (lugar 4). La 1 es la fábrica.
- Para comparar remitos con ventas usá la herramienta remitos_vs_ventas.
