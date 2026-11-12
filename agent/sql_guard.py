"""
Validación de SQL de solo lectura con sqlglot (dialecto PostgreSQL).

Reglas:
  - exactamente una sentencia, de tipo SELECT / WITH ... SELECT / UNION;
  - sin sentencias de escritura, DDL, bloqueos ni SELECT INTO en ningún nivel (incluidos CTE);
  - sin funciones peligrosas (pg_sleep, dblink, lo_*, lectura de archivos, ...);
  - si hay lista de tablas permitidas, solo esas tablas (los nombres de CTE no cuentan);
  - si una tabla permitida tiene columnas acotadas, solo esas columnas (SELECT * incluido).

Es una barrera de código para dar errores claros al modelo: la garantía final es el rol de
Postgres del perfil, que solo tiene GRANT SELECT sobre sus tablas.
"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import OptimizeError, ParseError, SqlglotError
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope


class SQLNoPermitido(ValueError):
    pass


_RAICES = tuple(getattr(exp, n) for n in ("Select", "SetOperation", "Union", "Subquery") if hasattr(exp, n))

_NODOS_PROHIBIDOS = tuple(getattr(exp, n) for n in (
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "TruncateTable", "Command",
    "Set", "Copy", "Into", "Lock", "Transaction", "Commit", "Rollback", "Grant", "Revoke", "Use",
    "Pragma", "Analyze", "LoadData", "Kill", "Refresh", "Describe",
) if hasattr(exp, n))

_FUNCIONES_PROHIBIDAS = {
    "pg_sleep", "pg_sleep_for", "pg_sleep_until", "pg_terminate_backend", "pg_cancel_backend",
    "pg_reload_conf", "pg_rotate_logfile", "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
    "pg_stat_file", "pg_file_write", "pg_advisory_lock", "pg_advisory_xact_lock",
    "set_config", "dblink", "dblink_exec", "dblink_connect", "query_to_xml", "query_to_json",
    "lo_import", "lo_export", "lo_from_bytea", "lo_put", "lo_unlink", "copy",
    "nextval", "setval", "txid_current",
}
_PREFIJOS_PROHIBIDOS = ("lo_", "dblink", "pg_read", "pg_ls", "pg_file", "pg_advisory")


def _nombre_funcion(f: exp.Func) -> str:
    return (f.name if isinstance(f, exp.Anonymous) else f.sql_name()).lower()


def _nombre_tabla(t: exp.Table) -> str:
    return f"{(t.db or 'public').lower()}.{t.name.lower()}"


def validar_sql(sql: str, tablas_permitidas: dict[str, frozenset[str] | None] | None = None,
                esquema_columnas: dict[str, list[str]] | None = None) -> str:
    """Devuelve el SQL listo para ejecutar o lanza SQLNoPermitido con el motivo."""
    limpio = sql.strip().rstrip(";").strip()
    try:
        sentencias = [s for s in sqlglot.parse(limpio, read="postgres") if s is not None]
    except ParseError as e:
        raise SQLNoPermitido(f"No se pudo interpretar la consulta: {str(e).splitlines()[0]}") from None
    if len(sentencias) != 1:
        raise SQLNoPermitido("Solo se permite una sentencia por consulta.")
    raiz = sentencias[0]
    if not isinstance(raiz, _RAICES):
        raise SQLNoPermitido("Solo se permiten consultas SELECT o WITH.")

    for nodo in raiz.walk():
        if isinstance(nodo, _NODOS_PROHIBIDOS):
            raise SQLNoPermitido(
                f"La consulta contiene operaciones no permitidas ({type(nodo).__name__}); solo lectura.")

    for f in raiz.find_all(exp.Func):
        nombre = _nombre_funcion(f)
        if nombre in _FUNCIONES_PROHIBIDAS or nombre.startswith(_PREFIJOS_PROHIBIDOS):
            raise SQLNoPermitido(f"La función {nombre} no está permitida.")

    ctes = {c.alias_or_name.lower() for c in raiz.find_all(exp.CTE)}
    tablas = set()
    for t in raiz.find_all(exp.Table):
        if not isinstance(t.this, exp.Identifier):  # función en FROM (generate_series, ...)
            continue
        if t.catalog:
            raise SQLNoPermitido("No se permiten referencias a otras bases de datos.")
        if not t.db and t.name.lower() in ctes:
            continue
        tablas.add(_nombre_tabla(t))

    if tablas_permitidas is None:
        return limpio

    no_permitidas = sorted(tablas - set(tablas_permitidas))
    if no_permitidas:
        raise SQLNoPermitido(
            f"Tablas no permitidas para este perfil: {', '.join(no_permitidas)}. "
            f"Permitidas: {', '.join(sorted(tablas_permitidas))}.")

    acotadas = {t: cols for t, cols in tablas_permitidas.items() if cols is not None and t in tablas}
    if acotadas:
        _validar_columnas(raiz, tablas, acotadas, esquema_columnas)
    return limpio


def _validar_columnas(raiz, tablas, acotadas, esquema_columnas):
    faltan = sorted(t for t in tablas if not esquema_columnas or t not in esquema_columnas)
    if faltan:
        raise ValueError(f"Falta el esquema de columnas de {', '.join(faltan)} para validar columnas.")
    esquema: dict = {}
    for t in tablas:
        db, nombre = t.split(".")
        esquema.setdefault(db, {})[nombre] = {c.lower(): "text" for c in esquema_columnas[t]}
    try:
        calificado = qualify(raiz.copy(), schema=esquema, db="public", dialect="postgres",
                             validate_qualify_columns=True, expand_stars=True)
    except (OptimizeError, SqlglotError) as e:
        raise SQLNoPermitido(f"Columna o referencia no válida: {e}") from None

    prohibidas = set()
    for scope in traverse_scope(calificado):
        for col in scope.columns:
            fuente = scope.sources.get(col.table)
            if isinstance(fuente, exp.Table):
                t = _nombre_tabla(fuente)
                if t in acotadas and col.name.lower() not in acotadas[t]:
                    prohibidas.add(f"{t}.{col.name.lower()}")
    if prohibidas:
        raise SQLNoPermitido(f"Columnas no permitidas para este perfil: {', '.join(sorted(prohibidas))}.")
