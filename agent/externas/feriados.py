"""Feriados nacionales de Argentina desde Nager.Date (https://date.nager.at, sin API key)."""

from datetime import date

from agent.externas.http import FuenteNoDisponible, get_json

URL = "https://date.nager.at/api/v3/PublicHolidays/{anio}/AR"
_TTL_ANIO_ACTUAL = 24 * 3600  # los traslados del año en curso pueden cambiar


def feriados_ar(anio: int) -> dict[date, str]:
    """{fecha: nombre} de los feriados nacionales del año. Lanza FuenteNoDisponible si falla."""
    ttl = _TTL_ANIO_ACTUAL if anio >= date.today().year else None
    datos = get_json(URL.format(anio=int(anio)), ttl_seg=ttl)
    if not isinstance(datos, list):
        raise FuenteNoDisponible("date.nager.at: respuesta inesperada")
    feriados = {}
    for f in datos:
        if f.get("global", True) and "Public" in (f.get("types") or ["Public"]):
            feriados[date.fromisoformat(f["date"])] = f.get("localName") or f.get("name", "")
    return feriados
