"""
Genera las páginas del plan a partir de plan/plan.json y de semanas/*/{kpis,avances}.json:
  - semanas/<AAAA-Www>/reporte_semana_<AAAA-Www>.html   (una por semana con datos, de domingo a sábado)
  - seguimiento_general.html                              (estado general del plan)

No necesita la base de datos. Uso:
    python3 plan_ventas/scripts/generar.py               # regenera todo
    python3 plan_ventas/scripts/generar.py --nueva 2026-W46   # solo crea la carpeta y avances.json de esa semana
    python3 plan_ventas/scripts/generar.py --equipo           # además arma el reporte para el equipo de ventas en reportes/
"""
import json, sys
from datetime import date, datetime, timedelta
from pathlib import Path

PV = Path(__file__).resolve().parents[1]
SCR = PV / "scripts"
PLAN = json.loads((PV / "plan" / "plan.json").read_text(encoding="utf-8"))
INICIO, FIN = date.fromisoformat(PLAN["inicio"]), date.fromisoformat(PLAN["fin"])
TOTAL_SEMANAS = (FIN - INICIO).days // 7 + 1
CERRADAS = ("hecha", "descartada")


def inicio_de(sem):
    """Domingo en que empieza la semana del plan (las semanas van de domingo a sábado)."""
    a, w = sem.split("-W")
    return date.fromisocalendar(int(a), int(w), 1) - timedelta(days=1)


def leer(p, defecto=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else defecto


def crear_avances(sem, carpeta):
    """Plantilla de carga manual. Hereda el estado de las acciones de la semana anterior."""
    p = carpeta / "avances.json"
    if p.exists():
        return
    previas = sorted(x for x in (PV / "semanas").glob("*/avances.json") if x.parent.name < sem)
    estados = leer(previas[-1], {}).get("acciones", {}) if previas else {}
    data = {
        "semana": sem,
        "acciones": {a["id"]: {"estado": estados.get(a["id"], {}).get("estado", "pendiente"), "nota": ""}
                     for e in PLAN["estrategias"] for a in e["acciones"]},
        "kpis_manuales": {x["id"]: None for x in PLAN["kpis"] if x["fuente"] == "manual"},
        "hechos": [], "decisiones": [], "proxima_semana": [],
    }
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def estado_kpi(k, v):
    """Devuelve (valor observado, estado). El observado es la variación interanual o el valor, según el modo."""
    if not v:
        return None, "sin_dato"
    obs = {"interanual": v.get("var"), "vs_base": v.get("var_base")}.get(k["modo"], v.get("valor"))
    if obs is None:
        return None, "sin_dato"
    if k["meta"] is None:
        return obs, "referencia"
    sube = k["sentido"] == "subir"
    if (obs >= k["meta"]) if sube else (obs <= k["meta"]):
        return obs, "en_meta"
    if k["base"] is not None and ((obs > k["base"]) if sube else (obs < k["base"])):
        return obs, "mejora"
    return obs, "sin_mejora"


def armar_semana(carpeta, urls):
    sem = carpeta.name
    kp, av = leer(carpeta / "kpis.json", {}), leer(carpeta / "avances.json", {})
    inicio = inicio_de(sem)
    valores = dict(kp.get("kpis", {}))
    for kid, val in (av.get("kpis_manuales") or {}).items():
        if val is not None:
            valores[kid] = {"valor": val}
    kpis = {}
    for k in PLAN["kpis"]:
        obs, est = estado_kpi(k, valores.get(k["id"]))
        kpis[k["id"]] = {**(valores.get(k["id"]) or {}), "obs": obs, "estado": est}
    acciones = av.get("acciones", {})
    vencidas = [a["id"] for e in PLAN["estrategias"] for a in e["acciones"]
                if a["semana"] <= sem and acciones.get(a["id"], {}).get("estado", "pendiente") not in CERRADAS]
    return {
        "semana": sem, "n": (inicio - INICIO).days // 7 + 1,
        "desde": inicio.isoformat(), "hasta": (inicio + timedelta(days=6)).isoformat(),
        "tiene_datos": bool(kp), "corte": kp.get("corte"), "completa": kp.get("completa"), "datos_hasta": kp.get("datos_hasta"),
        "kpis": kpis, "acciones": acciones, "vencidas": vencidas,
        "hechos": av.get("hechos", []), "decisiones": av.get("decisiones", []), "proxima_semana": av.get("proxima_semana", []),
        "diario": kp.get("diario", []), "detalle": kp.get("detalle", {}),
        "url": urls.get("semanas", {}).get(sem),
    }


def render(plantilla, data, destino):
    css = (SCR / "estilo.css").read_text(encoding="utf-8")
    comun = (SCR / "comun.js").read_text(encoding="utf-8")
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = ((SCR / plantilla).read_text(encoding="utf-8").replace("/*__CSS__*/", css)
            .replace("/*__DATA__*/", f"const DATA = {js};").replace("/*__JS__*/", comun))
    destino.write_text(html, encoding="utf-8")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--nueva":
        carpeta = PV / "semanas" / sys.argv[2]
        carpeta.mkdir(parents=True, exist_ok=True)
        crear_avances(sys.argv[2], carpeta)
        print(f"Creada {carpeta.relative_to(PV.parent)}/avances.json")
        return
    urls = leer(PV / "plan" / "artifacts.json", {})
    carpetas = sorted(c for c in (PV / "semanas").iterdir() if c.is_dir() and "-W" in c.name)
    semanas = [armar_semana(c, urls) for c in carpetas]
    base = {"plan": PLAN, "total_semanas": TOTAL_SEMANAS, "semanas": semanas,
            "objetivo": leer(PV / "plan" / "clientes_objetivo.json"), "urls": urls,
            "historico": leer(PV / "datos" / "historico.json"), "bases": leer(PV / "plan" / "bases.json"),
            "generado": datetime.now().isoformat(timespec="minutes")}
    for i, s in enumerate(semanas):
        if s["tiene_datos"] or s["hechos"] or any(a.get("estado") != "pendiente" for a in s["acciones"].values()):
            destino = carpetas[i] / f"reporte_semana_{s['semana']}.html"
            render("plantilla_semana.html", {**base, "actual": i}, destino)
            print("Generado", destino.relative_to(PV.parent))
    render("plantilla_general.html", base, PV / "seguimiento_general.html")
    print("Generado", (PV / "seguimiento_general.html").relative_to(PV.parent))
    if "--equipo" in sys.argv:
        # Reporte para el equipo de ventas: datos del plan + notas del analista (datos/notas_equipo.json)
        notas = leer(PV / "datos" / "notas_equipo.json", {})
        destino = PV.parent / "reportes" / f"reporte_equipo-ventas_{date.today().isoformat()}.html"
        render("plantilla_equipo.html", {**base, "notas": notas}, destino)
        print("Generado", destino.relative_to(PV.parent))


if __name__ == "__main__":
    main()
