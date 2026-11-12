"""Calificador y plumbing del set de evaluación (evals/evaluar.py), sin costo de API."""

import json
import os

import pytest

from evals import evaluar
from tests.fakes import ClienteFalso, mensaje, texto


def test_numeros_es_ar():
    t = "Vendimos $ 58.162.610,00 en 2.975 tickets (ticket $19.550,46), +58,9% y 45,3 millones; 5,21 u/ticket; 1.5%"
    nums = evaluar.numeros(t)
    assert (58162610.0, False) in nums and (2975.0, False) in nums and (19550.46, False) in nums
    assert (58.9, True) in nums and (45.3e6, False) in nums and (5.21, False) in nums and (1.5, True) in nums
    assert evaluar.numeros("cayó −21,8 %") == [(-21.8, True)]


def test_preguntas_bien_formadas():
    datos = evaluar.cargar()
    assert len(datos["preguntas"]) == 20
    esperado = json.loads(evaluar.ESPERADO.read_text())["valores"]
    for p in datos["preguntas"]:
        if p.get("sql"):
            assert set(esperado[p["id"]]) == set(p["valores"]), p["id"]


@pytest.mark.parametrize("respuesta, ok", [
    ("Octubre 2026: ventas $ 58,2 millones, 2.975 tickets, ticket promedio $ 19.550.", True),
    ("Octubre 2026: ventas $ 58.162.610, 2.975 tickets, ticket promedio $ 19.550,46.", True),
    ("Octubre 2026: ventas $ 60 millones, 2.975 tickets, ticket promedio $ 19.550.", False),  # 3% de error
    ("Octubre 2026: ventas $ 58.162.610 y ticket promedio $ 19.550.", False),  # faltan los tickets
])
def test_calificar_montos(respuesta, ok):
    p = next(p for p in evaluar.cargar()["preguntas"] if p["id"] == "ventas_oct_2026")
    esp = {"ventas": 58162610.0, "tickets": 2975, "ticket_promedio": 19550.4571}
    assert evaluar.calificar(p, esp, respuesta)["ok"] is ok


def test_calificar_porcentajes_texto_y_hora():
    pp = {"valores": {"var": "porcentaje", "lugar": "texto", "hora": "hora"}}
    esp = {"var": -21.79, "lugar": "Dietetica", "hora": 18}
    assert evaluar.calificar(pp, esp, "La Dietética cayó 21,8% y el pico es a las 18 h.")["ok"]
    r = evaluar.calificar(pp, esp, "La Dietética cayó 21,8 puntos; pico 18.")
    assert r["detalles"] == {"var": False, "lugar": True, "hora": False}
    assert evaluar.calificar({"menciona": ["costo"]}, {}, "No hay columna de COSTOS, así que...")["ok"]


def test_correr_con_cliente_simulado(tmp_path, ctx):
    cliente = ClienteFalso(mensaje(texto("Vendimos $ 58.162.610 en 2.975 tickets; ticket promedio $ 19.550.")),
                           mensaje(texto("No sé.")))
    r = evaluar.correr(["ventas_oct_2026", "unidades_sep_2026"], cliente=cliente, ctx=ctx,
                       salida=tmp_path / "r.json")
    assert (r["aciertos"], r["total"]) == (1, 2) and r["costo_usd"] > 0
    assert json.loads((tmp_path / "r.json").read_text())["resultados"][0]["ok"] is True
    assert "Analista comercial de Panacea" in cliente.llamadas[0]["system"][0]["text"]


@pytest.mark.db
def test_respuestas_esperadas_vigentes():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("Sin DATABASE_URL")
    assert evaluar.verificar(guardar=False) == 0
