import importlib.util as u, json
sp=u.spec_from_file_location('srv','mcp_server/server.py'); m=u.module_from_spec(sp); sp.loader.exec_module(m)
def show(t, s, n=6000):
    d=json.loads(s); print("\n##",t)
    if isinstance(d,dict) and "columnas" in d: print(d["columnas"]); [print(r) for r in d["filas"]]
    else: print(json.dumps(d,ensure_ascii=False)[:n])
G=[999,0,888,777]
show("seg", m.consultar("""select case when customer_id in (999,0,888,777) then 'mostrador' else 'nominado' end seg, round(sum(subtotal)::numeric) v, count(distinct document_id) t, round((100*sum(subtotal)/sum(sum(subtotal)) over())::numeric,1) pct from public.panacea_sales_v2 where operation_date between '2025-10-16' and '2026-10-15' group by 1"""))
show("inactivos", m.clientes_inactivos(dias_sin_compra=60, min_tickets=3, meses_historia=18, excluir_clientes=G, limite=25))
show("canasta", m.productos_asociados(desde="2025-10-16", hasta="2026-10-15", min_tickets_juntos=30, limite=30))
show("proy", m.proyectar_ventas(metrica="ventas", meses=6))
show("proy unidades", m.proyectar_ventas(metrica="unidades", meses=6))
show("mostrador UPT/tickets por mes", m.consultar("""select to_char(operation_date,'YYYY-MM') mes, count(distinct document_id) t, round((sum(count)/count(distinct document_id))::numeric,2) upt, round((sum(subtotal)/count(distinct document_id))::numeric) tp, round((count(*)::numeric/count(distinct document_id)),2) items from public.panacea_sales_v2 where customer_id in (999,0,888,777) and operation_date>='2025-01-01' group by 1 order by 1"""))
show("mono-producto", m.consultar("""with t as (select document_id, count(distinct product_id) n, sum(subtotal) v from public.panacea_sales_v2 where customer_id in (999,0,888,777) and operation_date between '2025-10-16' and '2026-10-15' group by 1) select case when n=1 then '1' when n=2 then '2' else '3+' end k, count(*) tickets, round(avg(v)::numeric) tp from t group by 1 order by 1"""))
show("cafe", m.consultar("""select count(distinct document_id) filter (where product ilike '%cafe%') con_cafe, count(distinct document_id) tot from public.panacea_sales_v2 where customer_id in (999,0,888,777) and operation_date between '2026-07-01' and '2026-10-15'"""))
