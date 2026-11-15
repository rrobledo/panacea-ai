## Context

La app web ya está preparada para más de un perfil: cada uno es un YAML con su prompt, sus tablas (con columnas opcionales), sus herramientas y su variable de credencial. `sql_guard` valida tablas y columnas, y cada perfil tiene su rol de Postgres. Hasta ahora solo existe `ventas`.

El relevamiento del 14/11/2026 (artifact "Tablas del agente Panacea", v2) clasificó las tablas de la base y las cruzó con los modelos, servicios y migraciones de `panacea-produccion-backend`. Ese documento es la fuente de las listas de este cambio.

Hay dos obstáculos de código:
- `describir_tabla` describe solo `ctx.tabla` y ordena por `operation_date`. En un perfil sin ventas falla o describe la tabla equivocada.
- La descripción de `consultar` habla de `operation_date`, que en los perfiles nuevos no existe.

## Goals / Non-Goals

**Goals:**
- Que compras, producción y tesorería puedan preguntar y pedir reportes sobre sus datos, con el mismo control de acceso que ventas.
- Exponer lo mínimo necesario: tablas vigentes, y columnas acotadas donde hay datos personales o columnas que no aportan.
- Que el agente conozca los problemas de datos de cada área antes de responder.
- No tocar el perfil de ventas.

**Non-Goals:**
- Herramientas específicas por área (aging de deuda, flujo de fondos, plan contra real, merma por receta). Primero hay que ver qué preguntan los usuarios con `consultar`; las herramientas vienen en un cambio posterior.
- Arreglar los datos de origen: fechas futuras en compras, arqueos cortados en 2024, Mercado Pago con dos meses.
- Exponer las copias por sucursal de `documentos` (`_cp`, `_va`, `_cba`, `_vgb`). Ver Open Questions.
- Cambiar el servidor MCP local, que sigue siendo de ventas.
- Asignar usuarios a los perfiles nuevos: lo decide el negocio en `config/usuarios.yaml`.

## Decisions

### 1. Qué entra en cada perfil
Entran las tablas marcadas Candidata para el área. Entran también tres marcadas Revisar, porque sin ellas el perfil no sirve: `compras_compra` y `compras_movimiento_cc` (compras y tesorería) y `costos_costos` (producción). En esos casos, el problema se explica en el prompt.

No entran las Revisar que no son imprescindibles:
- `cajasaperturas` y `cajasaperturas_cp`: cortadas en 2024.
- `mercadopago_movimientos`: dos meses cargados una vez.
- `planificacion2024`: reemplazada por `costos_planificacion`.
- `articulos` y `clientes`: tienen sustitutos o datos personales.

*Alternativa descartada:* dar a cada perfil todas las tablas de su módulo del backend. Expone tablas vacías y deprecadas, y el modelo pierde tiempo explorándolas.

### 2. Tablas compartidas entre perfiles
Una tabla puede estar en más de un perfil:
- Compras y tesorería comparten facturas, pagos, cuenta corriente y proveedores.
- Producción y compras comparten `costos_insumos`.

En tesorería, `compras_compra` se acota a las columnas de importes y vencimientos: no necesita el detalle fiscal. Los perfiles son vistas por pregunta de negocio, no particiones de la base.

### 3. Columnas acotadas
- `documentos` (76 columnas): solo las 24 de cobro. Quedan afuera el cliente (`idcliente`, `nombreclienteeventual`, `nrodoccliente`, `idtpdoccliente`) y los datos de AFIP.
- `costos_proveedor`: sin `telefono`, `email` ni `direccion`.
- `panacea_sales_v2` en producción: sin `customer_id` ni `customer`.
- `cajas`: sin `sincroweb` ni `idbase`.

Cuando un perfil tiene una tabla acotada, `contexto_para` ya carga las columnas reales de todas sus tablas para que `sql_guard` resuelva `*` y columnas sin calificar. No hace falta código nuevo.

### 4. Lista negra en la validación de perfiles
`agent/profiles.py` suma `TABLAS_NO_EXPONIBLES`: las deprecadas y las excluidas del relevamiento, más los prefijos `auth_`, `django_` y el esquema `app`. Si un perfil incluye alguna, la carga falla con archivo y tabla.

Esto convierte el relevamiento en una regla que se verifica, en lugar de un documento que se olvida. Las Vacía no entran en la lista: pueden empezar a cargarse y entonces sí sumarse.

### 5. describir_tabla con parámetro
El parámetro es `tabla: str | None = None`. Se normaliza a `public.<tabla>` si viene sin esquema y se valida contra `ctx.tablas_permitidas`. Las columnas salen de `information_schema` filtradas por las permitidas, y la consulta de ejemplo selecciona esas columnas explícitamente.

`ContextoPerfil` suma `columnas_fecha: dict[str, str]`, que se llena desde `Tabla.columna_fecha` en `contexto_para`. En el servidor MCP queda `{tabla: "operation_date"}`, así que la salida para ventas no cambia y el test de equivalencia con el servidor original sigue pasando.

### 6. Tabla principal
`ContextoPerfil.tabla` es obligatoria. En cada perfil de área es la tabla con más preguntas esperadas: `compras_compra`, `costos_programacion` y `compras_pago`. Solo la usan `describir_tabla()` sin parámetro y la auditoría.

### 7. Prompts y diccionarios
Un prompt por área, con la misma estructura que `prompts/ventas.md`: reglas de cálculo, problemas de datos conocidos, análisis frecuentes, formato de estrategias y reportes. Un diccionario por tabla, compartido entre los perfiles que la usan. Cuando una tabla está acotada distinto en dos perfiles (`compras_compra`, `costos_proveedor`), el diccionario documenta todas sus columnas, y el prompt del perfil acotado aclara cuáles ve: `system_prompt` ya agrega "(solo las columnas: …)" a la lista de tablas.

### 8. Roles de base
Un script, `sql/roles_perfiles_area.sql`, con los tres roles. Usa `GRANT SELECT (col1, col2…)` en las tablas acotadas y `GRANT SELECT` completo en el resto. Se ejecuta a mano como administrador, igual que `sql/usuario_solo_lectura.sql`. El `GRANT` sobre la vista `articulos_final` alcanza: la vista lee las tablas de base con los permisos de su dueño.

## Risks / Trade-offs

- [El modelo arma SQL incorrecto sobre esquemas que no conoce] → Diccionarios con claves de unión explícitas y ejemplos de consultas típicas en cada prompt. Evaluación con SQL de verificación antes de habilitar usuarios.
- [Fechas futuras en compras distorsionan los totales del período] → Regla en el prompt: separar fechas posteriores a hoy y avisarlas. Pregunta de evaluación que lo controla.
- [La receta vieja y la nueva conviven] → El prompt de producción indica cuál usar para qué: `costos_costos` para costo de materia prima, `procesos_proceso_linea` para rendimiento y merma esperada. El agente aclara cuál usó.
- [Prompt más largo con unos 15 diccionarios en producción] → Entra en el caché de prompt. Diccionarios concisos, solo con las columnas útiles.
- [Un `GRANT` por columna olvidado deja al rol sin acceso] → `contexto_para` falla al cargar columnas si el rol no ve la tabla, con un mensaje que nombra la tabla y la variable. Hay un test con la base real (`@pytest.mark.db`) por perfil.
- [Datos de proveedores (CUIT) en tesorería y compras] → Son datos de empresas, necesarios para identificar al proveedor. Se acotan los de contacto.

## Migration Plan

1. Mergear el cambio de código (`describir_tabla`, lista negra) con los perfiles nuevos, todavía sin usuarios asignados.
2. Ejecutar `sql/roles_perfiles_area.sql` en la base real y cargar las tres variables en Vercel (y en `.env.local` para pruebas).
3. Correr las evaluaciones de cada perfil y revisar las respuestas a mano.
4. Asignar usuarios en `config/usuarios.yaml`.

Rollback: quitar los perfiles de `config/perfiles/`, o sacarlos de los usuarios. Los roles pueden quedar: sin variable configurada no se usan.

## Open Questions

- **Copias por sucursal (relevado durante la implementación):** `documentos` es la base de Villa Allende y la Dietética. En octubre de 2026, `documentos_cp` coincide con los 1.360 tickets de Carlos Paz y `documentos_vgb` con los de VGB. Pero todas las copias comparten la misma historia de 2022 y 2023 (conteos idénticos): cada sucursal arrancó como clon de la base original. Para sumarlas hace falta una fecha de corte por sucursal (o un filtro por empresa o caja), a confirmar con quien administra el sistema de caja. Hasta entonces, tesorería cubre solo Villa Allende y la Dietética, y lo aclara.
- **Desperdicio:** `productos_fabricados.cantidad_desperdicio` vale 0 en las 421 filas. ¿Se carga en otro lado o el flujo de cierre de orden no lo pide?
- **Proveedores que son conceptos:** SUELDO, ADELANTOS, FERIADOS, HORAS EXTRAS, ALQUILER CP y COMBUSTIBLE figuran como proveedores. Conviene corregirlo en el backend; mientras tanto, los prompts los excluyen de los rankings.
- **Usuarios:** ¿quiénes usan compras, producción y tesorería, y con qué tope mensual?
- **Pagos en compras:** ¿el perfil de compras necesita también los medios de pago (`compras_pago_medio`), o eso queda solo en tesorería?
- **Arqueos y Mercado Pago:** si se reactiva la sincronización de `cajasaperturas` o la carga de `mercadopago_movimientos`, se suman a tesorería en un cambio aparte.
