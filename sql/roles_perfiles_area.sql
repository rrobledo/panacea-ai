-- Roles de solo lectura de los perfiles de área (cambio perfiles-compras-produccion-tesoreria).
-- Generado desde config/perfiles/{compras,produccion,tesoreria}.yaml: si cambian las tablas o
-- columnas de un perfil, actualizá este archivo (tests/test_perfiles_area.py lo controla).
--
-- Ejecutar como administrador en la base real. Antes, cambiá las contraseñas y reemplazá
-- "panacea" por el nombre de tu base. Después, cargá en Vercel (y en .env.local) las variables
-- DB_URL_COMPRAS, DB_URL_PRODUCCION y DB_URL_TESORERIA con cada usuario y el host con -pooler.
--
-- Las tablas acotadas usan GRANT por columna: el rol no puede leer las demás columnas aunque
-- sql_guard fallara.


-- ---------------------------------------------------------------- compras
CREATE ROLE agente_compras_ro LOGIN PASSWORD 'CAMBIAR_ESTA_CLAVE';
GRANT CONNECT ON DATABASE panacea TO agente_compras_ro;
GRANT USAGE ON SCHEMA public TO agente_compras_ro;
GRANT SELECT ON public.compras_compra TO agente_compras_ro;
GRANT SELECT ON public.compras_compra_detalle TO agente_compras_ro;
GRANT SELECT ON public.compras_compra_impuesto TO agente_compras_ro;
GRANT SELECT ON public.compras_pago TO agente_compras_ro;
GRANT SELECT ON public.compras_pago_aplicacion TO agente_compras_ro;
GRANT SELECT ON public.compras_movimiento_cc TO agente_compras_ro;
GRANT SELECT (id, codigo, nombre, nombre_fantasia, cuit, condicion_iva, condicion_pago, estado, fecha_alta) ON public.costos_proveedor TO agente_compras_ro;
GRANT SELECT ON public.costos_insumos TO agente_compras_ro;
ALTER ROLE agente_compras_ro SET default_transaction_read_only = on;
ALTER ROLE agente_compras_ro SET statement_timeout = '60s';

-- ---------------------------------------------------------------- produccion
CREATE ROLE agente_produccion_ro LOGIN PASSWORD 'CAMBIAR_ESTA_CLAVE';
GRANT CONNECT ON DATABASE panacea TO agente_produccion_ro;
GRANT USAGE ON SCHEMA public TO agente_produccion_ro;
GRANT SELECT ON public.costos_programacion TO agente_produccion_ro;
GRANT SELECT ON public.costos_planificacion TO agente_produccion_ro;
GRANT SELECT ON public.ordenes_produccion TO agente_produccion_ro;
GRANT SELECT ON public.ordenes_produccion_producto_linea TO agente_produccion_ro;
GRANT SELECT ON public.ordenes_produccion_insumo_linea TO agente_produccion_ro;
GRANT SELECT ON public.productos_fabricados TO agente_produccion_ro;
GRANT SELECT ON public.stock_movimientos TO agente_produccion_ro;
GRANT SELECT ON public.procesos_proceso TO agente_produccion_ro;
GRANT SELECT ON public.procesos_proceso_linea TO agente_produccion_ro;
GRANT SELECT ON public.costos_productos TO agente_produccion_ro;
GRANT SELECT ON public.costos_productosref TO agente_produccion_ro;
GRANT SELECT ON public.costos_costos TO agente_produccion_ro;
GRANT SELECT ON public.costos_insumos TO agente_produccion_ro;
GRANT SELECT ON public.costos_centro_trabajo TO agente_produccion_ro;
GRANT SELECT ON public.articulos_final TO agente_produccion_ro;
GRANT SELECT (product_id, product, category, lugar_venta_id, lugar_venta, operation_date, operation_year, operation_month, count, subtotal) ON public.panacea_sales_v2 TO agente_produccion_ro;
ALTER ROLE agente_produccion_ro SET default_transaction_read_only = on;
ALTER ROLE agente_produccion_ro SET statement_timeout = '60s';

-- ---------------------------------------------------------------- tesoreria
CREATE ROLE agente_tesoreria_ro LOGIN PASSWORD 'CAMBIAR_ESTA_CLAVE';
GRANT CONNECT ON DATABASE panacea TO agente_tesoreria_ro;
GRANT USAGE ON SCHEMA public TO agente_tesoreria_ro;
GRANT SELECT ON public.compras_pago TO agente_tesoreria_ro;
GRANT SELECT ON public.compras_pago_medio TO agente_tesoreria_ro;
GRANT SELECT ON public.compras_pago_aplicacion TO agente_tesoreria_ro;
GRANT SELECT (id, proveedor_id, tipo_comprobante, punto_venta, numero, fecha, fecha_vencimiento, condicion_pago, total, saldo_pendiente, estado, categoria) ON public.compras_compra TO agente_tesoreria_ro;
GRANT SELECT ON public.compras_movimiento_cc TO agente_tesoreria_ro;
GRANT SELECT (id, codigo, nombre, nombre_fantasia, cuit, condicion_iva, condicion_pago, estado, fecha_alta) ON public.costos_proveedor TO agente_tesoreria_ro;
GRANT SELECT (iddocumento, idcaja, idcajaapertura, fechadocumento, tipodocumento, prefijodocumento, nrodocumento, idvendedor, pagoefectivo, pagoefectivoneto, pagovuelto, idtarjeta, pagotarjeta, cuotastarjeta, idtipodescuento, descuento, porcdescuento, recargo, valorapagar, subtotal, iva, docanulado, condventa, estadodoc) ON public.documentos TO agente_tesoreria_ro;
GRANT SELECT (idcaja, nombre, activa, estadocaja) ON public.cajas TO agente_tesoreria_ro;
ALTER ROLE agente_tesoreria_ro SET default_transaction_read_only = on;
ALTER ROLE agente_tesoreria_ro SET statement_timeout = '60s';
