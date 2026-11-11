import importlib.util as u, json
sp=u.spec_from_file_location('srv','mcp_server/server.py'); m=u.module_from_spec(sp); sp.loader.exec_module(m)
E=lambda s: m._ejecutar(s, max_filas=100000)["filas"]
prod=E("""select producto_id, fecha::text, sum(prod) from costos_programacion
  where fecha between '2026-01-05' and '2026-10-11' and prod is not null group by 1,2""")
loaded=E("""select fecha::text from costos_programacion where fecha between '2026-01-05' and '2026-10-11' group by 1 having count(prod)>0""")
allrows=E("""select fecha::text, extract(dow from fecha)::int from costos_programacion where fecha between '2026-01-05' and '2026-10-11' group by 1,2""")
ventas=E("""select r.producto_id, s.operation_date::text, sum(s.count*r.unidad_conversion), sum(s.subtotal)
  from panacea_sales_v2 s join costos_productosref r on s.ref_id::text=r.ref_id
  where s.operation_date between '2026-01-05' and '2026-10-11' group by 1,2""")
precio=E("""select r.producto_id, sum(s.subtotal)/nullif(sum(s.count*r.unidad_conversion),0)
  from panacea_sales_v2 s join costos_productosref r on s.ref_id::text=r.ref_id
  where s.operation_date between '2026-09-14' and '2026-10-15' and s.subtotal>0 group by 1""")
maestro=E("select id, nombre, unidad_medida, naturaleza, vendible, categoria from costos_productos")
json.dump(dict(prod=prod,loaded=loaded,allrows=allrows,ventas=ventas,precio=precio,maestro=maestro), open("/tmp/claude-1000/-home-ubuntu-workspaces-panacea-agente-ventas/e5cc40e1-2769-4777-b8b0-ec146f5423eb/scratchpad/merma_raw.json","w"), default=str)
print(len(prod),len(loaded),len(allrows),len(ventas),len(precio),len(maestro))
