## 1. Código compartido

- [x] 1.1 `ContextoPerfil.columnas_fecha` y su carga en `contexto_para` desde `Tabla.columna_fecha`; en `mcp_server/server.py`, `{tabla: "operation_date"}`
- [x] 1.2 `describir_tabla(tabla=None)`: normalizar el nombre, validar contra el perfil, listar y seleccionar solo las columnas permitidas, y ordenar por la columna de fecha si existe
- [x] 1.3 Descripción de `consultar` sin mencionar `operation_date`
- [x] 1.4 `TABLAS_NO_EXPONIBLES` en `agent/profiles.py` (deprecadas, excluidas, `auth_*`, `django_*`, esquema `app`) con error que nombra archivo y tabla
- [x] 1.5 Tests: `describir_tabla` (sin parámetro igual que antes, tabla acotada, tabla sin fecha, tabla de otro perfil), lista negra y equivalencia con el servidor MCP original

## 2. Diccionarios

- [x] 2.1 Compras: `compras_compra`, `compras_compra_detalle`, `compras_compra_impuesto`, `compras_pago`, `compras_pago_aplicacion`, `compras_movimiento_cc`, `costos_proveedor`, `costos_insumos`
- [x] 2.2 Producción: `costos_programacion`, `costos_planificacion`, `ordenes_produccion`, `ordenes_produccion_producto_linea`, `ordenes_produccion_insumo_linea`, `productos_fabricados`, `stock_movimientos`, `procesos_proceso`, `procesos_proceso_linea`, `costos_productos`, `costos_productosref`, `costos_costos`, `costos_centro_trabajo`, `articulos_final`
- [x] 2.3 Tesorería: `compras_pago_medio`, `documentos` (solo columnas de cobro), `cajas`
- [x] 2.4 Revisar cada diccionario contra los modelos de `panacea-produccion-backend` (significado de estados, tipos y unidades)

## 3. Perfiles y prompts

- [x] 3.1 `config/perfiles/compras.yaml` y `prompts/compras.md`: tablas y columnas del spec, fechas futuras, facturas migradas sin desglose de impuestos
- [x] 3.2 `config/perfiles/produccion.yaml` y `prompts/produccion.md`: cruce por `product_id`, receta vieja y nueva, órdenes y desperdicio desde el 07/09/2026, plan vigente en `costos_planificacion`
- [x] 3.3 `config/perfiles/tesoreria.yaml` y `prompts/tesoreria.md`: cobros desde `documentos` sin anulados, vencimientos y saldos con proveedores, arqueos y Mercado Pago no disponibles
- [x] 3.4 Test de configuración real: los tres perfiles cargan, `ventas` no cambió y ninguna tabla de la lista negra aparece

## 4. Base de datos e infraestructura

- [x] 4.1 `sql/roles_perfiles_area.sql` con los roles `agente_compras_ro`, `agente_produccion_ro` y `agente_tesoreria_ro` (`GRANT` por tabla y por columna, solo lectura, timeout de 60 s)
- [x] 4.2 `DB_URL_COMPRAS`, `DB_URL_PRODUCCION` y `DB_URL_TESORERIA` en `.env.example` y en la sección de variables del README
- [x] 4.3 Test `@pytest.mark.db` por perfil: `contexto_para` carga las columnas y `sql_guard` rechaza una columna no permitida

## 5. Evaluación y documentación

- [x] 5.1 Preguntas de evaluación por perfil (4 o más con SQL de verificación sobre períodos cerrados, y 1 que el agente debe acotar), en un archivo por perfil, con `esperado.json` generado y revisado
- [x] 5.2 README: perfiles disponibles, tablas por perfil, cómo crear los roles y cómo sumar un usuario
- [ ] 5.3 Correr `pytest` completo y las evaluaciones de los tres perfiles con la base real (hecho: pytest y `verificar` de los tres perfiles; pendiente: `evaluar.py correr --perfil …` con la API, que necesita ANTHROPIC_API_KEY)
