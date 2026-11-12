"""
Backend de demostración para desarrollar el frontend sin base de datos ni costo de API.

Levanta el FastAPI real (api/index.py) con almacén en memoria, herramientas de ventas simuladas y un
Claude simulado con guion: una pregunta común consulta y responde con una tabla; un pedido que
menciona "reporte" pide aclaraciones y, al aprobarlas, genera un reporte de ejemplo.

  AUTH_SECRET=... .venv/bin/python scripts/demo_backend.py      # http://127.0.0.1:8000
  AUTH_SECRET=... npm run dev                                    # http://localhost:3000

Usuarios: los de config/usuarios.yaml más DEMO_EMAIL (por defecto demo@example.com, admin).
Para entrar sin Google, generá la cookie con: .venv/bin/python scripts/demo_backend.py --cookie
"""

import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent.almacen import AlmacenMemoria  # noqa: E402
from agent.contexto import ContextoPerfil  # noqa: E402
from agent.profiles import Usuario, cargar_configuracion  # noqa: E402
from agent.tools import registro  # noqa: E402
from api.index import Servicios, app  # noqa: E402
from tests.fakes import mensaje, texto, tool_use  # noqa: E402
from tests.test_reportes import BRIEF, CONTENIDO, PREGUNTAS  # noqa: E402

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@example.com")
PAUSA = float(os.environ.get("DEMO_PAUSA", "0.04"))  # segundos entre palabras, para ver el streaming


# ---------------------------------------------------------------- herramientas simuladas
def resumen_ventas(ctx, desde: str | None = None, hasta: str | None = None, agrupar_por: str | None = None) -> str:
    """Resumen de ventas (simulado)."""
    time.sleep(0.8)
    return json.dumps({"periodo": [desde, hasta], "resultado": {
        "columnas": ["lugar_venta", "ventas", "tickets"],
        "filas": [["Carlos Paz", 28791781, 1210], ["Villa Allende", 15002113, 803], ["Dietetica", 10950010, 690],
                  ["Cordoba", 3418706, 272]], "total_filas": 4, "truncado": False}})


def consultar(ctx, sql: str) -> str:
    """Consulta SQL (simulada)."""
    time.sleep(0.5)
    return json.dumps({"columnas": ["n"], "filas": [[1]], "total_filas": 1, "truncado": False})


# ---------------------------------------------------------------- Claude simulado
RESPUESTA = """En **octubre de 2026** vendimos **$ 58.162.610** en 2.975 tickets (ticket promedio $ 19.550).

| Lugar de venta | Ventas | Tickets |
|---|---:|---:|
| Carlos Paz | $ 28.791.781 | 1.210 |
| Villa Allende | $ 15.002.113 | 803 |
| Dietética | $ 10.950.010 | 690 |
| Córdoba | $ 3.418.706 | 272 |

- **Hecho:** Carlos Paz explica la mitad de las ventas.
- **Hipótesis:** el crecimiento en pesos está empujado por precios; conviene mirar unidades.

*(Respuesta de demostración: los números son de ejemplo.)*"""


def _ultimo_usuario(messages: list[dict]) -> list:
    return messages[-1]["content"] if messages and messages[-1]["role"] == "user" else []


def _texto_usuario(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m["role"] == "user":
            for b in m["content"]:
                if b.get("type") == "text" and not b["text"].startswith("[Sistema]"):
                    return b["text"].lower()
    return ""


def responder(params: dict):
    messages = params["messages"]
    ultimo = _ultimo_usuario(messages)
    resultados = {b["tool_use_id"]: b for b in ultimo if b.get("type") == "tool_result"}
    n = len(messages)

    for r in resultados.values():
        try:
            datos = json.loads(r["content"])
        except ValueError:
            continue
        if datos.get("decision") == "aprobado":
            return mensaje(texto("Perfecto, armo el reporte con lo que aprobaste."),
                           tool_use(f"g{n}", "generar_artifact", {"brief_id": datos["brief_id"], **CONTENIDO}),
                           stop="tool_use")
        if datos.get("decision") == "ajustar":
            return mensaje(texto(f"Ajusto el brief según tu comentario: “{datos.get('comentario', '')}”."),
                           tool_use(f"c{n}", "solicitar_aclaraciones",
                                    {"brief": {**BRIEF, "periodo": "Ajustado: " + BRIEF["periodo"]}, "preguntas": []}),
                           stop="tool_use")
        if "artifact_id" in datos:
            return mensaje(texto("Listo, el reporte quedó guardado. Lo principal: las ventas crecieron **12%** "
                                 "interanual y los tickets cayeron 3%."))
    if resultados:
        return mensaje(texto(RESPUESTA))
    if "reporte" in _texto_usuario(messages):
        return mensaje(texto("Antes de generarlo, confirmame el alcance:"),
                       tool_use(f"c{n}", "solicitar_aclaraciones", {"brief": BRIEF, "preguntas": PREGUNTAS}),
                       stop="tool_use")
    return mensaje(texto("Consulto las ventas del período."),
                   tool_use(f"t{n}", "resumen_ventas", {"desde": "2026-10-01", "hasta": "2026-10-31",
                                                        "agrupar_por": "lugar_venta"}), stop="tool_use")


class _Stream:
    def __init__(self, final):
        self.final = final

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        time.sleep(0.6)  # "pensando"
        for b in self.final.content:
            if b.type == "text":
                for palabra in b.text.split(" "):
                    time.sleep(PAUSA)
                    yield SimpleNamespace(type="text", text=palabra + " ")

    def get_final_message(self):
        # El texto emitido lleva un espacio extra por palabra; el guardado es el original.
        return self.final


class ClaudeDemo:
    def __init__(self):
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=lambda **p: _Stream(responder(p))))


class ServiciosDemo(Servicios):
    def __init__(self):
        config = cargar_configuracion()
        usuarios = dict(config.usuarios)
        usuarios.setdefault(DEMO_EMAIL, Usuario(email=DEMO_EMAIL, perfiles=list(config.perfiles), admin=True))
        self.__dict__.update(config=replace(config, usuarios=usuarios), almacen=AlmacenMemoria(), cliente=ClaudeDemo())
        self.fallbacks = False

    def contexto(self, perfil):
        return ContextoPerfil(engine=None, tabla=perfil.tabla_principal)


def cookie() -> str:
    import jwt
    return jwt.encode({"email": DEMO_EMAIL, "exp": int(time.time()) + 12 * 3600}, os.environ["AUTH_SECRET"],
                      algorithm="HS256")


if __name__ == "__main__":
    if not os.environ.get("AUTH_SECRET"):
        sys.exit("Falta AUTH_SECRET (el mismo que usa `npm run dev`)")
    if "--cookie" in sys.argv:
        print(cookie())
        sys.exit(0)
    registro.HERRAMIENTAS["resumen_ventas"] = resumen_ventas
    registro.HERRAMIENTAS["consultar"] = consultar
    app.state.servicios = ServiciosDemo()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
