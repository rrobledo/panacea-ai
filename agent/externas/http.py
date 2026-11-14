"""GET de JSON con timeout corto, un reintento y caché en memoria con vencimiento."""

import logging
import threading
import time

import httpx

# httpx registra cada request en INFO: en el servidor MCP y en Vercel es ruido.
logging.getLogger("httpx").setLevel(logging.WARNING)

TIMEOUT_SEG = 8.0
_cache: dict[tuple, tuple[float, object]] = {}
_lock = threading.Lock()


class FuenteNoDisponible(Exception):
    """La API externa no respondió o devolvió algo inválido. El mensaje es apto para mostrar."""


def _get_json(url: str, params: dict | None = None):
    ultimo = None
    for _ in range(2):  # un reintento
        try:
            r = httpx.get(url, params=params, timeout=TIMEOUT_SEG)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            ultimo = e
    raise FuenteNoDisponible(f"{httpx.URL(url).host}: {type(ultimo).__name__}: {str(ultimo)[:200]}")


def get_json(url: str, params: dict | None = None, ttl_seg: float | None = None):
    """ttl_seg None = sin vencimiento dentro del proceso. Los errores no se guardan en caché."""
    clave = (url, tuple(sorted((params or {}).items())))
    ahora = time.monotonic()
    with _lock:
        guardado = _cache.get(clave)
        if guardado and (guardado[0] is None or guardado[0] > ahora):
            return guardado[1]
    datos = _get_json(url, params)
    with _lock:
        _cache[clave] = (None if ttl_seg is None else ahora + ttl_seg, datos)
    return datos


def limpiar_cache() -> None:
    with _lock:
        _cache.clear()
