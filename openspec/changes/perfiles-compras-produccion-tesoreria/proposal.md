## Why

Hoy el agente tiene un solo perfil, `ventas`, que lee una tabla (`panacea_sales_v2`). Las áreas de compras, producción y tesorería no pueden usarlo, aunque la base ya tiene sus datos: facturas y pagos a proveedores, plan y producción diaria, órdenes, desperdicio, recetas y cobros por medio de pago. El relevamiento del 14/11/2026, cruzado con los módulos de `panacea-produccion-backend`, identificó qué tablas están vigentes, cuáles están deprecadas y cuáles conviene exponer.

Fuente: artifact "Tablas del agente Panacea", versión 2 (14/11/2026), https://claude.ai/artifact/9dmZKZ44VEe7jGSUB92iYE

## What Changes

- Tres perfiles nuevos en `config/perfiles/`: `compras`, `produccion` y `tesoreria`. Cada uno con su prompt, sus tablas, su rol de Postgres de solo lectura y su variable de credencial.
- Cada perfil recibe las tablas marcadas como **Candidata** en el relevamiento para su área. También recibe unas pocas marcadas **Revisar** que son imprescindibles (`compras_compra`, `compras_movimiento_cc`, `costos_costos`); su problema de datos se avisa en el prompt.
- Nunca se exponen las tablas **Deprecada**, **Excluir** ni **Vacía**: la cuenta corriente vieja, los remitos viejos, los costos en inglés, los adjuntos binarios, `socios`, etc.
- Las tablas con datos personales o muchas columnas se exponen acotadas a las columnas necesarias. Ejemplos: `documentos` solo con las columnas de cobro, `costos_proveedor` sin teléfono, email ni dirección, `panacea_sales_v2` sin cliente para producción.
- Un diccionario por tabla en `prompts/diccionarios/`, que entra en el prompt de cada perfil.
- `describir_tabla` pasa a recibir el nombre de la tabla: hoy describe solo la tabla principal y ordena por `operation_date`, así que no sirve para perfiles con varias tablas. Esto no cambia el comportamiento del perfil de ventas.
- Script SQL de roles (`sql/roles_perfiles_area.sql`) con `GRANT SELECT` por tabla y por columna.
- Preguntas de evaluación por perfil, con su SQL de verificación.
- **Sin cambios en el perfil `ventas`**: mismas tablas, herramientas y prompt.
- Fuera de alcance: herramientas específicas por área (aging de deuda, plan contra real, flujo de fondos). En esta etapa los perfiles nuevos usan `consultar`, `describir_tabla` y los reportes. El servidor MCP de Claude Code sigue siendo de ventas.

## Capabilities

### New Capabilities
- `area-profiles`: Perfiles `compras`, `produccion` y `tesoreria`: tablas y columnas permitidas, reglas de exclusión, prompts, diccionarios, roles de base y evaluación.
- `table-description`: `describir_tabla` con parámetro de tabla, limitado a las tablas y columnas del perfil y ordenado por la columna de fecha de cada tabla.

### Modified Capabilities
<!-- No hay specs archivadas en openspec/specs/. El perfil de ventas no cambia. -->

## Impact

- **Configuración**: `config/perfiles/compras.yaml`, `produccion.yaml`, `tesoreria.yaml`; los usuarios se asignan aparte en `config/usuarios.yaml`.
- **Prompts**: `prompts/compras.md`, `prompts/produccion.md`, `prompts/tesoreria.md` y unos 20 diccionarios nuevos en `prompts/diccionarios/`.
- **Código**: `agent/tools/generic.py` (`describir_tabla`), `agent/contexto.py` (columna de fecha por tabla), `agent/profiles.py` (pasa ese dato al contexto). Tests de perfiles, de `describir_tabla` y de `sql_guard` con columnas acotadas.
- **Base de datos**: roles `agente_compras_ro`, `agente_produccion_ro` y `agente_tesoreria_ro`, con `default_transaction_read_only` y `statement_timeout`.
- **Infraestructura**: variables `DB_URL_COMPRAS`, `DB_URL_PRODUCCION` y `DB_URL_TESORERIA` en Vercel y en `.env.example`.
- **Costos**: más prompt por perfil (los diccionarios). Entra en el caché, así que el impacto por turno es bajo.
