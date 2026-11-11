import importlib.util as u, json
sp=u.spec_from_file_location('srv','mcp_server/server.py'); m=u.module_from_spec(sp); sp.loader.exec_module(m)
T=m.TABLA
canasta=f"""
WITH t AS (SELECT DISTINCT document_id, product_id FROM {T}
  WHERE operation_date BETWEEN '2025-10-16' AND '2026-10-15' AND lugar_venta <> 'Dietetica'
    AND product_id IS NOT NULL AND product NOT ILIKE 'delivery%'),
n AS (SELECT COUNT(DISTINCT document_id)::numeric total FROM t),
p AS (SELECT product_id, COUNT(*)::numeric c FROM t GROUP BY 1),
nm AS (SELECT product_id, MAX(product) product FROM {T} GROUP BY 1),
pr AS (SELECT a.product_id a, b.product_id b, COUNT(*)::numeric c FROM t a JOIN t b
  ON a.document_id=b.document_id AND a.product_id<b.product_id GROUP BY 1,2 HAVING COUNT(*)>=40)
SELECT na.product, nb.product, pr.c::int juntos, ROUND(100*pr.c/pa.c,1) conf_ab, ROUND(100*pr.c/pb.c,1) conf_ba,
  ROUND(pr.c*n.total/(pa.c*pb.c),2) lift, n.total::int tickets_total
FROM pr CROSS JOIN n JOIN p pa ON pa.product_id=pr.a JOIN p pb ON pb.product_id=pr.b
JOIN nm na ON na.product_id=pr.a JOIN nm nb ON nb.product_id=pr.b
WHERE pr.c*n.total/(pa.c*pb.c) > 1.2 ORDER BY juntos DESC LIMIT 25"""
r=m._ejecutar(canasta); print(r["columnas"]); [print(x) for x in r["filas"]]
out={}
for lugar in ['Carlos Paz','Villa Allende','Dietetica',None]:
    f = "AND lugar_venta = :l" if lugar else ""
    sql=f"""
    WITH base AS (SELECT product_id, MAX(product) product, date_trunc('week',operation_date)::date sem,
        SUM(subtotal) v, SUM(count) u FROM {T}
      WHERE operation_date BETWEEN '2026-07-13' AND '2026-10-11' {f} GROUP BY 1,3),
    top AS (SELECT product_id, SUM(v) tv FROM base GROUP BY 1 ORDER BY tv DESC LIMIT 20)
    SELECT b.product_id, MAX(b.product) OVER (PARTITION BY b.product_id) product, b.sem::text, ROUND(b.v::numeric) v, ROUND(b.u::numeric,1) u, t.tv
    FROM base b JOIN top t USING (product_id) ORDER BY t.tv DESC, b.sem"""
    r=m._ejecutar(sql, {"l":lugar} if lugar else {}, max_filas=5000)
    out[lugar or 'Todas']=r["filas"]; print(lugar, len(r["filas"]), r["truncado"])
json.dump(out, open(f"/tmp/claude-1000/-home-ubuntu-workspaces-panacea-agente-ventas/e5cc40e1-2769-4777-b8b0-ec146f5423eb/scratchpad/semanal.json","w"), ensure_ascii=False)
