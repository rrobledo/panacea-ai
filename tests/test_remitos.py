"""remitos_vs_ventas con una base simulada: sucursales → lugares, transferencias y artículos sin vincular."""

import json

import pytest

from agent.contexto import ContextoPerfil
from agent.tools import remitos

# (origen, destino, producto, cantidad entregada)
REMITOS = [
    (1, 2, 45, 600),    # fábrica → Villa Allende, medialunas
    (1, 3, 45, 700),    # fábrica → Carlos Paz 9 de Julio
    (1, 4, 45, 300),    # fábrica → Carlos Paz San Martín (mismo lugar)
    (3, 4, 45, 50),     # entre las dos de Carlos Paz: no cambia nada
    (2, 1, 45, 20),     # Villa Allende devuelve a la fábrica
    (1, 5, 50, 100),    # fábrica → Villa General Belgrano, facturas
]
# (lugar, producto, nombre, unidades, importe)
VENTAS = [
    (1, 45, "Medialunas", 500, 950_000.0),
    (2, 45, "Medialunas", 1200, 2_300_000.0),
    (1, 397, "FACTURAS X 2 BOLSITA", 80, 240_000.0),  # artículo de caja sin vincular
    (0, 45, "Medialunas", 30, 60_000.0),              # Dietética: no recibe remitos, se ignora
]
PRODUCTOS = {45: "Medialunas", 50: "Facturas"}


class Base:
    def __init__(self):
        self.sql = []

    def __call__(self, ctx, sql, params=None, max_filas=None):
        self.sql.append((sql, params))
        if "pedidos_pedido" in sql:
            filas = [list(r) for r in REMITOS if params.get("p") in (None, r[2])]
        elif "costos_productos" in sql:
            filas = [[i, n] for i, n in PRODUCTOS.items() if i in params["ids"]]
        else:
            filas = [list(v) for v in VENTAS if params.get("p") in (None, v[1])]
        return {"columnas": [], "filas": filas, "total_filas": len(filas), "truncado": False}


@pytest.fixture
def base(monkeypatch):
    b = Base()
    monkeypatch.setattr(remitos, "ejecutar", b)
    return b


@pytest.fixture
def ctx():
    return ContextoPerfil(engine=None, tabla="public.panacea_sales_v2")


def filas(r):
    return {(f[0], f[2]): dict(zip(r["columnas"], f)) for f in r["filas"]}


def test_cruce_por_sucursal_y_producto(base, ctx):
    r = json.loads(remitos.remitos_vs_ventas(ctx, desde="2026-10-01", hasta="2026-10-31"))
    f = filas(r)
    va = f[(1, 45)]
    assert (va["recibido"], va["enviado_a_otras"], va["vendido"]) == (600, 20, 500)
    assert va["diferencia"] == 80 and va["pct_vendido"] == pytest.approx(86.2, abs=0.1)
    cp = f[(2, 45)]
    assert cp["recibido"] == 1000 and cp["enviado_a_otras"] == 0  # 9 de Julio + San Martín, sin la transferencia interna
    assert cp["diferencia"] == -200
    vgb = f[(4, 50)]
    assert vgb["producto"] == "Facturas" and vgb["vendido"] == 0 and vgb["pct_vendido"] == 0
    assert (0, 45) not in f  # la Dietética no recibe remitos
    assert r["totales_por_lugar"]["2"]["diferencia"] == -200


def test_remito_por_fecha_de_emision(base, ctx):
    remitos.remitos_vs_ventas(ctx, desde="2026-10-01", hasta="2026-10-31")
    sql_remitos = next(s for s, _ in base.sql if "pedidos_pedido" in s)
    assert "fecha_listo_para_entrega AT TIME ZONE 'America/Argentina/Cordoba'" in sql_remitos
    assert "tipo = 'SUCURSAL'" in sql_remitos and "<> 'CANCELADO'" in sql_remitos
    assert "ENTREGADO'" not in sql_remitos.replace("CANCELADO'", "")


def test_avisa_articulos_sin_vincular(base, ctx):
    r = json.loads(remitos.remitos_vs_ventas(ctx, desde="2026-10-01", hasta="2026-10-31"))
    assert any("FACTURAS X 2 BOLSITA" in a and "costos_productosref" in a for a in r["avisos"])
    assert any("no un inventario" in a for a in r["avisos"])


def test_filtros(base, ctx):
    r = json.loads(remitos.remitos_vs_ventas(ctx, desde="2026-10-01", hasta="2026-10-31", lugar_venta_id=2))
    assert {f[0] for f in r["filas"]} == {2}
    r = json.loads(remitos.remitos_vs_ventas(ctx, desde="2026-10-01", hasta="2026-10-31", producto_id=50))
    assert [f[2] for f in r["filas"]] == [50]


def test_errores(base, ctx):
    assert "no recibe remitos" in json.loads(remitos.remitos_vs_ventas(ctx, lugar_venta_id=0))["error"]
    assert "400 días" in json.loads(remitos.remitos_vs_ventas(ctx, desde="2025-01-01", hasta="2026-10-31"))["error"]
    assert "posterior" in json.loads(remitos.remitos_vs_ventas(ctx, desde="2026-10-31", hasta="2026-10-01"))["error"]
