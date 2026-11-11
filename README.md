# Agente de ventas Panacea (Claude Code + MCP + PostgreSQL)

## 1. Instalación
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code              # si todavía no tenés Claude Code
```
Si usás un venv, en `.mcp.json` cambiá `"command": "python"` por la ruta del python del venv
(ej. `.venv/bin/python`), para que Claude Code lance el servidor con las dependencias correctas.

## 2. Usuario de solo lectura (recomendado)
Ejecutá `sql/usuario_solo_lectura.sql` como administrador. Tiene índices opcionales para acelerar
los análisis de clientes y de canasta.

## 3. Conexión
```bash
export DATABASE_URL="postgresql+psycopg2://agente_ventas:CLAVE@host:5432/panacea"
```
No guardes la clave en `.mcp.json`. El archivo toma la variable de entorno.

## 4. Usarlo
```bash
cd agente-ventas
claude        # aprobá el servidor "ventas-db" la primera vez
/mcp          # dentro de Claude Code: verificá que esté conectado
```

## Herramientas del servidor
| Herramienta | Para qué |
|---|---|
| perfil_datos | Diagnóstico: rango de fechas, nulos, cliente genérico, codificación de días |
| describir_tabla | Columnas y ejemplos |
| resumen_ventas | KPIs agrupados por mes, semana, día, hora, categoría, producto, lugar, cliente |
| comparar_periodos | Variación entre dos rangos de fechas, total o por dimensión |
| clientes_inactivos | Clientes frecuentes que dejaron de comprar |
| productos_asociados | Canasta: soporte, confianza y lift entre productos |
| proyectar_ventas | Proyección mensual con tendencia, estacionalidad y rango |
| consultar | SQL libre de solo lectura |

## Ejemplos de pedidos
- "Hacé el perfil de los datos y contame qué ves."
- "Reporte de ventas 2026 vs 2025 por lugar de venta, con proyección a fin de año."
- "¿Qué productos se compran juntos? Sugerí 3 combos."
- "Listá los clientes que dejaron de comprar y armá una estrategia de recuperación."
- "Agregá al reporte un mapa de calor de día × hora." (itera sobre el mismo HTML)

## Reporte automático mensual
```bash
claude -p "Generá el reporte mensual del último mes cerrado en reportes/" --allowedTools "mcp__ventas-db" "Write"
```

## Base de pruebas (opcional, NUNCA en producción)
```bash
DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/pruebas python data/crear_demo_postgres.py
```
