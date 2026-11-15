## Tabla public.compras_pago

Una fila por pago a un proveedor. Módulo Tesorería de panacea-produccion-backend.

| Columna | Significado |
|---|---|
| id | Pago. Lo referencian compras_pago_medio.pago_id y compras_pago_aplicacion.pago_id |
| proveedor_id | Proveedor → costos_proveedor.id |
| fecha | Fecha del pago. Filtrá siempre por esta columna |
| importe | Importe total del pago en ARS |
| estado | REGISTRADO (único valor en uso) |
| observaciones | Texto libre |
| created_at | Alta del registro |

Un pago puede cancelar varias facturas, y una factura puede cancelarse con varios pagos: el vínculo está en compras_pago_aplicacion.
