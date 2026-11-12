import re
from pathlib import Path

import pytest

from agent.sql_guard import SQLNoPermitido, validar_sql

RAIZ = Path(__file__).resolve().parent.parent
VENTAS = "public.panacea_sales_v2"
COLUMNAS_VENTAS = [
    "document_id", "category_id", "category", "ref_id", "product_id", "product", "lugar_venta_id",
    "lugar_venta", "customer_id", "customer", "operation_date", "operation_hour", "operation_year",
    "operation_month", "week_of_year", "week_of_month", "day_of_week", "day_of_week_text", "count", "subtotal",
]
PERFIL_VENTAS = {VENTAS: None}
PERFIL_PRODUCCION = {
    "public.costos_costos": None,
    "public.costos_insumos": None,
    VENTAS: frozenset({"operation_date", "product_id", "product", "count"}),
}
ESQUEMA = {VENTAS: COLUMNAS_VENTAS,
           "public.costos_costos": ["product_id", "costo"],
           "public.costos_insumos": ["insumo_id", "precio"]}


def prod(sql):
    return validar_sql(sql, PERFIL_PRODUCCION, ESQUEMA)


# ------------------------------------------------------------ sentencias
@pytest.mark.parametrize("sql", [
    "SELECT 1; DROP TABLE x",
    "SELECT 1; SELECT 2",
])
def test_una_sola_sentencia(sql):
    with pytest.raises(SQLNoPermitido, match="una sentencia"):
        validar_sql(sql)


@pytest.mark.parametrize("sql", [
    "DELETE FROM public.panacea_sales_v2",
    "UPDATE public.panacea_sales_v2 SET subtotal = 0",
    "INSERT INTO public.panacea_sales_v2 (document_id) VALUES (1)",
    "DROP TABLE public.panacea_sales_v2",
    "CREATE TABLE x AS SELECT 1",
    "TRUNCATE public.panacea_sales_v2",
    "SET statement_timeout = 0",
    "COPY public.panacea_sales_v2 TO '/tmp/x'",
    "GRANT SELECT ON public.panacea_sales_v2 TO public",
    "VACUUM public.panacea_sales_v2",
])
def test_solo_lectura(sql):
    with pytest.raises(SQLNoPermitido):
        validar_sql(sql)


@pytest.mark.parametrize("sql", [
    "WITH x AS (DELETE FROM public.panacea_sales_v2 RETURNING *) SELECT * FROM x",
    "SELECT * INTO nueva FROM public.panacea_sales_v2",
    "SELECT * FROM public.panacea_sales_v2 FOR UPDATE",
])
def test_escritura_escondida(sql):
    with pytest.raises(SQLNoPermitido, match="no permitidas"):
        validar_sql(sql)


@pytest.mark.parametrize("fn", ["pg_sleep(10)", "pg_read_file('/etc/passwd')", "dblink('x', 'select 1')",
                                "lo_import('/etc/passwd')", "set_config('a', 'b', false)",
                                "pg_terminate_backend(1)"])
def test_funciones_prohibidas(fn):
    with pytest.raises(SQLNoPermitido, match="función"):
        validar_sql(f"SELECT {fn}")


def test_sql_invalido():
    with pytest.raises(SQLNoPermitido, match="interpretar"):
        validar_sql("SELEC mal escrito FROM")


def test_palabras_reservadas_en_textos_no_bloquean():
    # el validador anterior (regex) rechazaba esto por la palabra "update" en un literal
    validar_sql("SELECT count(*) FROM public.panacea_sales_v2 WHERE product ILIKE '%update%'", PERFIL_VENTAS)


def test_punto_y_coma_final_y_espacios():
    assert validar_sql("  SELECT 1 ;  ") == "SELECT 1"


# ------------------------------------------------------------ tablas
def test_tabla_de_otro_perfil():
    with pytest.raises(SQLNoPermitido, match="public.costos_costos"):
        validar_sql("SELECT * FROM public.costos_costos", PERFIL_VENTAS)


def test_tabla_sin_esquema_se_toma_como_public():
    validar_sql("SELECT sum(subtotal) FROM panacea_sales_v2", PERFIL_VENTAS)
    with pytest.raises(SQLNoPermitido):
        validar_sql("SELECT * FROM costos_costos", PERFIL_VENTAS)


def test_catalogo_del_sistema_bloqueado_en_perfil():
    with pytest.raises(SQLNoPermitido, match="pg_catalog.pg_authid|information_schema"):
        validar_sql("SELECT * FROM information_schema.tables", PERFIL_VENTAS)


def test_tabla_en_subconsulta_y_join():
    with pytest.raises(SQLNoPermitido, match="public.otra"):
        validar_sql("SELECT * FROM public.panacea_sales_v2 v WHERE v.product_id IN "
                    "(SELECT product_id FROM public.otra)", PERFIL_VENTAS)


def test_cte_valido_no_cuenta_como_tabla():
    validar_sql("""
        WITH t AS (SELECT document_id, product_id FROM public.panacea_sales_v2),
             n AS (SELECT count(DISTINCT document_id) AS total FROM t)
        SELECT * FROM t CROSS JOIN n""", PERFIL_VENTAS)


def test_cte_no_oculta_tabla_ajena():
    with pytest.raises(SQLNoPermitido, match="public.costos_costos"):
        validar_sql("WITH t AS (SELECT * FROM public.costos_costos) SELECT * FROM t", PERFIL_VENTAS)


def test_union_y_funcion_en_from():
    validar_sql("SELECT 1 FROM public.panacea_sales_v2 UNION ALL SELECT g FROM generate_series(1, 3) g",
                PERFIL_VENTAS)


def test_sin_lista_no_restringe_tablas():
    validar_sql("SELECT * FROM public.cualquiera")


# ------------------------------------------------------------ columnas
def test_columna_fuera_del_alcance():
    with pytest.raises(SQLNoPermitido, match="public.panacea_sales_v2.subtotal"):
        prod("SELECT product, sum(subtotal) FROM public.panacea_sales_v2 GROUP BY 1")


def test_columnas_permitidas():
    prod("SELECT v.product_id, sum(v.count) AS u, max(c.costo) FROM public.panacea_sales_v2 v "
         "JOIN public.costos_costos c ON c.product_id = v.product_id "
         "WHERE v.operation_date >= '2026-01-01' GROUP BY 1 ORDER BY u DESC")


def test_asterisco_sobre_tabla_acotada():
    with pytest.raises(SQLNoPermitido, match="Columnas no permitidas"):
        prod("SELECT * FROM public.panacea_sales_v2")


def test_count_asterisco_permitido():
    prod("SELECT count(*) FROM public.panacea_sales_v2 WHERE operation_date > '2026-01-01'")


def test_columna_acotada_dentro_de_cte():
    with pytest.raises(SQLNoPermitido, match="customer"):
        prod("WITH t AS (SELECT customer AS c FROM public.panacea_sales_v2) SELECT c FROM t")


def test_columna_inexistente():
    with pytest.raises(SQLNoPermitido, match="no válida"):
        prod("SELECT inventada FROM public.panacea_sales_v2")


def test_falta_esquema_de_columnas():
    with pytest.raises(ValueError, match="esquema de columnas"):
        validar_sql("SELECT product FROM public.panacea_sales_v2", PERFIL_PRODUCCION, None)


# ------------------------------------------------------------ consultas reales del proyecto
def _consultas_reales():
    sqls = []
    for f in [*sorted((RAIZ / "trabajo/scripts").glob("*.py")), RAIZ / "plan_ventas/scripts/kpis_semana.py"]:
        texto = f.read_text()
        for m in re.finditer(r'(f?)"""(.*?)"""', texto, re.S):
            sql = m.group(2)
            if m.group(1):  # f-string: solo se admite el marcador de tabla {T}
                sql = sql.replace("{T}", VENTAS)
            if re.match(r"\s*(select|with)\b", sql, re.I) and "{" not in sql:
                sqls.append(pytest.param(sql, id=f"{f.name}:{texto[:m.start()].count(chr(10)) + 1}"))
    return sqls


@pytest.mark.parametrize("sql", _consultas_reales())
def test_consultas_reales_pasan(sql):
    """Sin lista de tablas (servidor MCP local) todas pasan; con el perfil ventas, las que solo usan ventas."""
    validar_sql(sql)
    try:
        validar_sql(sql, PERFIL_VENTAS)
    except SQLNoPermitido as e:
        assert "Tablas no permitidas" in str(e) and "costos_" in str(e)
