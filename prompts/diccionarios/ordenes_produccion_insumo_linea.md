## Tabla public.ordenes_produccion_insumo_linea

Insumos que requiere cada orden según la receta.

| Columna | Significado |
|---|---|
| id | Línea |
| orden_id | Orden → ordenes_produccion.id |
| insumo_id | Insumo → costos_insumos.id |
| cantidad | Cantidad en la unidad de medida del insumo |

El consumo real registrado está en stock_movimientos (tipo CONSUMO).
