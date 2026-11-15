## ADDED Requirements

### Requirement: Criterio de selección de tablas
Cada perfil de área SHALL exponer solo tablas vigentes según el relevamiento del 14/11/2026, cruzado con `panacea-produccion-backend`. Puede incluir tablas marcadas Candidata y, cuando son imprescindibles para el área, las marcadas Revisar, con el problema de datos explicado en el prompt. Ningún perfil MUST incluir tablas marcadas Deprecada, Excluir o Vacía.

#### Scenario: Tabla deprecada
- **WHEN** un perfil lista `costos_cuentacorrienteproveedor`, `costos_remitos`, `costos_costs`, `costos_compras` o `panacea_sales`
- **THEN** la configuración no carga y el error nombra el archivo del perfil y la tabla no permitida

#### Scenario: Tabla excluida
- **WHEN** un perfil lista `socios`, `compras_compra_adjunto`, `compras_pago_adjunto`, `pedidos_remito_legacy` o una tabla de `auth_*`, `django_*` o `users`
- **THEN** la configuración no carga con el mismo tipo de error

#### Scenario: Consulta a una tabla fuera del perfil
- **WHEN** el agente de compras ejecuta `consultar` sobre `ordenes_produccion`
- **THEN** `sql_guard` rechaza la consulta indicando que la tabla no está permitida para el perfil, y el rechazo queda en la auditoría

### Requirement: Perfil de ventas sin cambios
El perfil `ventas` SHALL mantener exactamente sus tablas, herramientas, prompt, reglas y límites actuales.

#### Scenario: Configuración de ventas
- **WHEN** se carga la configuración después de este cambio
- **THEN** el perfil `ventas` tiene solo `public.panacea_sales_v2` y la misma lista de 14 herramientas que antes

### Requirement: Perfil de compras
El perfil `compras` SHALL exponer estas tablas, con `compras_compra` como tabla principal:

| Tabla | Columnas | Columna de fecha |
|---|---|---|
| compras_compra | todas | fecha |
| compras_compra_detalle | todas | — |
| compras_compra_impuesto | todas | — |
| compras_pago | todas | fecha |
| compras_pago_aplicacion | todas | — |
| compras_movimiento_cc | todas | fecha |
| costos_proveedor | id, codigo, nombre, nombre_fantasia, cuit, condicion_iva, condicion_pago, estado, fecha_alta | — |
| costos_insumos | todas | — |

Su prompt MUST avisar que `compras_compra` y `compras_movimiento_cc` tienen fechas hasta abril de 2027, que deben tratarse como posibles errores de carga, que las facturas migradas de la cuenta corriente vieja no traen el desglose de impuestos, y que hay "proveedores" que son conceptos de personal (SUELDO, ADELANTOS, FERIADOS, HORAS EXTRAS): se excluyen de los rankings y nunca se detallan por persona.

#### Scenario: Gasto por proveedor
- **WHEN** un usuario de compras pregunta cuánto se le compró a cada proveedor en octubre de 2026
- **THEN** el agente consulta `compras_compra` unida con `costos_proveedor`, filtrando por `fecha`, y responde con el total por proveedor

#### Scenario: Datos de contacto del proveedor
- **WHEN** el agente intenta leer `costos_proveedor.telefono` o `costos_proveedor.email`
- **THEN** `sql_guard` rechaza la consulta porque la columna no está permitida

#### Scenario: Fechas futuras
- **WHEN** una consulta de compras incluye comprobantes con fecha posterior a hoy
- **THEN** el agente los informa aparte como posibles errores de carga y no los suma al período en curso

### Requirement: Perfil de producción
El perfil `produccion` SHALL exponer estas tablas, con `costos_programacion` como tabla principal:

| Tabla | Columnas | Columna de fecha |
|---|---|---|
| costos_programacion | todas | fecha |
| costos_planificacion | todas | fecha |
| ordenes_produccion | todas | fecha_fabricacion |
| ordenes_produccion_producto_linea | todas | — |
| ordenes_produccion_insumo_linea | todas | — |
| productos_fabricados | todas | fecha |
| stock_movimientos | todas | fecha |
| procesos_proceso | todas | — |
| procesos_proceso_linea | todas | — |
| costos_productos | todas | — |
| costos_productosref | todas | — |
| costos_costos | todas | — |
| costos_insumos | todas | — |
| costos_centro_trabajo | todas | — |
| articulos_final (vista) | todas | — |
| panacea_sales_v2 | product_id, product, category, lugar_venta_id, lugar_venta, operation_date, operation_year, operation_month, count, subtotal | operation_date |

Su prompt MUST explicar que `panacea_sales_v2.product_id` es `costos_productos.id`; que `productos_fabricados.cantidad_desperdicio` hoy vale 0 en todas las filas, así que no debe informar una merma de 0%; que `costos_costos` es la receta del motor viejo y `procesos_proceso_linea` la del grafo nuevo; que las órdenes y el desperdicio real existen desde septiembre de 2026; y que el plan vigente está en `costos_planificacion`, no en `planificacion2024`.

#### Scenario: Plan contra real contra vendido
- **WHEN** un usuario de producción pregunta por el cumplimiento del plan de octubre de 2026
- **THEN** el agente cruza `costos_planificacion`, `costos_programacion` y `panacea_sales_v2` por producto, y responde con lo planeado, lo producido y lo vendido

#### Scenario: Sin datos de clientes
- **WHEN** el agente de producción intenta leer `panacea_sales_v2.customer_id`
- **THEN** `sql_guard` rechaza la consulta porque la columna no está permitida

#### Scenario: Desperdicio sin cargar
- **WHEN** un usuario pide la merma de octubre de 2026
- **THEN** el agente explica que el desperdicio no se está registrando, en lugar de responder 0%

#### Scenario: Desperdicio antes de septiembre de 2026
- **WHEN** un usuario pide el desperdicio de julio de 2026
- **THEN** el agente aclara que `productos_fabricados` empieza el 07/09/2026 y no inventa un valor para ese mes

### Requirement: Perfil de tesorería
El perfil `tesoreria` SHALL exponer estas tablas, con `compras_pago` como tabla principal:

| Tabla | Columnas | Columna de fecha |
|---|---|---|
| compras_pago | todas | fecha |
| compras_pago_medio | todas | fecha_acreditacion |
| compras_pago_aplicacion | todas | — |
| compras_compra | id, proveedor_id, tipo_comprobante, punto_venta, numero, fecha, fecha_vencimiento, condicion_pago, total, saldo_pendiente, estado, categoria | fecha |
| compras_movimiento_cc | todas | fecha |
| costos_proveedor | id, codigo, nombre, nombre_fantasia, cuit, condicion_iva, condicion_pago, estado, fecha_alta | — |
| documentos | iddocumento, idcaja, idcajaapertura, fechadocumento, tipodocumento, prefijodocumento, nrodocumento, idvendedor, pagoefectivo, pagoefectivoneto, pagovuelto, idtarjeta, pagotarjeta, cuotastarjeta, idtipodescuento, descuento, porcdescuento, recargo, valorapagar, subtotal, iva, docanulado, condventa, estadodoc | fechadocumento |
| cajas | idcaja, nombre, activa, estadocaja | — |

`documentos` cubre solo Villa Allende y la Dietética: las copias por sucursal (`documentos_cp`, `_va`, `_cba`, `_vgb`) arrancan como clon de la misma base (los conteos de 2022 y 2023 son idénticos) y no se pueden sumar sin una regla de corte por sucursal. Su prompt MUST indicar ese alcance, que los cobros se calculan como `pagoefectivoneto + pagotarjeta` de comprobantes no anulados (`docanulado`) y que `valorapagar` no es un cobro, porque la venta a cuenta corriente y su cobranza (tipo 14) aparecerían dos veces. También MUST indicar que los arqueos (`cajasaperturas`) y Mercado Pago no están disponibles porque sus datos están cortados desde 2024 y desde enero de 2026.

#### Scenario: Cobros por medio de pago
- **WHEN** un usuario de tesorería pregunta cuánto se cobró en efectivo y con tarjeta en octubre de 2026
- **THEN** el agente suma `pagoefectivoneto` y `pagotarjeta` de `documentos` no anulados con `fechadocumento` en ese mes

#### Scenario: Vencimientos a pagar
- **WHEN** un usuario pide los pagos a proveedores que vencen en los próximos 30 días
- **THEN** el agente lista las facturas de `compras_compra` con `saldo_pendiente > 0` y `fecha_vencimiento` en ese rango, con el nombre del proveedor

#### Scenario: Datos del cliente en un comprobante
- **WHEN** el agente intenta leer `documentos.idcliente`, `documentos.nrodoccliente` o `documentos.nombreclienteeventual`
- **THEN** `sql_guard` rechaza la consulta porque la columna no está permitida

#### Scenario: Pedido de arqueo de caja
- **WHEN** un usuario pide el arqueo de caja de ayer
- **THEN** el agente explica que los arqueos no se sincronizan desde 2024 y ofrece lo cobrado por caja según `documentos`

### Requirement: Herramientas de los perfiles de área
Los perfiles `compras`, `produccion` y `tesoreria` SHALL tener las herramientas `describir_tabla`, `consultar`, `solicitar_aclaraciones`, `generar_artifact` y `editar_artifact`. Las herramientas de ventas y de variables externas MUST NOT estar en esos perfiles, porque dependen de las columnas de `panacea_sales_v2`.

#### Scenario: Herramienta de ventas en un perfil de área
- **WHEN** `config/perfiles/compras.yaml` lista `resumen_ventas`
- **THEN** la configuración no carga, porque esa herramienta necesita la tabla de ventas completa como tabla principal

### Requirement: Credencial y rol por perfil
Cada perfil de área SHALL conectarse con su propia variable (`DB_URL_COMPRAS`, `DB_URL_PRODUCCION`, `DB_URL_TESORERIA`), ligada a un rol de solo lectura (`agente_compras_ro`, `agente_produccion_ro`, `agente_tesoreria_ro`) que tiene `GRANT SELECT` solo sobre sus tablas, o sobre sus columnas cuando la tabla está acotada, con `default_transaction_read_only = on` y `statement_timeout = '60s'`.

#### Scenario: Variable ausente
- **WHEN** un usuario abre una conversación con el perfil `tesoreria` y `DB_URL_TESORERIA` no está definida
- **THEN** la API responde con un error de configuración que nombra la variable faltante, y los demás perfiles siguen funcionando

#### Scenario: Defensa en profundidad
- **WHEN** una consulta pasara `sql_guard` por error y leyera una columna no otorgada
- **THEN** Postgres la rechaza por permisos del rol

### Requirement: Diccionario por tabla
Cada tabla de un perfil de área SHALL tener un diccionario en `prompts/diccionarios/<tabla>.md` que explica qué representa una fila, el significado de cada columna permitida, las claves para unir con otras tablas y los problemas de datos conocidos. El diccionario MUST describir solo las columnas permitidas en el perfil que lo usa.

#### Scenario: Diccionario faltante
- **WHEN** un perfil referencia un diccionario que no existe
- **THEN** la configuración no carga y el error nombra el perfil, la tabla y el archivo

### Requirement: Evaluación por perfil
Cada perfil de área SHALL tener al menos 4 preguntas de evaluación con SQL de verificación sobre períodos cerrados, más una pregunta que el agente debe rechazar o acotar (dato no disponible o fuera del perfil).

#### Scenario: Verificación de respuestas esperadas
- **WHEN** se corre `python evals/evaluar.py verificar` para un perfil de área
- **THEN** cada pregunta con SQL tiene su valor esperado guardado y vigente
