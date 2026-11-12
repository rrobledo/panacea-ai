"""Aclaraciones, artifacts y galería a nivel loop y almacén (cliente de Anthropic simulado)."""

import copy
import json
import uuid
from datetime import datetime, timedelta

import pytest

from agent.almacen import ZONA, FiltroArtifacts
from agent.artifacts import ArtifactInvalido, componer, secretos_del_entorno, validar_html
from agent.loop import Agente, paso_aclaracion
from agent.tools import clarify, reportes
from tests.conftest import perfil_prueba
from tests.fakes import ClienteFalso, mensaje, texto, tool_use

HERRAMIENTAS = ["resumen_ventas", "consultar", "solicitar_aclaraciones", "generar_artifact", "editar_artifact"]

BRIEF = {"titulo": "Ventas de octubre 2026", "objetivo": "Ver cómo cerró octubre",
         "periodo": "octubre 2026 vs octubre 2025", "secciones": ["Resumen", "Por sucursal"],
         "metricas": ["ventas", "tickets"], "audiencia": "gerencia"}
PREGUNTAS = [{"id": "comparar", "texto": "¿Contra qué período comparo?", "tipo": "opcion",
              "opciones": ["octubre 2025", "septiembre 2026"], "recomendada": "octubre 2025"},
             {"id": "sucursales", "texto": "¿Qué sucursales?", "tipo": "multiple",
              "opciones": ["Centro", "Carlos Paz", "VGB"], "recomendada": ["Centro", "Carlos Paz"]}]
CONTENIDO = {
    "titulo": "Ventas de octubre 2026", "periodo": "01/10/2026 – 31/10/2026",
    "resumen": ["Las ventas crecieron **12%** interanual.", "Los tickets cayeron 3%."],
    "kpis": [{"etiqueta": "Ventas", "valor": 1234567.5, "formato": "moneda", "variacion": 0.12,
              "comparacion": "vs oct 2025"}],
    "secciones": [
        {"titulo": "Evolución", "texto": "Crecimos en pesos.\n\n- Centro +15%\n- VGB -2%",
         "grafico": {"tipo": "line", "etiquetas": ["sep", "oct", "nov"], "formato": "moneda", "series": [
             {"nombre": "Real", "datos": [1.0, 2.0, None]},
             {"nombre": "Proyección", "datos": [None, 2.0, 3.0], "rol": "proyeccion"},
             {"nombre": "Mínimo", "datos": [None, 2.0, 2.5], "rol": "banda_min"},
             {"nombre": "Máximo", "datos": [None, 2.0, 3.5], "rol": "banda_max"}]}},
        {"titulo": "Por sucursal", "tabla": {"columnas": ["Sucursal", "Ventas"], "filas": [["Centro", 100.5]],
                                             "formatos": ["texto", "moneda"]}}],
    "estrategias": [{"titulo": "Combo café + medialuna", "dato": "lift 1,8", "accion": "Armar el combo",
                     "impacto": "+3% de ticket", "kpi": "ticket promedio", "prioridad": "alta"}],
    "nota_metodologica": "Fuente: panacea_sales_v2. Excluye clientes de mostrador.",
}


def agente(almacen, cliente, ctx, perfil_id="ventas"):
    p = perfil_prueba(id=perfil_id, herramientas=HERRAMIENTAS)
    conv = almacen.crear_conversacion("ana@example.com", p.id, "prueba")
    return Agente(cliente, almacen, p, ctx, "Sos un analista."), conv.id


def correr(ag, conv_id, msg):
    ag.almacen.tomar_turno(conv_id)
    return list(ag.turno(conv_id, msg))


def tipos(ev):
    return [e["tipo"] for e in ev]


def resultados(llamada) -> dict:
    """tool_result del último mensaje de una llamada, por tool_use_id."""
    return {b["tool_use_id"]: b for b in llamada["messages"][-1]["content"] if b.get("type") == "tool_result"}


def aprobar(almacen, conv_id, respuestas=None):
    """Lo mismo que hace POST /api/clarify al aprobar."""
    c = almacen.conversacion(conv_id)
    entrada = clarify.EntradaAclaraciones.model_validate(c.tool_use_pendiente["input"])
    resp = clarify.completar_respuestas(entrada, respuestas or {})
    brief = almacen.crear_brief(conv_id, c.tool_use_pendiente["id"], entrada.brief.model_dump(), resp)
    almacen.guardar_paso(conv_id, paso_aclaracion(c.tool_use_pendiente,
                                                  clarify.resultado("aprobado", resp, entrada, None, brief.id)))
    return brief.id


# ---------------------------------------------------------------- aclaraciones
def test_flujo_completo_aclaracion_generacion_y_versiones(almacen, herramientas, ctx):
    cliente = ClienteFalso(
        mensaje(tool_use("t1", "resumen_ventas", {"desde": "2026-10-01"}), stop="tool_use"),
        # Aclaración junto con otra herramienta en el mismo mensaje.
        mensaje(texto("Antes de armarlo, confirmame:"),
                tool_use("c1", "solicitar_aclaraciones", {"brief": BRIEF, "preguntas": PREGUNTAS}),
                tool_use("t2", "consultar", {"sql": "SELECT 1"}), stop="tool_use"),
    )
    ag, cid = agente(almacen, cliente, ctx)
    ev = correr(ag, cid, "Armame un reporte de octubre")

    assert tipos(ev)[-2:] == ["aclaraciones", "fin"] and ev[-1]["stop_reason"] == "aclaraciones"
    acl = ev[-2]
    assert acl["tool_use_id"] == "c1" and acl["brief"] == BRIEF and acl["preguntas"] == PREGUNTAS
    # La otra herramienta del mensaje se ejecutó y quedó guardada, pero el mensaje de resultados no se
    # agrega hasta que el usuario responda.
    assert [n for n, _ in herramientas.llamadas] == ["resumen_ventas", "consultar"]
    assert set(almacen.pasos(cid)) == {"t1", "t2"}
    assert almacen.mensajes(cid)[-1]["role"] == "assistant"
    c = almacen.conversacion(cid)
    assert c.estado == "esperando_aclaracion" and c.tool_use_pendiente["id"] == "c1"

    # El usuario aprueba (sin tocar nada: se usan las recomendadas).
    brief_id = aprobar(almacen, cid)
    cliente.guion += [
        mensaje(tool_use("g1", "generar_artifact", {"brief_id": brief_id, **CONTENIDO}), stop="tool_use"),
        mensaje(texto("Listo: las ventas crecieron 12%.")),
    ]
    almacen.tomar_turno(cid)
    ev = list(ag.turno(cid, None))
    r = resultados(cliente.llamadas[2])
    assert list(r) == ["c1", "t2"]  # mismo orden que los tool_use, en un solo mensaje
    cuerpo = json.loads(r["c1"]["content"])
    assert cuerpo["decision"] == "aprobado" and cuerpo["brief_id"] == brief_id
    assert {x["id"]: x["respuesta"] for x in cuerpo["respuestas"]} == {
        "comparar": "octubre 2025", "sucursales": ["Centro", "Carlos Paz"]}
    assert "is_error" not in r["c1"] and "is_error" not in r["t2"]
    assert "artifact" in tipos(ev) and tipos(ev)[-1] == "fin"
    art_ev = next(e for e in ev if e["tipo"] == "artifact")
    assert art_ev["version"] == 1 and art_ev["url"] == f"/artifacts/{art_ev['id']}"
    assert almacen.conversacion(cid).estado == "lista"

    a = almacen.artifact(art_ev["id"])
    assert (a.titulo, a.tipo, a.perfil, a.autor, a.conversacion_id, a.brief_id) == (
        "Ventas de octubre 2026", "reporte", "ventas", "ana@example.com", cid, brief_id)
    v1 = almacen.version(a.id)
    assert v1.version == 1 and "chart.js@4.4.1" in v1.html and "Ventas de octubre 2026" in v1.html
    assert [f["herramienta"] for f in v1.datos_fuente] == ["resumen_ventas", "consultar"]
    assert v1.datos_fuente[1]["sql"] == "SELECT 1"
    # El modelo recibe el enlace y el id para poder editarlo después.
    gen = json.loads(resultados(cliente.llamadas[3])["g1"]["content"])
    assert gen["artifact_id"] == a.id and gen["version"] == 1

    # Dos ediciones: la versión 3 conserva la 2; cada una registra solo sus propias fuentes.
    seccion = {"titulo": "Comparación 2025", "texto": "Octubre 2025 vendió menos."}
    cliente.guion += [
        mensaje(tool_use("t3", "resumen_ventas", {"desde": "2025-10-01"}), stop="tool_use"),
        mensaje(tool_use("e1", "editar_artifact", {"artifact_id": a.id, "nota": "Agrego 2025",
                                                   "secciones": CONTENIDO["secciones"] + [seccion]}),
                stop="tool_use"),
        mensaje(texto("Agregué la comparación.")),
    ]
    correr(ag, cid, "Agregá la comparación con 2025")
    cliente.guion += [
        mensaje(tool_use("e2", "editar_artifact", {"artifact_id": a.id, "nota": "Título nuevo",
                                                   "titulo": "Octubre 2026 vs 2025"}), stop="tool_use"),
        mensaje(texto("Hecho.")),
    ]
    ev = correr(ag, cid, "Cambiale el título")
    assert next(e for e in ev if e["tipo"] == "artifact")["version"] == 3
    vs = almacen.versiones(a.id)
    assert [(v.version, v.nota) for v in vs] == [(1, ""), (2, "Agrego 2025"), (3, "Título nuevo")]
    assert [f["herramienta"] for f in vs[1].datos_fuente] == ["resumen_ventas"]
    assert vs[2].datos_fuente == []
    assert "Comparación 2025" in vs[1].html and "Comparación 2025" in vs[2].html  # campo omitido: se mantiene
    assert "Octubre 2026 vs 2025" in vs[2].html and "Octubre 2026 vs 2025" not in vs[1].html
    assert almacen.artifact(a.id).version_actual == 3 and almacen.artifact(a.id).titulo == "Octubre 2026 vs 2025"


def test_sin_preguntas_igual_pausa(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("c1", "solicitar_aclaraciones", {"brief": BRIEF, "preguntas": []}),
                                   stop="tool_use"))
    ag, cid = agente(almacen, cliente, ctx)
    ev = correr(ag, cid, "Reporte de octubre")
    assert ev[-2]["tipo"] == "aclaraciones" and ev[-2]["preguntas"] == []
    assert almacen.conversacion(cid).estado == "esperando_aclaracion"


def test_mensaje_libre_es_ajuste(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("c1", "solicitar_aclaraciones", {"brief": BRIEF, "preguntas": PREGUNTAS}),
                                   stop="tool_use"))
    ag, cid = agente(almacen, cliente, ctx)
    correr(ag, cid, "Reporte de octubre")
    cliente.guion.append(mensaje(texto("Entendido, lo armo por semana.")))
    ev = correr(ag, cid, "Mejor por semana")
    msgs = cliente.llamadas[-1]["messages"]
    ultimo = msgs[-1]["content"]
    # Un solo mensaje: el tool_result del pendiente con el comentario, sin texto suelto ni brief_id.
    assert len(ultimo) == 1 and ultimo[0]["tool_use_id"] == "c1"
    cuerpo = json.loads(ultimo[0]["content"])
    assert cuerpo["decision"] == "ajustar" and cuerpo["comentario"] == "Mejor por semana"
    assert "brief_id" not in cuerpo
    assert tipos(ev)[-1] == "fin" and almacen.conversacion(cid).estado == "lista"


def test_retomar_sin_respuesta_vuelve_a_pausar(almacen, herramientas, ctx):
    cliente = ClienteFalso(mensaje(tool_use("c1", "solicitar_aclaraciones", {"brief": BRIEF}), stop="tool_use"))
    ag, cid = agente(almacen, cliente, ctx)
    correr(ag, cid, "Reporte")
    ev = correr(ag, cid, None)  # reintento sin respuesta del usuario: no llama al modelo
    assert tipos(ev) == ["aclaraciones", "fin"] and len(cliente.llamadas) == 1


def test_aclaracion_invalida_no_pausa(almacen, herramientas, ctx):
    mala = {"brief": BRIEF, "preguntas": [{"id": "x", "texto": "¿Cuál?", "tipo": "opcion", "opciones": ["a"]}]}
    cliente = ClienteFalso(mensaje(tool_use("c1", "solicitar_aclaraciones", mala), stop="tool_use"),
                           mensaje(texto("Corrijo.")))
    ag, cid = agente(almacen, cliente, ctx)
    ev = correr(ag, cid, "Reporte")
    r = resultados(cliente.llamadas[1])["c1"]
    assert r["is_error"] and "al menos 2 opciones" in r["content"]
    assert "aclaraciones" not in tipos(ev) and almacen.conversacion(cid).estado == "lista"


def test_generar_sin_brief(almacen, herramientas, ctx):
    cliente = ClienteFalso(
        mensaje(tool_use("g1", "generar_artifact", {"brief_id": str(uuid.uuid4()), **CONTENIDO}), stop="tool_use"),
        mensaje(tool_use("g2", "generar_artifact", {"brief_id": "inventado", **CONTENIDO}), stop="tool_use"),
        mensaje(texto("Perdón, primero pido aclaraciones.")))
    ag, cid = agente(almacen, cliente, ctx)
    ev = correr(ag, cid, "Reporte ya")
    for i, tid in ((1, "g1"), (2, "g2")):
        r = resultados(cliente.llamadas[i])[tid]
        assert r["is_error"] and "solicitar_aclaraciones" in r["content"]
    assert "artifact" not in tipos(ev)
    assert almacen.buscar_artifacts(FiltroArtifacts()) == []


def test_brief_de_otra_conversacion(almacen, herramientas, ctx):
    otra = almacen.crear_conversacion("ana@example.com", "ventas", "otra")
    brief = almacen.crear_brief(otra.id, "c9", BRIEF, {})
    cliente = ClienteFalso(
        mensaje(tool_use("g1", "generar_artifact", {"brief_id": brief.id, **CONTENIDO}), stop="tool_use"),
        mensaje(texto("No pude.")))
    ag, cid = agente(almacen, cliente, ctx)
    correr(ag, cid, "Usá el brief de la otra")
    r = resultados(cliente.llamadas[1])["g1"]
    assert r["is_error"] and "otra conversación" in r["content"]
    assert almacen.buscar_artifacts(FiltroArtifacts()) == []


def _contexto_turno(almacen, conv, tool_use_id, perfil="ventas"):
    return reportes.ContextoTurno(almacen, conv, perfil, "Analista comercial", tool_use_id, [], {},
                                  frozenset({"resumen_ventas", "consultar"}))


def _artifact(almacen, perfil="ventas", titulo="Reporte", tipo="reporte", autor="ana@example.com"):
    conv = almacen.crear_conversacion(autor, perfil, "x")
    brief = almacen.crear_brief(conv.id, "c", BRIEF, {})
    entrada = reportes.EntradaGenerar.model_validate({"brief_id": brief.id, **CONTENIDO, "titulo": titulo,
                                                      "tipo": tipo})
    r = json.loads(reportes.generar_artifact(_contexto_turno(almacen, conv, f"g-{uuid.uuid4()}", perfil), entrada))
    return almacen.artifact(r["artifact_id"]), conv


def test_retomar_no_duplica_el_artifact(almacen):
    conv = almacen.crear_conversacion("ana@example.com", "ventas", "x")
    brief = almacen.crear_brief(conv.id, "c", BRIEF, {})
    entrada = reportes.EntradaGenerar.model_validate({"brief_id": brief.id, **CONTENIDO})
    r1 = json.loads(reportes.generar_artifact(_contexto_turno(almacen, conv, "g1"), entrada))
    r2 = json.loads(reportes.generar_artifact(_contexto_turno(almacen, conv, "g1"), entrada))
    assert r1["artifact_id"] == r2["artifact_id"] and len(almacen.buscar_artifacts(FiltroArtifacts())) == 1


def test_editar_artifact_de_otro_perfil(almacen):
    a, _ = _artifact(almacen, perfil="produccion")
    conv = almacen.crear_conversacion("ana@example.com", "ventas", "x")
    r = json.loads(reportes.editar_artifact(_contexto_turno(almacen, conv, "e1"),
                                            reportes.EntradaEditar(artifact_id=a.id, nota="cambio", titulo="Otro")))
    assert "perfil produccion" in r["error"] and almacen.artifact(a.id).version_actual == 1
    r = json.loads(reportes.editar_artifact(_contexto_turno(almacen, conv, "e2"),
                                            reportes.EntradaEditar(artifact_id=str(uuid.uuid4()), nota="x y z")))
    assert "No existe" in r["error"]


def test_html_rechazado_no_crea_artifact(almacen):
    conv = almacen.crear_conversacion("ana@example.com", "ventas", "x")
    brief = almacen.crear_brief(conv.id, "c", BRIEF, {})
    malo = copy.deepcopy(CONTENIDO)
    malo["secciones"][0]["html"] = '<script src="https://evil.example.com/x.js"></script>'
    r = json.loads(reportes.generar_artifact(_contexto_turno(almacen, conv, "g1"),
                                             reportes.EntradaGenerar.model_validate({"brief_id": brief.id, **malo})))
    assert "evil.example.com" in r["error"] and almacen.buscar_artifacts(FiltroArtifacts()) == []


# ---------------------------------------------------------------- HTML
def contenido(**cambios):
    return reportes._Contenido.model_validate({**CONTENIDO, **cambios}).model_dump()


def test_componer_plantilla():
    doc = componer(contenido(), perfil="Analista comercial")
    validar_html(doc, secretos={})
    assert doc.startswith("<!doctype html>") and "{{" not in doc
    assert 'data-v="1234567.5" data-f="moneda"' in doc and 'data-delta="0.12"' in doc
    assert "Intl.NumberFormat(\"es-AR\"" in doc and "prefers-color-scheme: dark" in doc
    assert "<strong>12%</strong>" in doc and "<li>Centro +15%</li>" in doc
    assert "Prioridad alta" in doc and "Nota metodológica" in doc
    datos = json.loads(doc.split('id="panacea-graficos">')[1].split("</script>")[0])
    assert datos[0]["id"] == "g0" and [s["rol"] for s in datos[0]["series"]][1:] == ["proyeccion", "banda_min",
                                                                                     "banda_max"]


def test_componer_escapa_el_contenido():
    c = contenido(titulo="<script>alert(1)</script> {{cuerpo}}",
                  secciones=[{"titulo": "x", "grafico": {"tipo": "bar", "etiquetas": ["</script><script>alert(1)"],
                                                    "series": [{"nombre": "s", "datos": [1]}]}}])
    doc = componer(c, perfil="Ventas")
    assert "<h1>&lt;script&gt;alert(1)" in doc
    assert doc.count("</script>") == 3  # solo los de la plantilla: nada del modelo cierra un bloque
    assert "{{cuerpo}}" in doc  # el marcador del modelo no se reemplaza
    assert "<\\/script><script>alert(1)" in doc


@pytest.mark.parametrize("fragmento, mensaje_error", [
    ('<script src="https://evil.example.com/a.js"></script>', "evil.example.com"),
    ('<script src="http://cdn.jsdelivr.net/npm/x.js"></script>', "cdn.jsdelivr.net"),
    ('<script src="//unpkg.com/x.js"></script>', "unpkg.com"),
    ('<script src="/api/profiles"></script>', "ruta relativa"),
    ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2">', "fonts.googleapis.com"),
    ('<iframe src="https://example.com"></iframe>', "iframe"),
    ("<p>postgresql+psycopg2://agente:clave@host/db</p>", "cadena de conexión"),
    ("<p>postgres://x@y/z</p>", "cadena de conexión"),
])
def test_validar_html_rechaza(fragmento, mensaje_error):
    with pytest.raises(ArtifactInvalido, match=mensaje_error):
        validar_html(f"<html><body>{fragmento}</body></html>", secretos={})


def test_validar_html_acepta_jsdelivr():
    validar_html('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>', {})


def test_credencial_del_entorno():
    entorno = {"DB_URL_VENTAS": "postgresql+psycopg2://agente_ventas_ro:Sup3rClave@h.neon.tech/db",
               "AUTH_SECRET": "a" * 40, "HOME": "/home/ubuntu/workspaces", "ANTHROPIC_API_KEY": "sk-ant-123456789"}
    secretos = secretos_del_entorno(entorno)
    assert set(secretos.values()) == {"DB_URL_VENTAS", "AUTH_SECRET", "ANTHROPIC_API_KEY"}
    for texto_html, var in (("<p>Sup3rClave</p>", "DB_URL_VENTAS"), ("<p>sk-ant-123456789</p>", "ANTHROPIC_API_KEY")):
        with pytest.raises(ArtifactInvalido) as e:
            validar_html(texto_html, secretos)
        assert var in str(e.value) and "Sup3rClave" not in str(e.value)
    validar_html("<p>/home/ubuntu/workspaces</p>", secretos)


# ---------------------------------------------------------------- galería
def test_busqueda_filtros_y_fijados(almacen):
    viejo, _ = _artifact(almacen, titulo="Estrategia comercial 2026")
    medio, _ = _artifact(almacen, titulo="Tabla de precios", tipo="tabla", autor="beto@example.com")
    nuevo, _ = _artifact(almacen, titulo="Producción semanal", perfil="produccion")
    todos = almacen.buscar_artifacts(FiltroArtifacts())
    assert [a.id for a in todos] == [nuevo.id, medio.id, viejo.id]

    almacen.fijar(viejo.id, True)
    assert [a.id for a in almacen.buscar_artifacts(FiltroArtifacts(perfiles=frozenset({"ventas"})))] == [
        viejo.id, medio.id]
    hoy = datetime.now(ZONA).date()
    f = FiltroArtifacts(perfiles=frozenset({"ventas", "produccion"}), tipo="tabla", desde=hoy, hasta=hoy)
    assert [a.id for a in almacen.buscar_artifacts(f)] == [medio.id]
    assert almacen.buscar_artifacts(FiltroArtifacts(hasta=hoy - timedelta(days=1))) == []
    assert [a.id for a in almacen.buscar_artifacts(FiltroArtifacts(texto="ESTRATEGIA"))] == [viejo.id]
    assert almacen.buscar_artifacts(FiltroArtifacts(texto="100%_")) == []
    assert [a.id for a in almacen.buscar_artifacts(FiltroArtifacts(autor="beto@example.com"))] == [medio.id]
    assert almacen.buscar_artifacts(FiltroArtifacts(perfiles=frozenset())) == []
    assert almacen.artifact("no-es-uuid") is None and almacen.version(str(uuid.uuid4())) is None
