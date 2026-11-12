## 1. Fase 0 · Paquete de herramientas compartido

- [x] 1.1 Crear `agent/__init__.py`, `agent/tools/__init__.py` y `agent/contexto.py` con la dataclass `ContextoPerfil` (engine, tabla, columnas permitidas, max_filas, timeout_sql_seg, reglas)
- [x] 1.2 Mover utilidades (`_ser`, `_fecha`, `_ejecutar`, `_json`) a `agent/tools/base.py`, recibiendo el contexto en lugar de globales (`_filtros`, `DIMENSIONES` y `METRICAS` son propias de ventas y quedan en `agent/tools/ventas.py`)
- [x] 1.3 Mover `describir_tabla` y `consultar` a `agent/tools/generic.py` (`perfil_datos` usa columnas de ventas y queda en `ventas.py`; un `perfil_datos` genérico se agrega con el perfil producción, 9.1)
- [x] 1.4 Mover `resumen_ventas`, `comparar_periodos`, `clientes_inactivos`, `productos_asociados`, `proyectar_ventas` a `agent/tools/ventas.py`, aplicando `reglas.excluir_clientes_en_analisis`
- [x] 1.5 Crear el registro de herramientas (nombre → función + esquema JSON) en `agent/tools/registro.py`
- [x] 1.6 Reescribir `mcp_server/server.py` como adaptador: arma el contexto desde `DATABASE_URL`, `SALES_TABLE`, `MAX_FILAS`, `TIMEOUT_SEG` y registra las 8 herramientas desde el registro
- [x] 1.7 Implementar `agent/sql_guard.py` con `sqlglot`: sentencia única, raíz SELECT/WITH, funciones prohibidas, tablas y columnas permitidas, CTE excluidos
- [x] 1.8 Conectar `consultar` a `sql_guard` usando las tablas del contexto
- [x] 1.9 Pruebas de `sql_guard` (tabla ajena, varias sentencias, columna fuera de alcance, CTE válido, funciones prohibidas, consultas reales de `sql/` y `trabajo/`)
- [x] 1.10 Pruebas de equivalencia de las 8 herramientas antes/después del refactor contra una base de prueba
- [x] 1.11 Verificar desde Claude Code que el servidor MCP responde igual con el `.mcp.json` actual
- [x] 1.12 Actualizar `requirements.txt` (`sqlglot`, `pyyaml`, `pydantic`) y `requirements-dev.txt` (`pytest`)

## 2. Fase 1 · Perfiles y base de datos

- [x] 2.1 Crear `config/perfiles/ventas.yaml`, `config/usuarios.yaml` y `prompts/ventas.md` (a partir de `CLAUDE.md`) y `prompts/diccionarios/panacea_sales_v2.md`
- [x] 2.2 Implementar `agent/profiles.py`: carga y validación con pydantic, error con archivo y campo; herramientas inexistentes rechazadas
- [x] 2.3 Construir `ContextoPerfil` por perfil con engine cacheado por `credencial_env` (pool chico)
- [ ] 2.4 Script SQL `sql/roles_perfiles.sql`: rol `agente_ventas_ro` con `GRANT SELECT`, `statement_timeout`, `default_transaction_read_only`; ejecutarlo con el rol dueño de la base de Vercel y comprobar que el `GRANT` por columna y `ALTER ROLE ... SET` funcionan
- [x] 2.5 Migraciones `sql/app/001_esquema.sql`: `conversaciones`, `mensajes`, `pasos_herramienta`, `briefs`, `artifacts`, `artifact_versions`, `auditoria_sql`, `uso_tokens`, permisos de `agente_app` (el rol se crea en 2.4). Probada en un Postgres 16 temporal; falta aplicarla en la base de Vercel
- [x] 2.6 Pruebas de carga de perfiles y de aplicación de reglas

## 3. Fase 1 · Backend y loop del agente

- [x] 3.1 Crear `api/index.py` (FastAPI) con `/api/profiles`, `/api/chat`, `/api/conversaciones/{id}`
- [x] 3.2 Validación de sesión (JWT de Auth.js) y resolución de perfiles del usuario; 401/403 según corresponda
- [x] 3.3 Implementar `agent/loop.py`: Messages API en streaming, herramientas del perfil, ejecución de `tool_use`, `is_error` en fallos, corte en `end_turn` (confirmar parámetros con la skill `claude-api`)
- [x] 3.4 Armado del system prompt (prompt del perfil + diccionarios) con `cache_control` en system y herramientas
- [x] 3.5 Persistencia solo-agregado de mensajes (incluidos bloques de razonamiento) y de cada paso de herramienta
- [x] 3.6 Reanudación: al reintentar un turno, reutilizar resultados de herramientas ya guardados
- [x] 3.7 Eventos SSE: `conversacion`, `texto`, `reinicio`, `herramienta_inicio`, `herramienta_fin`, `aviso`, `error`, `fin` (`aclaraciones` y `artifact` se agregan en 5.2 y 6.2)
- [x] 3.8 Tope `max_herramientas_por_turno` con respuesta final sin herramientas y aviso
- [x] 3.9 Pruebas del loop con cliente Anthropic simulado (pasos, error de herramienta, tope, reanudación)

## 4. Fase 1 · Frontend, auth y despliegue

- [ ] 4.1 Inicializar Next.js (App Router, TypeScript, Tailwind) en la raíz y `package.json`
- [ ] 4.2 Configurar Auth.js (Google o email) y restringir a emails de `usuarios.yaml`; pantalla de acceso denegado
- [ ] 4.3 Layout con barra superior, selector de perfil y tema claro/oscuro
- [ ] 4.4 Componente `ChatStream`: consumo de SSE, texto parcial y pasos con duración
- [ ] 4.5 Rutas `/chat/[id]` (historial y continuar) y `/` (último chat o nuevo)
- [ ] 4.6 `vercel.json` con rewrite de `/api/*` a FastAPI (excepto `/api/auth/*`), `maxDuration` para chat y clarify
- [ ] 4.7 Vincular la base Postgres de Vercel al proyecto y configurar variables de entorno: `DB_URL_VENTAS`, `DB_URL_PRODUCCION` y `DB_URL_APP` con el rol de cada uno y el host con pooler; `POSTGRES_URL_NON_POOLING` solo para migraciones
- [ ] 4.8 Deploy en preview y prueba de punta a punta con el perfil ventas

## 5. Fase 2 · Aclaraciones obligatorias

- [x] 5.1 Herramienta `solicitar_aclaraciones` con esquema estricto (brief + hasta 6 preguntas) en `agent/tools/clarify.py`
- [x] 5.2 En el loop: al recibirla, guardar `tool_use` pendiente, estado `esperando_aclaracion`, emitir evento y cerrar turno
- [x] 5.3 Endpoint `POST /api/clarify`: aprobar (crea `brief_id`) o ajustar (comentario sin `brief_id`), arma el `tool_result` y reanuda el loop por SSE
- [x] 5.4 Mensaje libre con aclaración pendiente → se envía como ajuste del `tool_use` pendiente
- [ ] 5.5 Componente `ClarifyCard` (backend listo: evento `aclaraciones`, `aclaracion_pendiente` en el historial): preguntas por tipo, recomendada preseleccionada, brief "Voy a generar", botones Aprobar y Ajustar
- [x] 5.6 Pruebas: generación sin brief, brief de otra conversación, ajuste, aprobación

## 6. Fase 2 · Artifacts

- [x] 6.1 Plantilla `agent/plantillas/reporte.html` (estilos Panacea, claro/oscuro, Chart.js 4.4.1, formato es-AR, secciones de resumen, KPIs, gráficos, proyección con banda, estrategias, nota metodológica)
- [x] 6.2 Herramienta `generar_artifact`: valida `brief_id`, compone sobre la plantilla, valida scripts y credenciales, guarda versión 1 con `datos_fuente`, emite evento `artifact`
- [x] 6.3 Herramienta `editar_artifact`: nueva versión con nota, mismo perfil, conserva versiones previas
- [x] 6.4 Registro automático de `datos_fuente` a partir de los pasos de herramienta del turno
- [x] 6.5 Endpoints `GET /api/artifacts`, `GET /api/artifacts/{id}`, `GET /api/artifacts/{id}/html?version=n` (`&descargar=true` para bajarlo) con sesión, acceso por perfil y CSP
- [ ] 6.6 Componente `ArtifactFrame` con `iframe sandbox="allow-scripts"` y ruta `/artifacts/[id]` con selector de versión, descarga, copiar enlace, abrir conversación y ver fuentes
- [x] 6.7 Pruebas: dominio de script no permitido, credencial en HTML, edición de artifact de otro perfil, 401 sin sesión

## 7. Fase 2 · Galería

- [x] 7.1 Endpoint de listado con búsqueda por título y filtros por perfil, autor, tipo y fechas; visibilidad por perfil y admin
- [x] 7.2 Endpoint para fijar/desfijar artifacts por perfil
- [ ] 7.3 Ruta `/artifacts` con `Gallery`, filtros combinables, vista previa y fijados primero
- [ ] 7.4 Panel "Reportes recientes" en el chat que sigue al perfil seleccionado
- [x] 7.5 Pruebas de visibilidad (perfil ajeno → 404, admin ve todo)

## 8. Fase 3 · Auditoría, uso y topes

- [x] 8.1 Registrar cada consulta (ejecutada o rechazada) en `app.auditoria_sql`
- [x] 8.2 Registrar uso de tokens por llamada (entrada, salida, caché) y costo estimado en `app.uso_tokens`
- [x] 8.3 Corte por `presupuesto_tokens_por_turno` con respuesta final y aviso
- [x] 8.4 Tope mensual por usuario (`tope_mensual_usd` general y por usuario en `usuarios.yaml`): `POST /api/chat` y `POST /api/clarify` responden 429 al superarlo
- [ ] 8.5 Ruta `/admin/uso` con consumo y costo por usuario y perfil, solo para admin (backend listo: `GET /api/admin/uso?mes=AAAA-MM`, 403 sin admin; falta la pantalla)

## 9. Fase 3 · Segundo perfil y puesta en marcha

- [ ] 9.1 Confirmar tablas de producción y crear `config/perfiles/produccion.yaml`, `prompts/produccion.md` y rol `agente_produccion_ro` con columnas acotadas
- [x] 9.2 Set de 20 preguntas reales con respuestas verificadas y script de evaluación (`evals/`; respuestas calculadas con SQL independiente, falta revisión humana y la primera corrida con la API)
- [x] 9.3 Actualizar `README.md` con instalación, variables de entorno, alta de perfiles y despliegue
- [ ] 9.4 Deploy a producción en Vercel y verificación de punta a punta con ambos perfiles
