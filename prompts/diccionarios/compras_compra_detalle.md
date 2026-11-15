## Tabla public.compras_compra_detalle

Una fila por línea de un comprobante de proveedor.

| Columna | Significado |
|---|---|
| id | Línea |
| compra_id | Comprobante → compras_compra.id |
| tipo | INSUMO (con insumo_id), ITEM_GASTO (con item_gasto_id) o LIBRE (solo descripción). Hoy el 95% es LIBRE |
| insumo_id | Insumo → costos_insumos.id, solo si tipo = INSUMO |
| item_gasto_id | Ítem de gasto (casi sin uso) |
| descripcion | Texto de la línea |
| cantidad, precio_unitario, descuento | Cantidad, precio unitario en ARS y descuento |
| alicuota_iva | Alícuota de IVA en % |
| importe_neto, importe_iva, importe_total | Importes de la línea en ARS |
| centro_costo_id, cuenta_contable_id | Reservados, sin uso |

El precio de compra por insumo solo se puede seguir en las líneas con tipo INSUMO (70 líneas). Para el resto, el insumo está solo en la descripción.
