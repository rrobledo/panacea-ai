"""
Remitos de la fábrica a las sucursales contra lo vendido en cada sucursal (stock virtual del período).

Los remitos están en pedidos_pedido con tipo = 'SUCURSAL': un envío cuenta desde su
fecha_listo_para_entrega (cuando se emite el remito) con la cantidad de cantidad_entregada. La mayoría
nunca pasa a ENTREGADO, así que no se usa ese estado. Las sucursales se traducen a lugares de venta con
config/lugares_venta.yaml (campo sucursales).
"""

from datetime import date, timedelta

from agent.contexto import ContextoPerfil
from agent.externas import config
from agent.tools.base import a_json, ejecutar, fecha

TABLA_VENTAS = "public.panacea_sales_v2"
ZONA = "America/Argentina/Cordoba"
MAX_DIAS = 400
COLUMNAS = ["lugar_venta_id", "lugar_venta", "producto_id", "producto", "recibido", "enviado_a_otras",
            "vendido", "ventas_ars", "diferencia", "pct_vendido"]


def _tabla_ventas(ctx: ContextoPerfil) -> str:
    return ctx.tabla if ctx.tabla.endswith(".panacea_sales_v2") else TABLA_VENTAS


def remitos_vs_ventas(ctx: ContextoPerfil, desde: str | None = None, hasta: str | None = None,
                      lugar_venta_id: int | None = None, producto_id: int | None = None) -> str:
    """
    Compara, por sucursal y producto, lo recibido por remitos de la fábrica con lo vendido en el mismo
    período. diferencia = recibido − enviado_a_otras − vendido: es el stock virtual del período
    (positivo = sobró o hubo merma no registrada; negativo = se vendió más de lo recibido, por stock
    previo o un remito sin cargar). pct_vendido = vendido / (recibido − enviado_a_otras).
    Un remito cuenta por su fecha_listo_para_entrega con su cantidad_entregada.
    Fechas AAAA-MM-DD (por defecto, los últimos 7 días hasta ayer); máximo 400 días.
    lugar_venta_id: 1 Villa Allende, 2 Carlos Paz (sucursales 9 de Julio y San Martín), 4 Villa General
    Belgrano. producto_id es el de costos_productos (= product_id de ventas).
    No hay conteos de stock ni desperdicio de sucursal: la diferencia no es un inventario real.
    """
    try:
        h = fecha(hasta, date.today() - timedelta(days=1))
        d = fecha(desde, h - timedelta(days=6))
    except ValueError as e:
        return a_json({"error": f"Fecha inválida: {e}"})
    if d > h:
        return a_json({"error": "desde es posterior a hasta"})
    if (h - d).days + 1 > MAX_DIAS:
        return a_json({"error": f"El rango supera {MAX_DIAS} días: acotalo."})

    lugares = config.lugares()
    por_sucursal = lugares.lugar_de_sucursal()
    nombres_lugar = {l.id: l.nombre for l in lugares.lugares}
    if lugar_venta_id is not None and not any(l.id == lugar_venta_id and l.sucursales for l in lugares.lugares):
        con_sucursal = [f"{l.id} {l.nombre}" for l in lugares.lugares if l.sucursales]
        return a_json({"error": f"El lugar {lugar_venta_id} no recibe remitos. Lugares con remitos: {', '.join(con_sucursal)}."})

    params = {"d": d, "h": h}
    filtro_producto = ""
    if producto_id is not None:
        filtro_producto, params["p"] = " AND d.producto_id = :p", int(producto_id)
    remitos = ejecutar(ctx, f"""
        SELECT p.origen_sucursal_id, p.sucursal_id, d.producto_id, SUM(d.cantidad_entregada) AS cantidad
        FROM public.pedidos_pedido p
        JOIN public.pedidos_pedido_detalle d ON d.pedido_id = p.id
        WHERE p.tipo = 'SUCURSAL' AND p.estado <> 'CANCELADO' AND d.cantidad_entregada > 0
          AND (p.fecha_listo_para_entrega AT TIME ZONE '{ZONA}')::date BETWEEN :d AND :h{filtro_producto}
        GROUP BY 1, 2, 3""", params, max_filas=20_000)["filas"]

    filtro_ventas = " AND product_id = :p" if producto_id is not None else ""
    ventas = ejecutar(ctx, f"""
        SELECT lugar_venta_id, product_id, MAX(product) AS producto,
               SUM(count) AS unidades, SUM(subtotal) AS importe
        FROM {_tabla_ventas(ctx)}
        WHERE operation_date BETWEEN :d AND :h{filtro_ventas}
        GROUP BY 1, 2""", params, max_filas=20_000)["filas"]

    filas: dict[tuple[int, int], dict] = {}
    nombres_producto: dict[int, str] = {}
    sin_lugar: set[int] = set()

    def fila(lugar: int, prod: int) -> dict:
        return filas.setdefault((lugar, prod), {"recibido": 0.0, "enviado_a_otras": 0.0, "vendido": 0.0,
                                                "ventas_ars": 0.0})

    for origen, destino, prod, cantidad in remitos:
        lugar_destino = por_sucursal.get(destino)
        lugar_origen = por_sucursal.get(origen)
        if lugar_destino is None and destino is not None and destino != 1:
            sin_lugar.add(destino)
        if lugar_destino is not None and (lugar_origen is None or lugar_origen.id != lugar_destino.id):
            fila(lugar_destino.id, prod)["recibido"] += float(cantidad or 0)
        if lugar_origen is not None and (lugar_destino is None or lugar_destino.id != lugar_origen.id):
            fila(lugar_origen.id, prod)["enviado_a_otras"] += float(cantidad or 0)

    lugares_con_remitos = {l.id for l in lugares.lugares if l.sucursales}
    sin_vincular: dict[int, float] = {}
    for lugar, prod, nombre, unidades, importe in ventas:
        if lugar not in lugares_con_remitos:
            continue
        nombres_producto[prod] = nombre
        f = fila(lugar, prod)
        f["vendido"] += float(unidades or 0)
        f["ventas_ars"] += float(importe or 0)

    # product_id de ventas es el id de costos_productos cuando el artículo de caja está vinculado en
    # costos_productosref; si no, queda el id del artículo y no se cruza con ningún remito.
    de_fabrica: set[int] = set()
    ids = sorted({p for (_, p) in filas})
    if ids:
        for pid, nombre in ejecutar(ctx, "SELECT id, nombre FROM public.costos_productos WHERE id = ANY(:ids)",
                                    {"ids": ids}, max_filas=5000)["filas"]:
            de_fabrica.add(pid)
            nombres_producto.setdefault(pid, nombre)

    resultado = []
    totales: dict[int, dict] = {}
    for (lugar, prod), f in filas.items():
        if lugar_venta_id is not None and lugar != lugar_venta_id:
            continue
        disponible = f["recibido"] - f["enviado_a_otras"]
        diferencia = disponible - f["vendido"]
        resultado.append({
            "lugar_venta_id": lugar, "lugar_venta": nombres_lugar.get(lugar, str(lugar)), "producto_id": prod,
            "producto": nombres_producto.get(prod, f"producto {prod}"),
            "recibido": round(f["recibido"], 2), "enviado_a_otras": round(f["enviado_a_otras"], 2),
            "vendido": round(f["vendido"], 2), "ventas_ars": round(f["ventas_ars"], 2),
            "diferencia": round(diferencia, 2),
            "pct_vendido": round(100 * f["vendido"] / disponible, 1) if disponible > 0 else None,
        })
        t = totales.setdefault(lugar, {"lugar_venta": nombres_lugar.get(lugar, str(lugar)), "recibido": 0.0,
                                       "enviado_a_otras": 0.0, "vendido": 0.0, "ventas_ars": 0.0,
                                       "productos_sin_remito": 0})
        for k in ("recibido", "enviado_a_otras", "vendido", "ventas_ars"):
            t[k] = round(t[k] + f[k], 2)
        if f["recibido"] == 0 and f["vendido"] > 0:
            t["productos_sin_remito"] += 1
        if prod not in de_fabrica and f["vendido"] > 0:
            sin_vincular[prod] = sin_vincular.get(prod, 0) + f["vendido"]
    for t in totales.values():
        t["diferencia"] = round(t["recibido"] - t["enviado_a_otras"] - t["vendido"], 2)

    resultado.sort(key=lambda r: (r["lugar_venta_id"], -abs(r["diferencia"])))
    truncado = len(resultado) > ctx.max_filas
    avisos = ["No hay conteos de stock ni registro de desperdicio en las sucursales: la diferencia es lo "
              "que debería quedar o se perdió en el período, no un inventario."]
    if any(t["productos_sin_remito"] for t in totales.values()):
        avisos.append("Hay productos vendidos sin remitos en el período (productos_sin_remito): pueden venir "
                      "de stock anterior, elaborarse en la sucursal o comprarse a terceros.")
    if sin_vincular:
        top = sorted(sin_vincular.items(), key=lambda x: -x[1])[:8]
        avisos.append("Artículos vendidos que no están vinculados a un producto de fábrica en costos_productosref "
                      "(no pueden cruzarse con remitos; algunos son productos de reventa o cafetería): "
                      + "; ".join(f"{nombres_producto.get(p, p)} ({round(u)} u.)" for p, u in top) + ".")
    if sin_lugar:
        avisos.append(f"Remitos a sucursales sin lugar de venta en config/lugares_venta.yaml: {sorted(sin_lugar)}.")
    if truncado:
        avisos.append(f"Resultado truncado a {ctx.max_filas} filas: filtrá por lugar_venta_id o producto_id.")
    return a_json({"periodo": [d, h], "columnas": COLUMNAS,
                   "filas": [[r[c] for c in COLUMNAS] for r in resultado[:ctx.max_filas]],
                   "total_filas": min(len(resultado), ctx.max_filas), "truncado": truncado,
                   "totales_por_lugar": totales, "avisos": avisos})
