## Why

El analista de ventas de Panacea hoy solo funciona dentro de Claude Code, con un servidor MCP local y una única tabla. Eso limita su uso a quien tiene la consola configurada, no permite separar qué datos ve cada equipo y deja los reportes como archivos HTML sueltos en `reportes/`. Llevarlo a una aplicación web con perfiles, aclaraciones obligatorias y una galería permite que ventas, producción y gerencia lo usen con controles de acceso reales y que los reportes queden guardados, versionados y auditables.

Fuente: propuesta técnica "Agente Panacea Web" v1 (11/11/2026), https://claude.ai/artifact/V6dpG2EyFHEd9ZuSmkW3de

## What Changes

- Extraer las 8 herramientas de `mcp_server/server.py` a un paquete reutilizable (`agent/tools`) que recibe tabla, conexión y límites como parámetros. El servidor MCP pasa a importar ese paquete y sigue funcionando igual para Claude Code.
- Reemplazar la validación de SQL por expresiones regulares por un `sql_guard` basado en `sqlglot` que, además de exigir un único `SELECT`/`WITH`, valida que solo se usen las tablas (y columnas, si están acotadas) del perfil.
- Nuevo backend FastAPI en Python con un loop de agente propio sobre el SDK `anthropic` (Claude Opus 5.5), streaming por SSE y estado persistido después de cada herramienta.
- Perfiles definidos en `config/perfiles/*.yaml` (prompt, tablas, herramientas, credencial de base, reglas y límites) y asignación de usuarios en `config/usuarios.yaml`. Un rol de Postgres de solo lectura por perfil.
- Nueva herramienta `solicitar_aclaraciones`: el agente debe presentar preguntas y un brief, el turno se pausa y el usuario aprueba o ajusta. `generar_artifact` rechaza cualquier llamada sin un `brief_id` aprobado.
- Nuevas herramientas `generar_artifact` y `editar_artifact`: reportes HTML autocontenidos (Chart.js 4.4.1, formato es-AR, modo claro/oscuro) a partir de una plantilla Panacea, guardados con versiones y con las consultas SQL que los alimentaron.
- Frontend Next.js (App Router, Tailwind): login con Auth.js, chat con pasos visibles, tarjeta de aclaraciones, visor de reportes en iframe aislado y galería `/artifacts` con filtros.
- Esquema `app` en Postgres para conversaciones, mensajes, briefs, artifacts, versiones y auditoría de SQL y tokens, con presupuesto por turno y tope mensual por usuario.
- Despliegue en un único proyecto de Vercel (Next.js + función Python), con `vercel.json` reescribiendo `/api/*` hacia FastAPI.

## Capabilities

### New Capabilities
- `shared-tools`: Biblioteca de herramientas de análisis parametrizada por perfil, compartida entre el servidor MCP y el backend web, con validación de SQL por tablas permitidas.
- `profiles-access`: Perfiles en YAML, asignación de usuarios a perfiles, autenticación y aplicación del perfil (prompt, herramientas visibles, credencial de base) en cada pedido.
- `agent-chat`: Chat web con loop de agente, streaming SSE de texto y pasos de herramientas, y conversaciones persistidas y reanudables.
- `report-clarification`: Paso obligatorio de aclaraciones con brief aprobado por el usuario antes de generar cualquier reporte.
- `report-artifacts`: Generación, edición versionada, almacenamiento y visualización aislada de reportes HTML.
- `artifact-gallery`: Galería de reportes con búsqueda, filtros, fijados y visibilidad por perfil.
- `usage-audit`: Auditoría de cada consulta SQL y del consumo de tokens, con presupuestos por turno y topes mensuales por usuario.

### Modified Capabilities
<!-- No hay specs existentes en openspec/specs/. -->

## Impact

- **Código**: `mcp_server/server.py` se reduce a un adaptador sobre `agent/tools`. Nuevos directorios `app/`, `components/`, `api/`, `agent/`, `config/`, `prompts/` en la raíz del repo. `CLAUDE.md` se reutiliza como base de `prompts/ventas.md`.
- **Dependencias**: Python `fastapi`, `anthropic`, `sqlglot`, `pyyaml`, `pydantic`; Node `next`, `react`, `tailwindcss`, `next-auth` (Auth.js).
- **Base de datos**: roles `agente_ventas_ro` y `agente_produccion_ro` con `GRANT SELECT` acotado y `statement_timeout`; rol de escritura de la app sobre el nuevo esquema `app` en la misma base Postgres de Vercel.
- **Infraestructura**: proyecto de Vercel Pro con Fluid compute; variables de entorno `ANTHROPIC_API_KEY`, `DB_URL_VENTAS`, `DB_URL_PRODUCCION`, `DB_URL_APP`, secretos de Auth.js. La base Postgres ya está alojada en Vercel, así que la conectividad está resuelta; se usa la cadena de conexión con pooler.
- **Costos**: estimado US$100 a 250 por mes de API para 5 usuarios, 400 preguntas y 40 reportes, más Vercel Pro.
- **Bloqueante resuelto**: la base es Postgres en Vercel, en la misma plataforma que la app.
