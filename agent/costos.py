"""
Costo estimado de cada llamada a la Messages API.

Precios en USD por millón de tokens (lista pública de Anthropic, noviembre de 2026). Escritura de
caché con TTL de 5 minutos = 1,25 × entrada. Es una estimación para topes y tableros: la factura de
Anthropic es la referencia. Al cambiar precios o modelos, actualizar esta tabla.
"""

import logging

log = logging.getLogger("panacea.costos")

# modelo: (entrada, salida, lectura de caché)
PRECIOS_USD_MTOK: dict[str, tuple[float, float, float]] = {
    "claude-fable-5-2": (8.0, 40.0, 0.20),
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-opus-5": (5.0, 25.0, 0.50),       # lectura de caché: 0,1 × entrada (regla general)
    "claude-sonnet-5-5": (2.0, 10.0, 0.10),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),   # prompts de hasta 100K tokens; lectura: 0,1 × entrada
}
FACTOR_ESCRITURA_CACHE = 1.25
# Un modelo desconocido (por ejemplo, el de un fallback) se cobra al precio más alto: el tope
# mensual nunca subestima.
_PEOR_CASO = max(PRECIOS_USD_MTOK.values())


def precios(modelo: str) -> tuple[float, float, float]:
    for nombre, p in PRECIOS_USD_MTOK.items():
        if modelo == nombre or modelo.startswith(nombre + "-"):  # ids con fecha o sufijo
            return p
    log.warning("modelo sin precio en la tabla, se usa el más caro: %s", modelo)
    return _PEOR_CASO


def costo_usd(modelo: str, entrada: int, salida: int, cache_lectura: int, cache_escritura: int) -> float:
    p_in, p_out, p_read = precios(modelo)
    total = (entrada * p_in + salida * p_out + cache_lectura * p_read
             + cache_escritura * p_in * FACTOR_ESCRITURA_CACHE)
    return round(total / 1_000_000, 6)
