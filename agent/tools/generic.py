"""Herramientas genéricas, válidas para cualquier perfil."""

from agent.contexto import ContextoPerfil, validar_nombre_tabla
from agent.sql_guard import SQLNoPermitido, validar_sql
from agent.tools.base import a_json, ejecutar


def _resolver_tabla(ctx: ContextoPerfil, tabla: str | None) -> str:
    """Nombre esquema.tabla validado contra el perfil. Lanza ValueError con un mensaje para el modelo."""
    if not tabla:
        return ctx.tabla
    nombre = tabla.strip().lower()
    if "." not in nombre:
        nombre = f"{ctx.esquema}.{nombre}"
    nombre = validar_nombre_tabla(nombre)
    if ctx.tablas_permitidas is not None and nombre not in ctx.tablas_permitidas:
        raise ValueError(f"La tabla {nombre} no está disponible en este perfil. "
                         f"Tablas disponibles: {', '.join(sorted(ctx.tablas_permitidas))}.")
    return nombre


def describir_tabla(ctx: ContextoPerfil, tabla: str | None = None) -> str:
    """
    Columnas y tipos de una tabla, filas estimadas y 5 filas de ejemplo (las más recientes si la
    tabla tiene columna de fecha). Sin `tabla`, describe la tabla principal del perfil.
    `tabla` admite el nombre con o sin esquema (ej. compras_pago o public.compras_pago).
    """
    try:
        nombre = _resolver_tabla(ctx, tabla)
    except ValueError as e:
        return a_json({"error": str(e)})
    esquema, nombre_tabla = nombre.split(".")
    cols = ejecutar(ctx,
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = :e AND table_name = :t ORDER BY ordinal_position",
        {"e": esquema, "t": nombre_tabla})
    acotadas = (ctx.tablas_permitidas or {}).get(nombre)
    if acotadas is not None:
        cols["filas"] = [f for f in cols["filas"] if f[0].lower() in acotadas]
        cols["total_filas"] = len(cols["filas"])
    if not cols["filas"]:
        return a_json({"error": f"La tabla {nombre} no existe o este perfil no tiene permiso para verla."})
    est = ejecutar(ctx,
        "SELECT reltuples::bigint FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = :e AND c.relname = :t", {"e": esquema, "t": nombre_tabla})
    columnas = [f[0] for f in cols["filas"]]
    seleccion = "*" if acotadas is None else ", ".join(f'"{c}"' for c in columnas)
    columna_fecha = (ctx.columnas_fecha or {}).get(nombre)
    orden = f' ORDER BY "{columna_fecha}" DESC' if columna_fecha in columnas else ""
    ejemplo = ejecutar(ctx, f"SELECT {seleccion} FROM {nombre}{orden} LIMIT 5")
    return a_json({"tabla": nombre, "filas_estimadas": est["filas"][0][0] if est["filas"] else None,
                  "columnas": cols["filas"], "ejemplo": ejemplo})


def consultar(ctx: ContextoPerfil, sql: str) -> str:
    """
    Consulta SQL libre de SOLO LECTURA (SELECT/WITH) sobre PostgreSQL, para análisis que las otras
    herramientas no cubren. Agregá en SQL (GROUP BY) en lugar de traer filas crudas y filtrá siempre
    por la columna de fecha de cada tabla (figura en tus instrucciones) para aprovechar el índice.
    Devuelve hasta MAX_FILAS filas.
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
