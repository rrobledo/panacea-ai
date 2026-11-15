"""Perfiles de compras, producción y tesorería: configuración real, alcance y columnas acotadas."""

import pytest

from agent.profiles import HERRAMIENTAS_VENTAS, cargar_configuracion, tabla_no_exponible
from agent.sql_guard import SQLNoPermitido, validar_sql

AREAS = ("compras", "produccion", "tesoreria")
HERRAMIENTAS_AREA = ["describir_tabla", "consultar", "solicitar_aclaraciones", "generar_artifact", "editar_artifact"]
VENTAS_HERRAMIENTAS = ["perfil_datos", "describir_tabla", "resumen_ventas", "comparar_periodos",
                       "clientes_inactivos", "productos_asociados", "proyectar_ventas", "consultar",
                       "ventas_con_contexto", "impacto_variables", "contexto_proximos_dias",
                       "solicitar_aclaraciones", "generar_artifact", "editar_artifact"]


@pytest.fixture(scope="module")
def config():
    return cargar_configuracion()


def test_ventas_sin_cambios(config):
    v = config.perfiles["ventas"]
    assert [t.nombre for t in v.base_datos.tablas] == ["public.panacea_sales_v2"]
    assert v.herramientas == VENTAS_HERRAMIENTAS
    assert v.base_datos.credencial_env == "DB_URL_VENTAS"


@pytest.mark.parametrize("area", AREAS)
def test_perfil_de_area(config, area):
    p = config.perfiles[area]
    assert p.herramientas == HERRAMIENTAS_AREA
    assert not HERRAMIENTAS_VENTAS & set(p.herramientas)
    assert p.base_datos.credencial_env == f"DB_URL_{area.upper()}"
    for t in p.base_datos.tablas:
        assert not tabla_no_exponible(t.nombre), t.nombre
        assert t.diccionario, f"{area}: {t.nombre} sin diccionario"
    assert "# Tablas disponibles" in p.system_prompt()


def test_tablas_principales(config):
    assert config.perfiles["compras"].tabla_principal == "public.compras_compra"
    assert config.perfiles["produccion"].tabla_principal == "public.costos_programacion"
    assert config.perfiles["tesoreria"].tabla_principal == "public.compras_pago"


# Columnas reales (subconjunto suficiente para que sql_guard resuelva las consultas de prueba)
ESQUEMA = {
    "public.costos_proveedor": ["id", "codigo", "nombre", "nombre_fantasia", "cuit", "condicion_iva",
                                "condicion_pago", "direccion", "telefono", "email", "fecha_alta", "estado"],
    "public.documentos": ["iddocumento", "idcaja", "fechadocumento", "pagoefectivoneto", "pagotarjeta",
                          "docanulado", "idcliente", "nrodoccliente", "nombreclienteeventual"],
    "public.panacea_sales_v2": ["document_id", "product_id", "operation_date", "count", "subtotal",
                                "customer_id", "customer"],
}


def guard(config, area, sql):
    p = config.perfiles[area]
    esquema = {t.nombre: ESQUEMA.get(t.nombre, ["id"]) for t in p.base_datos.tablas}
    return validar_sql(sql, p.tablas_permitidas(), esquema)


@pytest.mark.parametrize("area,sql", [
    ("compras", "SELECT telefono FROM public.costos_proveedor"),
    ("compras", "SELECT email FROM public.costos_proveedor"),
    ("tesoreria", "SELECT idcliente FROM public.documentos"),
    ("tesoreria", "SELECT nrodoccliente FROM public.documentos"),
    ("produccion", "SELECT customer_id FROM public.panacea_sales_v2"),
    ("compras", "SELECT * FROM public.ordenes_produccion"),
    ("tesoreria", "SELECT * FROM public.cajasaperturas"),
])
def test_fuera_del_perfil(config, area, sql):
    with pytest.raises(SQLNoPermitido):
        guard(config, area, sql)


@pytest.mark.parametrize("area,sql", [
    ("compras", "SELECT nombre, cuit FROM public.costos_proveedor"),
    ("tesoreria", "SELECT SUM(pagoefectivoneto) + SUM(pagotarjeta) FROM public.documentos WHERE docanulado = 0"),
    ("produccion", "SELECT product_id, SUM(count) FROM public.panacea_sales_v2 GROUP BY 1"),
])
def test_dentro_del_perfil(config, area, sql):
    assert guard(config, area, sql)


def test_script_de_roles_coincide_con_los_perfiles(config):
    """sql/roles_perfiles_area.sql otorga exactamente las tablas y columnas de cada perfil."""
    import re
    from tests.conftest import RAIZ
    sql = (RAIZ / "sql/roles_perfiles_area.sql").read_text()
    for area in AREAS:
        rol = f"agente_{area}_ro"
        otorgado = {}
        for cols, tabla in re.findall(rf"GRANT SELECT (?:\(([^)]*)\) )?ON (public\.\w+) TO {rol};", sql):
            otorgado[tabla] = frozenset(c.strip() for c in cols.split(",")) if cols else None
        assert otorgado == config.perfiles[area].tablas_permitidas(), area
        assert f"ALTER ROLE {rol} SET default_transaction_read_only = on;" in sql


@pytest.mark.db
@pytest.mark.parametrize("area", AREAS)
def test_rol_real(config, area):
    """Con la variable del perfil definida: el rol ve sus tablas y sql_guard rechaza lo no permitido."""
    import os
    from agent.profiles import contexto_para
    from agent.tools.generic import consultar, describir_tabla
    if not os.environ.get(f"DB_URL_{area.upper()}"):
        pytest.skip(f"Sin DB_URL_{area.upper()}")
    p = config.perfiles[area]
    ctx = contexto_para(p)
    for t in p.base_datos.tablas:
        assert "error" not in describir_tabla(ctx, t.nombre), t.nombre
    assert "no permitid" in consultar(ctx, "SELECT * FROM public.socios").lower()
