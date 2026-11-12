"""Utilidades comunes: serialización, fechas y ejecución de solo lectura acotada."""

import json
import time
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text

from agent.contexto import ContextoPerfil


def ser(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def fecha(valor: str | None, defecto: date) -> date:
    return date.fromisoformat(valor) if valor else defecto


def a_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=ser)


def _ms(inicio: float) -> int:
    return int((time.monotonic() - inicio) * 1000)


def _primera_linea(e: Exception) -> str:
    """Mensaje del error de base sin el SQL ni datos de conexión que agrega SQLAlchemy."""
    orig = getattr(e, "orig", None)
    lineas = str(orig if orig is not None else e).strip().splitlines()
    return (lineas[0] if lineas else type(e).__name__)[:500]


def ejecutar(ctx: ContextoPerfil, sql: str, params: dict | None = None, max_filas: int | None = None) -> dict:
    """Ejecuta en una transacción READ ONLY con statement_timeout y devuelve hasta max_filas filas."""
    max_filas = ctx.max_filas if max_filas is None else max_filas
    inicio = time.monotonic()
    try:
        with ctx.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text(f"SET LOCAL statement_timeout = {int(ctx.timeout_sql_seg) * 1000}"))
                res = conn.execute(text(sql), params or {})
                columnas = list(res.keys())
                filas = res.fetchmany(max_filas + 1)
                conn.rollback()
    except Exception as e:
        ctx.auditar(sql=sql, parametros=params, duracion_ms=_ms(inicio), filas=None, error=_primera_linea(e))
        raise
    ctx.auditar(sql=sql, parametros=params, duracion_ms=_ms(inicio), filas=min(len(filas), max_filas), error=None)
    truncado = len(filas) > max_filas
    filas = filas[:max_filas]
    return {"columnas": columnas, "filas": [[ser(v) for v in f] for f in filas],
            "total_filas": len(filas), "truncado": truncado}
