"""
Equivalencia de las 8 herramientas entre el servidor MCP original (tests/legacy/server_v1.py,
copia congelada del commit c9b347b) y el adaptador nuevo sobre agent.tools.

Necesita DATABASE_URL apuntando a la base de ventas (solo lectura). Sin ella, se omite.
"""

import asyncio
import importlib.util
import json
import os
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.db


def _cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def servidores():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("Sin DATABASE_URL")
    return (_cargar("server_v1", RAIZ / "tests/legacy/server_v1.py"),
            _cargar("server_nuevo", RAIZ / "mcp_server/server.py"))


CASOS = [
    ("describir_tabla", {}),
    ("perfil_datos", {}),
    ("resumen_ventas", {}),
    ("resumen_ventas", {"desde": "2025-01-01", "hasta": "2026-10-31", "agrupar_por": ["mes", "lugar_venta"],
                        "ordenar_por": "mes", "limite": 200}),
    ("resumen_ventas", {"desde": "2026-01-01", "hasta": "2026-10-31", "agrupar_por": ["cliente"],
                        "excluir_clientes": [999, 0, 888, 777], "limite": 20}),
    ("resumen_ventas", {"agrupar_por": ["inventada"]}),
    ("comparar_periodos", {"desde_actual": "2026-01-01", "hasta_actual": "2026-10-15",
                           "desde_anterior": "2025-01-01", "hasta_anterior": "2025-10-15",
                           "agrupar_por": "categoria"}),
    ("comparar_periodos", {"desde_actual": "2026-10-01", "hasta_actual": "2026-10-31",
                           "desde_anterior": "2025-10-01", "hasta_anterior": "2025-10-31"}),
    ("clientes_inactivos", {"excluir_clientes": [999, 0, 888, 777], "limite": 30}),
    ("productos_asociados", {"min_tickets_juntos": 50, "limite": 20}),
    ("proyectar_ventas", {"metrica": "ventas", "meses": 6}),
    ("proyectar_ventas", {"metrica": "tickets", "meses": 3, "lugar_venta": "Carlos Paz"}),
    ("proyectar_ventas", {"metrica": "margen"}),
    ("consultar", {"sql": "SELECT lugar_venta, round(sum(subtotal)::numeric, 2) AS v FROM public.panacea_sales_v2 "
                          "WHERE operation_date >= '2026-10-01' GROUP BY 1 ORDER BY 1"}),
]


@pytest.mark.parametrize("nombre,args", CASOS, ids=[f"{n}-{i}" for i, (n, _) in enumerate(CASOS)])
def test_misma_salida(servidores, nombre, args):
    viejo, nuevo = servidores
    assert json.loads(getattr(nuevo, nombre)(**args)) == json.loads(getattr(viejo, nombre)(**args))


@pytest.mark.parametrize("sql", ["SELECT 1; DROP TABLE x", "DELETE FROM public.panacea_sales_v2"])
def test_consultar_rechaza_igual(servidores, sql):
    viejo, nuevo = servidores
    assert "error" in json.loads(viejo.consultar(sql))
    assert "error" in json.loads(nuevo.consultar(sql))


def test_misma_lista_de_herramientas(servidores):
    viejo, nuevo = servidores
    a = [t.model_dump() for t in asyncio.run(viejo.mcp.list_tools())]
    b = [t.model_dump() for t in asyncio.run(nuevo.mcp.list_tools())]
    assert b == a


def test_compatibilidad_scripts(servidores):
    """Nombres que usan trabajo/scripts y plan_ventas/scripts/kpis_semana.py."""
    _, nuevo = servidores
    assert nuevo.TABLA == "public.panacea_sales_v2"
    r = nuevo._ejecutar(nuevo._validar_sql("SELECT count(*) AS n FROM public.panacea_sales_v2"), {})
    assert r["columnas"] == ["n"] and r["filas"][0][0] > 0


def test_regla_de_exclusion_del_perfil(servidores):
    """Con excluir_clientes_ids en el contexto, clientes_inactivos excluye esos clientes aunque no se pidan."""
    from agent.contexto import ContextoPerfil
    from agent.tools.ventas import clientes_inactivos

    _, nuevo = servidores
    genericos = (999, 0, 888, 777)
    ctx = ContextoPerfil(engine=nuevo.engine, tabla=nuevo.TABLA, excluir_clientes_ids=genericos)
    con_regla = json.loads(clientes_inactivos(ctx, dias_sin_compra=0, min_tickets=1, limite=500))
    explicito = json.loads(nuevo.clientes_inactivos(dias_sin_compra=0, min_tickets=1, limite=500,
                                                    excluir_clientes=list(genericos)))
    assert con_regla == explicito
    ids = {f[0] for f in con_regla["resultado"]["filas"]}
    assert not ids & set(genericos)
    adicional = json.loads(clientes_inactivos(ctx, dias_sin_compra=0, min_tickets=1, limite=500,
                                              excluir_clientes=[250]))
    assert 250 not in {f[0] for f in adicional["resultado"]["filas"]}


def test_consultar_con_tablas_permitidas(servidores):
    from agent.contexto import ContextoPerfil
    from agent.tools.generic import consultar

    _, nuevo = servidores
    ctx = ContextoPerfil(engine=nuevo.engine, tabla=nuevo.TABLA, tablas_permitidas={nuevo.TABLA: None})
    assert "error" in json.loads(consultar(ctx, "SELECT * FROM public.costos_costos LIMIT 1"))
    assert json.loads(consultar(ctx, "SELECT 1 AS uno FROM public.panacea_sales_v2 LIMIT 1"))["filas"] == [[1]]
