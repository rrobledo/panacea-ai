"""
Loop del agente: Messages API en streaming + herramientas del perfil + persistencia por paso.

Un turno es un generador de eventos (dicts con "tipo") que la API reenvía por SSE:
  texto, reinicio, herramienta_inicio, herramienta_fin, artifact, aclaraciones, aviso, error, fin.

Reglas que sostiene:
  - el historial solo crece al final y se reenvía tal cual lo devolvió la API (incluidos los
    bloques de razonamiento), para conservar el razonamiento entre llamadas;
  - cada resultado de herramienta se guarda apenas termina, antes del tool_result, así un turno
    cortado se retoma sin repetir herramientas;
  - toda entrada de herramienta se valida antes de ejecutarla (eager_input_streaming no valida);
  - nunca queda un tool_use sin su tool_result;
  - solicitar_aclaraciones pausa el turno: las demás herramientas del mensaje se ejecutan y se
    guardan, la conversación queda en `esperando_aclaracion` y el tool_result se arma cuando el
    usuario responde (POST /api/clarify, o un mensaje libre que cuenta como ajuste).
"""

import json
import logging
import time
from dataclasses import dataclass, field, replace
from typing import Iterator

import anthropic
from pydantic import ValidationError

from agent.almacen import Almacen, Paso, RegistroConsulta, RegistroUso
from agent.contexto import ContextoPerfil
from agent.costos import costo_usd
from agent.profiles import Perfil
from agent.tools import clarify, registro
from agent.tools.reportes import ContextoTurno

log = logging.getLogger("panacea.loop")

MAX_TOKENS = 64_000
BETA_FALLBACK = "server-side-fallback-2026-07-01"
REINTENTOS_JSON = 2
REINTENTOS_TRUNCADO = 2
LATIDO_SEG = 20
MAX_RESULTADO = 200_000  # caracteres; un resultado más largo se recorta con aviso al modelo


@dataclass
class Uso:
    entrada: int = 0
    salida: int = 0
    cache_lectura: int = 0
    cache_escritura: int = 0
    llamadas: int = 0
    costo_usd: float = 0.0
    modelos: list[str] = field(default_factory=list)

    def sumar(self, mensaje) -> dict:
        """Suma una llamada y devuelve sus números (para registrarla aparte)."""
        u = mensaje.usage
        d = {"entrada": u.input_tokens or 0, "salida": u.output_tokens or 0,
             "cache_lectura": getattr(u, "cache_read_input_tokens", 0) or 0,
             "cache_escritura": getattr(u, "cache_creation_input_tokens", 0) or 0}
        d["costo_usd"] = costo_usd(mensaje.model, **d)
        self.entrada += d["entrada"]
        self.salida += d["salida"]
        self.cache_lectura += d["cache_lectura"]
        self.cache_escritura += d["cache_escritura"]
        self.costo_usd = round(self.costo_usd + d["costo_usd"], 6)
        self.llamadas += 1
        self.modelos.append(mensaje.model)
        return d

    @property
    def tokens_presupuesto(self) -> int:
        """Tokens que cuentan para el presupuesto del turno: los nuevos (entrada sin caché, escritura de
        caché y salida). Las lecturas de caché no cuentan: cada vuelta relee el historial completo y
        cuesta 1/20 de la entrada; contarlas cortaría cualquier turno largo."""
        return self.entrada + self.cache_escritura + self.salida

    def como_dict(self) -> dict:
        return {"entrada": self.entrada, "salida": self.salida, "cache_lectura": self.cache_lectura,
                "cache_escritura": self.cache_escritura, "llamadas": self.llamadas, "costo_usd": self.costo_usd}


_CIERRE = ("Respondé ahora con la información que ya tenés, sin llamar más herramientas, y aclarale al "
           "usuario qué quedó sin verificar.")


def _bloques(mensaje) -> list[dict]:
    """Contenido de la respuesta tal como lo devolvió la API, para reenviarlo sin cambios."""
    return [b.to_dict(mode="json") for b in mensaje.content]


def _tool_uses(contenido: list[dict]) -> list[dict]:
    return [b for b in contenido if isinstance(b, dict) and b.get("type") == "tool_use"]


def _pendientes(historia: list[dict]) -> list[dict]:
    """tool_use del último mensaje del asistente que todavía no tienen tool_result."""
    if not historia or historia[-1]["role"] != "assistant":
        return []
    contenido = historia[-1]["content"]
    return _tool_uses(contenido) if isinstance(contenido, list) else []


def _aclaracion_sin_responder(historia: list[dict], pasos: dict) -> dict | None:
    for u in _pendientes(historia):
        if u["name"] == clarify.NOMBRE and u["id"] not in pasos:
            return u
    return None


def paso_aclaracion(tool_use: dict, resultado: str) -> Paso:
    return Paso(tool_use["id"], clarify.NOMBRE, tool_use.get("input") or {}, resultado, False, 0)


def _resumen(obj, largo=200) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= largo else s[:largo - 1] + "…"


def _mensaje_error(e: Exception) -> str:
    """Mensaje de un error de base o de herramienta sin URL de conexión ni credenciales."""
    orig = getattr(e, "orig", None)
    texto = str(orig if orig is not None else e).strip().splitlines()
    texto = texto[0] if texto else type(e).__name__
    return texto[:500]


def _error_validacion(e: ValidationError, args) -> str:
    detalle = "; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors())
    return json.dumps({"error": "Argumentos inválidos", "detalle": detalle[:4000],
                       "recibido": _resumen(args, 2000)}, ensure_ascii=False)


def _filas(resultado: str) -> int | None:
    try:
        d = json.loads(resultado)
    except ValueError:
        return None
    for cand in (d, d.get("resultado") if isinstance(d, dict) else None):
        if isinstance(cand, dict) and isinstance(cand.get("total_filas"), int):
            return cand["total_filas"]
    return None


class Agente:
    def __init__(self, cliente: anthropic.Anthropic, almacen: Almacen, perfil: Perfil,
                 ctx: ContextoPerfil, system_prompt: str, fallbacks: bool = True):
        self.cliente = cliente
        self.almacen = almacen
        self.perfil = perfil
        self.ctx = ctx
        self.fallbacks = fallbacks
        self.system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
        self.herramientas = registro.definiciones(perfil.herramientas)
        for h in self.herramientas:
            h["eager_input_streaming"] = True
        if self.herramientas:
            self.herramientas[-1]["cache_control"] = {"type": "ephemeral"}
        self._ultimo_latido = 0.0
        self._conv_actual: str | None = None

    # ------------------------------------------------------------ turno
    def turno(self, conv_id: str, mensaje: str | None) -> Iterator[dict]:
        """Ejecuta un turno. El llamador ya tomó el turno con almacen.tomar_turno(conv_id)."""
        uso = Uso()
        stop_reason = None
        self._conv_actual = conv_id
        self._estado_final = ("lista", None)
        self._conv = self.almacen.conversacion(conv_id)
        try:
            historia = self.almacen.mensajes(conv_id)
            ejecutadas = 0
            # Mensaje libre con una aclaración pendiente: es el ajuste de ese tool_use, no un mensaje
            # aparte (así el tool_use no queda huérfano).
            pendiente = _aclaracion_sin_responder(historia, self.almacen.pasos(conv_id))
            if pendiente and mensaje:
                self.almacen.guardar_paso(conv_id, paso_aclaracion(pendiente, clarify.resultado(
                    "ajustar", {}, None, comentario=mensaje)))
                mensaje = None
            # Un turno anterior cortado pudo dejar tool_use sin respuesta: se completan primero.
            if _pendientes(historia):
                ejecutadas, pausa = yield from self._ejecutar_pendientes(conv_id, historia, ejecutadas)
                if pausa:
                    yield from self._pausar(pausa, uso)
                    return
            if mensaje:
                self._agregar(conv_id, historia, "user", [{"type": "text", "text": mensaje}])
            elif not historia or historia[-1]["role"] == "assistant":
                yield {"tipo": "fin", "stop_reason": "sin_cambios", "uso": uso.como_dict()}
                return

            forzar_final = False
            truncados = 0
            limite = self.perfil.limites.max_herramientas_por_turno
            for _ in range(limite + 10):
                if _pendientes(historia):
                    ejecutadas, pausa = yield from self._ejecutar_pendientes(conv_id, historia, ejecutadas)
                    if pausa:
                        yield from self._pausar(pausa, uso)
                        return
                    if ejecutadas >= limite and not forzar_final:
                        forzar_final = True
                        yield {"tipo": "aviso", "mensaje": f"Se alcanzó el límite de {limite} herramientas "
                                                         "en este turno; el agente responde con lo que tiene."}
                    continue

                respuesta = yield from self._llamar(historia, forzar_final)
                if respuesta is None:
                    return
                self._registrar_uso(respuesta.model, uso.sumar(respuesta))
                contenido = _bloques(respuesta)
                self._agregar(conv_id, historia, "assistant", contenido)
                stop_reason = respuesta.stop_reason
                usos = _tool_uses(contenido)

                presupuesto = self.perfil.limites.presupuesto_tokens_por_turno
                # Presupuesto: solo corta si el modelo quiere seguir con herramientas.
                if (usos and not forzar_final and stop_reason == "tool_use"
                        and uso.tokens_presupuesto > presupuesto):
                    forzar_final = True
                    yield {"tipo": "aviso", "mensaje": f"Se alcanzó el presupuesto de {presupuesto:,} tokens del "
                                                     "turno; el agente responde con lo que tiene.".replace(",", ".")}
                    self._responder_sin_ejecutar(
                        conv_id, historia, usos, "No se ejecutó: se alcanzó el presupuesto de tokens del turno.",
                        texto=f"[Sistema] Se alcanzó el presupuesto de tokens del turno. {_CIERRE}")
                    continue

                if stop_reason == "refusal":
                    if usos:  # un rechazo puede cortar un tool_use: se responde sin ejecutarlo
                        self._responder_sin_ejecutar(conv_id, historia, usos, "No se ejecutó: el modelo "
                                                     "rechazó continuar.")
                    yield {"tipo": "error", "mensaje": "El modelo no pudo responder este pedido. "
                                                       "Probá reformularlo."}
                    break
                if stop_reason == "max_tokens" and usos:
                    self._responder_sin_ejecutar(conv_id, historia, usos, "No se ejecutó: la entrada de "
                                                 "la herramienta quedó truncada. Volvé a llamarla con una "
                                                 "entrada más corta.")
                    truncados += 1
                    if truncados > REINTENTOS_TRUNCADO:
                        yield {"tipo": "error", "mensaje": "La respuesta superó el largo máximo varias veces."}
                        break
                    continue
                if stop_reason == "pause_turn":
                    continue
                if usos and not forzar_final:
                    continue  # la próxima vuelta ejecuta las herramientas
                if usos:  # con tool_choice none no debería pasar
                    self._responder_sin_ejecutar(conv_id, historia, usos, "No se ejecutó: límite alcanzado.")
                if stop_reason == "max_tokens":
                    yield {"tipo": "aviso", "mensaje": "La respuesta se cortó por largo."}
                break
            else:
                yield {"tipo": "aviso", "mensaje": "El turno se detuvo por exceso de iteraciones."}
            yield {"tipo": "fin", "stop_reason": stop_reason, "uso": uso.como_dict(),
                   "modelos": sorted(set(uso.modelos))}
        finally:
            estado, pendiente = self._estado_final
            self.almacen.soltar_turno(conv_id, estado, pendiente)

    def _pausar(self, tool_use: dict, uso: Uso):
        self._estado_final = ("esperando_aclaracion", {"id": tool_use["id"], "input": tool_use["input"]})
        yield {"tipo": "aclaraciones", "tool_use_id": tool_use["id"], **tool_use["input"]}
        yield {"tipo": "fin", "stop_reason": "aclaraciones", "uso": uso.como_dict(),
               "modelos": sorted(set(uso.modelos))}

    # ------------------------------------------------------------ modelo
    def _llamar(self, historia: list[dict], forzar_final: bool):
        """Una llamada en streaming. Emite los textos y devuelve el mensaje final (o None si falló)."""
        params = dict(
            model=self.perfil.modelo,
            max_tokens=MAX_TOKENS,
            system=self.system,
            tools=self.herramientas,
            messages=historia,
            thinking={"type": "adaptive"},
            output_config={"effort": self.perfil.esfuerzo},
            # Caché automático hasta el último bloque: cada vuelta del loop reutiliza el historial
            # de la anterior. Se suma a los puntos fijos del system y de las herramientas.
            cache_control={"type": "ephemeral"},
        )
        if forzar_final:
            params["tool_choice"] = {"type": "none"}
        if self.fallbacks:
            params["betas"] = [BETA_FALLBACK]
            params["fallbacks"] = "default"

        for intento in range(REINTENTOS_JSON + 1):
            emitido = False
            try:
                with self.cliente.beta.messages.stream(**params) as stream:
                    for ev in stream:
                        if ev.type == "text" and ev.text:
                            emitido = True
                            yield {"tipo": "texto", "texto": ev.text}
                        self._latir()
                    return stream.get_final_message()
            except ValueError:
                # JSON de herramienta que el SDK no pudo interpretar: no hay tool_use_id que
                # responder, se repite la llamada. Los errores de la API no son ValueError.
                if emitido:
                    yield {"tipo": "reinicio"}
                if intento == REINTENTOS_JSON:
                    yield {"tipo": "error", "mensaje": "El modelo generó una llamada inválida varias veces."}
                    return None
            except anthropic.RateLimitError:
                yield {"tipo": "error", "mensaje": "Hay demasiados pedidos en este momento. Probá en un minuto."}
                return None
            except anthropic.APIConnectionError:
                yield {"tipo": "error", "mensaje": "No se pudo conectar con el modelo. Probá de nuevo."}
                return None
            except anthropic.APIStatusError as e:
                yield {"tipo": "error", "mensaje": f"Error del servicio del modelo ({e.status_code})."}
                return None
        return None

    # ------------------------------------------------------------ herramientas
    def _ejecutar_pendientes(self, conv_id: str, historia: list[dict], ejecutadas: int):
        """Responde los tool_use del último mensaje. Devuelve (ejecutadas, tool_use que pausa o None).

        Si hay que pausar por aclaraciones, los demás pasos quedan guardados pero no se agrega el
        mensaje de resultados: se arma completo cuando llega la respuesta del usuario."""
        limite = self.perfil.limites.max_herramientas_por_turno
        guardados = self.almacen.pasos(conv_id)
        resultados = []
        pausa = None
        for uso in _pendientes(historia):
            tid, nombre, args = uso["id"], uso["name"], uso.get("input")
            paso = guardados.get(tid)
            reutilizado = paso is not None
            if nombre == clarify.NOMBRE and paso is None and nombre in self.perfil.herramientas:
                error = self._validar(nombre, args)
                if error is None and pausa is None:
                    pausa = uso  # se responde cuando el usuario conteste
                    continue
                paso = Paso(tid, nombre, args if isinstance(args, dict) else {},
                            error or json.dumps({"error": "Solo se puede pedir una aclaración por vez."},
                                                ensure_ascii=False), True, 0)
                self.almacen.guardar_paso(conv_id, paso)
                guardados[tid] = paso
            yield {"tipo": "herramienta_inicio", "id": tid, "nombre": nombre, "argumentos": _resumen(args)}
            eventos: list[dict] = []
            if paso is None:
                if ejecutadas >= limite:
                    paso = Paso(tid, nombre, args if isinstance(args, dict) else {},
                                json.dumps({"error": f"No se ejecutó: se alcanzó el límite de {limite} "
                                                     "herramientas en este turno."}, ensure_ascii=False),
                                True, 0)
                else:
                    paso = self._ejecutar(conv_id, historia, guardados, tid, nombre, args, eventos)
                    ejecutadas += 1
                self.almacen.guardar_paso(conv_id, paso)
                guardados[tid] = paso
            else:
                ejecutadas += 1
            self._latir(forzar=True)
            yield {"tipo": "herramienta_fin", "id": tid, "nombre": nombre, "duracion_ms": paso.duracion_ms,
                   "es_error": paso.es_error, "reutilizado": reutilizado, "filas": _filas(paso.resultado)}
            yield from eventos
            r = {"type": "tool_result", "tool_use_id": tid, "content": paso.resultado}
            if paso.es_error:
                r["is_error"] = True
            resultados.append(r)
        if pausa is not None:
            return ejecutadas, pausa
        if ejecutadas >= limite:
            resultados.append({"type": "text", "text": f"[Sistema] Se alcanzó el límite de {limite} "
                               f"herramientas en este turno. {_CIERRE}"})
        self._agregar(conv_id, historia, "user", resultados)
        return ejecutadas, None

    def _validar(self, nombre: str, args):
        """None si la entrada es válida; si no, el resultado de error para el modelo."""
        try:
            registro.modelo_de(nombre).model_validate(args if isinstance(args, dict) else {})
            return None
        except ValidationError as e:
            return _error_validacion(e, args)

    def _ejecutar(self, conv_id: str, historia: list[dict], pasos: dict, tid: str, nombre: str, args,
                  eventos: list[dict]) -> Paso:
        inicio = time.monotonic()

        def paso(resultado: str, es_error: bool) -> Paso:
            if len(resultado) > MAX_RESULTADO:
                resultado = resultado[:MAX_RESULTADO] + "\n[resultado recortado: pedí menos filas o agregá en SQL]"
            return Paso(tid, nombre, args if isinstance(args, dict) else {"_crudo": args}, resultado,
                        es_error, int((time.monotonic() - inicio) * 1000))

        if nombre not in self.perfil.herramientas:
            return paso(json.dumps({"error": f"La herramienta {nombre} no está disponible en este perfil."},
                                   ensure_ascii=False), True)
        try:
            validado = registro.modelo_de(nombre).model_validate(args if isinstance(args, dict) else {})
        except ValidationError as e:
            return paso(_error_validacion(e, args), True)
        try:
            if nombre in registro.HERRAMIENTAS_AGENTE:
                tc = ContextoTurno(self.almacen, self.almacen.conversacion(conv_id), self.perfil.id,
                                   self.perfil.nombre, tid, historia, pasos, frozenset(registro.HERRAMIENTAS))
                resultado = registro.HERRAMIENTAS_AGENTE[nombre].ejecutar(tc, validado)
                eventos.extend(tc.eventos)
            else:
                ctx = replace(self.ctx, auditor=self._auditor(nombre))
                resultado = registro.HERRAMIENTAS[nombre](ctx, **validado.model_dump(exclude_unset=True))
        except Exception as e:  # error de base u otro: se informa al modelo como error de herramienta
            return paso(json.dumps({"error": _mensaje_error(e)}, ensure_ascii=False), True)
        try:
            datos = json.loads(resultado)
        except ValueError:
            datos = None
        return paso(resultado, isinstance(datos, dict) and "error" in datos)

    def _responder_sin_ejecutar(self, conv_id, historia, usos, motivo, texto: str | None = None):
        contenido = [{"type": "tool_result", "tool_use_id": u["id"], "is_error": True,
                      "content": json.dumps({"error": motivo}, ensure_ascii=False)} for u in usos]
        if texto:
            contenido.append({"type": "text", "text": texto})
        self._agregar(conv_id, historia, "user", contenido)

    # ------------------------------------------------------------ auditoría
    def _registrar_uso(self, modelo: str, d: dict) -> None:
        try:
            self.almacen.registrar_uso(RegistroUso(self._conv.usuario, self.perfil.id, self._conv.id, modelo, **d))
        except Exception:
            log.exception("no se pudo registrar el uso de tokens")

    def _auditor(self, herramienta: str):
        def auditar(*, sql, parametros, duracion_ms, filas, error):
            self.almacen.registrar_consulta(RegistroConsulta(
                self._conv.usuario, self.perfil.id, self._conv.id, herramienta, sql, parametros, duracion_ms,
                filas, error))
        return auditar

    # ------------------------------------------------------------ persistencia
    def _agregar(self, conv_id: str, historia: list[dict], rol: str, contenido: list[dict]) -> None:
        self.almacen.agregar_mensaje(conv_id, rol, contenido)
        historia.append({"role": rol, "content": contenido})

    def _latir(self, forzar: bool = False) -> None:
        ahora = time.monotonic()
        if forzar or ahora - self._ultimo_latido > LATIDO_SEG:
            self._ultimo_latido = ahora
            self.almacen.latido(self._conv_actual)
