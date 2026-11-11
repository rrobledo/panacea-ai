"""
Servidor MCP de análisis de ventas sobre PostgreSQL (tabla public.panacea_sales_v2).

Variables de entorno:
  DATABASE_URL   postgresql+psycopg2://usuario:clave@host:5432/base   (obligatoria)
  SALES_TABLE    tabla de ventas (por defecto public.panacea_sales_v2)
  MAX_FILAS      máximo de filas devueltas por consulta (por defecto 500)
  TIMEOUT_SEG    tiempo máximo por consulta (por defecto 60)

Seguridad: cada consulta corre en una transacción READ ONLY con statement_timeout.
Igual se recomienda conectar con un usuario de solo lectura (ver sql/usuario_solo_lectura.sql).
"""

import json
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

try:  # SDK mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # SDK mcp 1.x
    from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Falta la variable de entorno DATABASE_URL.")
# Neon/Vercel/Heroku entregan "postgres://", que SQLAlchemy 2 no reconoce
DATABASE_URL = re.sub(r"^postgres(ql)?://", "postgresql+psycopg2://", DATABASE_URL)
TABLA = os.environ.get("SALES_TABLE", "public.panacea_sales_v2")
if not re.fullmatch(r"[a-zA-Z_][\w]*\.[a-zA-Z_][\w]*", TABLA):
    raise SystemExit("SALES_TABLE debe tener el formato esquema.tabla")
ESQUEMA, NOMBRE_TABLA = TABLA.split(".")
MAX_FILAS = int(os.environ.get("MAX_FILAS", "500"))
TIMEOUT_SEG = int(os.environ.get("TIMEOUT_SEG", "60"))

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=2, max_overflow=2)
mcp = FastMCP("ventas-db")

# Dimensiones permitidas para agrupar (evita inyectar SQL en GROUP BY)
DIMENSIONES = {
    "mes": "to_char(date_trunc('month', operation_date), 'YYYY-MM')",
    "semana": "to_char(date_trunc('week', operation_date), 'YYYY-MM-DD')",
    "dia": "operation_date::text",
    "anio": "operation_year::text",
    "dia_semana": "day_of_week::text || ' ' || day_of_week_text",
    "hora": "lpad(operation_hour::text, 2, '0')",
    "semana_del_mes": "week_of_month::text",
    "categoria": "category",
    "producto": "product_id::text || ' - ' || product",
    "lugar_venta": "lugar_venta",
    "cliente": "customer_id::text || ' - ' || customer",
}

METRICAS = f"""
    ROUND(SUM(subtotal)::numeric, 2)                                   AS ventas,
    ROUND(SUM(count)::numeric, 2)                                      AS unidades,
    COUNT(DISTINCT document_id)                                        AS tickets,
    ROUND((SUM(subtotal) / NULLIF(COUNT(DISTINCT document_id), 0))::numeric, 2) AS ticket_promedio,
    ROUND((SUM(count) / NULLIF(COUNT(DISTINCT document_id), 0))::numeric, 2)    AS unidades_por_ticket,
    COUNT(DISTINCT customer_id)                                        AS clientes
"""

PROHIBIDAS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|copy|vacuum|"
    r"lock|listen|notify|set|reset|do|call|execute|prepare|pg_sleep|pg_terminate_backend|"
    r"pg_cancel_backend|dblink|lo_import|lo_export|pg_read_file|pg_ls_dir)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------- utilidades
def _ser(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _fecha(valor: str | None, defecto: date) -> date:
    return date.fromisoformat(valor) if valor else defecto


def _validar_sql(sql: str) -> str:
    limpio = re.sub(r"--[^\n]*", "", sql).strip().rstrip(";").strip()
    if ";" in limpio:
        raise ValueError("Solo se permite una sentencia por consulta.")
    if not re.match(r"^(select|with)\b", limpio, re.IGNORECASE):
        raise ValueError("Solo se permiten consultas SELECT o WITH.")
    if PROHIBIDAS.search(limpio):
        raise ValueError("La consulta contiene operaciones no permitidas (solo lectura).")
    return limpio


def _ejecutar(sql: str, params: dict | None = None, max_filas: int = MAX_FILAS) -> dict:
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text(f"SET LOCAL statement_timeout = {TIMEOUT_SEG * 1000}"))
            res = conn.execute(text(sql), params or {})
            columnas = list(res.keys())
            filas = res.fetchmany(max_filas + 1)
            conn.rollback()
    truncado = len(filas) > max_filas
    filas = filas[:max_filas]
    return {"columnas": columnas, "filas": [[_ser(v) for v in f] for f in filas],
            "total_filas": len(filas), "truncado": truncado}


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=_ser)


def _filtros(categoria=None, lugar_venta=None, product_id=None, excluir_clientes=None):
    cond, params = [], {}
    if categoria:
        cond.append("category = :categoria"); params["categoria"] = categoria
    if lugar_venta:
        cond.append("lugar_venta = :lugar_venta"); params["lugar_venta"] = lugar_venta
    if product_id is not None:
        cond.append("product_id = :product_id"); params["product_id"] = int(product_id)
    if excluir_clientes:
        cond.append("customer_id <> ALL(:excluir)"); params["excluir"] = [int(c) for c in excluir_clientes]
    return ("".join(f" AND {c}" for c in cond)), params


# ---------------------------------------------------------------- herramientas
@mcp.tool()
def describir_tabla() -> str:
    """Columnas y tipos de la tabla de ventas, filas estimadas y 5 filas de ejemplo."""
    cols = _ejecutar(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = :e AND table_name = :t ORDER BY ordinal_position",
        {"e": ESQUEMA, "t": NOMBRE_TABLA})
    est = _ejecutar(
        "SELECT reltuples::bigint FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = :e AND c.relname = :t", {"e": ESQUEMA, "t": NOMBRE_TABLA})
    ejemplo = _ejecutar(f"SELECT * FROM {TABLA} ORDER BY operation_date DESC LIMIT 5")
    return _json({"tabla": TABLA, "filas_estimadas": est["filas"][0][0] if est["filas"] else None,
                  "columnas": cols["filas"], "ejemplo": ejemplo})


@mcp.tool()
def perfil_datos() -> str:
    """
    Diagnóstico inicial de la tabla: rango de fechas, cantidad de tickets, productos, clientes,
    categorías y lugares de venta; nulos y valores negativos (devoluciones); clientes con mayor
    participación (para detectar "consumidor final" genérico); codificación de day_of_week.
    Usala al comenzar una sesión de análisis.
    """
    general = _ejecutar(f"""
        SELECT MIN(operation_date) AS desde, MAX(operation_date) AS hasta,
               COUNT(*) AS lineas, COUNT(DISTINCT document_id) AS tickets,
               COUNT(DISTINCT product_id) AS productos, COUNT(DISTINCT customer_id) AS clientes,
               COUNT(DISTINCT category_id) AS categorias, COUNT(DISTINCT lugar_venta_id) AS lugares_venta,
               ROUND(SUM(subtotal)::numeric, 2) AS ventas_totales,
               SUM(CASE WHEN subtotal < 0 OR count < 0 THEN 1 ELSE 0 END) AS lineas_negativas,
               SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS sin_cliente,
               SUM(CASE WHEN product_id IS NULL THEN 1 ELSE 0 END) AS sin_producto,
               SUM(CASE WHEN subtotal IS NULL THEN 1 ELSE 0 END) AS sin_subtotal,
               COUNT(DISTINCT ref_id) AS ref_ids_distintos
        FROM {TABLA}""")
    top_clientes = _ejecutar(f"""
        SELECT customer_id, customer, COUNT(DISTINCT document_id) AS tickets,
               ROUND((100.0 * SUM(subtotal) / SUM(SUM(subtotal)) OVER ())::numeric, 2) AS pct_ventas
        FROM {TABLA} GROUP BY 1, 2 ORDER BY tickets DESC LIMIT 5""")
    dias = _ejecutar(f"SELECT DISTINCT day_of_week, day_of_week_text FROM {TABLA} ORDER BY 1")
    lugares = _ejecutar(f"""
        SELECT lugar_venta_id, lugar_venta, MIN(operation_date) AS primera_venta, MAX(operation_date) AS ultima_venta
        FROM {TABLA} GROUP BY 1, 2 ORDER BY 1""")
    return _json({"general": general, "clientes_mas_frecuentes": top_clientes,
                  "codificacion_dia_semana": dias["filas"], "lugares_venta": lugares})


@mcp.tool()
def resumen_ventas(desde: str | None = None, hasta: str | None = None,
                   agrupar_por: list[str] | None = None, categoria: str | None = None,
                   lugar_venta: str | None = None, product_id: int | None = None,
                   excluir_clientes: list[int] | None = None,
                   ordenar_por: str = "ventas", limite: int = 100) -> str:
    """
    KPIs de ventas (ventas, unidades, tickets, ticket promedio, unidades por ticket, clientes)
    agrupados por una o más dimensiones. Fechas en formato AAAA-MM-DD (por defecto, últimos 12 meses).
    agrupar_por admite: mes, semana, dia, anio, dia_semana, hora, semana_del_mes, categoria,
    producto, lugar_venta, cliente. Sin agrupar devuelve los totales del período.
    Incluye la participación % de cada grupo sobre el total.
    """
    hoy = date.today()
    d, h = _fecha(desde, hoy - timedelta(days=365)), _fecha(hasta, hoy)
    grupos = agrupar_por or []
    invalidas = [g for g in grupos if g not in DIMENSIONES]
    if invalidas:
        return _json({"error": f"Dimensiones no válidas: {invalidas}", "validas": list(DIMENSIONES)})
    if ordenar_por not in ("ventas", "unidades", "tickets", "ticket_promedio", "clientes", "grupo"):
        ordenar_por = "ventas"
    extra, params = _filtros(categoria, lugar_venta, product_id, excluir_clientes)
    params.update(d=d, h=h)
    sel = ", ".join(f"{DIMENSIONES[g]} AS {g}" for g in grupos)
    group = f"GROUP BY {', '.join(str(i + 1) for i in range(len(grupos)))}" if grupos else ""
    temporal = bool(grupos) and grupos[0] in ("mes", "semana", "dia", "anio", "dia_semana", "hora", "semana_del_mes")
    orden = "1" if (ordenar_por == "grupo" or temporal) and grupos else f"{ordenar_por} DESC"
    sql = f"""
        SELECT {sel + ',' if sel else ''} {METRICAS},
               ROUND((100.0 * SUM(subtotal) / NULLIF(SUM(SUM(subtotal)) OVER (), 0))::numeric, 2) AS pct_ventas
        FROM {TABLA}
        WHERE operation_date BETWEEN :d AND :h {extra}
        {group} ORDER BY {orden} LIMIT {int(min(limite, MAX_FILAS))}"""
    return _json({"periodo": [d, h], "resultado": _ejecutar(sql, params)})


@mcp.tool()
def comparar_periodos(desde_actual: str, hasta_actual: str, desde_anterior: str, hasta_anterior: str,
                      agrupar_por: str | None = None, excluir_clientes: list[int] | None = None,
                      limite: int = 50) -> str:
    """
    Compara dos períodos (ej. este mes vs mismo mes del año pasado) con variación absoluta y %.
    agrupar_por opcional: categoria, producto, lugar_venta, cliente, dia_semana, hora.
    Útil para detectar qué creció o cayó y explicar el porqué de un cambio total.
    """
    if agrupar_por and agrupar_por not in DIMENSIONES:
        return _json({"error": "Dimensión no válida", "validas": list(DIMENSIONES)})
    dim = DIMENSIONES[agrupar_por] if agrupar_por else "'total'"
    extra, params = _filtros(excluir_clientes=excluir_clientes)
    params.update(da=date.fromisoformat(desde_actual), ha=date.fromisoformat(hasta_actual),
                  dp=date.fromisoformat(desde_anterior), hp=date.fromisoformat(hasta_anterior))
    sql = f"""
        WITH base AS (
            SELECT {dim} AS grupo,
                   CASE WHEN operation_date BETWEEN :da AND :ha THEN 'actual' ELSE 'anterior' END AS periodo,
                   subtotal, count, document_id
            FROM {TABLA}
            WHERE (operation_date BETWEEN :da AND :ha OR operation_date BETWEEN :dp AND :hp) {extra}
        ), agg AS (
            SELECT grupo,
                   SUM(subtotal) FILTER (WHERE periodo = 'actual')   AS ventas_actual,
                   SUM(subtotal) FILTER (WHERE periodo = 'anterior') AS ventas_anterior,
                   SUM(count) FILTER (WHERE periodo = 'actual')      AS unidades_actual,
                   SUM(count) FILTER (WHERE periodo = 'anterior')    AS unidades_anterior,
                   COUNT(DISTINCT document_id) FILTER (WHERE periodo = 'actual')   AS tickets_actual,
                   COUNT(DISTINCT document_id) FILTER (WHERE periodo = 'anterior') AS tickets_anterior
            FROM base GROUP BY grupo
        )
        SELECT grupo,
               ROUND(COALESCE(ventas_actual, 0)::numeric, 2) AS ventas_actual,
               ROUND(COALESCE(ventas_anterior, 0)::numeric, 2) AS ventas_anterior,
               ROUND((COALESCE(ventas_actual, 0) - COALESCE(ventas_anterior, 0))::numeric, 2) AS variacion,
               ROUND((100.0 * (ventas_actual - ventas_anterior) / NULLIF(ventas_anterior, 0))::numeric, 2) AS variacion_pct,
               unidades_actual, unidades_anterior, tickets_actual, tickets_anterior
        FROM agg ORDER BY ABS(COALESCE(ventas_actual, 0) - COALESCE(ventas_anterior, 0)) DESC
        LIMIT {int(min(limite, MAX_FILAS))}"""
    return _json(_ejecutar(sql, params))


@mcp.tool()
def clientes_inactivos(dias_sin_compra: int = 90, min_tickets: int = 3,
                       meses_historia: int = 18, excluir_clientes: list[int] | None = None,
                       limite: int = 100) -> str:
    """
    Clientes que compraban con regularidad y dejaron de comprar (riesgo de fuga).
    Devuelve última compra, días sin comprar, frecuencia habitual, gasto histórico y su categoría
    favorita. Ordenados por valor histórico. Excluí clientes genéricos (ej. "consumidor final").
    """
    extra, params = _filtros(excluir_clientes=excluir_clientes)
    params.update(dias=int(dias_sin_compra), min_t=int(min_tickets), meses=int(meses_historia))
    sql = f"""
        WITH ref AS (SELECT MAX(operation_date) AS hoy,
                            (MAX(operation_date) - make_interval(months => :meses))::date AS desde FROM {TABLA}),
        c AS (
            SELECT customer_id, MAX(customer) AS customer,
                   MIN(operation_date) AS primera_compra, MAX(operation_date) AS ultima_compra,
                   COUNT(DISTINCT document_id) AS tickets, SUM(subtotal) AS gasto_total
            FROM {TABLA}
            WHERE operation_date >= (SELECT desde FROM ref) AND customer_id IS NOT NULL {extra}
            GROUP BY customer_id
        ), fav AS (
            SELECT DISTINCT ON (customer_id) customer_id, category
            FROM {TABLA} WHERE operation_date >= (SELECT desde FROM ref) {extra}
            GROUP BY customer_id, category ORDER BY customer_id, SUM(subtotal) DESC
        )
        SELECT c.customer_id, c.customer, c.ultima_compra, (ref.hoy - c.ultima_compra) AS dias_sin_compra,
               c.tickets, ROUND(((c.ultima_compra - c.primera_compra)::numeric / NULLIF(c.tickets - 1, 0)), 1) AS dias_entre_compras,
               ROUND(c.gasto_total::numeric, 2) AS gasto_total,
               ROUND((c.gasto_total / c.tickets)::numeric, 2) AS ticket_promedio, fav.category AS categoria_favorita
        FROM c CROSS JOIN ref LEFT JOIN fav USING (customer_id)
        WHERE c.tickets >= :min_t AND (ref.hoy - c.ultima_compra) >= :dias
        ORDER BY c.gasto_total DESC LIMIT {int(min(limite, MAX_FILAS))}"""
    res = _ejecutar(sql, params)
    return _json({"nota": "Los días se cuentan hasta la última fecha con ventas en la tabla.", "resultado": res})


@mcp.tool()
def productos_asociados(desde: str | None = None, hasta: str | None = None,
                        product_id: int | None = None, min_tickets_juntos: int = 20,
                        limite: int = 30) -> str:
    """
    Análisis de canasta: pares de productos que se compran en el mismo ticket (document_id).
    Devuelve soporte (% de tickets con ambos), confianza (prob. de B dado A) y lift (>1 = asociación real).
    Con product_id muestra qué se lleva junto con ese producto. Ideal para combos, cross-selling
    y ubicación en góndola. Por defecto analiza los últimos 6 meses.
    """
    hoy = date.today()
    params = {"d": _fecha(desde, hoy - timedelta(days=182)), "h": _fecha(hasta, hoy),
              "min": int(min_tickets_juntos)}
    filtro_par = ""
    if product_id is not None:
        filtro_par = "AND (a.product_id = :pid OR b.product_id = :pid)"
        params["pid"] = int(product_id)
    sql = f"""
        WITH t AS (
            SELECT DISTINCT document_id, product_id FROM {TABLA}
            WHERE operation_date BETWEEN :d AND :h AND product_id IS NOT NULL
        ),
        n AS (SELECT COUNT(DISTINCT document_id)::numeric AS total FROM t),
        p AS (SELECT product_id, COUNT(*)::numeric AS c FROM t GROUP BY 1),
        nombres AS (SELECT product_id, MAX(product) AS product FROM {TABLA} GROUP BY 1),
        pares AS (
            SELECT a.product_id AS a, b.product_id AS b, COUNT(*)::numeric AS c
            FROM t a JOIN t b ON a.document_id = b.document_id AND a.product_id < b.product_id
            WHERE TRUE {filtro_par}
            GROUP BY 1, 2 HAVING COUNT(*) >= :min
        )
        SELECT na.product AS producto_a, nb.product AS producto_b, pares.c::int AS tickets_juntos,
               ROUND(100 * pares.c / n.total, 3) AS soporte_pct,
               ROUND(100 * pares.c / pa.c, 2) AS confianza_a_b_pct,
               ROUND(100 * pares.c / pb.c, 2) AS confianza_b_a_pct,
               ROUND(pares.c * n.total / (pa.c * pb.c), 2) AS lift
        FROM pares CROSS JOIN n
        JOIN p pa ON pa.product_id = pares.a JOIN p pb ON pb.product_id = pares.b
        JOIN nombres na ON na.product_id = pares.a JOIN nombres nb ON nb.product_id = pares.b
        ORDER BY lift DESC, tickets_juntos DESC LIMIT {int(min(limite, MAX_FILAS))}"""
    return _json({"periodo": [params["d"], params["h"]], "resultado": _ejecutar(sql, params)})


def _proyectar(filas: list, periodos: int) -> dict:
    y = [float(f[1] or 0) for f in filas]
    n = len(y)
    x = list(range(n))
    mx, my = sum(x) / n, sum(y) / n
    pend = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sum((a - mx) ** 2 for a in x)
    inter = my - pend * mx
    usa_est = n >= 24
    est = [1.0] * 12
    if usa_est:
        for i in range(12):
            r = [y[j] / (inter + pend * j) for j in range(i, n, 12) if (inter + pend * j) > 0]
            if r:
                est[i] = sum(r) / len(r)
    ajustado = [(inter + pend * j) * (est[j % 12] if usa_est else 1) for j in x]
    desvio = (sum((a - b) ** 2 for a, b in zip(y, ajustado)) / max(n - 2, 1)) ** 0.5
    proy = []
    for k in range(1, periodos + 1):
        j = n - 1 + k
        v = (inter + pend * j) * (est[j % 12] if usa_est else 1)
        proy.append({"periodo_futuro": k, "valor": round(v, 2),
                     "rango_bajo": round(max(v - 1.96 * desvio, 0), 2), "rango_alto": round(v + 1.96 * desvio, 2)})
    mape = sum(abs(a - b) / a for a, b in zip(y, ajustado) if a) / n * 100
    return {"tendencia_por_periodo": round(pend, 2), "estacionalidad_aplicada": usa_est,
            "factores_estacionales": [round(e, 3) for e in est] if usa_est else None,
            "error_ajuste_mape_pct": round(mape, 2), "proyeccion": proy}


@mcp.tool()
def proyectar_ventas(metrica: str = "ventas", meses: int = 6, categoria: str | None = None,
                     lugar_venta: str | None = None, product_id: int | None = None,
                     incluir_mes_en_curso: bool = False) -> str:
    """
    Proyección mensual de ventas, unidades o tickets (metrica: ventas | unidades | tickets) para los
    próximos N meses, con tendencia lineal + estacionalidad (si hay >= 24 meses) y rango aproximado del 95%.
    Se puede filtrar por categoria, lugar_venta o product_id. Excluye el mes en curso (incompleto)
    salvo que se pida. Devuelve también el error de ajuste (MAPE) para juzgar la confiabilidad.
    """
    expr = {"ventas": "SUM(subtotal)", "unidades": "SUM(count)", "tickets": "COUNT(DISTINCT document_id)"}
    if metrica not in expr:
        return _json({"error": "metrica debe ser ventas, unidades o tickets"})
    extra, params = _filtros(categoria, lugar_venta, product_id)
    # Excluye el último mes solo si está incompleto (la última venta no es el último día del mes)
    corte = "" if incluir_mes_en_curso else f"""
        AND operation_date < (
            SELECT CASE WHEN MAX(operation_date) = (date_trunc('month', MAX(operation_date))
                                                   + interval '1 month - 1 day')::date
                        THEN MAX(operation_date) + 1
                        ELSE date_trunc('month', MAX(operation_date))::date END
            FROM {TABLA})"""
    sql = f"""
        SELECT to_char(date_trunc('month', operation_date), 'YYYY-MM') AS mes, {expr[metrica]} AS valor
        FROM {TABLA} WHERE TRUE {corte} {extra}
        GROUP BY 1 ORDER BY 1"""
    filas = _ejecutar(sql, params, max_filas=1000)["filas"]
    if len(filas) < 6:
        return _json({"error": "Se necesitan al menos 6 meses de historia para proyectar."})
    ultimo = date.fromisoformat(filas[-1][0] + "-01")
    res = _proyectar(filas, max(1, min(int(meses), 24)))
    for p in res["proyeccion"]:
        m = ultimo.month - 1 + p["periodo_futuro"]
        p["mes"] = f"{ultimo.year + m // 12}-{m % 12 + 1:02d}"
    res["historico"] = [{"mes": f[0], "valor": round(float(f[1] or 0), 2)} for f in filas]
    res["nota"] = "Modelo estadístico simple y orientativo; combinar con criterio comercial."
    return _json(res)


@mcp.tool()
def consultar(sql: str) -> str:
    """
    Consulta SQL libre de SOLO LECTURA (SELECT/WITH) sobre PostgreSQL, para análisis que las otras
    herramientas no cubren. Agregá en SQL (GROUP BY) en lugar de traer filas crudas y filtrá siempre
    por operation_date para aprovechar el índice. Devuelve hasta MAX_FILAS filas.
    """
    try:
        return _json(_ejecutar(_validar_sql(sql)))
    except Exception as e:
        return _json({"error": str(e)})


if __name__ == "__main__":
    mcp.run()  # stdio, para Claude Code
