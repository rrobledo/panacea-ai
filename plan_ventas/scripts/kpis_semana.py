"""
Calcula los KPI de una semana del plan (domingo a sábado) y los guarda en semanas/<AAAA-Www>/kpis.json.
También crea avances.json para esa semana, si no existe, copiando los estados de la semana anterior.

Uso (desde la raíz del proyecto, con DATABASE_URL exportada):
    .venv/bin/python plan_ventas/scripts/kpis_semana.py            # última semana completa
    .venv/bin/python plan_ventas/scripts/kpis_semana.py 2026-W45   # una semana puntual

Las semanas del plan van de domingo a sábado. La clave AAAA-Www es la semana ISO del lunes siguiente al domingo:
2026-W44 = domingo 25/10 a sábado 31/10/2026.

Antes de la primera corrida, o después de un aumento de precios, correr historico.py para recalcular
plan/bases.json, que tiene la base post aumento de cada sucursal.

Accede a la base importando mcp_server/server.py, en una transacción de solo lectura.
"""
import importlib.util, json, sys
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PV = RAIZ / "plan_ventas"
PLAN = json.loads((PV / "plan" / "plan.json").read_text(encoding="utf-8"))
DEF = PLAN["definiciones"]
INICIO = date.fromisoformat(PLAN["inicio"])
T = "public.panacea_sales_v2"
METRICAS_MOST = ("tp", "upt", "pct_uno", "pct_cafe")

sp = importlib.util.spec_from_file_location("srv", RAIZ / "mcp_server" / "server.py")
srv = importlib.util.module_from_spec(sp); sp.loader.exec_module(srv)
sys.path.insert(0, str(Path(__file__).parent))
from generar import crear_avances  # noqa: E402


def q(sql, **params):
    r = srv._ejecutar(srv._validar_sql(sql), params)
    return [dict(zip(r["columnas"], f)) for f in r["filas"]]


def semana_iso(s=None):
    """(clave, domingo, sábado). Sin argumento, la última semana completa (termina el sábado pasado)."""
    if s:
        a, w = s.split("-W")
        domingo = date.fromisocalendar(int(a), int(w), 1) - timedelta(days=1)
    else:
        hoy = date.today()
        domingo = hoy - timedelta(days=(hoy.weekday() - 5) % 7 or 7) - timedelta(days=6)
    a, w, _ = (domingo + timedelta(days=1)).isocalendar()
    return f"{a}-W{w:02d}", domingo, domingo + timedelta(days=6)


def var(a, b):
    return None if not a or not b else round((a / b - 1) * 100, 1)


# ------------------------------------------------------------------ consultas
# Semanas de domingo a sábado: se suma 1 día antes de tomar la semana ISO.
# :shift corre las fechas del año anterior 364 días para que la clave de semana coincida con la actual
SQL_PERIODO = f"""
select coalesce(sum(subtotal),0) ventas, coalesce(sum(count),0) unidades, count(distinct document_id) tickets,
  coalesce(sum(subtotal) filter (where customer_id <> all(:most)),0) ventas_mayoristas,
  count(distinct document_id) filter (where lugar_venta ilike :va) tickets_villa_allende,
  count(distinct document_id) filter (where customer_id = any(:most) and extract(isodow from operation_date) between 1 and 5
                                      and operation_hour between 9 and 10) tickets_9a11,
  count(distinct document_id) filter (where customer_id = any(:most) and extract(isodow from operation_date) = 1
                                      and operation_hour between 7 and 11) tickets_lunes_manana,
  coalesce(sum(count) filter (where product ilike :cuad),0) unidades_cuadrados,
  coalesce(sum(count) filter (where product ~* :caida),0) unidades_en_caida
from {T} where operation_date between :d1 and :d2 and lugar_venta = any(:suc)"""

# Por semana y sucursal (más una fila 'Todas'). Las métricas de ticket son solo de mostrador
SQL_SUC_SEMANAL = f"""
with tk as (select to_char(operation_date + 1 + cast(:shift as int), 'IYYY-"W"IW') sem, lugar_venta, document_id,
                   bool_and(customer_id = any(:most)) most, count(distinct product_id) n, sum(count) u, sum(subtotal) v,
                   bool_or(product ~* :cafe) cafe
            from {T} where operation_date between :d1 and :d2 group by 1, 2, 3)
select sem, coalesce(lugar_venta, 'Todas') lugar, count(*) tickets, sum(u) unidades, sum(v) ventas,
       count(*) filter (where most) tickets_most, avg(v) filter (where most) tp, avg(u) filter (where most) upt,
       100.0 * avg((n = 1)::int) filter (where most) pct_uno, 100.0 * avg(cafe::int) filter (where most) pct_cafe
from tk group by grouping sets ((sem, lugar_venta), (sem)) order by 1, 2"""

# Índice de precios de mostrador (Laspeyres): canasta y precios de referencia = semanas base post aumento (= 100)
SQL_INDICE = f"""
with b as (select product_id, sum(count) qb, sum(subtotal) / sum(count) p0 from {T}
           where customer_id = any(:most) and count > 0 and subtotal > 0 and operation_date between :b1 and :b2
           group by 1 having sum(count) >= 20),
     w as (select to_char(operation_date + 1 + cast(:shift as int), 'IYYY-"W"IW') sem, product_id, sum(subtotal) / sum(count) p
           from {T} where customer_id = any(:most) and count > 0 and subtotal > 0 and operation_date between :d1 and :d2
           group by 1, 2)
select sem, 100 * sum(w.p * b.qb) / sum(b.p0 * b.qb) indice, count(*) productos from w join b using (product_id)
group by 1 order by 1"""

SQL_DIARIO = f"""
select operation_date fecha, sum(subtotal) ventas, count(distinct document_id) tickets, sum(count) unidades
from {T} where operation_date between :d1 and :d2 and lugar_venta = any(:suc) group by 1 order by 1"""

SQL_INACTIVOS = f"""
with h as (select customer_id, max(customer) cliente, count(distinct document_id) tickets, max(operation_date) ultima,
                  sum(subtotal) filter (where operation_date > cast(:corte as date) - 365) ventas_12m
           from {T} where customer_id <> all(:most) and operation_date <= :corte group by 1)
select * from h where tickets >= 3 and ultima < cast(:corte as date) - :dias and ventas_12m > 0
order by ventas_12m desc limit 10"""

SQL_REACTIVADOS = f"""
select customer_id, max(customer) cliente, min(operation_date) primera, sum(subtotal) ventas
from {T} where customer_id = any(:obj) and operation_date between :ini and :d2 group by 1 order by 4 desc"""

SQL_NUEVOS = f"""
with f as (select customer_id, max(customer) cliente, min(operation_date) primera,
                  sum(subtotal) filter (where operation_date >= :ini) ventas
           from {T} where customer_id <> all(:most) and operation_date <= :d2 group by 1)
select * from f where primera >= :ini order by ventas desc"""

SQL_MAYOR = f"""
select customer_id, max(customer) cliente, sum(subtotal) ventas, sum(sum(subtotal)) over () total
from {T} where customer_id <> all(:most) and operation_date between :d1 and :d2 group by 1 order by 3 desc limit 1"""


def ventana_base():
    sems = DEF["semanas_base"]
    return semana_iso(sems[0])[1], semana_iso(sems[-1])[2]


def por_sucursal(d1, d2, shift=0):
    """{semana: {lugar: fila}} con tickets, unidades, ventas y métricas de mostrador."""
    out = {}
    for r in q(SQL_SUC_SEMANAL, d1=d1, d2=d2, shift=shift, most=DEF["clientes_mostrador"], cafe=DEF["regex_cafe"]):
        out.setdefault(r["sem"], {})[r["lugar"]] = r
    return out


def indices(d1, d2, shift=0):
    b1, b2 = ventana_base()
    return {r["sem"]: round(r["indice"], 1)
            for r in q(SQL_INDICE, d1=d1, d2=d2, shift=shift, b1=b1, b2=b2, most=DEF["clientes_mostrador"])}


def ponderado(filas, campo):
    """Promedio de una métrica de mostrador entre sucursales, ponderado por tickets de mostrador."""
    filas = [f for f in filas if f.get(campo) is not None and f.get("tickets_most")]
    t = sum(f["tickets_most"] for f in filas)
    return sum(f[campo] * f["tickets_most"] for f in filas) / t if t else None


def bases():
    p = PV / "plan" / "bases.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"sucursales": {}}


def clientes_objetivo():
    """Lista fija de mayoristas inactivos a la fecha de la línea base. Se calcula una sola vez."""
    p = PV / "plan" / "clientes_objetivo.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    filas = q(SQL_INACTIVOS, most=DEF["clientes_mostrador"], corte=DEF["corte_linea_base"], dias=DEF["dias_inactivo"])
    data = {"corte": DEF["corte_linea_base"], "criterio": f"3 o más tickets, más de {DEF['dias_inactivo']} días sin comprar y compras en los últimos 12 meses",
            "clientes": filas}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main():
    sem, d1, d2 = semana_iso(sys.argv[1] if len(sys.argv) > 1 else None)
    pat = dict(most=DEF["clientes_mostrador"], va=DEF["patron_villa_allende"], cuad=DEF["patron_cuadrados"], caida=DEF["regex_productos_caida"])

    hasta = q(f"select max(operation_date) m from {T} where operation_date >= :d", d=d1 - timedelta(days=60))[0]["m"]
    # Semana incompleta: se compara solo hasta el último día cargado, contra los mismos días de 2025
    fin = min(d2, date.fromisoformat(hasta)) if hasta else d2
    if fin < d1:
        sys.exit(f"No hay ventas cargadas para {sem}: los datos llegan hasta {hasta}.")
    l1, l2 = d1 - timedelta(days=364), fin - timedelta(days=364)

    # Interanual a sucursales comparables: las que vendieron en las dos semanas (Córdoba cerró, Villa General Belgrano es nueva)
    suc_act = por_sucursal(d1, fin).get(sem, {})
    suc_ant = por_sucursal(l1, l2, 364).get(sem, {})
    comp = sorted((set(suc_act) & set(suc_ant)) - {"Todas"})
    idx, idx_ant = indices(d1, fin).get(sem), indices(l1, l2, 364).get(sem)
    act, ant = q(SQL_PERIODO, d1=d1, d2=fin, suc=comp, **pat)[0], q(SQL_PERIODO, d1=l1, d2=l2, suc=comp, **pat)[0]

    obj = clientes_objetivo()
    ids = [c["customer_id"] for c in obj["clientes"]]
    react = q(SQL_REACTIVADOS, obj=ids, ini=INICIO, d2=d2) if ids else []
    nuevos = q(SQL_NUEVOS, most=DEF["clientes_mostrador"], ini=INICIO, d2=d2)
    mayor = q(SQL_MAYOR, most=DEF["clientes_mostrador"], d1=d2 - timedelta(days=27), d2=d2)

    k = {}
    for c in ("ventas", "unidades", "tickets", "ventas_mayoristas", "tickets_villa_allende", "tickets_9a11",
              "tickets_lunes_manana", "unidades_cuadrados", "unidades_en_caida"):
        k[c] = {"valor": act[c], "anterior": ant[c], "var": var(act[c], ant[c])}

    # Mostrador, todas las sucursales, contra la base post aumento
    tot, B = suc_act.get("Todas", {}), bases()["sucursales"].get("Todas", {})
    for kid, campo in (("ticket_promedio", "tp"), ("unidades_por_ticket_mostrador", "upt"),
                       ("pct_tickets_un_producto", "pct_uno"), ("pct_tickets_cafe", "pct_cafe")):
        v, b = tot.get(campo), B.get(campo)
        k[kid] = {"valor": round(v, 2) if v is not None else None, "base": b, "var_base": var(v, b)}
    # Ticket a precios constantes, interanual en sucursales comparables: descuenta el aumento de precios
    tp_c = ponderado([suc_act[l] for l in comp], "tp")
    tp_a = ponderado([suc_ant[l] for l in comp], "tp")
    tc = tp_c / idx * 100 if tp_c and idx else None
    tca = tp_a / idx_ant * 100 if tp_a and idx_ant else None
    k["ticket_constante"] = {"valor": round(tc) if tc else None, "anterior": round(tca) if tca else None, "var": var(tc, tca),
                             "indice": idx, "indice_anterior": idx_ant}
    k["mayoristas_reactivados"] = {"valor": len(react), "de": len(ids)}
    k["mayoristas_nuevos"] = {"valor": len(nuevos)}
    k["peso_mayor_cliente"] = {"valor": round(100 * mayor[0]["ventas"] / mayor[0]["total"], 1) if mayor and mayor[0]["total"] else None}

    diario_ant = {r["fecha"]: r for r in q(SQL_DIARIO, d1=l1, d2=l2, suc=comp)}
    diario = []
    for r in q(SQL_DIARIO, d1=d1, d2=fin, suc=comp):
        a = diario_ant.get((date.fromisoformat(r["fecha"]) - timedelta(days=364)).isoformat(), {})
        diario.append({**r, "ventas_ant": a.get("ventas", 0), "tickets_ant": a.get("tickets", 0), "unidades_ant": a.get("unidades", 0)})

    bs = bases()["sucursales"]
    sucursales = []
    for l in sorted((set(suc_act) | set(suc_ant)) - {"Todas"}) + ["Todas"]:
        a, p, b = suc_act.get(l, {}), suc_ant.get(l, {}), bs.get(l, {})
        fila = {"lugar": l, "comparable": l in comp}
        for c in ("ventas", "tickets", "unidades", "tickets_most") + METRICAS_MOST:
            fila[c], fila[c + "_ant"], fila[c + "_base"] = a.get(c, 0 if c in ("ventas", "tickets", "unidades") else None), p.get(c), b.get(c)
        sucursales.append(fila)

    out = {
        "semana": sem, "desde": d1.isoformat(), "hasta": d2.isoformat(), "corte": fin.isoformat(),
        "anterior_desde": l1.isoformat(), "anterior_hasta": l2.isoformat(),
        "datos_hasta": hasta, "completa": bool(hasta and hasta >= d2.isoformat()),
        "generado": datetime.now().isoformat(timespec="minutes"),
        "kpis": k, "diario": diario,
        "detalle": {
            "reactivados": [{"cliente": r["cliente"], "primera": r["primera"], "ventas": r["ventas"]} for r in react],
            "nuevos": [{"cliente": r["cliente"], "primera": r["primera"], "ventas": r["ventas"]} for r in nuevos[:15]],
            "mayor_cliente": mayor[0]["cliente"] if mayor else None,
            "sucursales_comparables": comp,
            "sucursales": sucursales,
        },
    }
    carpeta = PV / "semanas" / sem
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "kpis.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    crear_avances(sem, carpeta)
    print(f"{sem} ({d1:%d/%m} al {d2:%d/%m}) · datos hasta {hasta} · tickets {act['tickets']} ({k['tickets']['var']}% interanual)")
    if not out["completa"]:
        print("ATENCIÓN: la semana todavía no tiene datos completos.")


if __name__ == "__main__":
    main()
