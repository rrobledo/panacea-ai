import shutil
from pathlib import Path

import pytest
import yaml

from agent.profiles import ErrorConfiguracion, cargar_configuracion, contexto_para
from tests.conftest import RAIZ


def test_configuracion_real():
    c = cargar_configuracion()
    p = c.perfiles["ventas"]
    assert p.modelo == "claude-opus-5-5" and p.tabla_principal == "public.panacea_sales_v2"
    assert p.reglas.excluir_clientes_en_analisis == [999, 0, 888, 777]
    prompt = p.system_prompt()
    assert "Analista comercial de Panacea" in prompt and "| document_id |" in prompt
    assert "`public.panacea_sales_v2`" in prompt


@pytest.fixture
def raiz(tmp_path):
    """Copia de config/ y prompts/ para modificar sin tocar el repo."""
    for d in ("config", "prompts"):
        shutil.copytree(RAIZ / d, tmp_path / d)
    return tmp_path


def editar(raiz: Path, archivo: str, cambio):
    ruta = raiz / archivo
    datos = yaml.safe_load(ruta.read_text())
    cambio(datos)
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True))


def falla(raiz, *fragmentos):
    with pytest.raises(ErrorConfiguracion) as e:
        cargar_configuracion(raiz)
    for f in fragmentos:
        assert f in str(e.value), str(e.value)


def test_falta_tablas(raiz):
    editar(raiz, "config/perfiles/ventas.yaml", lambda d: d["base_datos"].pop("tablas"))
    falla(raiz, "ventas.yaml", "base_datos.tablas")


def test_herramienta_inexistente(raiz):
    editar(raiz, "config/perfiles/ventas.yaml", lambda d: d["herramientas"].append("borrar_todo"))
    falla(raiz, "ventas.yaml", "herramientas", "borrar_todo")


def test_campo_desconocido(raiz):
    editar(raiz, "config/perfiles/ventas.yaml", lambda d: d.update(modleo="x"))
    falla(raiz, "ventas.yaml", "modleo")


def test_prompt_inexistente(raiz):
    editar(raiz, "config/perfiles/ventas.yaml", lambda d: d.update(prompt="prompts/no.md"))
    falla(raiz, "ventas.yaml", "prompt", "prompts/no.md")


def test_tabla_mal_formada(raiz):
    editar(raiz, "config/perfiles/ventas.yaml", lambda d: d["base_datos"]["tablas"][0].update(nombre="ventas;drop"))
    falla(raiz, "base_datos.tablas.0.nombre")


def test_herramientas_de_ventas_con_tabla_acotada(raiz):
    editar(raiz, "config/perfiles/ventas.yaml",
           lambda d: d["base_datos"]["tablas"][0].update(columnas=["operation_date", "count"]))
    falla(raiz, "necesitan todas las columnas")


def test_perfil_nuevo_sin_codigo(raiz):
    (raiz / "prompts/produccion.md").write_text("Sos planificador de producción.")
    (raiz / "config/perfiles/produccion.yaml").write_text(yaml.safe_dump({
        "id": "produccion", "nombre": "Planificación", "prompt": "prompts/produccion.md",
        "base_datos": {"credencial_env": "DB_URL_PRODUCCION", "tablas": [
            {"nombre": "public.costos_costos"},
            {"nombre": "public.panacea_sales_v2", "columnas": ["operation_date", "product_id", "product", "count"]}]},
        "herramientas": ["describir_tabla", "consultar"]}))
    editar(raiz, "config/usuarios.yaml", lambda d: d.update(usuarios=[
        {"email": "Planta@Example.com", "perfiles": ["produccion"]},
        {"email": "jefa@example.com", "perfiles": ["ventas"], "admin": True}]))
    c = cargar_configuracion(raiz)
    planta = c.usuario("planta@example.com ")
    assert [p.id for p in c.perfiles_de(planta)] == ["produccion"]
    assert c.puede_usar(planta, "produccion") and not c.puede_usar(planta, "ventas")
    assert {p.id for p in c.perfiles_de(c.usuario("jefa@example.com"))} == {"ventas", "produccion"}
    assert c.usuario("nadie@example.com") is None
    p = c.perfiles["produccion"]
    assert p.tablas_permitidas()["public.panacea_sales_v2"] == frozenset({"operation_date", "product_id",
                                                                          "product", "count"})
    assert "solo las columnas: operation_date" in p.system_prompt(raiz)


def test_usuario_con_perfil_inexistente(raiz):
    editar(raiz, "config/usuarios.yaml",
           lambda d: d.update(usuarios=[{"email": "a@example.com", "perfiles": ["compras"]}]))
    falla(raiz, "usuarios.yaml", "compras")


def test_email_repetido(raiz):
    editar(raiz, "config/usuarios.yaml", lambda d: d.update(usuarios=[
        {"email": "a@example.com", "perfiles": ["ventas"]}, {"email": "A@example.com", "perfiles": []}]))
    falla(raiz, "email repetido")


def test_contexto_del_perfil():
    p = cargar_configuracion().perfiles["ventas"]
    ctx = contexto_para(p, engine=object())  # sin tablas acotadas no consulta la base
    assert ctx.tabla == "public.panacea_sales_v2"
    assert ctx.tablas_permitidas == {"public.panacea_sales_v2": None}
    assert ctx.excluir_clientes_ids == (999, 0, 888, 777)
    assert (ctx.max_filas, ctx.timeout_sql_seg) == (500, 60)


def test_falta_credencial(monkeypatch):
    from agent import profiles
    monkeypatch.delenv("DB_URL_VENTAS", raising=False)
    monkeypatch.setattr(profiles, "_engines", {})
    with pytest.raises(ErrorConfiguracion, match="DB_URL_VENTAS"):
        contexto_para(cargar_configuracion().perfiles["ventas"])
