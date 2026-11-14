"""
Clima diario desde Open-Meteo: histórico (API de archivo) y pronóstico hasta 16 días.

Open-Meteo es gratis sin clave para uso no comercial. Con OPEN_METEO_API_KEY se usan los
hosts comerciales (customer-*). Solo se envían coordenadas y fechas.
"""

import os
from datetime import date, timedelta

from agent.externas.http import FuenteNoDisponible, get_json

VARIABLES = "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
ZONA = "America/Argentina/Cordoba"
# El archivo se completa con unos días de demora: lo más reciente sale del pronóstico (past_days).
DEMORA_ARCHIVO_DIAS = 6
MAX_PRONOSTICO_DIAS = 16


def _url(servicio: str) -> tuple[str, dict]:
    clave = os.environ.get("OPEN_METEO_API_KEY", "").strip()
    host = {"archive": "archive-api.open-meteo.com/v1/archive",
            "forecast": "api.open-meteo.com/v1/forecast"}[servicio]
    if clave:
        return f"https://customer-{host}", {"apikey": clave}
    return f"https://{host}", {}


def _parsear(datos) -> dict[date, dict]:
    try:
        d = datos["daily"]
        cols = zip(d["time"], d["temperature_2m_max"], d["temperature_2m_min"],
                   d["precipitation_sum"], d["weather_code"])
        return {date.fromisoformat(t): {"temp_max": tmax, "temp_min": tmin, "lluvia_mm": lluvia,
                                        "codigo_clima": codigo}
                for t, tmax, tmin, lluvia, codigo in cols}
    except (KeyError, TypeError, ValueError):
        raise FuenteNoDisponible("open-meteo: respuesta inesperada") from None


def _completo(dia: dict | None) -> bool:
    return bool(dia) and dia["temp_max"] is not None and dia["lluvia_mm"] is not None


def _historico_anio(lat: float, lon: float, anio: int, hoy: date) -> dict[date, dict]:
    """Un año completo por llamada (una sola request por lugar y año, cacheada)."""
    inicio = date(anio, 1, 1)
    fin = min(date(anio, 12, 31), hoy - timedelta(days=DEMORA_ARCHIVO_DIAS))
    if fin < inicio:
        return {}
    url, extra = _url("archive")
    params = {"latitude": lat, "longitude": lon, "start_date": inicio.isoformat(), "end_date": fin.isoformat(),
              "daily": VARIABLES, "timezone": ZONA, **extra}
    ttl = 3600 if anio == hoy.year else None
    return _parsear(get_json(url, params, ttl_seg=ttl))


def _reciente(lat: float, lon: float, dias_pasados: int, dias_futuros: int) -> dict[date, dict]:
    url, extra = _url("forecast")
    params = {"latitude": lat, "longitude": lon, "daily": VARIABLES, "timezone": ZONA,
              "past_days": dias_pasados, "forecast_days": dias_futuros, **extra}
    return _parsear(get_json(url, params, ttl_seg=3600))


def clima_diario(lat: float, lon: float, desde: date, hasta: date, hoy: date | None = None) -> dict[date, dict]:
    """
    {fecha: {temp_max, temp_min, lluvia_mm, codigo_clima}} entre desde y hasta (inclusive).
    Los días pasados salen del archivo; los últimos días y los futuros, del pronóstico.
    Lanza FuenteNoDisponible si Open-Meteo falla.
    """
    hoy = hoy or date.today()
    if hasta > hoy + timedelta(days=MAX_PRONOSTICO_DIAS - 1):
        hasta = hoy + timedelta(days=MAX_PRONOSTICO_DIAS - 1)
    res: dict[date, dict] = {}
    for anio in range(desde.year, min(hasta, hoy).year + 1):
        res.update(_historico_anio(lat, lon, anio, hoy))
    if hasta >= hoy - timedelta(days=DEMORA_ARCHIVO_DIAS + 3):
        futuros = max((hasta - hoy).days + 1, 1)
        for f, v in _reciente(lat, lon, DEMORA_ARCHIVO_DIAS + 4, futuros).items():
            if not _completo(res.get(f)):
                res[f] = v
    return {f: v for f, v in res.items() if desde <= f <= hasta}
