## Vista public.articulos_final

Artículos activos del sistema de caja con su precio de venta.

| Columna | Significado |
|---|---|
| idarticulo | Artículo. idarticulo < 2000 = Villa Allende; ≥ 2000 = Carlos Paz |
| nombre | Nombre en el sistema de caja |
| idcategoria, categoria | Categoría del sistema de caja |
| precio | Precio de venta al público en ARS |
| activo | 1 = activo |

Se une con producción por costos_productosref.ref_id::int = idarticulo.
