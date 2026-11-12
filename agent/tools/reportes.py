"""
Herramientas de reportes: generar_artifact y editar_artifact.

A diferencia de las herramientas de datos, necesitan la conversación (brief aprobado, autor, perfil)
y el almacén, así que reciben un ContextoTurno. No se exponen por el servidor MCP.
"""

import json
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent.almacen import Almacen, Conversacion, Paso
from agent.artifacts import ArtifactInvalido, componer, validar_html

Formato = Literal["moneda", "moneda2", "numero", "decimal", "porcentaje"]


@dataclass
class ContextoTurno:
    almacen: Almacen
    conversacion: Conversacion
    perfil_id: str
    perfil_nombre: str
    tool_use_id: str
    historia: list[dict]
    pasos: dict[str, Paso]
    herramientas_datos: frozenset[str]
    eventos: list[dict] = field(default_factory=list)  # se emiten por SSE después del paso


# ---------------------------------------------------------------- entrada
class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Kpi(_Estricto):
    etiqueta: str = Field(max_length=80)
    valor: float
    formato: Formato = "numero"
    variacion: float | None = Field(None, description="Variación como fracción: 0.12 = +12%")
    comparacion: str = Field("", max_length=120, description="Ej. 'vs oct 2025'")


class Serie(_Estricto):
    nombre: str = Field(max_length=80)
    datos: list[float | None] = Field(max_length=500)
    tipo: Literal["line", "bar"] | None = Field(None, description="Para combinar barras y líneas")
    rol: Literal["normal", "proyeccion", "banda_min", "banda_max"] = Field(
        "normal", description="proyeccion = línea punteada; banda_min y banda_max (en ese orden, después de "
                              "la proyección) dibujan el rango sombreado")


class Grafico(_Estricto):
    tipo: Literal["line", "bar", "doughnut", "pie"]
    etiquetas: list[str] = Field(max_length=500)
    series: list[Serie] = Field(min_length=1, max_length=12)
    formato: Formato = "numero"
    apilado: bool = False
    titulo: str = ""
    nota: str = Field("", max_length=500, description="Lectura del gráfico, debajo de él")

    @model_validator(mode="after")
    def _largos(self):
        for s in self.series:
            if len(s.datos) != len(self.etiquetas):
                raise ValueError(f"la serie {s.nombre!r} tiene {len(s.datos)} datos y hay "
                                 f"{len(self.etiquetas)} etiquetas")
        return self


class TablaDatos(_Estricto):
    columnas: list[str] = Field(min_length=1, max_length=20)
    filas: list[list[str | float | None]] = Field(max_length=500)
    formatos: list[Literal["texto", "moneda", "moneda2", "numero", "decimal", "porcentaje"]] = Field(
        default_factory=list, description="Uno por columna; 'texto' para las no numéricas")


class Seccion(_Estricto):
    titulo: str = Field(max_length=200)
    texto: str = Field("", max_length=8000, description="Párrafos; '- ' para viñetas; **negrita**")
    grafico: Grafico | None = None
    tabla: TablaDatos | None = None
    html: str = Field("", max_length=60_000, description="HTML propio (ej. mapa de calor). Sin scripts "
                      "externos salvo cdn.jsdelivr.net; usá las clases y variables CSS de la plantilla")


class Estrategia(_Estricto):
    titulo: str = Field(max_length=200)
    dato: str = Field(description="Dato que la respalda")
    accion: str = Field(description="Acción concreta")
    impacto: str = Field(description="Impacto estimado en ARS o %")
    kpi: str = Field(description="KPI para medirla")
    prioridad: Literal["alta", "media", "baja"]


class _Contenido(_Estricto):
    titulo: str = Field(min_length=3, max_length=200)
    subtitulo: str = Field("", max_length=500)
    periodo: str = Field("", max_length=200)
    resumen: list[str] = Field(default_factory=list, max_length=8, description="3 a 5 hallazgos")
    kpis: list[Kpi] = Field(default_factory=list, max_length=12)
    secciones: list[Seccion] = Field(default_factory=list, max_length=20)
    estrategias: list[Estrategia] = Field(default_factory=list, max_length=12)
    nota_metodologica: str = Field("", max_length=4000)


class EntradaGenerar(_Contenido):
    brief_id: str
    tipo: Literal["reporte", "tablero", "tabla"] = "reporte"


class EntradaEditar(_Estricto):
    artifact_id: str
    nota: str = Field(min_length=3, max_length=500, description="Qué cambió en esta versión")
    titulo: str | None = Field(None, min_length=3, max_length=200)
    subtitulo: str | None = None
    periodo: str | None = None
    resumen: list[str] | None = Field(None, max_length=8)
    kpis: list[Kpi] | None = Field(None, max_length=12)
    secciones: list[Seccion] | None = Field(None, max_length=20)
    estrategias: list[Estrategia] | None = Field(None, max_length=12)
    nota_metodologica: str | None = None


DESCRIPCION_GENERAR = """Crea un reporte HTML guardado y versionado (versión 1) que el usuario ve en el chat y
en la galería. Requiere el brief_id que devuelve solicitar_aclaraciones cuando el usuario aprueba; sin
él, falla.

Mandá el contenido estructurado y el backend lo arma sobre la plantilla de Panacea (modo claro y
oscuro, Chart.js, formato es-AR):
- resumen: 3 a 5 hallazgos, cada uno una oración con su número.
- kpis: valor crudo (sin formatear) + formato + variación como fracción.
- secciones: texto, y opcionalmente un gráfico (series con los valores), una tabla o HTML propio.
  Para una proyección usá una serie rol "proyeccion" seguida de "banda_min" y "banda_max".
- estrategias: dato → acción → impacto → KPI → prioridad.
- nota_metodologica: fuentes, exclusiones, supuestos y error de la proyección.
Todos los números tienen que salir de herramientas ejecutadas en esta conversación: las consultas
quedan registradas como fuentes de la versión. Nunca incluyas credenciales ni datos de conexión."""

DESCRIPCION_EDITAR = """Crea una nueva versión de un reporte existente del mismo perfil, sin pedir aclaraciones
de nuevo. Las versiones anteriores se conservan.

Mandá artifact_id, una nota breve de qué cambió y solo los campos que cambian: cada campo enviado
reemplaza completo al de la versión anterior (por ejemplo, para agregar una sección mandá la lista
completa de secciones) y los omitidos se mantienen. Usala cuando el usuario pida cambios sobre un
reporte ya generado; si pide un reporte distinto, empezá con solicitar_aclaraciones."""


# ---------------------------------------------------------------- ejecución
def _error(mensaje: str) -> str:
    return json.dumps({"error": mensaje}, ensure_ascii=False)


def datos_fuente(tc: ContextoTurno) -> list[dict]:
    """Herramientas de datos ejecutadas sin error desde la última versión creada en la conversación."""
    fuentes: list[dict] = []
    for m in tc.historia:
        if m["role"] != "assistant" or not isinstance(m["content"], list):
            continue
        for b in m["content"]:
            if b.get("type") != "tool_use":
                continue
            paso = tc.pasos.get(b["id"])
            if paso is None or paso.es_error:
                continue
            if b["name"] in ("generar_artifact", "editar_artifact"):
                fuentes = []
            elif b["name"] in tc.herramientas_datos:
                f = {"herramienta": b["name"], "argumentos": paso.argumentos, "tool_use_id": b["id"]}
                if b["name"] == "consultar":
                    f["sql"] = paso.argumentos.get("sql")
                fuentes.append(f)
    return fuentes


def _publicar(tc: ContextoTurno, artifact, version: int) -> str:
    url = f"/artifacts/{artifact.id}"
    tc.eventos.append({"tipo": "artifact", "id": artifact.id, "version": version, "titulo": artifact.titulo,
                       "artifact_tipo": artifact.tipo, "url": url})
    return json.dumps({"artifact_id": artifact.id, "version": version, "titulo": artifact.titulo, "url": url,
                       "mensaje": "Reporte guardado. Contale al usuario los hallazgos principales en el chat; "
                                  "el enlace ya se le muestra."}, ensure_ascii=False)


def _ya_creada(tc: ContextoTurno) -> str | None:
    """Un turno retomado puede repetir la llamada: se devuelve la versión que ya creó."""
    v = tc.almacen.version_de_tool_use(tc.tool_use_id)
    if v is None:
        return None
    a = tc.almacen.artifact(v.artifact_id)
    return _publicar(tc, a, v.version)


def generar_artifact(tc: ContextoTurno, entrada: EntradaGenerar) -> str:
    brief = tc.almacen.brief(entrada.brief_id)
    if brief is None or brief.estado != "aprobado":
        return _error("No hay un brief aprobado con ese brief_id. Primero llamá a solicitar_aclaraciones y "
                      "esperá que el usuario apruebe; usá el brief_id que te devuelve.")
    if brief.conversacion_id != tc.conversacion.id:
        return _error("Ese brief_id se aprobó en otra conversación. Pedí aclaraciones en esta conversación "
                      "con solicitar_aclaraciones.")
    if (hecho := _ya_creada(tc)) is not None:
        return hecho
    contenido = entrada.model_dump(exclude={"brief_id", "tipo"})
    try:
        documento = componer(contenido, perfil=tc.perfil_nombre)
        validar_html(documento)
    except ArtifactInvalido as e:
        return _error(f"Reporte rechazado: {e}. Corregí el contenido y volvé a llamar.")
    a = tc.almacen.crear_artifact(titulo=entrada.titulo, tipo=entrada.tipo, perfil=tc.perfil_id,
                                  autor=tc.conversacion.usuario, conversacion_id=tc.conversacion.id,
                                  brief_id=brief.id, html=documento, contenido=contenido,
                                  datos_fuente=datos_fuente(tc), tool_use_id=tc.tool_use_id)
    return _publicar(tc, a, 1)


def editar_artifact(tc: ContextoTurno, entrada: EntradaEditar) -> str:
    a = tc.almacen.artifact(entrada.artifact_id)
    if a is None:
        return _error("No existe un reporte con ese artifact_id.")
    if a.perfil != tc.perfil_id:
        return _error(f"El reporte es del perfil {a.perfil} y esta conversación es del perfil {tc.perfil_id}: "
                      "no se puede editar desde acá.")
    if (hecho := _ya_creada(tc)) is not None:
        return hecho
    anterior = tc.almacen.version(a.id)
    cambios = entrada.model_dump(exclude={"artifact_id", "nota"}, exclude_none=True)
    contenido = _Contenido.model_validate({**anterior.contenido, **cambios}).model_dump()
    try:
        documento = componer(contenido, perfil=tc.perfil_nombre)
        validar_html(documento)
    except ArtifactInvalido as e:
        return _error(f"Versión rechazada: {e}. Corregí el contenido y volvé a llamar.")
    a = tc.almacen.agregar_version(a.id, html=documento, nota=entrada.nota, contenido=contenido,
                                   datos_fuente=datos_fuente(tc), tool_use_id=tc.tool_use_id,
                                   titulo=cambios.get("titulo"))
    return _publicar(tc, a, a.version_actual)
