## ADDED Requirements

### Requirement: Generar artifact
La herramienta `generar_artifact(brief_id, titulo, tipo, contenido estructurado)` (resumen, KPIs, secciones con texto, gráfico, tabla o HTML propio, estrategias, nota metodológica) SHALL crear un artifact de tipo `reporte`, `tablero` o `tabla` con su versión 1, ligado al perfil, autor, conversación y brief, y SHALL emitir el evento `artifact` con su enlace.

#### Scenario: Reporte creado
- **WHEN** el modelo llama a `generar_artifact` con un `brief_id` aprobado
- **THEN** se guarda en `app.artifacts` y `app.artifact_versions` (versión 1) y el chat muestra el enlace al reporte

### Requirement: Formato del reporte
El HTML generado SHALL armarse sobre la plantilla base de Panacea, ser autocontenido, cargar solo Chart.js 4.4.1 desde jsdelivr, formatear montos con `Intl.NumberFormat('es-AR', {style:'currency', currency:'ARS'})`, soportar modo claro y oscuro, ser responsive, y MUST NOT contener credenciales ni datos de conexión.

#### Scenario: Script externo no permitido
- **WHEN** el HTML incluye un `<script src>` de un dominio distinto de cdn.jsdelivr.net
- **THEN** la herramienta lo rechaza con un error que nombra el dominio

#### Scenario: Credencial en el HTML
- **WHEN** el HTML contiene una cadena con forma de URL de conexión `postgres://` o el valor de una variable de credencial
- **THEN** la herramienta rechaza el artifact

### Requirement: Trazabilidad de datos
Cada versión SHALL guardar en `datos_fuente` las consultas SQL (o llamadas a herramientas con sus argumentos) que alimentaron sus números. El backend las registra solo, a partir de las herramientas de datos ejecutadas sin error en la conversación desde la versión anterior; el modelo no las declara.

#### Scenario: Auditar un número
- **WHEN** un usuario abre la información de una versión
- **THEN** ve la lista de consultas y herramientas usadas para construirla

### Requirement: Edición versionada
La herramienta `editar_artifact(artifact_id, nota, campos que cambian)` SHALL crear la versión siguiente (los campos omitidos se mantienen de la versión anterior) sobre el mismo brief, sin requerir aclaraciones nuevas, y conservar las versiones previas.

#### Scenario: Agregar comparación
- **WHEN** el usuario pide "agregá la comparación con 2025" sobre un reporte en versión 2
- **THEN** se crea la versión 3 con su nota de cambio y la versión 2 sigue disponible

#### Scenario: Artifact de otro perfil
- **WHEN** el modelo intenta editar un artifact de un perfil distinto al de la conversación
- **THEN** la herramienta devuelve error

### Requirement: Visualización aislada
Los artifacts SHALL servirse desde `GET /api/artifacts/{id}/html` (opcionalmente `?version=n`) solo con sesión válida y acceso al perfil, con una cabecera CSP que permita scripts únicamente inline y de cdn.jsdelivr.net, y SHALL mostrarse en un `<iframe sandbox="allow-scripts">` sin `allow-same-origin`.

#### Scenario: Sin sesión
- **WHEN** se pide la URL del HTML sin sesión
- **THEN** la respuesta es 401

#### Scenario: Script del reporte intenta leer la sesión
- **WHEN** el HTML del reporte intenta leer `document.cookie` o llamar a `/api/*`
- **THEN** el navegador lo impide por el origen opaco del iframe

### Requirement: Acciones sobre el reporte
El visor SHALL ofrecer descargar el HTML, copiar el enlace interno, elegir versión y abrir la conversación que lo creó.

#### Scenario: Descarga
- **WHEN** el usuario pulsa "Descargar HTML"
- **THEN** recibe un archivo `.html` de la versión que está viendo
