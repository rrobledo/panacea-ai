"""Herramientas genéricas, válidas para cualquier perfil."""

from agent.contexto import ContextoPerfil
from agent.sql_guard import SQLNoPermitido, validar_sql
from agent.tools.base import a_json, ejecutar


def describir_tabla(ctx: ContextoPerfil) -> str:
    """Columnas y tipos de la tabla de ventas, filas estimadas y 5 filas de ejemplo."""
    cols = ejecutar(ctx,
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = :e AND table_name = :t ORDER BY ordinal_position",
        {"e": ctx.esquema, "t": ctx.nombre_tabla})
    est = ejecutar(ctx,
        "SELECT reltuples::bigint FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = :e AND c.relname = :t", {"e": ctx.esquema, "t": ctx.nombre_tabla})
    ejemplo = ejecutar(ctx, f"SELECT * FROM {ctx.tabla} ORDER BY operation_date DESC LIMIT 5")
    return a_json({"tabla": ctx.tabla, "filas_estimadas": est["filas"][0][0] if est["filas"] else None,
                  "columnas": cols["filas"], "ejemplo": ejemplo})


def consultar(ctx: ContextoPerfil, sql: str) -> str:
    """
    Consulta SQL libre de SOLO LECTURA (SELECT/WITH) sobre PostgreSQL, para análisis que las otras
    herramientas no cubren. Agregá en SQL (GROUP BY) en lugar de traer filas crudas y filtrá siempre
    por operation_date para aprovechar el índice. Devuelve hasta MAX_FILAS filas.
    """
    try:
        validado = validar_sql(sql, ctx.tablas_permitidas, ctx.esquema_columnas)
    except SQLNoPermitido as e:
        ctx.auditar(sql=sql, parametros=None, duracion_ms=0, filas=None, error=f"rechazada: {e}")
        return a_json({"error": str(e)})
    try:
        return a_json(ejecutar(ctx, validado))
    except Exception as e:
        return a_json({"error": str(e)})
