## Tabla public.documentos

Comprobantes del sistema de caja de Villa Allende y la Dietética (las demás sucursales están en otras tablas, no disponibles). Solo están disponibles las columnas de cobro.

| Columna | Significado |
|---|---|
| iddocumento | Comprobante |
| idcaja | Caja → cajas.idcaja: 1 Dietética, 2 Local turno tarde, 3 Local turno mañana; 5 no figura en cajas: concentra cobranzas de cuenta corriente y facturas (tipos 14, 17 y 18) |
| idcajaapertura | Turno de caja |
| fechadocumento | Fecha y hora. Filtrá siempre por esta columna |
| tipodocumento | 3 = ticket de mostrador (85%). 14 = cobranza de cuenta corriente (inferido: siempre en efectivo y con condventa 2). 17, 18, 23, 24 = facturas y notas (significado exacto a confirmar) |
| prefijodocumento, nrodocumento | Numeración |
| idvendedor | Vendedor |
| pagoefectivo, pagovuelto, pagoefectivoneto | Efectivo entregado, vuelto y efectivo neto cobrado |
| idtarjeta, pagotarjeta, cuotastarjeta | Tarjeta, importe cobrado con tarjeta y cuotas |
| idtipodescuento, descuento, porcdescuento, recargo | Descuentos y recargos |
| valorapagar | Total del comprobante |
| subtotal, iva | Subtotal e IVA |
| docanulado | 1 = anulado: excluilo siempre |
| condventa | 1 = contado; 2 = cuenta corriente (inferido): no es un cobro hasta su cobranza, tipo 14 |
| estadodoc | Estado interno del comprobante |

Reglas:
- Cobrado = SUM(pagoefectivoneto) + SUM(pagotarjeta) de comprobantes con docanulado = 0.
- No sumes valorapagar como cobros: una venta a cuenta corriente (condventa = 2) y su cobranza (tipo 14) aparecerían dos veces.
