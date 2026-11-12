"""
Evaluación del agente con preguntas reales (tarea 9.2).

  python evals/evaluar.py verificar            recalcula las respuestas con el SQL de cada pregunta y
                                               las compara con esperado.json (sin costo de API)
  python evals/evaluar.py verificar --guardar  escribe esperado.json (revisarlo a mano)
  python evals/evaluar.py correr [--solo a,b]  corre el agente con la API real y califica.
                                               CUESTA PLATA: ~US$ 0,10–0,30 por pregunta con Opus 5.5.

Base: DB_URL_VENTAS (o DATABASE_URL), solo lectura. API: ANTHROPIC_API_KEY.
Correr antes y después de cambiar el prompt, el modelo o el esfuerzo de un perfil.
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import yaml  # noqa: E402

DIR = Path(__file__).resolve().parent
PREGUNTAS = DIR / "preguntas.yaml"
ESPERADO = DIR / "esperado.json"
TOLERANCIA = {"monto": ("rel", 0.01), "cantidad": ("rel", 0.005), "decimal": ("abs", 0.05),
              "porcentaje": ("abs", 0.6)}


def cargar(ruta: Path = PREGUNTAS) -> dict:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    ids = [p["id"] for p in datos["preguntas"]]
    if len(set(ids)) != len(ids):
        raise ValueError("ids de pregunta repetidos")
    for p in datos["preguntas"]:
        tipos = set((p.get("valores") or {}).values()) - set(TOLERANCIA) - {"hora", "texto"}
        if tipos or not (p.get("sql") or p.get("menciona")):
            raise ValueError(f"pregunta {p['id']} mal formada")
    return datos


# ---------------------------------------------------------------- calificación
def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


_NUM = re.compile(r"(?<![\w.,])([-−+]?\d{1,3}(?:\.\d{3})+(?:,\d+)?|[-−+]?\d+(?:[.,]\d+)?)"
                  r"(?:\s*(millones|millón|millon|mill\.|M\b|mil\b))?(\s*%)?")
_MULT = {"millones": 1e6, "millón": 1e6, "millon": 1e6, "mill.": 1e6, "M": 1e6, "mil": 1e3}


def numeros(texto: str) -> list[tuple[float, bool]]:
    """Números del texto en formato es-AR (1.234.567,89; 45,3 millones; 12,5%) → (valor, es_porcentaje)."""
    out = []
    for m in _NUM.finditer(texto.replace(" ", " ")):
        s = m.group(1).replace("−", "-")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"[-+]?\d{1,3}(\.\d{3})+", s):
            s = s.replace(".", "")
        try:
            v = float(s)
        except ValueError:
            continue
        out.append((v * _MULT.get(m.group(2) or "", 1), bool(m.group(3))))
    return out


def _cerca(n: float, v: float, tipo: str) -> bool:
    modo, tol = TOLERANCIA[tipo]
    n, v = abs(n), abs(v)  # una devolución o una caída se puede escribir con o sin signo
    return abs(n - v) <= (tol * v if modo == "rel" else tol) + (0.5 if tipo == "cantidad" else 0)


def calificar(pregunta: dict, esperado: dict, respuesta: str) -> dict:
    """{"ok": bool, "detalles": {valor: bool}}. Todos los valores tienen que aparecer."""
    detalles = {}
    nums = numeros(respuesta)
    norm = normalizar(respuesta)
    for col, tipo in (pregunta.get("valores") or {}).items():
        v = esperado[col]
        if tipo == "texto":
            detalles[col] = normalizar(str(v)) in norm
        elif tipo == "hora":
            h = int(v)
            detalles[col] = bool(re.search(rf"(?<!\d){h}(?::\d\d|\s*(?:h|hs|hrs|horas)\b)|\blas {h}\b", norm))
        else:
            detalles[col] = any(_cerca(n, float(v), tipo) for n, pct in nums if pct or tipo != "porcentaje")
    for palabra in pregunta.get("menciona") or []:
        detalles[f"menciona:{palabra}"] = normalizar(palabra) in norm
    return {"ok": all(detalles.values()), "detalles": detalles}


# ---------------------------------------------------------------- verificar
def _ctx_db():
    from agent.contexto import ContextoPerfil
    from agent.profiles import engine_para
    nombre = "DB_URL_VENTAS" if os.environ.get("DB_URL_VENTAS") else "DATABASE_URL"
    return ContextoPerfil(engine=engine_para(nombre), tabla="public.panacea_sales_v2", timeout_sql_seg=120)


def calcular(datos: dict, ctx=None) -> dict:
    from agent.tools.base import ejecutar
    ctx = ctx or _ctx_db()
    valores = {}
    for p in datos["preguntas"]:
        if not p.get("sql"):
            continue
        r = ejecutar(ctx, p["sql"].replace("{T}", datos["tabla"]), max_filas=1)
        fila = dict(zip(r["columnas"], r["filas"][0]))
        valores[p["id"]] = {c: (round(fila[c], 4) if isinstance(fila[c], float) else fila[c]) for c in p["valores"]}
    return valores


def verificar(guardar: bool) -> int:
    datos = cargar()
    valores = calcular(datos)
    if guardar:
        ESPERADO.write_text(json.dumps({"generado": datetime.now().isoformat(timespec="seconds"),
                                        "valores": valores}, ensure_ascii=False, indent=2) + "\n")
        print(f"Guardado {ESPERADO} con {len(valores)} preguntas. Revisá los valores antes de usarlos.")
        return 0
    guardado = json.loads(ESPERADO.read_text())["valores"]
    distintos = [(pid, col, guardado.get(pid, {}).get(col), v)
                 for pid, cols in valores.items() for col, v in cols.items()
                 if guardado.get(pid, {}).get(col) != v]
    for d in distintos:
        print("DISTINTO", *d)
    print("OK: las respuestas esperadas coinciden con la base" if not distintos else f"{len(distintos)} diferencias")
    return 1 if distintos else 0


# ---------------------------------------------------------------- correr
def correr_pregunta(agente, almacen, pregunta: dict) -> dict:
    conv = almacen.crear_conversacion("eval@panacea.local", agente.perfil.id, pregunta["id"])
    almacen.tomar_turno(conv.id)
    inicio = time.monotonic()
    textos, herramientas, problemas, uso = [], [], [], {}
    for ev in agente.turno(conv.id, pregunta["pregunta"]):
        if ev["tipo"] == "texto":
            textos.append(ev["texto"])
        elif ev["tipo"] == "reinicio":
            textos.clear()
        elif ev["tipo"] == "herramienta_fin":
            herramientas.append(ev["nombre"] + (" (error)" if ev["es_error"] else ""))
        elif ev["tipo"] in ("error", "aviso", "aclaraciones"):
            problemas.append(ev.get("mensaje") or ev["tipo"])
        elif ev["tipo"] == "fin":
            uso = ev["uso"]
    return {"respuesta": "".join(textos), "herramientas": herramientas, "problemas": problemas,
            "costo_usd": uso.get("costo_usd", 0), "segundos": round(time.monotonic() - inicio, 1)}


def correr(solo: list[str] | None, cliente=None, ctx=None, salida: Path | None = None) -> dict:
    from agent.almacen import AlmacenMemoria
    from agent.loop import Agente
    from agent.profiles import cargar_configuracion, contexto_para

    datos = cargar()
    esperado = json.loads(ESPERADO.read_text())["valores"]
    config = cargar_configuracion()
    perfil = config.perfiles[datos["perfil"]]
    if cliente is None:
        import anthropic
        cliente = anthropic.Anthropic()
    almacen = AlmacenMemoria()
    agente = Agente(cliente, almacen, perfil, ctx or contexto_para(perfil), perfil.system_prompt(config.raiz))
    resultados = []
    for p in datos["preguntas"]:
        if solo and p["id"] not in solo:
            continue
        r = {"id": p["id"], **correr_pregunta(agente, almacen, p)}
        r.update(calificar(p, esperado.get(p["id"], {}), r["respuesta"]))
        resultados.append(r)
        print(f"{'OK ' if r['ok'] else 'MAL'} {p['id']:<32} US$ {r['costo_usd']:.3f} {r['segundos']:>6}s "
              + ", ".join(k for k, v in r["detalles"].items() if not v), flush=True)
    resumen = {"fecha": datetime.now().isoformat(timespec="seconds"), "modelo": perfil.modelo,
               "esfuerzo": perfil.esfuerzo, "aciertos": sum(r["ok"] for r in resultados), "total": len(resultados),
               "costo_usd": round(sum(r["costo_usd"] for r in resultados), 4), "resultados": resultados}
    print(f"\n{resumen['aciertos']}/{resumen['total']} correctas · US$ {resumen['costo_usd']:.2f}")
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n")
        print(f"Detalle en {salida}")
    return resumen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="comando", required=True)
    v = sub.add_parser("verificar")
    v.add_argument("--guardar", action="store_true")
    c = sub.add_parser("correr")
    c.add_argument("--solo", help="ids separados por coma")
    c.add_argument("--salida", type=Path,
                   default=DIR / "resultados" / f"{datetime.now():%Y-%m-%d_%H%M}.json")
    a = ap.parse_args(argv)
    if a.comando == "verificar":
        return verificar(a.guardar)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Falta ANTHROPIC_API_KEY")
        return 2
    r = correr(a.solo.split(",") if a.solo else None, salida=a.salida)
    return 0 if r["aciertos"] == r["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
