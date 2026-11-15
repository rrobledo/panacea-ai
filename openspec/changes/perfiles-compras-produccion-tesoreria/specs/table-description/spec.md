## ADDED Requirements

### Requirement: Describir cualquier tabla del perfil
`describir_tabla(tabla?)` SHALL aceptar el nombre de una tabla del perfil, con o sin esquema (`compras_pago` o `public.compras_pago`), y devolver sus columnas permitidas con su tipo, las filas estimadas y 5 filas de ejemplo. Sin parámetro, MUST describir la tabla principal del perfil, como hasta ahora.

#### Scenario: Sin parámetro en ventas
- **WHEN** el perfil `ventas` llama a `describir_tabla()`
- **THEN** la respuesta es igual a la actual: columnas de `public.panacea_sales_v2` y 5 filas ordenadas por `operation_date` descendente

#### Scenario: Tabla de otro perfil
- **WHEN** el perfil `compras` llama a `describir_tabla("ordenes_produccion")`
- **THEN** la herramienta responde con un error que lista las tablas disponibles para el perfil, sin consultar la base

### Requirement: Solo columnas permitidas
Cuando la tabla tiene columnas acotadas en el perfil, `describir_tabla` SHALL listar y seleccionar solo esas columnas. MUST NOT usar `SELECT *`.

#### Scenario: Tabla acotada
- **WHEN** el perfil `tesoreria` llama a `describir_tabla("documentos")`
- **THEN** las columnas y las filas de ejemplo incluyen solo las 24 columnas permitidas, sin `idcliente` ni `nrodoccliente`

### Requirement: Orden por la columna de fecha de cada tabla
Las filas de ejemplo SHALL ordenarse por la `columna_fecha` configurada para la tabla, en forma descendente. Una tabla sin columna de fecha MUST devolver 5 filas sin orden.

#### Scenario: Tabla con fecha
- **WHEN** el perfil `produccion` describe `productos_fabricados`
- **THEN** las 5 filas de ejemplo son las de `fecha` más reciente

#### Scenario: Tabla sin fecha
- **WHEN** el perfil `produccion` describe `costos_costos`
- **THEN** devuelve 5 filas cualquiera sin fallar por falta de `operation_date`

### Requirement: Descripción de consultar independiente de ventas
La descripción de `consultar` SHALL pedir filtrar por la columna de fecha de cada tabla (la que figura en el prompt del perfil), en lugar de nombrar `operation_date`.

#### Scenario: Descripción en un perfil de área
- **WHEN** el modelo del perfil `compras` recibe la definición de `consultar`
- **THEN** el texto no menciona `operation_date`
