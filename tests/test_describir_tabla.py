"""describir_tabla con parámetro: tablas del perfil, columnas acotadas y orden por columna de fecha."""

import json

import pytest

from agent.contexto import ContextoPerfil
from agent.tools import generic

COLUMNAS = {
    "panacea_sales_v2": [("document_id", "bigint"), ("customer_id", "integer"), ("operation_date", "date")],
    "documentos": [("iddocumento", "integer"), ("idcliente", "integer"), ("fechadocumento", "timestamp"),
                   ("pagoefectivo", "double precision")],
    "costos_costos": [("id", "integer"), ("cantidad", "double precision")],
}


class Base:
    def __init__(self):
        self.sql: list[str] = []

    def __call__(self, ctx, sql, params=None, max_filas=None):
        self.sql.append(sql)
        if "information_schema" in sql:
            filas = [list(c) for c in COLUMNAS.get(params["t"], [])]
        elif "reltuples" in sql:
            filas = [[1000]]
        else:
            filas = [[1, 2]]
        return {"columnas": [], "filas": filas, "total_filas": len(filas), "truncado": False}


@pytest.fixture
def base(monkeypatch):
    b = Base()
    monkeypatch.setattr(generic, "ejecutar", b)
    return b


def ctx_perfil(**cambios):
    datos = dict(engine=None, tabla="public.documentos",
                 tablas_permitidas={"public.documentos": frozenset({"iddocumento", "fechadocumento", "pagoefectivo"}),
                                    "public.costos_costos": None},
                 columnas_fecha={"public.documentos": "fechadocumento"})
    datos.update(cambios)
    return ContextoPerfil(**datos)


def test_sin_parametro_describe_la_principal_como_antes(base):
    ctx = ContextoPerfil(engine=None, tabla="public.panacea_sales_v2",
                         columnas_fecha={"public.panacea_sales_v2": "operation_date"})
    r = json.loads(generic.describir_tabla(ctx))
    assert r["tabla"] == "public.panacea_sales_v2" and len(r["columnas"]) == 3
    assert base.sql[-1] == 'SELECT * FROM public.panacea_sales_v2 ORDER BY "operation_date" DESC LIMIT 5'


def test_tabla_acotada_solo_columnas_permitidas(base):
    r = json.loads(generic.describir_tabla(ctx_perfil(), "documentos"))
    assert [c[0] for c in r["columnas"]] == ["iddocumento", "fechadocumento", "pagoefectivo"]
    ejemplo = base.sql[-1]
    assert "*" not in ejemplo and "idcliente" not in ejemplo
    assert ejemplo.endswith('ORDER BY "fechadocumento" DESC LIMIT 5')


def test_tabla_sin_fecha_no_ordena(base):
    r = json.loads(generic.describir_tabla(ctx_perfil(), "public.costos_costos"))
    assert r["tabla"] == "public.costos_costos"
    assert base.sql[-1] == "SELECT * FROM public.costos_costos LIMIT 5"


def test_tabla_de_otro_perfil_no_consulta_la_base(base):
    r = json.loads(generic.describir_tabla(ctx_perfil(), "ordenes_produccion"))
    assert "no está disponible" in r["error"] and "public.costos_costos" in r["error"]
    assert base.sql == []


def test_nombre_invalido(base):
    r = json.loads(generic.describir_tabla(ctx_perfil(), "documentos; drop table x"))
    assert "error" in r and base.sql == []


def test_consultar_no_menciona_operation_date():
    assert "operation_date" not in generic.consultar.__doc__
