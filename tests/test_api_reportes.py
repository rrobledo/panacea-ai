"""Endpoints de aclaraciones, artifacts y galería."""

import json

from agent.almacen import FiltroArtifacts
from agent.artifacts import CSP
from tests.fakes import mensaje, texto, tool_use
from tests.test_api import entorno, eventos_sse, h  # noqa: F401  (fixture)
from tests.test_reportes import BRIEF, CONTENIDO, PREGUNTAS, _artifact


def pausar(c, cliente, email="ana@example.com"):
    cliente.guion.append(mensaje(tool_use("c1", "solicitar_aclaraciones", {"brief": BRIEF, "preguntas": PREGUNTAS}),
                                 stop="tool_use"))
    ev = eventos_sse(c.post("/api/chat", headers=h(email), json={"perfil": "ventas", "mensaje": "Reporte"}))
    assert ev[-2]["tipo"] == "aclaraciones"
    return ev[0]["id"]


def test_aprobar_y_generar(entorno):
    c, srv, cliente = entorno
    cid = pausar(c, cliente)
    det = c.get(f"/api/conversaciones/{cid}", headers=h("ana@example.com")).json()
    assert det["conversacion"]["estado"] == "esperando_aclaracion"
    assert det["aclaracion_pendiente"]["tool_use_id"] == "c1" and det["aclaracion_pendiente"]["brief"] == BRIEF

    def generar(params):  # el brief_id recién existe al aprobar: se toma del tool_result
        brief_id = json.loads(params["messages"][-1]["content"][0]["content"])["brief_id"]
        return mensaje(tool_use("g1", "generar_artifact", {"brief_id": brief_id, **CONTENIDO}), stop="tool_use")

    cliente.guion += [generar, mensaje(texto("Listo."))]
    r = c.post("/api/clarify", headers=h("ana@example.com"),
               json={"conversacion_id": cid, "tool_use_id": "c1", "decision": "aprobar",
                     "respuestas": {"comparar": "septiembre 2026"}})
    assert r.status_code == 200
    ev = eventos_sse(r)
    assert ev[0]["tipo"] == "conversacion" and "artifact" in [e["tipo"] for e in ev] and ev[-1]["tipo"] == "fin"
    resultado = json.loads(cliente.llamadas[1]["messages"][-1]["content"][0]["content"])
    assert {x["id"]: x["respuesta"] for x in resultado["respuestas"]}["comparar"] == "septiembre 2026"

    det = c.get(f"/api/conversaciones/{cid}", headers=h("ana@example.com")).json()
    assert det["aclaracion_pendiente"] is None
    tipos = [i["tipo"] for i in det["items"]]
    assert tipos == ["usuario", "aclaraciones", "paso", "artifact", "agente"]
    assert det["items"][1]["respuesta"]["decision"] == "aprobado"
    art = det["items"][3]
    assert art["version"] == 1 and art["url"] == f"/artifacts/{art['id']}"

    # Responder dos veces la misma aclaración no vale.
    r = c.post("/api/clarify", headers=h("ana@example.com"),
               json={"conversacion_id": cid, "tool_use_id": "c1", "decision": "aprobar"})
    assert r.status_code == 409


def test_ajustar(entorno):
    c, _, cliente = entorno
    cid = pausar(c, cliente)
    base = {"conversacion_id": cid, "tool_use_id": "c1"}
    assert c.post("/api/clarify", headers=h("ana@example.com"), json={**base, "decision": "ajustar"}).status_code == 400
    assert c.post("/api/clarify", headers=h("ana@example.com"),
                  json={**base, "decision": "aprobar", "respuestas": {"nada": "x"}}).status_code == 400
    assert c.post("/api/clarify", headers=h("ana@example.com"),
                  json={**base, "tool_use_id": "otro", "decision": "aprobar"}).status_code == 409
    assert c.post("/api/clarify", headers=h("jefa@example.com"),
                  json={**base, "decision": "aprobar"}).status_code == 404
    assert cliente.llamadas[1:] == []

    cliente.guion.append(mensaje(tool_use("c2", "solicitar_aclaraciones", {"brief": {**BRIEF, "periodo": "semanal"}}),
                                 stop="tool_use"))
    ev = eventos_sse(c.post("/api/clarify", headers=h("ana@example.com"),
                            json={**base, "decision": "ajustar", "comentario": "Por semana"}))
    cuerpo = json.loads(cliente.llamadas[1]["messages"][-1]["content"][0]["content"])
    assert cuerpo["decision"] == "ajustar" and cuerpo["comentario"] == "Por semana" and "brief_id" not in cuerpo
    assert ev[-2]["tipo"] == "aclaraciones" and ev[-2]["tool_use_id"] == "c2"


def test_html_aislado(entorno):
    c, srv, _ = entorno
    a, _ = _artifact(srv.almacen, titulo="Estrategia comercial 2026")
    url = f"/api/artifacts/{a.id}/html"
    assert c.get(url).status_code == 401
    assert c.get(url, headers=h("planta@example.com")).status_code == 404
    r = c.get(url, headers=h("ana@example.com"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert r.headers["content-security-policy"] == CSP and "sandbox allow-scripts" in CSP
    assert "allow-same-origin" not in CSP and "Estrategia comercial 2026" in r.text
    assert c.get(url + "?version=2", headers=h("ana@example.com")).status_code == 404
    r = c.get(url + "?version=1&descargar=true", headers=h("jefa@example.com"))
    assert r.headers["content-disposition"] == 'attachment; filename="estrategia-comercial-2026_v1.html"'


def test_detalle_y_visibilidad(entorno):
    c, srv, _ = entorno
    a, conv = _artifact(srv.almacen, titulo="Ventas", autor="ana@example.com")
    b, _ = _artifact(srv.almacen, titulo="Planta", perfil="produccion", autor="planta@example.com")
    assert c.get(f"/api/artifacts/{a.id}", headers=h("planta@example.com")).status_code == 404
    assert c.get(f"/api/artifacts/{a.id}").status_code == 401
    d = c.get(f"/api/artifacts/{a.id}", headers=h("ana@example.com")).json()
    assert d["conversacion_id"] == conv.id and [v["version"] for v in d["versiones"]] == [1]
    assert "html" not in d["versiones"][0] and isinstance(d["versiones"][0]["datos_fuente"], list)
    assert c.get(f"/api/artifacts/{b.id}", headers=h("jefa@example.com")).json()["conversacion_id"] == \
        b.conversacion_id

    ids = lambda email, q="": [x["id"] for x in c.get(f"/api/artifacts{q}", headers=h(email)).json()["artifacts"]]
    assert ids("ana@example.com") == [a.id]
    assert ids("planta@example.com") == [b.id]
    assert ids("jefa@example.com") == [b.id, a.id]
    assert ids("jefa@example.com", "?perfil=ventas") == [a.id]
    assert ids("ana@example.com", "?perfil=produccion") == []  # filtrar no amplía la visibilidad
    assert ids("jefa@example.com", "?tipo=tabla") == []
    assert ids("jefa@example.com", "?q=plan&autor=PLANTA@example.com") == [b.id]
    assert c.get("/api/artifacts?desde=no-fecha", headers=h("ana@example.com")).status_code == 422


def test_fijar(entorno):
    c, srv, _ = entorno
    viejo, _ = _artifact(srv.almacen, titulo="Estrategia comercial 2026")
    _artifact(srv.almacen, titulo="Otro")
    assert c.post(f"/api/artifacts/{viejo.id}/fijar", headers=h("planta@example.com"),
                  json={"fijado": True}).status_code == 404
    assert c.post(f"/api/artifacts/{viejo.id}/fijar", headers=h("ana@example.com"),
                  json={"fijado": True}).json() == {"id": viejo.id, "fijado": True}
    lista = c.get("/api/artifacts", headers=h("ana@example.com")).json()["artifacts"]
    assert lista[0]["id"] == viejo.id and lista[0]["fijado"]
    assert srv.almacen.buscar_artifacts(FiltroArtifacts())[0].id == viejo.id
