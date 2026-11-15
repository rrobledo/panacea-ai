## Tabla public.compras_movimiento_cc

Cuenta corriente con proveedores: un registro por factura (debe) y por pago (haber). El saldo no se guarda: se calcula sumando debe − haber ordenado por fecha e id.

| Columna | Significado |
|---|---|
| id | Movimiento |
| proveedor_id | Proveedor → costos_proveedor.id |
| fecha | Fecha del movimiento. Filtrá siempre por esta columna |
| tipo | FACTURA o PAGO |
| documento | Identificación del comprobante o pago |
| debe | Importe adeudado (facturas), en ARS |
| haber | Importe pagado (pagos), en ARS |
| compra_id, pago_id | Origen → compras_compra.id o compras_pago.id |
| created_at | Alta del registro |

Tiene las mismas fechas futuras que compras_compra: excluilas del saldo a hoy y avisalas.
