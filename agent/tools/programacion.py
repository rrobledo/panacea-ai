"""
cambiar_programacion: única herramienta que escribe en la base. Cambia el plan diario de
costos_programacion (columna plan) en filas que ya existen, desde hoy en adelante.

Flujo en dos pasos, con la confirmación exigida por el código y no solo por el prompt:
1. Sin codigo_confirmacion: valida, lee el plan actual y devuelve la propuesta con un código que
   depende de las filas, el plan actual y el plan nuevo. No escribe nada.
2. Con codigo_confirmacion: solo aplica si el código coincide con los mismos cambios, si la propuesta
   está en esta conversación y si el usuario escribió un mensaje después de verla. El UPDATE comprueba
   que el plan no haya cambiado desde la propuesta (otro usuario o la app de producción).

Escribe con un rol aparte (escritura.credencial_env del perfil) que solo tiene UPDATE sobre plan.
"""

import hashlib
import json
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from agent.tools.base import a_json, ejecutar

NOMBRE = "cambiar_programacion"
ZONA = ZoneInfo("America/Argentina/Cordoba")
MAX_CAMBIOS = 200
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CambioPlan(_Estricto):
    producto_id: int = Field(ge=1, description="id de costos_productos")
    fecha: date = Field(description="Día del plan, AAAA-MM-DD; hoy o posterior")
    plan: int = Field(ge=0, le=100_000, description="Unidades planificadas nuevas")


class EntradaProgramacion(_Estricto):
    cambios: list[CambioPlan] = Field(min_length=1, max_length=MAX_CAMBIOS)
    codigo_confirmacion: str | None = Field(
        None, pattern=r"^[A-F0-9]{8}$",
        description="Solo en la segunda llamada: el código que devolvió la propuesta, después de que el "
                    "usuario la confirmó en el chat")


DESCRIPCION = f"""Cambia el plan diario de producción (costos_programacion.plan) de uno o más productos, desde
hoy en adelante, sobre filas de programación que ya existen. Es la única herramienta que escribe datos.

Siempre en dos pasos:
1. Llamala sin codigo_confirmacion: no escribe nada, valida y devuelve la propuesta (producto, fecha,
   plan actual y plan nuevo) con un codigo_confirmacion. Mostrale la tabla completa al usuario y
   preguntale si confirma. Terminá tu respuesta ahí.
2. Solo si el usuario responde que confirma, llamala de nuevo con exactamente los mismos cambios y el
   codigo_confirmacion. Si pide ajustes, volvé al paso 1 con los cambios nuevos.

No sirve para fechas pasadas, para lo producido (prod) ni para crear filas: la programación de cada mes
se genera desde la app de producción. Máximo {MAX_CAMBIOS} cambios por llamada."""


def _hoy() -> date:
    return datetime.now(ZONA).date()


def _codigo(filas: list[dict]) -> str:
    base = sorted((f["programacion_id"], f["plan_actual"], f["plan_nuevo"]) for f in filas)
    return hashlib.sha256(json.dumps(base).encode()).hexdigest()[:8].upper()


def _textos(contenido) -> list[str]:
    if isinstance(contenido, str):
        return [contenido]
    return [b.get("text", "") for b in contenido or [] if isinstance(b, dict) and b.get("type") == "text"]


def _confirmada_en_el_chat(historia: list[dict], codigo: str) -> bool:
    """La propuesta con ese código está en la conversación y hay un mensaje del usuario después."""
    marca = f'"codigo_confirmacion": "{codigo}"'
    propuesta = None
    for i, m in enumerate(historia):
        if m.get("role") != "user" or isinstance(m.get("content"), str):
            continue
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                cont = b.get("content")
                cont = cont if isinstance(cont, str) else json.dumps(cont, ensure_ascii=False)
                if marca in cont and '"estado": "propuesta"' in cont:
                    propuesta = i
    if propuesta is None:
        return False
    return any(m.get("role") == "user" and any(t.strip() for t in _textos(m.get("content")))
               for m in historia[propuesta + 1:])


def _error(mensaje: str, **extra) -> str:
    return a_json({"error": mensaje, **extra})


def cambiar_programacion(tc, entrada: EntradaProgramacion) -> str:
    ctx = tc.datos
    if ctx is None or tc.escritura is None:
        return _error("Este perfil no tiene permiso para cambiar la programación.")
    hoy = _hoy()
    claves = [(c.producto_id, c.fecha) for c in entrada.cambios]
    repetidos = sorted({f"{p} {f}" for p, f in claves if claves.count((p, f)) > 1})
    if repetidos:
        return _error(f"Hay cambios repetidos para el mismo producto y fecha: {', '.join(repetidos)}.")
    pasadas = sorted({str(c.fecha) for c in entrada.cambios if c.fecha < hoy})
    if pasadas:
        return _error(f"Solo se puede cambiar el plan desde hoy ({hoy}) en adelante. Fechas pasadas: {', '.join(pasadas)}.")

    ids = sorted({c.producto_id for c in entrada.cambios})
    productos = {pid: (nombre, habilitado) for pid, nombre, habilitado in ejecutar(
        ctx, "SELECT id, nombre, habilitado FROM public.costos_productos WHERE id = ANY(:ids)",
        {"ids": ids}, max_filas=MAX_CAMBIOS)["filas"]}
    desconocidos = [p for p in ids if p not in productos]
    if desconocidos:
        return _error(f"Productos inexistentes en costos_productos: {desconocidos}.")
    deshabilitados = [f"{p} {productos[p][0]}" for p in ids if not productos[p][1]]
    if deshabilitados:
        return _error(f"Productos deshabilitados: {', '.join(deshabilitados)}.")

    fechas = [c.fecha for c in entrada.cambios]
    actuales = {(pid, date.fromisoformat(f) if isinstance(f, str) else f): (rid, plan, prod)
                for rid, pid, f, plan, prod in ejecutar(
                    ctx, "SELECT id, producto_id, fecha, plan, prod FROM public.costos_programacion "
                         "WHERE producto_id = ANY(:ids) AND fecha BETWEEN :d AND :h",
                    {"ids": ids, "d": min(fechas), "h": max(fechas)}, max_filas=20_000)["filas"]}
    sin_fila = [f"{productos[c.producto_id][0]} {c.fecha}" for c in entrada.cambios
                if (c.producto_id, c.fecha) not in actuales]
    if sin_fila:
        return _error("No hay fila de programación para: " + ", ".join(sin_fila)
                      + ". La programación de cada mes se genera desde la app de producción.")

    filas, sin_cambio = [], 0
    for c in sorted(entrada.cambios, key=lambda c: (c.fecha, productos[c.producto_id][0])):
        rid, plan_actual, prod = actuales[(c.producto_id, c.fecha)]
        if plan_actual == c.plan:
            sin_cambio += 1
            continue
        filas.append({"programacion_id": rid, "producto_id": c.producto_id, "producto": productos[c.producto_id][0],
                      "fecha": c.fecha.isoformat(), "dia": DIAS[c.fecha.weekday()], "plan_actual": plan_actual,
                      "plan_nuevo": c.plan, "producido": prod})
    if not filas:
        return a_json({"estado": "sin_cambios", "mensaje": "El plan ya tiene esos valores: no hay nada que cambiar."})
    codigo = _codigo(filas)
    columnas = ["producto_id", "producto", "fecha", "dia", "plan_actual", "plan_nuevo", "producido"]

    if entrada.codigo_confirmacion is None:
        return a_json({
            "estado": "propuesta", "codigo_confirmacion": codigo, "columnas": columnas,
            "cambios": [[f[c] for c in columnas] for f in filas], "sin_cambio": sin_cambio,
            "instruccion": "No se escribió nada. Mostrale esta tabla completa al usuario y preguntale si confirma. "
                           "Terminá la respuesta ahí. Solo si confirma, volvé a llamar con los mismos cambios "
                           "y este codigo_confirmacion."})

    if entrada.codigo_confirmacion != codigo:
        return _error("Los cambios o el plan actual no coinciden con la propuesta confirmada (puede haberlo "
                      "modificado otra persona). Volvé a llamar sin codigo_confirmacion para armar una propuesta nueva.")
    if not _confirmada_en_el_chat(tc.historia, codigo):
        return _error("Falta la confirmación del usuario: mostrale la propuesta, esperá que responda y recién "
                      "después llamá con codigo_confirmacion.")

    sql = ("UPDATE public.costos_programacion SET plan = :plan "
           "WHERE id = :id AND plan IS NOT DISTINCT FROM :actual RETURNING id")
    parametros = {"usuario": tc.conversacion.usuario, "conversacion": tc.conversacion.id, "codigo": codigo,
                  "cambios": [{"id": f["programacion_id"], "plan_actual": f["plan_actual"], "plan": f["plan_nuevo"]}
                              for f in filas]}
    inicio = time.monotonic()
    try:
        with tc.escritura().begin() as conn:
            conn.execute(text(f"SET LOCAL statement_timeout = {int(ctx.timeout_sql_seg) * 1000}"))
            for f in filas:
                ok = conn.execute(text(sql), {"plan": f["plan_nuevo"], "id": f["programacion_id"],
                                              "actual": f["plan_actual"]}).first()
                if ok is None:
                    raise _PlanModificado(f"{f['producto']} {f['fecha']}")
    except _PlanModificado as e:
        ctx.auditar(sql=sql, parametros=parametros, duracion_ms=_ms(inicio), filas=0, error=f"plan modificado: {e}")
        return _error(f"El plan de {e} cambió desde la propuesta: no se aplicó ningún cambio. Volvé a proponer.")
    except Exception as e:
        ctx.auditar(sql=sql, parametros=parametros, duracion_ms=_ms(inicio), filas=0, error=str(e)[:500])
        raise
    ctx.auditar(sql=sql, parametros=parametros, duracion_ms=_ms(inicio), filas=len(filas), error=None)
    return a_json({"estado": "aplicado", "cambios_aplicados": len(filas), "columnas": columnas,
                   "cambios": [[f[c] for c in columnas] for f in filas],
                   "mensaje": "Programación actualizada. La app de producción ya muestra los planes nuevos."})


class _PlanModificado(Exception):
    pass


def _ms(inicio: float) -> int:
    return int((time.monotonic() - inicio) * 1000)
