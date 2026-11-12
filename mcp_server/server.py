"""
Servidor MCP de análisis de ventas sobre PostgreSQL (tabla public.panacea_sales_v2).

Es un adaptador: las herramientas viven en el paquete `agent.tools`, compartido con el backend web.

Variables de entorno:
  DATABASE_URL       postgresql+psycopg2://usuario:clave@host:5432/base   (obligatoria)
  SALES_TABLE        tabla de ventas (por defecto public.panacea_sales_v2)
  MAX_FILAS          máximo de filas devueltas por consulta (por defecto 500)
  TIMEOUT_SEG        tiempo máximo por consulta (por defecto 60)
  TABLAS_PERMITIDAS  opcional: lista separada por comas de esquema.tabla que puede leer `consultar`.
                     Sin definir, `consultar` no restringe tablas (la base aplica los permisos del rol).

Seguridad: cada consulta corre en una transacción READ ONLY con statement_timeout, y `consultar`
valida el SQL con sqlglot. Igual se recomienda conectar con un usuario de solo lectura
(ver sql/usuario_solo_lectura.sql).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:  # SDK mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # SDK mcp 1.x
    from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine

from agent.contexto import ContextoPerfil, normalizar_url
from agent.sql_guard import validar_sql
from agent.tools.base import ejecutar
from agent.tools.registro import HERRAMIENTAS, vincular


def crear_contexto() -> ContextoPerfil:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Falta la variable de entorno DATABASE_URL.")
    tablas_env = os.environ.get("TABLAS_PERMITIDAS", "").strip()
    try:
        ctx = ContextoPerfil(
            engine=create_engine(normalizar_url(url), pool_pre_ping=True, pool_size=2, max_overflow=2),
            tabla=os.environ.get("SALES_TABLE", "public.panacea_sales_v2"),
            tablas_permitidas=({t.strip(): None for t in tablas_env.split(",") if t.strip()}
                               if tablas_env else None),
            max_filas=int(os.environ.get("MAX_FILAS", "500")),
            timeout_sql_seg=int(os.environ.get("TIMEOUT_SEG", "60")),
        )
    except ValueError as e:
        raise SystemExit(f"SALES_TABLE o TABLAS_PERMITIDAS mal formadas: {e}")
    return ctx


contexto = crear_contexto()
mcp = FastMCP("ventas-db")
for _nombre, _fn in HERRAMIENTAS.items():
    globals()[_nombre] = vincular(_fn, contexto)
    mcp.add_tool(globals()[_nombre])

# Compatibilidad con los scripts que importan este módulo (trabajo/scripts, plan_ventas/scripts):
# las herramientas quedan como funciones del módulo (arriba) y se mantienen estos nombres.
TABLA = contexto.tabla
ESQUEMA, NOMBRE_TABLA = contexto.esquema, contexto.nombre_tabla
MAX_FILAS, TIMEOUT_SEG = contexto.max_filas, contexto.timeout_sql_seg
engine = contexto.engine


def _ejecutar(sql: str, params: dict | None = None, max_filas: int = MAX_FILAS) -> dict:
    return ejecutar(contexto, sql, params, max_filas)


def _validar_sql(sql: str) -> str:
    return validar_sql(sql, contexto.tablas_permitidas, contexto.esquema_columnas)


if __name__ == "__main__":
    mcp.run()  # stdio, para Claude Code
