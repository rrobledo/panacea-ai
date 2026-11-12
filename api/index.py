"""
Backend FastAPI del Agente Panacea Web. Vercel lo sirve como función Python en /api/*.

Rutas:
  GET  /api/salud
  GET  /api/profiles                 perfiles del usuario
  GET  /api/conversaciones           conversaciones del usuario (admin: ?todas=true)
  GET  /api/conversaciones/{id}      historial para mostrar en el chat
  POST /api/chat                     un turno del agente, respuesta en SSE
  POST /api/clarify                  aprobar o ajustar el brief pendiente y seguir el turno (SSE)
  GET  /api/artifacts                galería: búsqueda y filtros, fijados primero
  GET  /api/artifacts/{id}           datos, versiones y fuentes
  GET  /api/artifacts/{id}/html      HTML de una versión (?version=n, ?descargar=1) con CSP aislada
  POST /api/artifacts/{id}/fijar     fijar o desfijar para el perfil
  GET  /api/admin/uso                tablero de uso y costo (solo admin; ?mes=AAAA-MM)
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from functools import cached_property
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic  # noqa: E402
from fastapi import Depends, FastAPI, HTTPException, Query, Request  # noqa: E402
from fastapi.responses import HTMLResponse, StreamingResponse  # noqa: E402
from starlette.background import BackgroundTask  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from agent.almacen import ZONA, Almacen, AlmacenPostgres, ConversacionOcupada, FiltroArtifacts  # noqa: E402
from agent.artifacts import CSP  # noqa: E402
from agent.auth import SesionInvalida, email_de_token, token_de  # noqa: E402
from agent.contexto import ContextoPerfil, normalizar_url  # noqa: E402
from agent.loop import Agente, _resumen, paso_aclaracion  # noqa: E402
from agent.tools import clarify  # noqa: E402
from agent.profiles import Configuracion, ErrorConfiguracion, Perfil, Usuario, cargar_configuracion, contexto_para  # noqa: E402

log = logging.getLogger("panacea.api")


# ---------------------------------------------------------------- servicios (reemplazables en pruebas)
class Servicios:
    @cached_property
    def config(self) -> Configuracion:
        return cargar_configuracion()

    @cached_property
    def almacen(self) -> Almacen:
        url = os.environ.get("DB_URL_APP")
        if not url:
            raise ErrorConfiguracion("Falta la variable de entorno DB_URL_APP")
        return AlmacenPostgres(create_engine(normalizar_url(url), pool_pre_ping=True,
                                             pool_size=1, max_overflow=1, pool_recycle=300))

    @cached_property
    def cliente(self) -> anthropic.Anthropic:
        return anthropic.Anthropic()

    def contexto(self, perfil: Perfil) -> ContextoPerfil:
        return contexto_para(perfil)

    def system_prompt(self, perfil: Perfil) -> str:
        return perfil.system_prompt(self.config.raiz)

    fallbacks: bool = True


app = FastAPI(title="Agente Panacea", docs_url=None, redoc_url=None, openapi_url=None)
app.state.servicios = Servicios()


def servicios(request: Request) -> Servicios:
    return request.app.state.servicios


@dataclass
class Sesion:
    usuario: Usuario
    srv: Servicios


def sesion(request: Request, srv: Servicios = Depends(servicios)) -> Sesion:
    try:
        email = email_de_token(token_de(request.headers, request.cookies))
    except SesionInvalida:
        raise HTTPException(401, "Iniciá sesión") from None
    usuario = srv.config.usuario(email)
    if usuario is None:
        raise HTTPException(403, "Tu usuario no tiene acceso a la aplicación")
    return Sesion(usuario, srv)


# ---------------------------------------------------------------- rutas
@app.get("/api/salud")
def salud():
    return {"ok": True}


@app.get("/api/profiles")
def perfiles(s: Sesion = Depends(sesion)):
    return {"usuario": {"email": s.usuario.email, "admin": s.usuario.admin},
            "perfiles": [{"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion}
                         for p in s.srv.config.perfiles_de(s.usuario)]}


def _conv_dict(c) -> dict:
    return {"id": c.id, "perfil": c.perfil, "titulo": c.titulo, "estado": c.estado, "usuario": c.usuario,
            "creada": c.creada.isoformat(), "actualizada": c.actualizada.isoformat()}


@app.get("/api/conversaciones")
def conversaciones(todas: bool = False, s: Sesion = Depends(sesion)):
    usuario = None if (todas and s.usuario.admin) else s.usuario.email
    return {"conversaciones": [_conv_dict(c) for c in s.srv.almacen.conversaciones_de(usuario)]}


def _conversacion_visible(s: Sesion, conv_id: str):
    c = s.srv.almacen.conversacion(conv_id)
    if c is None or (c.usuario != s.usuario.email and not s.usuario.admin):
        raise HTTPException(404, "No existe la conversación")
    return c


def _items(mensajes: list[dict], pasos: dict) -> list[dict]:
    """Historial de la API → elementos para mostrar: mensajes del usuario, del agente y pasos."""
    items = []
    for m in mensajes:
        bloques = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
        if m["role"] == "user":
            for b in bloques:
                if b.get("type") == "text" and not b["text"].startswith("[Sistema]"):
                    items.append({"tipo": "usuario", "texto": b["text"]})
        elif m["role"] == "assistant":
            for b in bloques:
                if b.get("type") == "text" and b.get("text"):
                    if items and items[-1]["tipo"] == "agente":
                        items[-1]["texto"] += b["text"]
                    else:
                        items.append({"tipo": "agente", "texto": b["text"]})
                elif b.get("type") == "tool_use" and b["name"] == clarify.NOMBRE:
                    p = pasos.get(b["id"])
                    items.append({"tipo": "aclaraciones", "id": b["id"], **(b.get("input") or {}),
                                  "respuesta": _json_o_none(p.resultado) if p else None})
                elif b.get("type") == "tool_use":
                    p = pasos.get(b["id"])
                    items.append({"tipo": "paso", "id": b["id"], "nombre": b["name"],
                                  "argumentos": _resumen(b.get("input")),
                                  "duracion_ms": p.duracion_ms if p else None,
                                  "es_error": p.es_error if p else None})
                    r = _json_o_none(p.resultado) if p and not p.es_error else None
                    if b["name"] in ("generar_artifact", "editar_artifact") and r and "artifact_id" in r:
                        items.append({"tipo": "artifact", "id": r["artifact_id"], "version": r["version"],
                                      "titulo": r["titulo"], "url": r["url"]})
    return items


def _json_o_none(texto: str):
    try:
        return json.loads(texto)
    except ValueError:
        return None


@app.get("/api/conversaciones/{conv_id}")
def conversacion(conv_id: str, s: Sesion = Depends(sesion)):
    c = _conversacion_visible(s, conv_id)
    return {"conversacion": _conv_dict(c),
            "aclaracion_pendiente": ({"tool_use_id": c.tool_use_pendiente["id"], **c.tool_use_pendiente["input"]}
                                     if c.estado == "esperando_aclaracion" and c.tool_use_pendiente else None),
            "items": _items(s.srv.almacen.mensajes(c.id), s.srv.almacen.pasos(c.id))}


class PedidoChat(BaseModel):
    perfil: str | None = None
    conversacion_id: str | None = None
    mensaje: str | None = Field(None, max_length=20_000)


def _sse(evento: dict) -> str:
    return f"event: {evento['tipo']}\ndata: {json.dumps(evento, ensure_ascii=False, default=str)}\n\n"


@app.post("/api/chat")
def chat(pedido: PedidoChat, s: Sesion = Depends(sesion)):
    srv, almacen = s.srv, s.srv.almacen
    mensaje = (pedido.mensaje or "").strip() or None
    if pedido.conversacion_id:
        c = almacen.conversacion(pedido.conversacion_id)
        if c is None or c.usuario != s.usuario.email:
            raise HTTPException(404, "No existe la conversación")
        if pedido.perfil and pedido.perfil != c.perfil:
            raise HTTPException(400, "La conversación es de otro perfil")
        perfil_id = c.perfil
    else:
        if not pedido.perfil or not mensaje:
            raise HTTPException(400, "Indicá el perfil y el mensaje")
        perfil_id = pedido.perfil
    if not srv.config.puede_usar(s.usuario, perfil_id):
        raise HTTPException(403, "No tenés asignado ese perfil")
    _controlar_tope(s)
    agente = _agente(srv, srv.config.perfiles[perfil_id])

    if pedido.conversacion_id:
        conv = c
    else:
        conv = almacen.crear_conversacion(s.usuario.email, perfil_id, mensaje[:80])
    _tomar_turno(almacen, conv.id)
    return _respuesta_turno(almacen, agente, conv, mensaje)


def _inicio_de_mes(anio: int, mes: int) -> datetime:
    return datetime(anio, mes, 1, tzinfo=ZONA)


def _mes_siguiente(d: datetime) -> datetime:
    return _inicio_de_mes(d.year + d.month // 12, d.month % 12 + 1)


def _controlar_tope(s: Sesion) -> None:
    """429 si el usuario ya consumió su tope mensual; no se llama al modelo."""
    tope = s.srv.config.tope_de(s.usuario)
    if tope is None:
        return
    ahora = datetime.now(ZONA)
    consumido = s.srv.almacen.costo_desde(s.usuario.email, _inicio_de_mes(ahora.year, ahora.month))
    if consumido >= tope:
        renueva = _mes_siguiente(ahora)
        raise HTTPException(429, f"Alcanzaste el tope mensual de US$ {tope:.2f} (consumido: US$ {consumido:.2f}). "
                                 f"Se renueva el {renueva:%d/%m/%Y}; si lo necesitás antes, pedile a un "
                                 "administrador que lo amplíe.")


def _agente(srv: Servicios, perfil: Perfil) -> Agente:
    try:
        return Agente(srv.cliente, srv.almacen, perfil, srv.contexto(perfil), srv.system_prompt(perfil),
                      fallbacks=srv.fallbacks)
    except ErrorConfiguracion as e:
        log.error("configuración: %s", e)
        raise HTTPException(500, "El perfil no está configurado correctamente") from None


def _tomar_turno(almacen: Almacen, conv_id: str) -> None:
    try:
        almacen.tomar_turno(conv_id)
    except ConversacionOcupada:
        raise HTTPException(409, "Ya hay una respuesta en curso en esta conversación") from None


def _respuesta_turno(almacen: Almacen, agente: Agente, conv, mensaje: str | None) -> StreamingResponse:
    """Corre el turno (ya tomado) y lo devuelve por SSE."""
    iniciado = False

    def eventos():
        nonlocal iniciado
        iniciado = True
        yield _sse({"tipo": "conversacion", "id": conv.id, "titulo": conv.titulo, "perfil": conv.perfil})
        try:
            for ev in agente.turno(conv.id, mensaje):
                yield _sse(ev)
        except Exception:
            log.exception("turno %s", conv.id)
            yield _sse({"tipo": "error", "mensaje": "Error interno. El turno se puede retomar."})

    def liberar_si_no_empezo():
        # Si el cliente se desconectó antes del primer evento, el turno nunca corrió. Lo que ya se
        # guardó (por ejemplo, la respuesta a una aclaración) se reutiliza en el próximo turno.
        if not iniciado:
            almacen.soltar_turno(conv.id, "lista")

    return StreamingResponse(eventos(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                             background=BackgroundTask(liberar_si_no_empezo))


# ---------------------------------------------------------------- aclaraciones
class PedidoAclaracion(BaseModel):
    conversacion_id: str
    tool_use_id: str
    decision: Literal["aprobar", "ajustar"]
    respuestas: dict[str, str | list[str] | None] = {}
    comentario: str | None = Field(None, max_length=5_000)


@app.post("/api/clarify")
def aclarar(pedido: PedidoAclaracion, s: Sesion = Depends(sesion)):
    srv, almacen = s.srv, s.srv.almacen
    c = almacen.conversacion(pedido.conversacion_id)
    if c is None or c.usuario != s.usuario.email:
        raise HTTPException(404, "No existe la conversación")
    pendiente = c.tool_use_pendiente if c.estado == "esperando_aclaracion" else None
    if not pendiente or pendiente["id"] != pedido.tool_use_id:
        raise HTTPException(409, "No hay una aclaración pendiente con ese id")
    if not srv.config.puede_usar(s.usuario, c.perfil):
        raise HTTPException(403, "No tenés asignado ese perfil")
    comentario = (pedido.comentario or "").strip() or None
    if pedido.decision == "ajustar" and not comentario:
        raise HTTPException(400, "Contá qué querés ajustar")
    _controlar_tope(s)
    entrada = clarify.EntradaAclaraciones.model_validate(pendiente["input"])
    try:
        respuestas = clarify.completar_respuestas(entrada, pedido.respuestas)
    except clarify.RespuestaInvalida as e:
        raise HTTPException(400, str(e)) from None
    agente = _agente(srv, srv.config.perfiles[c.perfil])

    _tomar_turno(almacen, c.id)
    if pedido.tool_use_id in almacen.pasos(c.id):  # otra respuesta ganó la carrera
        almacen.soltar_turno(c.id, "lista")
        raise HTTPException(409, "La aclaración ya fue respondida")
    if pedido.decision == "aprobar":
        brief = almacen.crear_brief(c.id, pedido.tool_use_id, entrada.brief.model_dump(), respuestas)
        resultado = clarify.resultado("aprobado", respuestas, entrada, comentario, brief.id)
    else:
        resultado = clarify.resultado("ajustar", respuestas, entrada, comentario)
    almacen.guardar_paso(c.id, paso_aclaracion(pendiente, resultado))
    return _respuesta_turno(almacen, agente, c, None)


# ---------------------------------------------------------------- artifacts
def _artifact_dict(a) -> dict:
    return {"id": a.id, "titulo": a.titulo, "tipo": a.tipo, "perfil": a.perfil, "autor": a.autor,
         "fijado": a.fijado, "version_actual": a.version_actual, "creado": a.creado.isoformat(),
         "actualizado": a.actualizado.isoformat(), "url": f"/artifacts/{a.id}",
         "html_url": f"/api/artifacts/{a.id}/html"}


def _perfiles_visibles(s: Sesion) -> frozenset[str] | None:
    return None if s.usuario.admin else frozenset(p.id for p in s.srv.config.perfiles_de(s.usuario))


def _artifact_visible(s: Sesion, artifact_id: str):
    a = s.srv.almacen.artifact(artifact_id)
    visibles = _perfiles_visibles(s)
    if a is None or (visibles is not None and a.perfil not in visibles):
        raise HTTPException(404, "No existe el reporte")
    return a


@app.get("/api/artifacts")
def artifacts(q: str | None = Query(None, max_length=200), perfil: str | None = None,
              autor: str | None = None, tipo: Literal["reporte", "tablero", "tabla"] | None = None,
              desde: date | None = None, hasta: date | None = None,
              limite: int = Query(100, ge=1, le=200), s: Sesion = Depends(sesion)):
    filtro = FiltroArtifacts(perfiles=_perfiles_visibles(s), texto=(q or "").strip() or None, perfil=perfil,
                             autor=(autor or "").strip().lower() or None, tipo=tipo, desde=desde, hasta=hasta,
                             limite=limite)
    return {"artifacts": [_artifact_dict(a) for a in s.srv.almacen.buscar_artifacts(filtro)]}


@app.get("/api/artifacts/{artifact_id}")
def artifact(artifact_id: str, s: Sesion = Depends(sesion)):
    a = _artifact_visible(s, artifact_id)
    d = _artifact_dict(a)
    # La conversación es privada de su autor: el enlace solo se ofrece a quien puede abrirla.
    d["conversacion_id"] = a.conversacion_id if (a.autor == s.usuario.email or s.usuario.admin) else None
    d["versiones"] = [{"version": v.version, "nota": v.nota, "creado": v.creado.isoformat(),
                       "datos_fuente": v.datos_fuente} for v in s.srv.almacen.versiones(a.id)]
    return d


def _nombre_archivo(titulo: str, version: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", titulo.lower().encode("ascii", "ignore").decode()).strip("-")[:60]
    return f"{base or 'reporte'}_v{version}.html"


@app.get("/api/artifacts/{artifact_id}/html")
def artifact_html(artifact_id: str, version: int | None = Query(None, ge=1), descargar: bool = False,
                  s: Sesion = Depends(sesion)):
    a = _artifact_visible(s, artifact_id)
    v = s.srv.almacen.version(a.id, version)
    if v is None:
        raise HTTPException(404, "No existe esa versión")
    headers = {"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff",
               "Referrer-Policy": "no-referrer", "Cache-Control": "private, no-cache"}
    if descargar:
        headers["Content-Disposition"] = f'attachment; filename="{_nombre_archivo(a.titulo, v.version)}"'
    return HTMLResponse(v.html, headers=headers)


class PedidoFijar(BaseModel):
    fijado: bool


@app.post("/api/artifacts/{artifact_id}/fijar")
def fijar(artifact_id: str, pedido: PedidoFijar, s: Sesion = Depends(sesion)):
    a = _artifact_visible(s, artifact_id)
    s.srv.almacen.fijar(a.id, pedido.fijado)
    return {"id": a.id, "fijado": pedido.fijado}


# ---------------------------------------------------------------- uso (admin)
@app.get("/api/admin/uso")
def uso(mes: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), s: Sesion = Depends(sesion)):
    if not s.usuario.admin:
        raise HTTPException(403, "Solo para administradores")
    ahora = datetime.now(ZONA)
    anio, m = (int(x) for x in mes.split("-")) if mes else (ahora.year, ahora.month)
    desde = _inicio_de_mes(anio, m)
    hasta = _mes_siguiente(desde)
    almacen, config = s.srv.almacen, s.srv.config
    por_usuario = almacen.uso_agrupado(desde, hasta, "usuario")
    for f in por_usuario:
        u = config.usuario(f["clave"])
        f["tope_usd"] = config.tope_de(u) if u else None
    # Historial: los 12 meses que terminan en el pedido.
    inicio_hist = _inicio_de_mes(anio - 1 + (m == 12), m % 12 + 1)
    historial = sorted(almacen.uso_agrupado(inicio_hist, hasta, "mes"), key=lambda f: f["clave"])
    return {"mes": f"{anio:04d}-{m:02d}", "desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "por_usuario": por_usuario, "por_perfil": almacen.uso_agrupado(desde, hasta, "perfil"),
            "historial": historial,
            "nota": "Costo estimado con la tabla de precios de agent/costos.py; la factura de Anthropic es la referencia."}
