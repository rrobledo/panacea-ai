## Tabla public.compras_compra_impuesto

Desglose de impuestos de un comprobante. Casi sin datos (13 filas, todas PERCEPCION_IVA): los totales de impuestos están en compras_compra.

| Columna | Significado |
|---|---|
| id | Registro |
| compra_id | Comprobante → compras_compra.id |
| tipo | Tipo de impuesto (hoy solo PERCEPCION_IVA) |
| base_imponible, porcentaje, importe | Base, alícuota en % e importe en ARS |
