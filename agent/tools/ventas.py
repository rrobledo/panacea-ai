"""Herramientas de análisis de ventas sobre una tabla con el esquema de panacea_sales_v2."""

from datetime import date, timedelta

from agent.contexto import ContextoPerfil
from agent.tools.base import a_json, ejecutar, fecha


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


def perfil_datos(ctx: ContextoPerfil) -> str:
    """
    Diagnóstico inicial de la tabla: rango de fechas, cantidad de tickets, productos, clientes,
    categorías y lugares de venta; nulos y valores negativos (devoluciones); clientes con mayor
    participación (para detectar "consumidor final" genérico); codificación de day_of_week.
    Usala al comenzar una sesión de análisis.
    """
    general = ejecutar(ctx, f"""
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
        FROM {ctx.tabla}""")
    top_clientes = ejecutar(ctx, f"""
        SELECT customer_id, customer, COUNT(DISTINCT document_id) AS tickets,
               ROUND((100.0 * SUM(subtotal) / SUM(SUM(subtotal)) OVER ())::numeric, 2) AS pct_ventas
        FROM {ctx.tabla} GROUP BY 1, 2 ORDER BY tickets DESC LIMIT 5""")
    dias = ejecutar(ctx, f"SELECT DISTINCT day_of_week, day_of_week_text FROM {ctx.tabla} ORDER BY 1")
    lugares = ejecutar(ctx, f"""
        SELECT lugar_venta_id, lugar_venta, MIN(operation_date) AS primera_venta, MAX(operation_date) AS ultima_venta
        FROM {ctx.tabla} GROUP BY 1, 2 ORDER BY 1""")
    return a_json({"general": general, "clientes_mas_frecuentes": top_clientes,
                  "codificacion_dia_semana": dias["filas"], "lugares_venta": lugares})


def resumen_ventas(ctx: ContextoPerfil, desde: str | None = None, hasta: str | None = None,
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
    d, h = fecha(desde, hoy - timedelta(days=365)), fecha(hasta, hoy)
    grupos = agrupar_por or []
    invalidas = [g for g in grupos if g not in DIMENSIONES]
    if invalidas:
        return a_json({"error": f"Dimensiones no válidas: {invalidas}", "validas": list(DIMENSIONES)})
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
        FROM {ctx.tabla}
        WHERE operation_date BETWEEN :d AND :h {extra}
        {group} ORDER BY {orden} LIMIT {int(min(limite, ctx.max_filas))}"""
    return a_json({"periodo": [d, h], "resultado": ejecutar(ctx, sql, params)})


def comparar_periodos(ctx: ContextoPerfil, desde_actual: str, hasta_actual: str, desde_anterior: str, hasta_anterior: str,
                      agrupar_por: str | None = None, excluir_clientes: list[int] | None = None,
                      limite: int = 50) -> str:
    """
    Compara dos períodos (ej. este mes vs mismo mes del año pasado) con variación absoluta y %.
    agrupar_por opcional: categoria, producto, lugar_venta, cliente, dia_semana, hora.
    Útil para detectar qué creció o cayó y explicar el porqué de un cambio total.
    """
    if agrupar_por and agrupar_por not in DIMENSIONES:
        return a_json({"error": "Dimensión no válida", "validas": list(DIMENSIONES)})
    dim = DIMENSIONES[agrupar_por] if agrupar_por else "'total'"
    extra, params = _filtros(excluir_clientes=excluir_clientes)
    params.update(da=date.fromisoformat(desde_actual), ha=date.fromisoformat(hasta_actual),
                  dp=date.fromisoformat(desde_anterior), hp=date.fromisoformat(hasta_anterior))
    sql = f"""
        WITH base AS (
            SELECT {dim} AS grupo,
                   CASE WHEN operation_date BETWEEN :da AND :ha THEN 'actual' ELSE 'anterior' END AS periodo,
                   subtotal, count, document_id
            FROM {ctx.tabla}
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
        LIMIT {int(min(limite, ctx.max_filas))}"""
    return a_json(ejecutar(ctx, sql, params))


def clientes_inactivos(ctx: ContextoPerfil, dias_sin_compra: int = 90, min_tickets: int = 3,
                       meses_historia: int = 18, excluir_clientes: list[int] | None = None,
                       limite: int = 100) -> str:
    """
    Clientes que compraban con regularidad y dejaron de comprar (riesgo de fuga).
    Devuelve última compra, días sin comprar, frecuencia habitual, gasto histórico y su categoría
    favorita. Ordenados por valor histórico. Excluí clientes genéricos (ej. "consumidor final").
    """
    # Regla del perfil: los clientes genéricos se excluyen siempre, además de los pedidos.
    excluir_clientes = list(excluir_clientes or []) + [
        c for c in ctx.excluir_clientes_ids if c not in (excluir_clientes or [])]
    extra, params = _filtros(excluir_clientes=excluir_clientes)
    params.update(dias=int(dias_sin_compra), min_t=int(min_tickets), meses=int(meses_historia))
    sql = f"""
        WITH ref AS (SELECT MAX(operation_date) AS hoy,
                            (MAX(operation_date) - make_interval(months => :meses))::date AS desde FROM {ctx.tabla}),
        c AS (
            SELECT customer_id, MAX(customer) AS customer,
                   MIN(operation_date) AS primera_compra, MAX(operation_date) AS ultima_compra,
                   COUNT(DISTINCT document_id) AS tickets, SUM(subtotal) AS gasto_total
            FROM {ctx.tabla}
            WHERE operation_date >= (SELECT desde FROM ref) AND customer_id IS NOT NULL {extra}
            GROUP BY customer_id
        ), fav AS (
            SELECT DISTINCT ON (customer_id) customer_id, category
            FROM {ctx.tabla} WHERE operation_date >= (SELECT desde FROM ref) {extra}
            GROUP BY customer_id, category ORDER BY customer_id, SUM(subtotal) DESC
        )
        SELECT c.customer_id, c.customer, c.ultima_compra, (ref.hoy - c.ultima_compra) AS dias_sin_compra,
               c.tickets, ROUND(((c.ultima_compra - c.primera_compra)::numeric / NULLIF(c.tickets - 1, 0)), 1) AS dias_entre_compras,
               ROUND(c.gasto_total::numeric, 2) AS gasto_total,
               ROUND((c.gasto_total / c.tickets)::numeric, 2) AS ticket_promedio, fav.category AS categoria_favorita
        FROM c CROSS JOIN ref LEFT JOIN fav USING (customer_id)
        WHERE c.tickets >= :min_t AND (ref.hoy - c.ultima_compra) >= :dias
        ORDER BY c.gasto_total DESC LIMIT {int(min(limite, ctx.max_filas))}"""
    res = ejecutar(ctx, sql, params)
    return a_json({"nota": "Los días se cuentan hasta la última fecha con ventas en la tabla.", "resultado": res})


def productos_asociados(ctx: ContextoPerfil, desde: str | None = None, hasta: str | None = None,
                        product_id: int | None = None, min_tickets_juntos: int = 20,
                        limite: int = 30) -> str:
    """
    Análisis de canasta: pares de productos que se compran en el mismo ticket (document_id).
    Devuelve soporte (% de tickets con ambos), confianza (prob. de B dado A) y lift (>1 = asociación real).
    Con product_id muestra qué se lleva junto con ese producto. Ideal para combos, cross-selling
    y ubicación en góndola. Por defecto analiza los últimos 6 meses.
    """
    hoy = date.today()
    params = {"d": fecha(desde, hoy - timedelta(days=182)), "h": fecha(hasta, hoy),
              "min": int(min_tickets_juntos)}
    filtro_par = ""
    if product_id is not None:
        filtro_par = "AND (a.product_id = :pid OR b.product_id = :pid)"
        params["pid"] = int(product_id)
    sql = f"""
        WITH t AS (
            SELECT DISTINCT document_id, product_id FROM {ctx.tabla}
            WHERE operation_date BETWEEN :d AND :h AND product_id IS NOT NULL
        ),
        n AS (SELECT COUNT(DISTINCT document_id)::numeric AS total FROM t),
        p AS (SELECT product_id, COUNT(*)::numeric AS c FROM t GROUP BY 1),
        nombres AS (SELECT product_id, MAX(product) AS product FROM {ctx.tabla} GROUP BY 1),
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
        ORDER BY lift DESC, tickets_juntos DESC LIMIT {int(min(limite, ctx.max_filas))}"""
    return a_json({"periodo": [params["d"], params["h"]], "resultado": ejecutar(ctx, sql, params)})


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


def proyectar_ventas(ctx: ContextoPerfil, metrica: str = "ventas", meses: int = 6, categoria: str | None = None,
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
        return a_json({"error": "metrica debe ser ventas, unidades o tickets"})
    extra, params = _filtros(categoria, lugar_venta, product_id)
    # Excluye el último mes solo si está incompleto (la última venta no es el último día del mes)
    corte = "" if incluir_mes_en_curso else f"""
        AND operation_date < (
            SELECT CASE WHEN MAX(operation_date) = (date_trunc('month', MAX(operation_date))
                                                   + interval '1 month - 1 day')::date
                        THEN MAX(operation_date) + 1
                        ELSE date_trunc('month', MAX(operation_date))::date END
            FROM {ctx.tabla})"""
    sql = f"""
        SELECT to_char(date_trunc('month', operation_date), 'YYYY-MM') AS mes, {expr[metrica]} AS valor
        FROM {ctx.tabla} WHERE TRUE {corte} {extra}
        GROUP BY 1 ORDER BY 1"""
    filas = ejecutar(ctx, sql, params, max_filas=1000)["filas"]
    if len(filas) < 6:
        return a_json({"error": "Se necesitan al menos 6 meses de historia para proyectar."})
    ultimo = date.fromisoformat(filas[-1][0] + "-01")
    res = _proyectar(filas, max(1, min(int(meses), 24)))
    for p in res["proyeccion"]:
        m = ultimo.month - 1 + p["periodo_futuro"]
        p["mes"] = f"{ultimo.year + m // 12}-{m % 12 + 1:02d}"
    res["historico"] = [{"mes": f[0], "valor": round(float(f[1] or 0), 2)} for f in filas]
    res["nota"] = "Modelo estadístico simple y orientativo; combinar con criterio comercial."
    return a_json(res)
