## Tabla public.compras_pago_aplicacion

Qué parte de cada pago se aplicó a cada comprobante.

| Columna | Significado |
|---|---|
| id | Registro |
| pago_id | Pago → compras_pago.id |
| compra_id | Comprobante cancelado → compras_compra.id |
| importe | Importe aplicado en ARS |

Días de pago de una factura = compras_pago.fecha − compras_compra.fecha (o − fecha_vencimiento para medir atraso), ponderado por el importe aplicado.
