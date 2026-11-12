import json

import anthropic
import httpx
import pytest

from agent.almacen import ConversacionOcupada, Paso
from agent.loop import Agente
from tests.conftest import perfil_prueba
from tests.fakes import ClienteFalso, Falla, mensaje, pensamiento, texto, tool_use


def correr(agente, almacen, conv_id, msg):
    almacen.tomar_turno(conv_id)
    return list(agente.turno(conv_id, msg))


def tipos(eventos):
    return [e["tipo"] for e in eventos]


def nuevo(almacen, cliente, ctx, **perfil):
    p = perfil_prueba(**perfil)
    conv = almacen.crear_conversacion("ana@example.com", p.id, "prueba")
    return Agente(cliente, almacen, p, ctx, "Sos un analista."), conv.id


def es_prefijo(corto, largo):
    return largo[:len(corto)] == corto


# ---------------------------------------------------------------- flujo normal
def test_pasos_texto_y_parametros(almacen, herramientas, ctx):
    cliente = ClienteFalso(
        mensaje(pensamiento(), tool_use("t1", "resumen_ventas", {"desde": "2026-10-01"}), stop="tool_use"),
        mensaje(pensamiento("f2"), texto("Octubre vendió "), texto("$100."), stop="end_turn"),
    )
    agente, cid = nuevo(almacen, cliente, ctx)
    ev = correr(agente, almacen, cid, "¿Cuánto vendimos en octubre?")

    assert tipos(ev) == ["herramienta_inicio", "herramienta_fin", "texto", "texto", "fin"]
    assert ev[1]["nombre"] == "resumen_ventas" and ev[1]["es_error"] is False and ev[1]["filas"] == 1
    assert ev[-1]["uso"] == {"entrada": 2000, "salida": 200, "cache_lectura": 0, "cache_escritura": 0,
                             "llamadas": 2, "costo_usd": 0.012}
    assert herramientas.llamadas == [("resumen_ventas", {"desde": "2026-10-01", "hasta": None})]

    p1, p2 = cliente.llamadas
    assert p1["model"] == "claude-opus-5-5"
    assert p1["thinking"] == {"type": "adaptive"} and p1["output_config"] == {"effort": "medium"}
    assert p1["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert p1["cache_control"] == {"type": "ephemeral"}
    assert [t["name"] for t in p1["tools"]] == ["resumen_ventas", "consultar"]
    assert all(t["eager_input_streaming"] for t in p1["tools"])
    assert p1["tools"][-1]["cache_control"] == {"type": "ephemeral"} and "cache_control" not in p1["tools"][0]
    assert p1["fallbacks"] == "default" and p1["betas"] == ["server-side-fallback-2026-07-01"]
    assert "tool_choice" not in p1
    # Historial solo-agregado: la segunda llamada extiende la primera sin cambiar nada.
    assert es_prefijo(p1["messages"], p2["messages"])
    asistente, resultado = p2["messages"][1], p2["messages"][2]
    assert asistente["content"][0] == {"type": "thinking", "thinking": "", "signature": "firma-1"}
    assert resultado["content"][0]["tool_use_id"] == "t1" and "is_error" not in resultado["content"][0]

    guardado = almacen.mensajes(cid)
    assert [m["role"] for m in guardado] == ["user", "assistant", "user", "assistant"]
    assert guardado[:3] == p2["messages"]
    assert almacen.pasos(cid)["t1"].nombre == "resumen_ventas"
    assert almacen.conversacion(cid).estado == "lista"


def test_segundo_turno_extiende_el_historial(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(texto("Hola")), mensaje(texto("Sí")))
    agente, cid = nuevo(almacen, cliente, ctx)
    correr(agente, almacen, cid, "Hola")
    correr(agente, almacen, cid, "¿Seguís?")
    p1, p2 = cliente.llamadas
    assert es_prefijo(p1["messages"], p2["messages"]) and len(p2["messages"]) == 3


# ---------------------------------------------------------------- errores de herramientas
def test_error_de_herramienta_se_envia_como_is_error(almacen, herramientas, ctx):
    herramientas.falla_consultar = RuntimeError("relation \"x\" does not exist\nLINE 1: ...")
    cliente = ClienteFalso(mensaje(tool_use("t1", "consultar", {"sql": "SELECT * FROM x"}), stop="tool_use"),
                           mensaje(texto("No existe esa tabla.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    ev = correr(agente, almacen, cid, "Consultá x")
    assert ev[1]["es_error"] is True and ev[-1]["tipo"] == "fin"
    r = cliente.llamadas[1]["messages"][-1]["content"][0]
    assert r["is_error"] is True and json.loads(r["content"]) == {"error": 'relation "x" does not exist'}


def test_resultado_con_error_se_marca(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("t1", "consultar", {"sql": "SELECT * FROM public.costos_costos"}),
                                   stop="tool_use"), mensaje(texto("No tengo acceso.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    correr(agente, almacen, cid, "Costos")
    assert cliente.llamadas[1]["messages"][-1]["content"][0]["is_error"] is True


def test_argumentos_invalidos_no_ejecutan(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("t1", "resumen_ventas", {"desde": "2026-01-01", "inventado": 1}),
                                   stop="tool_use"), mensaje(texto("Perdón.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    correr(agente, almacen, cid, "Ventas")
    assert herramientas.llamadas == []
    r = cliente.llamadas[1]["messages"][-1]["content"][0]
    assert r["is_error"] and "inventado" in json.loads(r["content"])["detalle"]


def test_herramienta_fuera_del_perfil(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("t1", "clientes_inactivos", {}), stop="tool_use"),
                           mensaje(texto("No puedo.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    correr(agente, almacen, cid, "Inactivos")
    r = cliente.llamadas[1]["messages"][-1]["content"][0]
    assert r["is_error"] and "no está disponible" in r["content"]


# ---------------------------------------------------------------- tope de herramientas
def test_tope_de_herramientas(almacen, herramientas, ctx):
    usos = [tool_use(f"t{i}", "consultar", {"sql": f"SELECT {i}"}) for i in range(3)]
    cliente = ClienteFalso(mensaje(*usos, stop="tool_use"), mensaje(texto("Con lo que tengo: ...")))
    agente, cid = nuevo(almacen, cliente, ctx, limites={"max_herramientas_por_turno": 2})
    ev = correr(agente, almacen, cid, "Muchas consultas")

    assert len(herramientas.llamadas) == 2
    assert "aviso" in tipos(ev) and ev[-1]["tipo"] == "fin"
    resultados = cliente.llamadas[1]["messages"][-1]["content"]
    assert [r.get("is_error", False) for r in resultados[:3]] == [False, False, True]
    assert resultados[3]["type"] == "text" and "límite de 2" in resultados[3]["text"]
    assert cliente.llamadas[1]["tool_choice"] == {"type": "none"}


# ---------------------------------------------------------------- reanudación
def test_reanuda_turno_cortado_sin_repetir_herramientas(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(texto("Listo, retomé.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    # Estado que deja una función cortada: asistente con 2 tool_use, 1 resultado guardado, sin tool_result.
    almacen.agregar_mensaje(cid, "user", [{"type": "text", "text": "Dos consultas"}])
    almacen.agregar_mensaje(cid, "assistant", [
        {"type": "tool_use", "id": "a", "name": "consultar", "input": {"sql": "SELECT 1"}},
        {"type": "tool_use", "id": "b", "name": "consultar", "input": {"sql": "SELECT 2"}}])
    almacen.guardar_paso(cid, Paso("a", "consultar", {"sql": "SELECT 1"}, '{"filas": [[1]]}', False, 12))

    ev = correr(agente, almacen, cid, None)
    fines = [e for e in ev if e["tipo"] == "herramienta_fin"]
    assert [(e["id"], e["reutilizado"]) for e in fines] == [("a", True), ("b", False)]
    assert herramientas.llamadas == [("consultar", {"sql": "SELECT 2"})]
    msgs = cliente.llamadas[0]["messages"]
    assert [r["tool_use_id"] for r in msgs[-1]["content"]] == ["a", "b"]
    assert msgs[-1]["content"][0]["content"] == '{"filas": [[1]]}'


def test_mensaje_nuevo_con_tool_use_pendiente(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(texto("Ok.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    almacen.agregar_mensaje(cid, "user", [{"type": "text", "text": "Una"}])
    almacen.agregar_mensaje(cid, "assistant", [{"type": "tool_use", "id": "a", "name": "consultar",
                                                "input": {"sql": "SELECT 1"}}])
    correr(agente, almacen, cid, "¿Y ahora?")
    roles = [(m["role"], m["content"][0]["type"]) for m in cliente.llamadas[0]["messages"]]
    assert roles == [("user", "text"), ("assistant", "tool_use"), ("user", "tool_result"), ("user", "text")]


def test_sin_mensaje_y_turno_terminado_no_llama_al_modelo(almacen, herramientas, ctx):
    cliente = ClienteFalso()
    agente, cid = nuevo(almacen, cliente, ctx)
    almacen.agregar_mensaje(cid, "user", [{"type": "text", "text": "Hola"}])
    almacen.agregar_mensaje(cid, "assistant", [{"type": "text", "text": "Hola"}])
    ev = correr(agente, almacen, cid, None)
    assert ev == [{"tipo": "fin", "stop_reason": "sin_cambios", "uso": ev[0]["uso"]}] and not cliente.llamadas


# ---------------------------------------------------------------- motivos de corte
def test_rechazo(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("t1", "consultar", {"sql": "SEL"}), stop="refusal"))
    agente, cid = nuevo(almacen, cliente, ctx)
    ev = correr(agente, almacen, cid, "Algo")
    assert "error" in tipos(ev) and herramientas.llamadas == []
    ultimo = almacen.mensajes(cid)[-1]
    assert ultimo["role"] == "user" and ultimo["content"][0]["is_error"] is True  # sin tool_use huérfano


def test_max_tokens_con_tool_use_no_ejecuta(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("t1", "consultar", {"sql": "SELECT"}), stop="max_tokens"),
                           mensaje(tool_use("t2", "consultar", {"sql": "SELECT 1"}), stop="tool_use"),
                           mensaje(texto("Listo.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    correr(agente, almacen, cid, "Algo")
    assert herramientas.llamadas == [("consultar", {"sql": "SELECT 1"})]
    assert "truncada" in cliente.llamadas[1]["messages"][-1]["content"][0]["content"]


def test_json_invalido_reintenta_y_avisa_reinicio(almacen, herramientas, ctx):
    cliente = ClienteFalso(Falla(ValueError("bad json"), texto_previo="Parcial"), mensaje(texto("Bien.")))
    agente, cid = nuevo(almacen, cliente, ctx)
    ev = correr(agente, almacen, cid, "Algo")
    assert tipos(ev) == ["texto", "reinicio", "texto", "fin"]
    assert len(cliente.llamadas) == 2


def test_error_de_api_libera_el_turno(almacen, herramientas, ctx):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.RateLimitError("limite", response=httpx.Response(429, request=req), body=None)
    cliente = ClienteFalso(Falla(err))
    agente, cid = nuevo(almacen, cliente, ctx)
    ev = correr(agente, almacen, cid, "Algo")
    assert tipos(ev) == ["error"] and "demasiados pedidos" in ev[0]["mensaje"]
    assert almacen.conversacion(cid).estado == "lista"
    assert [m["role"] for m in almacen.mensajes(cid)] == ["user"]  # nada a medias


def test_sin_fallbacks(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(texto("Hola")))
    p = perfil_prueba()
    conv = almacen.crear_conversacion("ana@example.com", p.id, "x")
    agente = Agente(cliente, almacen, p, ctx, "x", fallbacks=False)
    correr(agente, almacen, conv.id, "Hola")
    assert "fallbacks" not in cliente.llamadas[0] and "betas" not in cliente.llamadas[0]


# ---------------------------------------------------------------- turno exclusivo
def test_turno_ocupado(almacen):
    cid = almacen.crear_conversacion("ana@example.com", "ventas", "x").id
    almacen.tomar_turno(cid)
    with pytest.raises(ConversacionOcupada):
        almacen.tomar_turno(cid)
    almacen.soltar_turno(cid)
    almacen.tomar_turno(cid)
