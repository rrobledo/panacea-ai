## Tabla public.compras_compra

Una fila por comprobante de proveedor (factura, ticket o gasto). Módulo Compras de panacea-produccion-backend.

| Columna | Significado |
|---|---|
| id | Comprobante. Lo referencian compras_compra_detalle.compra_id, compras_pago_aplicacion.compra_id y compras_movimiento_cc.compra_id |
| proveedor_id | Proveedor → costos_proveedor.id |
| orden_compra_id | Orden de compra (sin uso: siempre vacío) |
| tipo_comprobante | GASTO (93%), FACTURA_A, TICKET |
| punto_venta, numero | Numeración del comprobante del proveedor |
| fecha | Fecha del comprobante. Filtrá siempre por esta columna |
| fecha_vencimiento | Vencimiento de pago (puede estar vacío) |
| condicion_pago | CONTADO (79%) o CUENTA_CORRIENTE |
| categoria | MATERIA_PRIMA, DELIVERY, SERVICIOS, ALQUILERES, SUELDO, MANTENIMIENTO, HONORARIOS, IMPUESTOS, OTROS |
| observaciones | Texto libre |
| subtotal, iva, percepciones, impuestos, total | Importes en ARS. total = subtotal + iva + percepciones + impuestos |
| saldo_pendiente | Lo que falta pagar. Lo mantiene un trigger a partir de compras_pago_aplicacion |
| estado | PAGADO, PENDIENTE, PARCIAL |
| created_at, updated_at | Alta y última modificación del registro (no es la fecha del comprobante) |

Problemas conocidos:
- Hay comprobantes con `fecha` posterior a hoy, hasta abril de 2027. Tratalos como posibles errores de carga: informalos aparte y no los sumes al período en curso.
- Los comprobantes desde mayo de 2025 se migraron de la cuenta corriente vieja: muchos no traen detalle por insumo (tipo LIBRE) ni desglose de impuestos.
- La categoría SUELDO incluye pagos de sueldos: informala solo agregada, nunca por persona.
- Algunos "proveedores" son conceptos de personal o de gasto, no empresas: SUELDO, ADELANTOS, FERIADOS, HORAS EXTRAS, ALQUILER CP, COMBUSTIBLE, Delivery. Excluilos de los rankings de proveedores y aclaralo.
- La categoría MATERIA_PRIMA también tiene compras que no son insumos (iluminación, vajilla, servicios): para insumos usá las líneas con tipo INSUMO.
