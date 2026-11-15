## Tabla public.costos_proveedor

Proveedores. Los datos de contacto (teléfono, email, dirección) no están disponibles para el agente.

| Columna | Significado |
|---|---|
| id | Proveedor. Lo referencian compras_compra, compras_pago y compras_movimiento_cc |
| codigo | Código interno |
| nombre, nombre_fantasia | Razón social y nombre comercial |
| cuit | CUIT |
| condicion_iva | EXENTO, RESPONSABLE_INSCRIPTO o vacío (60% vacío) |
| condicion_pago | CUENTA_CORRIENTE o CONTADO |
| estado | activo |
| fecha_alta | Alta del proveedor |
