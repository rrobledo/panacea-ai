## ADDED Requirements

### Requirement: Herramientas parametrizadas por perfil
El sistema SHALL exponer las herramientas `describir_tabla`, `perfil_datos`, `resumen_ventas`, `comparar_periodos`, `clientes_inactivos`, `productos_asociados`, `proyectar_ventas` y `consultar` como funciones de un paquete Python que reciben como parámetros la tabla, la conexión a la base y los límites (`max_filas`, `timeout_sql_seg`), sin leer variables de entorno globales.

#### Scenario: Misma herramienta, dos perfiles
- **WHEN** el backend invoca `resumen_ventas` con el contexto del perfil `ventas`
- **THEN** la consulta se ejecuta sobre la tabla y con la credencial definidas en `config/perfiles/ventas.yaml`

#### Scenario: Resultados equivalentes al servidor actual
- **WHEN** se ejecuta cualquiera de las 8 herramientas con los mismos argumentos antes y después del refactor
- **THEN** el JSON devuelto tiene las mismas columnas y los mismos valores

### Requirement: Servidor MCP compatible
El servidor `mcp_server/server.py` SHALL seguir publicando las mismas 8 herramientas, con los mismos nombres y parámetros, importándolas del paquete compartido y construyendo su contexto desde `DATABASE_URL`, `SALES_TABLE`, `MAX_FILAS` y `TIMEOUT_SEG`.

#### Scenario: Claude Code sin cambios de configuración
- **WHEN** Claude Code arranca el servidor con el `.mcp.json` actual
- **THEN** las 8 herramientas están disponibles y responden igual que antes del refactor

### Requirement: Validación de SQL por tablas permitidas
La herramienta `consultar` SHALL parsear el SQL con `sqlglot` (dialecto PostgreSQL) y rechazarlo si no es exactamente una sentencia `SELECT` o `WITH`, si contiene funciones o sentencias prohibidas, o si referencia una tabla (o una columna, cuando el perfil acota columnas) fuera de la lista del perfil.

#### Scenario: Tabla de otro perfil
- **WHEN** el perfil `ventas` envía `SELECT * FROM public.costos_costos`
- **THEN** la herramienta devuelve un error que nombra la tabla no permitida y no se ejecuta ninguna consulta

#### Scenario: Varias sentencias
- **WHEN** se envía `SELECT 1; DROP TABLE x`
- **THEN** la herramienta devuelve un error de sentencia única y no ejecuta nada

#### Scenario: Columna fuera del alcance
- **WHEN** el perfil `produccion`, que solo tiene `operation_date, product_id, product, count` de `panacea_sales_v2`, consulta `subtotal`
- **THEN** la herramienta rechaza la consulta indicando la columna no permitida

#### Scenario: CTE válido
- **WHEN** se envía un `WITH` cuyas subconsultas solo usan tablas permitidas
- **THEN** la consulta se ejecuta y los nombres de los CTE no se tratan como tablas no permitidas

### Requirement: Ejecución de solo lectura acotada
Toda consulta SHALL ejecutarse en una transacción `READ ONLY` con `statement_timeout` igual al límite del perfil y SHALL devolver como máximo `max_filas` filas, indicando `truncado: true` cuando hubo más.

#### Scenario: Resultado truncado
- **WHEN** una consulta devuelve más filas que `max_filas`
- **THEN** la respuesta contiene exactamente `max_filas` filas y `truncado: true`

#### Scenario: Consulta lenta
- **WHEN** una consulta supera `timeout_sql_seg`
- **THEN** la base la cancela y la herramienta devuelve un error de tiempo agotado
