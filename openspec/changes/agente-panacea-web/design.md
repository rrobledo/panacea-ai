## Context

Hoy el agente es Claude Code + `mcp_server/server.py` (stdio, 417 líneas), que lee `DATABASE_URL` y `SALES_TABLE` de variables de entorno globales, valida SQL con expresiones regulares y expone 8 herramientas sobre `public.panacea_sales_v2`. Las reglas de negocio y de reportes viven en `CLAUDE.md`. Los reportes son HTML sueltos en `reportes/`.

La propuesta "Agente Panacea Web" v1 (https://claude.ai/artifact/V6dpG2EyFHEd9ZuSmkW3de) define llevarlo a una app web en Vercel con perfiles, aclaraciones obligatorias, artifacts versionados y galería. Usuarios: ventas, planta/producción y gerencia (≈5 personas). Restricciones: serverless (sin estado en proceso, duración limitada), base de negocio solo lectura, costo de API acotado. La base de negocio es Postgres alojado en Vercel (Vercel Postgres / Neon del Marketplace), en la misma plataforma que la app.

## Goals / Non-Goals

**Goals:**
- Una sola implementación de las herramientas, usada por el servidor MCP y por la web.
- Permisos por perfil aplicados en la base (roles) y en el código (`sql_guard`, herramientas visibles), no solo en el prompt.
- Aclaraciones obligatorias garantizadas por código antes de cualquier reporte.
- Reportes guardados, versionados, trazables a sus consultas y mostrados de forma aislada.
- Costo y uso auditables, con topes.

**Non-Goals:**
- Publicar Artifacts de claude.ai desde la API (no existe esa función; la app tiene su propio sistema).
- Escritura en la base de negocio, carga de datos o ETL.
- Enlaces públicos fuera de la empresa (queda para una iteración posterior).
- Cálculo de margen: no hay columna de costo en ventas (el perfil producción podría aportarla más adelante).
- App móvil nativa; la web es responsive.

## Decisions

### 1. Repositorio: la web vive en este repo
Next.js en la raíz (`app/`, `components/`), FastAPI en `api/index.py`, paquete `agent/` compartido. `mcp_server/server.py` importa `agent.tools`.
- *Por qué*: el servidor MCP y la web deben compartir el mismo código sin publicar un paquete. Vercel detecta Next.js en la raíz y la función Python en `api/`.
- *Alternativa*: repo nuevo `panacea-agente-web/` como sugiere el boceto → obliga a vendorizar o publicar las herramientas. Descartado por ahora.

### 2. Herramientas en el mismo proceso (no MCP por HTTP)
`agent/tools/*` son funciones puras que reciben un `ContextoPerfil` (engine SQLAlchemy, tabla, columnas permitidas, límites, reglas). Un registro mapea nombre → (función, esquema JSON) y se usa tanto para `FastMCP` como para el array `tools` de la Messages API.
- *Por qué*: sin red extra, permisos por perfil triviales de aplicar, se puede pausar el turno.
- *Alternativas*: conector MCP de la API contra el servidor publicado (hay que exponerlo con auth y es difícil pausar); Claude Agent SDK (necesita proceso largo y FS, no encaja en Vercel); Managed Agents (la base debería ser accesible desde Anthropic; más adelante).

### 3. Loop de agente propio con el SDK `anthropic`
`agent/loop.py`: Messages API en streaming con `claude-opus-5-5`, `esfuerzo` del perfil (high al generar reportes). Por cada `tool_use`: validar que la herramienta esté en el perfil, ejecutar, persistir el resultado, emitir eventos SSE. Corta en `end_turn`, en `solicitar_aclaraciones`, al llegar a `max_herramientas_por_turno` o al superar el presupuesto de tokens.
- El historial se guarda tal cual lo devuelve la API (incluidos bloques de razonamiento) y solo se agrega al final.
- System prompt y herramientas por perfil son estables → `cache_control` en el último bloque del system y de las herramientas.
- Pensamiento adaptativo (`thinking: {type: "adaptive"}`); en Opus 5.5 no se puede desactivar y el esfuerzo por defecto es `medium`, por eso se fija siempre desde el perfil.
- Caché en tres puntos: system, última herramienta y `cache_control` automático en el pedido, que cubre el historial y hace que cada vuelta del loop reutilice la anterior. Verificar `cache_read_input_tokens` en las primeras llamadas reales: si el prefijo (system + herramientas) queda por debajo del mínimo cacheable, no se cachea.
- Herramientas con `eager_input_streaming: true`; como el servidor deja de validar la entrada, cada entrada se valida con un modelo pydantic derivado de la firma de la función antes de ejecutarla (inválida → `tool_result` con `is_error`).
- Rechazos: `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) re-ejecuta el pedido en otro modelo si el modelo principal rechaza por política. Configurable (`Servicios.fallbacks`). Un `stop_reason: refusal` final corta el turno y responde los `tool_use` sin ejecutarlos.
- Nunca queda un `tool_use` sin `tool_result`: truncado por `max_tokens`, rechazo o tope de herramientas se responden con `is_error`. El aviso de tope va como bloque de texto `[Sistema]` dentro del mensaje de resultados (no como mensaje `system`, que no puede quedar seguido de un mensaje del usuario), y la llamada siguiente usa `tool_choice: none`.
- Uso y costos: cada llamada se registra en `app.uso_tokens` con su costo estimado (`agent/costos.py`, precios por modelo; un modelo desconocido se cobra al precio más alto). El presupuesto por turno cuenta los tokens nuevos (sin lecturas de caché) y solo corta cuando el modelo pide más herramientas. El tope mensual (`tope_mensual_usd` en `usuarios.yaml`, general o por usuario) se controla antes de cada turno con lo consumido desde el 1° del mes (hora de Córdoba).
- Auditoría de SQL: `ContextoPerfil.auditor` se fija por herramienta en el loop; `ejecutar` registra cada consulta (filas, duración, error) y `consultar` también los rechazos de `sql_guard`. El servidor MCP no audita.
- Un turno por conversación a la vez: `tomar_turno` marca `en_curso` con un latido que se renueva durante el turno; otro pedido recibe 409. Si el latido tiene más de 5 minutos, el turno se considera cortado y se puede retomar.

### 4. Pausa por aclaraciones con `tool_use` pendiente
Al recibir `solicitar_aclaraciones`, se guarda la conversación en estado `esperando_aclaracion` con el `tool_use_id`. `POST /api/clarify` construye el `tool_result` (respuestas + `brief_id` si se aprobó) y reanuda el loop en la misma respuesta SSE. `generar_artifact` consulta `app.briefs` y exige `estado='aprobado'` y la misma conversación. Si el mismo mensaje trae otras herramientas, se ejecutan y guardan al pausar, y el mensaje con todos los `tool_result` se arma al reanudar. Un mensaje libre con la aclaración pendiente se guarda como respuesta de ajuste de ese `tool_use`.
- *Por qué*: forzarlo por código hace la regla inviolable; usar el mismo `tool_use` respeta el historial solo-agregado.
- *Alternativa*: solo instrucción en el prompt → el modelo puede saltearla.

### 5. Permisos en dos capas
- Base: un rol `agente_<perfil>_ro` por perfil con `GRANT SELECT` sobre sus tablas (o columnas), `statement_timeout` por rol, `default_transaction_read_only = on`.
- Código: `agent/sql_guard.py` con `sqlglot` (dialecto postgres): una sola sentencia, raíz `Select`/`With`/`Union`, sin funciones en lista negra (`pg_sleep`, `dblink`, `lo_*`, `pg_read_file`…), tablas calificadas resueltas contra la lista del perfil (excluyendo nombres de CTE), columnas validadas cuando el perfil las acota.
- *Por qué*: la validación da errores útiles al modelo; la base es la garantía final.

### 6. Esquema `app` y persistencia
Tablas: `conversaciones` (id, usuario, perfil, estado, tool_use_pendiente), `mensajes` (conversación, orden, rol, contenido JSONB), `pasos_herramienta` (mensaje, tool_use_id, nombre, argumentos, resultado, duración), `briefs` (conversación, contenido, estado), `artifacts` (título, tipo, perfil, autor, conversación, brief, fijado, versión_actual), `artifact_versions` (artifact, n, html, nota, datos_fuente JSONB), `auditoria_sql`, `uso_tokens`. Migraciones con SQL plano versionado en `sql/app/`. Conexión con rol de escritura `agente_app` vía `DB_URL_APP`.
- *Ubicación*: el esquema `app` va en la misma base Postgres de Vercel, separado de `public` por esquema y por rol. *Alternativa*: una base aparte en el mismo proveedor si se quiere aislar backups o carga; el código solo depende de `DB_URL_APP`, así que el cambio es de configuración.

### 7. Artifacts sobre plantilla y visor aislado
`agent/plantillas/reporte.html` con estilos Panacea, tokens claro/oscuro, Chart.js 4.4.1 y helpers de formato es-AR. El modelo envía secciones y datos (y opcionalmente HTML de secciones), el backend compone el documento. Validación: scripts externos solo de cdn.jsdelivr.net, sin cadenas de conexión. Se sirve con `Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline'; img-src data:` dentro de `<iframe sandbox="allow-scripts">`.
- *Por qué*: menos tokens de salida y estilo uniforme; el sandbox sin `allow-same-origin` impide leer la sesión.
- La CSP incluye además `sandbox allow-scripts`: aunque alguien abra la URL del HTML directamente (fuera del iframe), el documento corre con origen opaco.
- Cada versión guarda su `contenido` estructurado; `editar_artifact` recibe solo los campos que cambian y recompone sobre la versión anterior. `tool_use_id` único por versión: un turno retomado que repite la llamada devuelve la versión ya creada en vez de duplicarla.
- `datos_fuente` lo arma el backend con las herramientas de datos ejecutadas sin error desde la versión anterior en la conversación.
- Las herramientas de aclaraciones y reportes viven en un registro aparte (`HERRAMIENTAS_AGENTE`): reciben la conversación y el almacén, y no se exponen por MCP.

### 8. Frontend
Next.js App Router + Tailwind. Rutas: `/` (redirige al último chat), `/chat/[id]`, `/artifacts`, `/artifacts/[id]`, `/admin/uso`. Componentes: `ChatStream` (consume SSE con `fetch` + `ReadableStream`), `ClarifyCard`, `ArtifactFrame`, `Gallery`, `ProfileSelector`. El login es el mismo que el de panacea-compras: `/auth/google` (ruta de Next) redirige a panacea-produccion-backend, que hace el OAuth con Google y vuelve a `/auth/callback?token=<JWT>`; esa URL tiene que estar en su `FRONTEND_URLS`. El callback solo acepta un login iniciado en el mismo navegador (cookie `panacea.login`, 10 minutos, que además guarda la ruta interna a la que volver), valida el token, controla el email contra `usuarios.yaml` y lo guarda en la cookie httpOnly `panacea.sesion` (no en localStorage: los reportes que se abren en otra pestaña y el SSE la reciben solos). El backend lo vuelve a controlar en cada pedido. El rewrite de `/api/*` a FastAPI vive en `next.config.ts`: en desarrollo apunta a uvicorn y en Vercel a la función `api/index.py`, que recibe la ruta original. `scripts/demo_backend.py` levanta el backend con un Claude simulado para desarrollar la interfaz sin costo. El token es un JWT HS256 firmado con el `SECRET_KEY` de ese backend (claims `sub`, `email`, `role`, `exp`, 7 días); acá `AUTH_SECRET` tiene ese mismo valor y FastAPI lo valida con PyJWT leyendo la cookie `panacea.sesion` o un `Authorization: Bearer`. El usuario tiene que existir en ese backend y además figurar en `usuarios.yaml`. Los perfiles salen de `usuarios.yaml`.

### 9. Despliegue
Un proyecto de Vercel, `vercel.json` con rewrite `/api/(.*)` → `api/index.py` (salvo `/api/auth/*`, que atiende Next), Fluid compute y `maxDuration` alto para `/api/chat` y `/api/clarify`. Pool SQLAlchemy chico (`pool_size=1, max_overflow=1`) contra el host con pooler de la base de Vercel (`-pooler` en el host, PgBouncer en modo transacción). Como cada perfil tiene su propio rol, las variables `DB_URL_<PERFIL>` se arman a mano con ese usuario y el host con pooler; las variables que Vercel genera (`POSTGRES_URL`, `DATABASE_URL`) usan el rol dueño y quedan solo para migraciones. Como el pooler en modo transacción no conserva parámetros de sesión, `READ ONLY` y `statement_timeout` se fijan con `SET LOCAL` dentro de cada transacción (como ya hace `_ejecutar`) y además por rol con `ALTER ROLE ... SET`.

## Risks / Trade-offs

- [Creación de roles en Postgres de Vercel/Neon] → los roles por perfil se crean por SQL con el rol dueño (o desde la consola de Neon). Verificar al inicio de Fase 1 que `GRANT` por columna y `ALTER ROLE ... SET statement_timeout` funcionan en el plan contratado.
- [Límite de conexiones o de cómputo del plan de base] → siempre por el pooler, pool chico, timeouts por rol. Revisar si la base escala a cero (cold start de pocos segundos en la primera consulta).
- [Funciones cortadas en reportes de 1 a 3 min] → streaming obligatorio, estado guardado tras cada herramienta y reintento que retoma.
- [`sqlglot` no cubre algún SQL válido de Postgres] → mensaje de error claro al modelo; la base sigue siendo la barrera final; pruebas con las consultas reales de `sql/` y `trabajo/`.
- [Costo de API mayor al estimado] → caché de prompt, plantilla de reportes, presupuesto por turno, tope mensual y evaluar Sonnet 5.5 por perfil.
- [Regresiones al cambiar prompt o modelo] → set de 20 preguntas reales con respuestas verificadas (Fase 3).
- [HTML generado malicioso o con errores] → sandbox + CSP + validación previa; el riesgo residual es solo visual.
- [Divergencia entre CLAUDE.md y `prompts/ventas.md`] → `prompts/ventas.md` es la fuente; CLAUDE.md lo referencia o se genera desde ahí.

## Migration Plan

1. **Fase 0 (2 a 3 días)**: refactor a `agent/tools` + `sql_guard` + pruebas. El servidor MCP sigue funcionando; verificar con Claude Code antes de seguir. Rollback: revertir el commit.
2. **Fase 1 (1 semana)**: proyecto Next.js + FastAPI, login vía panacea-produccion-backend, `usuarios.yaml`, loop con streaming, esquema `app`, roles de Postgres, perfil ventas. Deploy en preview de Vercel.
3. **Fase 2 (1 semana)**: aclaraciones, artifacts con plantilla y versiones, visor aislado y galería.
4. **Fase 3 (3 a 5 días)**: perfil producción, tablero de uso y topes, set de evaluación. Pasar a producción.

El flujo actual con Claude Code se mantiene en todo momento; no hay migración de datos de negocio. Los HTML existentes de `reportes/` pueden importarse opcionalmente como artifacts versión 1.

## Open Questions

1. ¿Qué perfiles arrancan y con qué tablas? Falta la lista confirmada de tablas de producción y los usuarios de cada perfil.
2. ~~¿Dónde está la base y cómo llega Vercel?~~ Resuelto: Postgres en Vercel. Falta confirmar el plan de la base (límite de conexiones, escalado a cero).
3. ~~¿Login con Google Workspace o enlace por email?~~ Resuelto: Google (cualquier cuenta con email verificado que figure en `usuarios.yaml`).
4. ¿Todos los usuarios de un perfil ven sus reportes, o cada uno los suyos más los fijados? (diseño actual: por perfil)
5. ¿Presupuesto mensual de API? Define modelo y esfuerzo por perfil y el tope por usuario.
6. ¿Hace falta compartir reportes fuera de la empresa? (por defecto, no)
7. ~~¿El esquema `app` va en la instancia actual o en Neon?~~ Resuelto: misma base, esquema `app`.
