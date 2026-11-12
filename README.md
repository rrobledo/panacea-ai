# Agente de ventas Panacea

Dos formas de usar el mismo agente analista sobre la base Postgres de Panacea:

- **Claude Code + servidor MCP** (`mcp_server/server.py`): desde la terminal, para quien trabaja con
  Claude Code. Funciona hoy.
- **App web** (`api/` + futura interfaz Next.js, en construcción): chat con perfiles, aclaraciones
  obligatorias antes de cada reporte, reportes HTML versionados, galería y control de costos.

Las dos usan las mismas herramientas (`agent/tools`) y la misma validación de SQL (`agent/sql_guard.py`).

## 1. Instalación
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # requirements-dev.txt para pruebas
npm install -g @anthropic-ai/claude-code              # solo para el uso con Claude Code
```

## 2. Uso con Claude Code (MCP)
```bash
export DATABASE_URL="postgresql+psycopg2://agente_ventas:CLAVE@host:5432/panacea"
claude        # aprobá el servidor "ventas-db" la primera vez; /mcp para verificar
```
- Si usás un venv, en `.mcp.json` cambiá `"command": "python"` por `.venv/bin/python`.
- No guardes la clave en `.mcp.json`: se toma de la variable de entorno.
- Usuario de solo lectura recomendado: `sql/usuario_solo_lectura.sql` (incluye índices opcionales).
- `TABLAS_PERMITIDAS=public.panacea_sales_v2,...` limita las tablas que puede leer `consultar`.
- Reporte mensual automático:
  `claude -p "Generá el reporte mensual del último mes cerrado en reportes/" --allowedTools "mcp__ventas-db" "Write"`

| Herramienta | Para qué |
|---|---|
| perfil_datos | Diagnóstico: rango de fechas, nulos, cliente genérico, codificación de días |
| describir_tabla | Columnas y ejemplos |
| resumen_ventas | KPIs agrupados por mes, semana, día, hora, categoría, producto, lugar, cliente |
| comparar_periodos | Variación entre dos rangos de fechas, total o por dimensión |
| clientes_inactivos | Clientes frecuentes que dejaron de comprar |
| productos_asociados | Canasta: soporte, confianza y lift entre productos |
| proyectar_ventas | Proyección mensual con tendencia, estacionalidad y rango |
| consultar | SQL libre de solo lectura, validado con sqlglot |

## 3. App web

### Cómo funciona
- `api/index.py` (FastAPI) es el backend; Vercel lo sirve como función Python en `/api/*`.
- `agent/loop.py` corre cada turno contra la Messages API (Claude Opus 5.5) en streaming (SSE).
  Guarda cada paso en Postgres, así un turno cortado se retoma sin repetir consultas.
- Antes de un reporte, el agente llama a `solicitar_aclaraciones`. El turno se pausa hasta que el
  usuario aprueba o ajusta el brief (`POST /api/clarify`). `generar_artifact` exige el brief aprobado.
- Los reportes se arman sobre `agent/plantillas/reporte.html`, se guardan versionados con las
  consultas que los alimentaron y se sirven aislados (CSP + `sandbox`) en `/api/artifacts/{id}/html`.
- Cada consulta SQL (ejecutada o rechazada) va a `app.auditoria_sql`, y cada llamada al modelo a
  `app.uso_tokens` con su costo estimado (`agent/costos.py`).
- Límites del uso:
  - presupuesto de tokens por turno, configurado por perfil;
  - tope de costo mensual por usuario: al superarlo, el chat responde 429;
  - tablero de uso para administradores en `GET /api/admin/uso`.

### Variables de entorno
| Variable | Qué es |
|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Anthropic |
| `AUTH_SECRET` | Secreto de Auth.js (≥ 32 caracteres); el backend valida con él la sesión (JWT HS256) |
| `DB_URL_APP` | Base del esquema `app`, con el rol `agente_app` |
| `DB_URL_<PERFIL>` | Una por perfil (ej. `DB_URL_VENTAS`), con el rol de solo lectura de ese perfil |

En Vercel/Neon usá el host con `-pooler` en las URL de la app. La conexión directa
(`POSTGRES_URL_NON_POOLING`, rol dueño) queda solo para migraciones.

### Base de datos
1. Roles por perfil y de la app: `sql/roles_perfiles.sql` (pendiente, tarea 2.4).
2. Esquema de la app: `psql "$POSTGRES_URL_NON_POOLING" -f sql/app/001_esquema.sql`. El script es
   idempotente y da permisos a `agente_app` si ese rol ya existe.

### Perfiles y usuarios
Un perfil se agrega sin tocar código:
1. `config/perfiles/<id>.yaml` con el modelo, el esfuerzo, el prompt, las tablas (y, si hace falta, las
   columnas), las herramientas, las reglas y los límites. Usá `config/perfiles/ventas.yaml` de modelo.
   Las herramientas de reportes (`generar_artifact`, `editar_artifact`) requieren `solicitar_aclaraciones`.
2. `prompts/<id>.md` con las instrucciones, y diccionarios de datos en `prompts/diccionarios/`.
3. Un rol de Postgres de solo lectura con `GRANT SELECT` sobre esas tablas, y su `DB_URL_<ID>`.

Un YAML inválido frena el arranque con un error que nombra el archivo y el campo.

Usuarios: `config/usuarios.yaml`. Un email que no figura no entra. Cada usuario lleva sus perfiles,
`admin: true` (ve todo y el tablero de uso) y `tope_mensual_usd` (si no lo tiene, rige el tope general
del archivo).

### Correr local
```bash
pip install uvicorn && uvicorn api.index:app --reload
```

### Despliegue (pendiente, grupo 4)
Un proyecto de Vercel con Next.js en la raíz y `api/index.py` como función Python:
- `vercel.json` reescribe `/api/*` (salvo `/api/auth/*`) al backend y da `maxDuration` alto a
  `/api/chat` y `/api/clarify`.
- Las variables de entorno de arriba se cargan en el proyecto.
- Auth.js se configura para firmar la sesión como JWT HS256 (ver `design.md` del cambio).

## 4. Pruebas y evaluación
```bash
pip install -r requirements-dev.txt
pytest   # test_equivalencia y test_evals leen la base de ventas con DATABASE_URL (solo lectura);
         # los tests del almacén Postgres levantan un postgres:16 en Docker
         # (o usan TEST_APP_DB_URL; SIN_DOCKER=1 los omite)
```

Set de evaluación con 20 preguntas reales (`evals/preguntas.yaml`). Cada pregunta trae el SQL que
calcula su respuesta:
```bash
python evals/evaluar.py verificar            # recalcula las respuestas esperadas (sin costo)
python evals/evaluar.py correr               # corre el agente con la API real y califica
                                             # (≈ US$ 0,10–0,30 por pregunta)
```
Correlo antes y después de cambiar el prompt, el modelo o el esfuerzo de un perfil.

## Ejemplos de pedidos
- "Hacé el perfil de los datos y contame qué ves."
- "Reporte de ventas 2026 vs 2025 por lugar de venta, con proyección a fin de año."
- "¿Qué productos se compran juntos? Sugerí 3 combos."
- "Listá los clientes que dejaron de comprar y armá una estrategia de recuperación."
- "Agregá al reporte un mapa de calor de día × hora." (crea una versión nueva del mismo reporte)

## Base de pruebas (opcional, NUNCA en producción)
```bash
DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/pruebas python data/crear_demo_postgres.py
```
