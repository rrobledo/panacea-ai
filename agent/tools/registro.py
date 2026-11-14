"""
Registro de herramientas.

- HERRAMIENTAS (de datos): nombre → función. Cada función recibe un ContextoPerfil como primer
  parámetro. `vincular` lo fija y devuelve una función con la firma pública (sin el contexto),
  que es lo que necesitan el servidor MCP y el esquema para la Messages API.
- HERRAMIENTAS_AGENTE: aclaraciones y reportes. Solo existen en la app web: necesitan la
  conversación y el almacén, tienen su propio modelo de entrada y no se exponen por MCP.
"""

import copy
import functools
import inspect
import typing
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, create_model

from agent.contexto import ContextoPerfil
from agent.tools import clarify, externas, generic, reportes, ventas

# Mismo orden que el servidor MCP original.
HERRAMIENTAS: dict[str, typing.Callable[..., str]] = {
    f.__name__: f for f in (
        generic.describir_tabla,
        ventas.perfil_datos,
        ventas.resumen_ventas,
        ventas.comparar_periodos,
        ventas.clientes_inactivos,
        ventas.productos_asociados,
        ventas.proyectar_ventas,
        generic.consultar,
        externas.ventas_con_contexto,
        externas.impacto_variables,
        externas.contexto_proximos_dias,
    )
}




@dataclass(frozen=True)
class HerramientaAgente:
    descripcion: str
    entrada: type[BaseModel]
    # None = la ejecuta el loop (solicitar_aclaraciones pausa el turno)
    ejecutar: typing.Callable[[reportes.ContextoTurno, BaseModel], str] | None


HERRAMIENTAS_AGENTE: dict[str, HerramientaAgente] = {
    clarify.NOMBRE: HerramientaAgente(clarify.DESCRIPCION, clarify.EntradaAclaraciones, None),
    "generar_artifact": HerramientaAgente(reportes.DESCRIPCION_GENERAR, reportes.EntradaGenerar,
                                          reportes.generar_artifact),
    "editar_artifact": HerramientaAgente(reportes.DESCRIPCION_EDITAR, reportes.EntradaEditar,
                                         reportes.editar_artifact),
}


def existe(nombre: str) -> bool:
    return nombre in HERRAMIENTAS or nombre in HERRAMIENTAS_AGENTE


def _firma_publica(fn) -> inspect.Signature:
    hints = typing.get_type_hints(fn)
    sig = inspect.signature(fn)
    params = [p.replace(annotation=hints.get(p.name, p.annotation))
              for p in list(sig.parameters.values())[1:]]
    return sig.replace(parameters=params, return_annotation=hints.get("return", sig.return_annotation))


def vincular(fn, ctx: ContextoPerfil):
    """Devuelve fn con el contexto fijado y la firma sin el parámetro ctx."""
    @functools.wraps(fn)
    def envoltura(*args, **kwargs):
        return fn(ctx, *args, **kwargs)

    firma = _firma_publica(fn)
    del envoltura.__wrapped__
    envoltura.__signature__ = firma
    envoltura.__annotations__ = {p.name: p.annotation for p in firma.parameters.values()}
    envoltura.__annotations__["return"] = firma.return_annotation
    return envoltura


def descripcion(fn) -> str:
    return inspect.cleandoc(fn.__doc__ or "")


@functools.cache
def modelo_entrada(fn) -> type[BaseModel]:
    """Modelo pydantic de los parámetros públicos: valida la entrada del modelo antes de ejecutar."""
    campos = {}
    for p in _firma_publica(fn).parameters.values():
        defecto = ... if p.default is inspect.Parameter.empty else p.default
        campos[p.name] = (p.annotation, defecto)
    return create_model(f"{fn.__name__}_args", __config__=ConfigDict(extra="forbid"), **campos)


def _limpiar(nodo, defs):
    """Resuelve $ref locales y quita los 'title' que agrega pydantic: esquema plano y más corto."""
    if isinstance(nodo, list):
        return [_limpiar(x, defs) for x in nodo]
    if not isinstance(nodo, dict):
        return nodo
    if "$ref" in nodo:
        return _limpiar(copy.deepcopy(defs[nodo["$ref"].rsplit("/", 1)[-1]]), defs)
    out = {}
    for k, v in nodo.items():
        if k in ("$defs", "title"):
            continue
        out[k] = {p: _limpiar(x, defs) for p, x in v.items()} if k == "properties" else _limpiar(v, defs)
    return out


def esquema_modelo(modelo: type[BaseModel]) -> dict:
    esquema = modelo.model_json_schema()
    return _limpiar(esquema, esquema.get("$defs", {}))


def esquema_entrada(fn) -> dict:
    """JSON Schema de los parámetros públicos, para el campo input_schema de la Messages API."""
    return esquema_modelo(modelo_entrada(fn))


def modelo_de(nombre: str) -> type[BaseModel]:
    return HERRAMIENTAS_AGENTE[nombre].entrada if nombre in HERRAMIENTAS_AGENTE else modelo_entrada(HERRAMIENTAS[nombre])


def definiciones(nombres: list[str]) -> list[dict]:
    """Definiciones de herramientas para la Messages API (solo las indicadas)."""
    desconocidas = [n for n in nombres if not existe(n)]
    if desconocidas:
        raise ValueError(f"Herramientas inexistentes: {desconocidas}")
    out = []
    for n in nombres:
        if n in HERRAMIENTAS_AGENTE:
            h = HERRAMIENTAS_AGENTE[n]
            out.append({"name": n, "description": h.descripcion, "input_schema": esquema_modelo(h.entrada)})
        else:
            out.append({"name": n, "description": descripcion(HERRAMIENTAS[n]),
                        "input_schema": esquema_entrada(HERRAMIENTAS[n])})
    return out
