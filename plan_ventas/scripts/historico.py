"""
Serie semanal por sucursal (desde definiciones.historico_desde hasta la última semana completa), con la misma
semana del año anterior y el índice de precios de mostrador. Escribe:
  - datos/historico.json : la serie, para los gráficos de evolución por sucursal
  - plan/bases.json      : base post aumento por sucursal (promedio de definiciones.semanas_base)

Uso: .venv/bin/python plan_ventas/scripts/historico.py
Después de un aumento de precios, actualizar ultimo_aumento y semanas_base en plan.json y volver a correrlo.
"""
import json
from datetime import date, datetime, timedelta
from statistics import mean

from kpis_semana import DEF, PV, T, METRICAS_MOST, indices, por_sucursal, q, semana_iso, srv

CAMPOS = ("tickets", "unidades", "ventas", "tickets_most") + METRICAS_MOST


def main():
    hasta = date.fromisoformat(q(f"select max(operation_date) m from {T}")[0]["m"])
    fin = hasta - timedelta(days=(hasta.weekday() - 5) % 7)  # último sábado: las semanas van de domingo a sábado
    d1 = date.fromisoformat(DEF["historico_desde"])
    act, ant = por_sucursal(d1, fin), por_sucursal(d1 - timedelta(days=364), fin - timedelta(days=364), 364)
    idx, idx_ant = indices(d1, fin), indices(d1 - timedelta(days=364), fin - timedelta(days=364), 364)

    semanas = []
    for sem in sorted(act):
        filas = {}
        for lugar, r in act[sem].items():
            p = ant.get(sem, {}).get(lugar, {})
            filas[lugar] = {**{c: r.get(c) for c in CAMPOS}, **{c + "_ant": p.get(c) for c in CAMPOS}}
        semanas.append({"semana": sem, "desde": semana_iso(sem)[1].isoformat(), "indice": idx.get(sem), "indice_ant": idx_ant.get(sem), "sucursales": filas})

    bs = {}
    base_sem = [s for s in semanas if s["semana"] in DEF["semanas_base"]]
    for lugar in {l for s in base_sem for l in s["sucursales"]}:
        bs[lugar] = {c: round(mean(v), 2) for c in CAMPOS
                     if (v := [s["sucursales"][lugar][c] for s in base_sem if s["sucursales"].get(lugar, {}).get(c) is not None])}
    meta = {"ultimo_aumento": DEF["ultimo_aumento"], "semanas_base": DEF["semanas_base"],
            "indice_base": round(mean(s["indice"] for s in base_sem if s["indice"]), 1),
            "generado": datetime.now().isoformat(timespec="minutes")}

    # Proyección mensual de tickets por sucursal con historia comparable (modelo del servidor MCP)
    proy = {}
    for lugar in DEF["sucursales_proyeccion"]:
        r = json.loads(srv.proyectar_ventas(metrica="tickets", meses=3, lugar_venta=lugar))
        if "error" not in r:
            proy[lugar] = {"mape": r["error_ajuste_mape_pct"], "historico": r["historico"][-12:], "proyeccion": r["proyeccion"]}
    meta["proyeccion"] = proy

    (PV / "datos").mkdir(exist_ok=True)
    (PV / "datos" / "historico.json").write_text(json.dumps({**meta, "hasta": fin.isoformat(), "semanas": semanas},
                                                            ensure_ascii=False, indent=1), encoding="utf-8")
    (PV / "plan" / "bases.json").write_text(json.dumps({**meta, "sucursales": bs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Histórico {semanas[0]['semana']} a {semanas[-1]['semana']} ({len(semanas)} semanas). Base: {', '.join(DEF['semanas_base'])}")
    for l, b in sorted(bs.items()):
        print(f"  {l:24} tickets {b.get('tickets', 0):6.0f} · ticket mostrador {b.get('tp', 0):8.0f} · upt {b.get('upt', 0):.2f} · "
              f"1 prod {b.get('pct_uno', 0):.1f}% · café {b.get('pct_cafe', 0):.1f}%")


if __name__ == "__main__":
    main()
