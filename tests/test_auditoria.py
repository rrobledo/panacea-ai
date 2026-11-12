"""Auditoría de SQL, uso de tokens, presupuesto por turno, tope mensual y tablero de uso."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine

from agent.almacen import ZONA, RegistroUso
from agent.contexto import ContextoPerfil
from agent.costos import costo_usd, precios
from agent.loop import Agente
from tests.conftest import perfil_prueba
from tests.fakes import ClienteFalso, mensaje, texto, tool_use
from tests.test_api import entorno, eventos_sse, h  # noqa: F401  (fixture)


def agente(almacen, cliente, ctx, **perfil):
    p = perfil_prueba(**perfil)
    conv = almacen.crear_conversacion("ana@example.com", p.id, "prueba")
    return Agente(cliente, almacen, p, ctx, "Sos un analista."), conv.id


def correr(ag, cid, msg):
    ag.almacen.tomar_turno(cid)
    return list(ag.turno(cid, msg))


def mes_actual():
    ahora = datetime.now(ZONA)
    return datetime(ahora.year, ahora.month, 1, tzinfo=ZONA), datetime.now(timezone.utc) + timedelta(days=1)


# ---------------------------------------------------------------- costos
def test_costos():
    assert costo_usd("claude-opus-5-5", 1_000_000, 0, 0, 0) == 4.0
    assert costo_usd("claude-opus-5-5", 0, 1_000_000, 1_000_000, 1_000_000) == 20.0 + 0.20 + 5.0
    assert precios("claude-opus-5") == (5.0, 25.0, 0.50) and precios("claude-opus-5-5-20261101")[0] == 4.0
    assert precios("modelo-desconocido") == precios("claude-fable-5-2")  # nunca subestima


# ---------------------------------------------------------------- 8.1 auditoría de SQL
def test_consulta_rechazada_queda_auditada(almacen, ctx):
    cliente = ClienteFalso(
        mensaje(tool_use("t1", "consultar", {"sql": "DELETE FROM public.panacea_sales_v2"}), stop="tool_use"),
        mensaje(texto("No puedo borrar.")))
    ag, cid = agente(almacen, cliente, ctx, herramientas=["consultar"])
    correr(ag, cid, "Borrá todo")
    filas = almacen.uso_agrupado(*mes_actual(), "usuario")
    assert filas[0]["clave"] == "ana@example.com" and filas[0]["consultas"] == 1
    assert filas[0]["consultas_con_error"] == 1
    if hasattr(almacen, "_consultas"):
        _, r = almacen._consultas[0]
        assert (r.herramienta, r.sql, r.conversacion_id, r.perfil) == (
            "consultar", "DELETE FROM public.panacea_sales_v2", cid, "ventas")
        assert r.error.startswith("rechazada: Solo se permiten consultas SELECT")


def test_consultas_ejecutadas_quedan_auditadas(almacen, url_postgres):
    """consultar contra un Postgres real (el de prueba): una consulta que anda y una que falla."""
    ctx = ContextoPerfil(engine=create_engine(url_postgres), tabla="public.panacea_sales_v2")
    cliente = ClienteFalso(
        mensaje(tool_use("t1", "consultar", {"sql": "SELECT generate_series(1, 3) AS n"}),
                tool_use("t2", "consultar", {"sql": "SELECT * FROM public.no_existe"}), stop="tool_use"),
        mensaje(texto("Listo.")))
    ag, cid = agente(almacen, cliente, ctx, herramientas=["consultar"])
    correr(ag, cid, "Probá")
    f = almacen.uso_agrupado(*mes_actual(), "perfil")[0]
    assert (f["clave"], f["consultas"], f["consultas_con_error"]) == ("ventas", 2, 1)
    if hasattr(almacen, "_consultas"):
        ok, mal = (r for _, r in almacen._consultas)
        assert ok.filas == 3 and ok.error is None and ok.duracion_ms >= 0
        assert mal.filas is None and "no_existe" in mal.error and "postgresql" not in mal.error


def test_auditoria_que_falla_no_corta_la_herramienta(ctx):
    def explota(**_):
        raise RuntimeError("base de auditoría caída")
    from dataclasses import replace
    from agent.tools.generic import consultar
    r = json.loads(consultar(replace(ctx, auditor=explota), "DROP TABLE x"))
    assert "error" in r and "Solo se permiten" in r["error"]


# ---------------------------------------------------------------- 8.2 uso de tokens
def test_uso_por_llamada(almacen, herramientas, ctx):
    cliente = ClienteFalso(*[mensaje(tool_use(f"t{i}", "resumen_ventas", {}), stop="tool_use", entrada=1000,
                                     salida=100, cache_lectura=5000) for i in range(3)],
                           mensaje(texto("Fin."), modelo="claude-sonnet-5-5"))
    ag, cid = agente(almacen, cliente, ctx)
    ev = correr(ag, cid, "Analizá")
    assert ev[-1]["uso"]["llamadas"] == 4
    esperado = 3 * costo_usd("claude-opus-5-5", 1000, 100, 5000, 0) + costo_usd("claude-sonnet-5-5", 1000, 100, 0, 0)
    assert ev[-1]["uso"]["costo_usd"] == pytest.approx(esperado)
    f = almacen.uso_agrupado(*mes_actual(), "usuario")[0]
    assert (f["llamadas"], f["entrada"], f["salida"], f["cache_lectura"]) == (4, 4000, 400, 15000)
    assert f["costo_usd"] == pytest.approx(esperado)
    assert almacen.costo_desde("ana@example.com", mes_actual()[0]) == pytest.approx(esperado)
    assert almacen.costo_desde("otro@example.com", mes_actual()[0]) == 0


def test_uso_agrupado_por_mes(almacen):
    viejo = datetime(2026, 9, 15, 12, tzinfo=ZONA)
    for creado, costo in ((viejo, 1.5), (viejo, 0.5), (datetime(2026, 10, 31, 22, tzinfo=ZONA), 2.0)):
        almacen.registrar_uso(RegistroUso("ana@example.com", "ventas", None, "claude-opus-5-5", 1, 1, 0, 0, costo,
                                          creado))
    # 31/10 22:00 en Córdoba es 1/11 en UTC: cuenta en octubre.
    filas = almacen.uso_agrupado(datetime(2026, 1, 1, tzinfo=ZONA), datetime(2027, 1, 1, tzinfo=ZONA), "mes")
    assert {f["clave"]: f["costo_usd"] for f in filas} == {"2026-09": 2.0, "2026-10": 2.0}


# ---------------------------------------------------------------- 8.3 presupuesto por turno
def test_presupuesto_por_turno(almacen, herramientas, ctx):
    cliente = ClienteFalso(
        mensaje(tool_use("t1", "resumen_ventas", {}), stop="tool_use", entrada=6000, salida=100),
        mensaje(tool_use("t2", "resumen_ventas", {}), stop="tool_use", entrada=6000, salida=100),
        mensaje(texto("Con lo que tengo: ...")))
    ag, cid = agente(almacen, cliente, ctx, limites={"presupuesto_tokens_por_turno": 10_000})
    ev = correr(ag, cid, "Analizá todo")
    assert len(herramientas.llamadas) == 1  # t2 no se ejecutó
    avisos = [e["mensaje"] for e in ev if e["tipo"] == "aviso"]
    assert avisos == ["Se alcanzó el presupuesto de 10.000 tokens del turno; el agente responde con lo que tiene."]
    final = cliente.llamadas[-1]
    assert final["tool_choice"] == {"type": "none"}
    ultimo = final["messages"][-1]["content"]
    assert ultimo[0]["tool_use_id"] == "t2" and ultimo[0]["is_error"]
    assert ultimo[1]["text"].startswith("[Sistema] Se alcanzó el presupuesto")
    assert ev[-1]["tipo"] == "fin"


def test_presupuesto_no_corta_la_respuesta_final(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(texto("Respuesta larga."), entrada=50_000))
    ag, cid = agente(almacen, cliente, ctx, limites={"presupuesto_tokens_por_turno": 10_000})
    ev = correr(ag, cid, "Hola")
    assert [e["tipo"] for e in ev] == ["texto", "fin"]


# ---------------------------------------------------------------- 8.4 tope mensual
def _gastar(srv, email, usd):
    srv.almacen.registrar_uso(RegistroUso(email, "ventas", None, "claude-opus-5-5", 0, 0, 0, 0, usd))


def test_tope_mensual(entorno):
    c, srv, cliente = entorno
    assert srv.config.tope_mensual_usd == 50  # el general de config/usuarios.yaml
    _gastar(srv, "ana@example.com", 49.99)
    cliente.guion.append(mensaje(texto("Hola.")))
    assert c.post("/api/chat", headers=h("ana@example.com"), json={"perfil": "ventas", "mensaje": "x"}).status_code == 200
    _gastar(srv, "ana@example.com", 0.01)
    r = c.post("/api/chat", headers=h("ana@example.com"), json={"perfil": "ventas", "mensaje": "y"})
    assert r.status_code == 429 and "US$ 50.00" in r.json()["detail"] and "administrador" in r.json()["detail"]
    assert len(cliente.llamadas) == 1
    r = c.post("/api/clarify", headers=h("ana@example.com"),
               json={"conversacion_id": "x", "tool_use_id": "c1", "decision": "aprobar"})
    assert r.status_code == 404  # la conversación se controla antes que el tope
    # Un gasto del mes anterior no cuenta.
    _gastar(srv, "planta@example.com", 0)
    srv.almacen.registrar_uso(RegistroUso("planta@example.com", "produccion", None, "claude-opus-5-5", 0, 0, 0, 0,
                                          500, datetime(2020, 1, 1, tzinfo=ZONA)))
    cliente.guion.append(mensaje(texto("Hola.")))
    assert c.post("/api/chat", headers=h("planta@example.com"),
                  json={"perfil": "produccion", "mensaje": "x"}).status_code == 200


def test_tope_por_usuario(entorno):
    from dataclasses import replace
    c, srv, cliente = entorno
    jefa = srv.config.usuarios["jefa@example.com"]
    srv.config.usuarios["jefa@example.com"] = jefa.model_copy(update={"tope_mensual_usd": 200})
    _gastar(srv, "jefa@example.com", 100)
    cliente.guion.append(mensaje(texto("Hola.")))
    assert c.post("/api/chat", headers=h("jefa@example.com"), json={"perfil": "ventas", "mensaje": "x"}).status_code == 200
    srv.__dict__["config"] = replace(srv.config, tope_mensual_usd=None)
    _gastar(srv, "ana@example.com", 10_000)
    cliente.guion.append(mensaje(texto("Hola.")))
    assert c.post("/api/chat", headers=h("ana@example.com"), json={"perfil": "ventas", "mensaje": "x"}).status_code == 200


# ---------------------------------------------------------------- 8.5 tablero de uso
def test_tablero_de_uso(entorno):
    c, srv, _ = entorno
    assert c.get("/api/admin/uso", headers=h("ana@example.com")).status_code == 403
    assert c.get("/api/admin/uso").status_code == 401
    _gastar(srv, "ana@example.com", 3)
    _gastar(srv, "planta@example.com", 1)
    srv.almacen.registrar_uso(RegistroUso("ana@example.com", "ventas", None, "claude-opus-5-5", 0, 0, 0, 0, 7,
                                          datetime(2026, 1, 10, tzinfo=ZONA)))
    d = c.get("/api/admin/uso", headers=h("jefa@example.com")).json()
    assert d["mes"] == datetime.now(ZONA).strftime("%Y-%m")
    assert [(f["clave"], f["costo_usd"], f["tope_usd"]) for f in d["por_usuario"]] == [
        ("ana@example.com", 3, 50), ("planta@example.com", 1, 50)]
    assert {f["clave"] for f in d["por_perfil"]} == {"ventas"}
    assert d["historial"][-1]["clave"] == d["mes"]
    enero = c.get("/api/admin/uso?mes=2026-01", headers=h("jefa@example.com")).json()
    assert [(f["clave"], f["costo_usd"]) for f in enero["por_usuario"]] == [("ana@example.com", 7)]
    assert [f["clave"] for f in enero["historial"]] == ["2026-01"]
    assert c.get("/api/admin/uso?mes=2026-13", headers=h("jefa@example.com")).status_code == 422
