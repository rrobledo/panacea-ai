"""
Carga validada de config/lugares_venta.yaml y config/calendario_externo.yaml.

Ante un error lanza ErrorConfigExterna con el archivo y el campo, igual que los perfiles.
"""

import functools
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RAIZ = Path(__file__).resolve().parent.parent.parent
ARCHIVO_LUGARES = "config/lugares_venta.yaml"
ARCHIVO_CALENDARIO = "config/calendario_externo.yaml"

Estado = Literal["confirmado", "a_confirmar"]


class ErrorConfigExterna(Exception):
    pass


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------- lugares
class Lugar(_Estricto):
    id: int
    nombre: str
    localidad: str | None = None
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    perfil: Literal["residencial", "turistico", "eventos", "capital", "sin_ubicacion"]

    @model_validator(mode="after")
    def _coordenadas(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat y lon van juntas: cargá las dos o ninguna")
        return self

    @property
    def ubicado(self) -> bool:
        return self.lat is not None


class Lugares(_Estricto):
    zona_horaria: str = "America/Argentina/Cordoba"
    lugares: list[Lugar] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_unicos(self):
        ids = [l.id for l in self.lugares]
        repetidos = sorted({i for i in ids if ids.count(i) > 1})
        if repetidos:
            raise ValueError(f"ids repetidos: {repetidos}")
        return self

    def por_id(self) -> dict[int, Lugar]:
        return {l.id: l for l in self.lugares}


# ---------------------------------------------------------------- calendario
class NoLaborable(_Estricto):
    fecha: date
    nombre: str
    estado: Estado


class Rango(_Estricto):
    desde: date
    hasta: date
    estado: Estado

    @model_validator(mode="after")
    def _orden(self):
        if self.hasta < self.desde:
            raise ValueError("hasta es anterior a desde")
        return self


class Evento(Rango):
    nombre: str
    lugares: list[int] | None = None  # None = todos


class VentanaAguinaldo(_Estricto):
    mes: int = Field(ge=1, le=12)
    desde_dia: int = Field(ge=1, le=31)
    hasta_dia: int = Field(ge=1, le=31)


class Calendario(_Estricto):
    actualizado: date
    no_laborables: list[NoLaborable] = []
    vacaciones_invierno: list[Rango] = []
    eventos: list[Evento] = []
    aguinaldo: list[VentanaAguinaldo] = []


# ---------------------------------------------------------------- carga
def _cargar(ruta: Path, modelo):
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except OSError as e:
        raise ErrorConfigExterna(f"{ruta}: no se pudo leer: {e.strerror}") from None
    except yaml.YAMLError as e:
        raise ErrorConfigExterna(f"{ruta}: YAML inválido: {e}") from None
    try:
        return modelo.model_validate(datos)
    except ValidationError as e:
        detalles = "; ".join(f"{'.'.join(str(x) for x in err['loc']) or '(raíz)'}: {err['msg']}"
                             for err in e.errors())
        raise ErrorConfigExterna(f"{ruta}: {detalles}") from None


def cargar_lugares(raiz: Path = RAIZ) -> Lugares:
    return _cargar(raiz / ARCHIVO_LUGARES, Lugares)


def cargar_calendario(raiz: Path = RAIZ) -> Calendario:
    calendario = _cargar(raiz / ARCHIVO_CALENDARIO, Calendario)
    ids = {l.id for l in cargar_lugares(raiz).lugares}
    for i, ev in enumerate(calendario.eventos):
        desconocidos = sorted(set(ev.lugares or []) - ids)
        if desconocidos:
            raise ErrorConfigExterna(f"{raiz / ARCHIVO_CALENDARIO}: eventos.{i}.lugares: "
                                     f"ids sin catalogar en {ARCHIVO_LUGARES}: {desconocidos}")
    return calendario


@functools.lru_cache(maxsize=1)
def lugares() -> Lugares:
    return cargar_lugares()


@functools.lru_cache(maxsize=1)
def calendario() -> Calendario:
    return cargar_calendario()
