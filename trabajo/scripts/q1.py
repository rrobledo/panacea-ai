import importlib.util as u, json
sp=u.spec_from_file_location('srv','mcp_server/server.py'); m=u.module_from_spec(sp); sp.loader.exec_module(m)
def show(t, s):
    d=json.loads(s); print("\n##",t)
    if "columnas" in d: print(d["columnas"]); [print(r) for r in d["filas"]]
    else: print(json.dumps(d,ensure_ascii=False)[:4000])
G=[999,0,888]
show("mensual", m.resumen_ventas(desde="2024-01-01", hasta="2026-10-16", agrupar_por=["mes"], ordenar_por="mes", limite=100))
show("mensual lugar 2025-2026", m.resumen_ventas(desde="2025-01-01", hasta="2026-10-16", agrupar_por=["mes","lugar_venta"], ordenar_por="mes", limite=200))
show("YTD por lugar", m.comparar_periodos("2026-01-01","2026-10-15","2025-01-01","2025-10-15", agrupar_por="lugar_venta"))
show("YTD total", m.comparar_periodos("2026-01-01","2026-10-15","2025-01-01","2025-10-15"))
show("YTD categoria", m.comparar_periodos("2026-01-01","2026-10-15","2025-01-01","2025-10-15", agrupar_por="categoria"))
show("YTD clientes no genericos", m.comparar_periodos("2026-01-01","2026-10-15","2025-01-01","2025-10-15", agrupar_por="cliente", excluir_clientes=G, limite=30))
