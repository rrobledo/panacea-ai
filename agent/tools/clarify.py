"""
Aclaraciones obligatorias antes de un reporte.

`solicitar_aclaraciones` no se ejecuta como las demás herramientas: el loop corta el turno, deja el
tool_use pendiente y el usuario responde con POST /api/clarify (o con un mensaje libre, que cuenta
como ajuste). Este módulo define la entrada, su validación y el tool_result que recibe el modelo.
"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NOMBRE = "solicitar_aclaraciones"

DESCRIPCION = """Pide al usuario que confirme el alcance de un reporte antes de generarlo. Es OBLIGATORIA
antes de generar_artifact: sin el brief_id aprobado que devuelve, no se puede crear ningún reporte.

Mandá un brief con lo que vas a generar (título, objetivo, período, secciones, métricas, audiencia) y
hasta 6 preguntas sobre lo que no esté claro, cada una con la opción que recomendás. Si no hay dudas,
mandá preguntas vacía: el usuario igual tiene que aprobar el brief.

El turno se pausa hasta que el usuario responda. El resultado trae la decisión:
- "aprobado": incluye brief_id y las respuestas. Generá el reporte con generar_artifact y ese brief_id.
- "ajustar": incluye el comentario del usuario y no trae brief_id. Corregí el brief y volvé a llamar
  a esta herramienta; no generes el reporte todavía.

Antes de llamarla, hacé las consultas que necesites para proponer un brief concreto (por ejemplo, el
rango de fechas disponible). No la uses para preguntas que no sean sobre un reporte."""


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BriefPropuesto(_Estricto):
    titulo: str = Field(min_length=3, max_length=200)
    objetivo: str = Field(min_length=3, max_length=1000, description="Para qué se usa el reporte")
    periodo: str = Field(max_length=200, description="Ej. 'enero a octubre 2026 vs mismo período 2025'")
    secciones: list[str] = Field(min_length=1, max_length=20)
    metricas: list[str] = Field(min_length=1, max_length=20)
    audiencia: str = Field(max_length=200, description="Ej. 'gerencia', 'encargados de sucursal'")


class Pregunta(_Estricto):
    id: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    texto: str = Field(min_length=3, max_length=500)
    tipo: Literal["opcion", "multiple", "texto", "fecha"]
    opciones: list[str] = Field(default_factory=list, max_length=8,
                                description="Obligatorias para 'opcion' y 'multiple' (2 a 8)")
    recomendada: str | list[str] | None = Field(None, description="Opción sugerida; lista para 'multiple'")

    @model_validator(mode="after")
    def _coherencia(self):
        if self.tipo in ("opcion", "multiple"):
            if len(self.opciones) < 2:
                raise ValueError(f"la pregunta {self.id} es de tipo {self.tipo} y necesita al menos 2 opciones")
            recomendadas = self.recomendada if isinstance(self.recomendada, list) else (
                [self.recomendada] if self.recomendada is not None else [])
            if self.tipo == "opcion" and isinstance(self.recomendada, list):
                raise ValueError(f"la pregunta {self.id} admite una sola recomendada")
            fuera = [r for r in recomendadas if r not in self.opciones]
            if fuera:
                raise ValueError(f"la recomendada de {self.id} no está entre las opciones: {fuera}")
        elif self.opciones:
            raise ValueError(f"la pregunta {self.id} es de tipo {self.tipo} y no lleva opciones")
        return self


class EntradaAclaraciones(_Estricto):
    brief: BriefPropuesto
    preguntas: list[Pregunta] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _ids(self):
        ids = [p.id for p in self.preguntas]
        if len(set(ids)) != len(ids):
            raise ValueError("ids de pregunta repetidos")
        return self


class RespuestaInvalida(ValueError):
    pass


def completar_respuestas(entrada: EntradaAclaraciones, respuestas: dict) -> dict:
    """Valida las respuestas del usuario y completa las faltantes con la opción recomendada."""
    por_id = {p.id: p for p in entrada.preguntas}
    desconocidas = sorted(set(respuestas) - set(por_id))
    if desconocidas:
        raise RespuestaInvalida(f"Preguntas inexistentes: {', '.join(desconocidas)}")
    out = {}
    for p in entrada.preguntas:
        r = respuestas.get(p.id, p.recomendada)
        if r is None or r == "" or r == []:
            out[p.id] = None
            continue
        if p.tipo == "multiple":
            r = r if isinstance(r, list) else [r]
            if not all(isinstance(x, str) for x in r):
                raise RespuestaInvalida(f"{p.id}: se esperaban textos")
        elif not isinstance(r, str):
            raise RespuestaInvalida(f"{p.id}: se esperaba un texto")
        out[p.id] = r
    return out


def resultado(decision: Literal["aprobado", "ajustar"], respuestas: dict, entrada: EntradaAclaraciones | None,
              comentario: str | None = None, brief_id: str | None = None) -> str:
    """tool_result de solicitar_aclaraciones. El brief_id solo viaja si el usuario aprobó."""
    preguntas = {p.id: p.texto for p in entrada.preguntas} if entrada else {}
    r = {"decision": decision,
         "respuestas": [{"id": k, "pregunta": preguntas.get(k, ""), "respuesta": v} for k, v in respuestas.items()]}
    if comentario:
        r["comentario"] = comentario
    if decision == "aprobado":
        r["brief_id"] = brief_id
        r["instruccion"] = ("El usuario aprobó el brief. Hacé las consultas que falten y generá el reporte "
                            "con generar_artifact usando este brief_id, respetando las respuestas.")
    else:
        r["instruccion"] = ("El usuario pidió cambios. Ajustá el brief según el comentario y volvé a llamar a "
                            "solicitar_aclaraciones; no generes el reporte todavía.")
    return json.dumps(r, ensure_ascii=False)
