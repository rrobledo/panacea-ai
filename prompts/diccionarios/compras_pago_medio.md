## Tabla public.compras_pago_medio

Cómo se pagó: un pago puede dividirse en varios medios.

| Columna | Significado |
|---|---|
| id | Registro |
| pago_id | Pago → compras_pago.id |
| tipo | TRANSFERENCIA (98%), EFECTIVO, NOTA_CREDITO |
| importe | Importe en ARS pagado con ese medio |
| banco, numero | Banco y número de operación o cheque |
| fecha_acreditacion | Fecha en que se acredita (puede estar vacía) |
