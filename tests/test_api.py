import json
import shutil
import time

import jwt
import pytest
import yaml
from fastapi.testclient import TestClient

from agent.almacen import AlmacenMemoria
from agent.contexto import ContextoPerfil
from agent.profiles import cargar_configuracion
from api.index import Servicios, app
from tests.conftest import RAIZ
from tests.fakes import ClienteFalso, mensaje, texto, tool_use

SECRETO = "s" * 40


def token(email, segundos=3600):
    return jwt.encode({"email": email, "exp": int(time.time()) + segundos}, SECRETO, algorithm="HS256")


class ServiciosPrueba(Servicios):
    def __init__(self, config, almacen, cliente):
        self.__dict__.update(config=config, almacen=almacen, cliente=cliente)
        self.fallbacks = True

    def contexto(self, perfil):
        return ContextoPerfil(engine=None, tabla=perfil.tabla_principal)


@pytest.fixture
def entorno(tmp_path, monkeypatch, herramientas):
    monkeypatch.setenv("AUTH_SECRET", SECRETO)
    for d in ("config", "prompts"):
        shutil.copytree(RAIZ / d, tmp_path / d)
    perfil = yaml.safe_load((tmp_path / "config/perfiles/ventas.yaml").read_text())
    perfil["herramientas"] = ["resumen_ventas", "consultar", "solicitar_aclaraciones", "generar_artifact",
                              "editar_artifact"]
    (tmp_path / "config/perfiles/ventas.yaml").write_text(yaml.safe_dump(perfil))
    otro = dict(perfil, id="produccion", nombre="Producción")
    (tmp_path / "config/perfiles/produccion.yaml").write_text(yaml.safe_dump(otro))
    (tmp_path / "config/usuarios.yaml").write_text(yaml.safe_dump({"tope_mensual_usd": 50, "usuarios": [
        {"email": "ana@example.com", "perfiles": ["ventas"]},
        {"email": "planta@example.com", "perfiles": ["produccion"]},
        {"email": "jefa@example.com", "perfiles": [], "admin": True}]}))
    cliente = ClienteFalso()
    srv = ServiciosPrueba(cargar_configuracion(tmp_path), AlmacenMemoria(), cliente)
    app.state.servicios = srv
    yield TestClient(app), srv, cliente
    app.state.servicios = Servicios()


def h(email):
    return {"Authorization": f"Bearer {token(email)}"}


def eventos_sse(r):
    out = []
    for bloque in r.text.strip().split("\n\n"):
        lineas = dict(l.split(": ", 1) for l in bloque.splitlines())
        out.append(json.loads(lineas["data"]))
    return out


def test_sin_sesion(entorno):
    c, _, _ = entorno
    assert c.get("/api/profiles").status_code == 401
    assert c.get("/api/profiles", headers={"Authorization": "Bearer basura"}).status_code == 401
    vencido = {"Authorization": f"Bearer {token('ana@example.com', -120)}"}
    assert c.get("/api/profiles", headers=vencido).status_code == 401


def test_cookie_de_auth_js(entorno):
    c, _, _ = entorno
    c.cookies.set("__Secure-authjs.session-token", token("ana@example.com"))
    assert c.get("/api/profiles").status_code == 200


def test_usuario_no_registrado(entorno):
    c, _, _ = entorno
    r = c.get("/api/profiles", headers=h("intruso@example.com"))
    assert r.status_code == 403


def test_perfiles(entorno):
    c, _, _ = entorno
    assert [p["id"] for p in c.get("/api/profiles", headers=h("ana@example.com")).json()["perfiles"]] == ["ventas"]
    jefa = c.get("/api/profiles", headers=h("jefa@example.com")).json()
    assert jefa["usuario"]["admin"] and {p["id"] for p in jefa["perfiles"]} == {"ventas", "produccion"}


def test_perfil_no_asignado_no_invoca_al_modelo(entorno):
    c, _, cliente = entorno
    r = c.post("/api/chat", headers=h("planta@example.com"), json={"perfil": "ventas", "mensaje": "Hola"})
    assert r.status_code == 403 and cliente.llamadas == []


def test_chat_completo_y_historial(entorno):
    c, srv, cliente = entorno
    cliente.guion += [mensaje(tool_use("t1", "resumen_ventas", {"desde": "2026-10-01"}), stop="tool_use"),
                      mensaje(texto("Octubre: $100."))]
    r = c.post("/api/chat", headers=h("ana@example.com"), json={"perfil": "ventas", "mensaje": "Ventas de octubre"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = eventos_sse(r)
    assert [e["tipo"] for e in ev] == ["conversacion", "herramienta_inicio", "herramienta_fin", "texto", "fin"]
    cid = ev[0]["id"]
    assert srv.almacen.conversacion(cid).titulo == "Ventas de octubre"
    assert "Analista comercial de Panacea" in cliente.llamadas[0]["system"][0]["text"]

    hist = c.get(f"/api/conversaciones/{cid}", headers=h("ana@example.com")).json()
    assert [i["tipo"] for i in hist["items"]] == ["usuario", "paso", "agente"]
    assert hist["items"][1]["nombre"] == "resumen_ventas" and hist["items"][1]["es_error"] is False
    assert [x["id"] for x in c.get("/api/conversaciones", headers=h("ana@example.com")).json()["conversaciones"]] == [cid]

    # Continuar la misma conversación.
    cliente.guion.append(mensaje(texto("Sí.")))
    r2 = c.post("/api/chat", headers=h("ana@example.com"), json={"conversacion_id": cid, "mensaje": "¿Seguro?"})
    assert eventos_sse(r2)[-1]["tipo"] == "fin" and len(cliente.llamadas[-1]["messages"]) == 5


def test_conversacion_ajena(entorno):
    c, srv, _ = entorno
    conv = srv.almacen.crear_conversacion("ana@example.com", "ventas", "privada")
    assert c.get(f"/api/conversaciones/{conv.id}", headers=h("planta@example.com")).status_code == 404
    assert c.post("/api/chat", headers=h("planta@example.com"),
                  json={"conversacion_id": conv.id, "mensaje": "x"}).status_code == 404
    assert c.get(f"/api/conversaciones/{conv.id}", headers=h("jefa@example.com")).status_code == 200
    todas = c.get("/api/conversaciones?todas=true", headers=h("jefa@example.com")).json()["conversaciones"]
    assert [x["id"] for x in todas] == [conv.id]


def test_turno_en_curso(entorno):
    c, srv, _ = entorno
    conv = srv.almacen.crear_conversacion("ana@example.com", "ventas", "x")
    srv.almacen.tomar_turno(conv.id)
    r = c.post("/api/chat", headers=h("ana@example.com"), json={"conversacion_id": conv.id, "mensaje": "x"})
    assert r.status_code == 409


def test_pedido_incompleto(entorno):
    c, _, _ = entorno
    assert c.post("/api/chat", headers=h("ana@example.com"), json={"perfil": "ventas"}).status_code == 400
