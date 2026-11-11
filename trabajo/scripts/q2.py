import importlib.util as u, json
sp=u.spec_from_file_location('srv','mcp_server/server.py'); m=u.module_from_spec(sp); sp.loader.exec_module(m)
def show(t, s, n=4000):
    d=json.loads(s) if isinstance(s,str) else s; print("\n##",t)
    if isinstance(d,dict) and "columnas" in d: print(d["columnas"]); [print(r) for r in d["filas"]]
    else: print(json.dumps(d,ensure_ascii=False)[:n])
G=[999,0,888]
show("Q3 lugar", m.comparar_periodos("2026-07-01","2026-09-30","2025-07-01","2025-09-30", agrupar_por="lugar_venta"))
show("Q3 categoria", m.comparar_periodos("2026-07-01","2026-09-30","2025-07-01","2025-09-30", agrupar_por="categoria"))
show("Q3 producto", m.comparar_periodos("2026-07-01","2026-09-30","2025-07-01","2025-09-30", agrupar_por="producto", limite=40))
q=lambda s: show(s[:60], m.consultar(s))
q("""select case when customer_id in (999,0,888,777) then 'mostrador' else 'nominado' end seg, round(sum(subtotal)) v, count(distinct document_id) t, round(100*sum(subtotal)/sum(sum(subtotal)) over(),1) pct from public.panacea_sales_v2 where operation_date between '2025-10-16' and '2026-10-15' group by 1""")
q("""select operation_year, count(*) lineas, round(sum(subtotal)) neg from public.panacea_sales_v2 where subtotal<0 group by 1 order by 1""")
q("""with p as (select product, sum(subtotal) v from public.panacea_sales_v2 where operation_date between '2025-10-16' and '2026-10-15' group by 1), r as (select v, sum(v) over(order by v desc) c, sum(v) over() t, row_number() over(order by v desc) n, count(*) over() k from p) select min(n) n80, max(k) total from r where c>=0.8*t""")
q("""with p as (select customer_id, sum(subtotal) v from public.panacea_sales_v2 where operation_date between '2025-10-16' and '2026-10-15' and customer_id not in (999,0,888,777) group by 1), r as (select v, sum(v) over(order by v desc) c, sum(v) over() t, row_number() over(order by v desc) n, count(*) over() k from p) select min(n) n80, max(k) total, max(t) ventas from r where c>=0.8*t""")
q("""select day_of_week, day_of_week_text, operation_hour, round(sum(subtotal)) v, count(distinct document_id) t from public.panacea_sales_v2 where operation_date between '2025-10-16' and '2026-10-15' and customer_id in (999,0,888,777) group by 1,2,3 order by 1,3""")
