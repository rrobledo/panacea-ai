"""
Herramientas que cruzan las ventas diarias con variables externas: clima (Open-Meteo), feriados
(Nager.Date) y el calendario propio (no laborables, temporadas, eventos, cobro y aguinaldo).

El cruce se hace acá y no en el modelo: la base devuelve la serie diaria agregada por lugar y las
variables se agregan en Python. Hacia afuera solo salen coordenadas y fechas.
"""

import statistics
from datetime import date, timedelta

from agent.contexto import ContextoPerfil
from agent.externas import config
from agent.externas.calendario import CalendarioDias
from agent.externas.clima import clima_diario
from agent.externas.http import FuenteNoDisponible
from agent.tools.base import a_json, ejecutar, fecha

MAX_DIAS_SERIE = 400
MAX_DIAS_IMPACTO = 5 * 366
MAX_DIAS_PROXIMOS = 14
MIN_DIAS_CONFIABLE = 8
DIAS_INACTIVO = 30
VENTANA_MOVIL = 28
UMBRAL_LLUVIA_MM = 1.0
UMBRAL_CALOR = 33.0
UMBRAL_FRIO = 12.0
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
METRICAS = ("ventas", "tickets", "unidades")
TEMPORADAS = ("verano", "vacaciones_invierno", "semana_santa", "fuera_de_temporada")

COLUMNAS = ["fecha", "dia_semana", "lugar_venta_id", "lugar_venta", "ventas", "tickets", "unidades",
            "temp_max", "temp_min", "lluvia_mm", "dia_lluvioso", "calor_extremo", "frio",
            "feriado", "feriado_nombre", "no_laborable", "fin_de_semana_largo", "vispera_feriado",
            "dia_cobro", "aguinaldo", "temporada", "evento"]

# Variable binaria → cómo se lee de una fila (None = desconocida, el día no cuenta)
VARIABLES = {
    "dia_lluvioso": lambda r: r["dia_lluvioso"],
    "calor_extremo": lambda r: r["calor_extremo"],
    "frio": lambda r: r["frio"],
    "feriado": lambda r: r["feriado"],
    "no_laborable": lambda r: r["no_laborable"],
    "fin_de_semana_largo": lambda r: r["fin_de_semana_largo"],
    "vispera_feriado": lambda r: r["vispera_feriado"],
    "dia_cobro": lambda r: r["dia_cobro"],
    "aguinaldo": lambda r: r["aguinaldo"],
    "verano": lambda r: r["temporada"] == "verano",
    "vacaciones_invierno": lambda r: r["temporada"] == "vacaciones_invierno",
    "semana_santa": lambda r: r["temporada"] == "semana_santa",
    "evento": lambda r: r["evento"] is not None,
}


def _fuentes() -> list[str]:
    return ["Clima: Open-Meteo (open-meteo.com), datos diarios en hora de Córdoba",
            "Feriados nacionales: Nager.Date (date.nager.at)",
            f"No laborables, temporadas, eventos y aguinaldo: config/calendario_externo.yaml "
            f"(actualizado {config.calendario().actualizado:%d/%m/%Y})"]


def _rango(desde: str | None, hasta: str | None, dias_defecto: int) -> tuple[date, date]:
    """Por defecto termina ayer: el día de hoy está incompleto."""
    h = fecha(hasta, date.today() - timedelta(days=1))
    d = fecha(desde, h - timedelta(days=dias_defecto - 1))
    if d > h:
        raise ValueError("desde es posterior a hasta")
    return d, h


def _ventas_diarias(ctx: ContextoPerfil, desde: date, hasta: date, lugar_venta_id: int | None) -> dict[int, dict]:
    """{lugar_id: {"nombre": str, "dias": {fecha: (ventas, tickets, unidades)}}}"""
    extra, params = "", {"d": desde, "h": hasta}
    if lugar_venta_id is not None:
        extra, params["l"] = " AND lugar_venta_id = :l", int(lugar_venta_id)
    res = ejecutar(ctx, f"""
        SELECT lugar_venta_id, MAX(lugar_venta) AS lugar_venta, operation_date,
               ROUND(SUM(subtotal)::numeric, 2) AS ventas, COUNT(DISTINCT document_id) AS tickets,
               ROUND(SUM(count)::numeric, 2) AS unidades
        FROM {ctx.tabla}
        WHERE operation_date BETWEEN :d AND :h{extra}
        GROUP BY lugar_venta_id, operation_date
        ORDER BY lugar_venta_id, operation_date""", params, max_filas=50_000)
    lugares: dict[int, dict] = {}
    for lid, nombre, f, ventas, tickets, unidades in res["filas"]:
        f = date.fromisoformat(f) if isinstance(f, str) else f
        lugar = lugares.setdefault(lid, {"nombre": nombre, "dias": {}})
        lugar["dias"][f] = (float(ventas or 0), int(tickets or 0), float(unidades or 0))
    return lugares


def _clima_por_lugar(lugar_ids, desde: date, hasta: date, avisos: list[str]) -> dict[int, dict]:
    catalogo = config.lugares().por_id()
    clima: dict[int, dict] = {}
    for lid in lugar_ids:
        lugar = catalogo.get(lid)
        if lugar is None or not lugar.ubicado:
            motivo = "no está en config/lugares_venta.yaml" if lugar is None else "no tiene coordenadas"
            avisos.append(f"Lugar de venta {lid} {motivo}: sin datos de clima.")
            clima[lid] = {}
            continue
        try:
            clima[lid] = clima_diario(lugar.lat, lugar.lon, desde, hasta)
        except FuenteNoDisponible as e:
            avisos.append(f"Clima no disponible para {lugar.nombre} ({e}): columnas de clima en null.")
            clima[lid] = {}
    return clima


def _variables_clima(c: dict | None) -> dict:
    c = c or {}
    tmax, tmin, lluvia = c.get("temp_max"), c.get("temp_min"), c.get("lluvia_mm")
    return {"temp_max": tmax, "temp_min": tmin, "lluvia_mm": lluvia,
            "dia_lluvioso": None if lluvia is None else lluvia >= UMBRAL_LLUVIA_MM,
            "calor_extremo": None if tmax is None else tmax >= UMBRAL_CALOR,
            "frio": None if tmax is None else tmax <= UMBRAL_FRIO}


def _serie_enriquecida(ctx, desde, hasta, lugar_venta_id) -> tuple[list[dict], list[str], dict[int, int]]:
    """
    Filas por día y lugar. Los días sin ventas van en 0 desde la primera venta del rango hasta `hasta`
    (o hasta la última venta, si el lugar lleva más de DIAS_INACTIVO días sin vender: ej. un local cerrado).
    """
    avisos: list[str] = []
    ventas = _ventas_diarias(ctx, desde, hasta, lugar_venta_id)
    cal = CalendarioDias(desde, hasta)
    clima = _clima_por_lugar(ventas, desde, hasta, avisos)
    filas, dias_por_lugar = [], {}
    for lid, lugar in sorted(ventas.items()):
        dias = lugar["dias"]
        if not dias:
            continue
        f, ultima = min(dias), max(dias)
        if (hasta - ultima).days <= DIAS_INACTIVO:  # sigue activo: completa los días sin ventas hasta el final
            ultima = min(hasta, date.today())
        dias_por_lugar[lid] = (ultima - f).days + 1
        while f <= ultima:
            v, t, u = dias.get(f, (0.0, 0, 0.0))
            filas.append({"fecha": f, "dia_semana": DIAS_SEMANA[f.weekday()], "lugar_venta_id": lid,
                          "lugar_venta": lugar["nombre"], "ventas": v, "tickets": t, "unidades": u,
                          **_variables_clima(clima[lid].get(f)), **cal.variables(f, lid)})
            f += timedelta(days=1)
    return filas, avisos + cal.todos_los_avisos(), dias_por_lugar


def ventas_con_contexto(ctx: ContextoPerfil, desde: str | None = None, hasta: str | None = None,
                        lugar_venta_id: int | None = None) -> str:
    """
    Serie diaria de ventas, tickets y unidades por lugar de venta, con variables externas al lado:
    clima (temp. máx/mín, lluvia mm, día lluvioso ≥1 mm, calor extremo ≥33 °C, frío máx ≤12 °C),
    feriado, día no laborable, fin de semana largo, víspera de feriado, día de cobro (primeros 5
    días hábiles), aguinaldo, temporada (verano, vacaciones_invierno, semana_santa) y evento local.
    Fechas AAAA-MM-DD (por defecto, los 90 días hasta ayer); máximo 400 días por llamada.
    lugar_venta_id opcional (ver perfil_datos). Días sin ventas aparecen en 0.
    Revisá `avisos`: fuentes caídas, lugares sin ubicación y fechas no confirmadas.
    Para medir cuánto pesa cada variable usá impacto_variables.
    """
    try:
        d, h = _rango(desde, hasta, 90)
    except ValueError as e:
        return a_json({"error": str(e)})
    if (h - d).days + 1 > MAX_DIAS_SERIE:
        return a_json({"error": f"El rango supera {MAX_DIAS_SERIE} días. Acotalo, filtrá por lugar_venta_id "
                                f"o usá impacto_variables para analizar períodos largos."})
    filas, avisos, _ = _serie_enriquecida(ctx, d, h, lugar_venta_id)
    truncado = len(filas) > ctx.max_filas
    filas = filas[:ctx.max_filas]
    if truncado:
        avisos.append(f"Resultado truncado a {ctx.max_filas} filas: acotá el rango o filtrá por lugar_venta_id.")
    return a_json({"periodo": [d, h], "columnas": COLUMNAS, "filas": [[r[c] for c in COLUMNAS] for r in filas],
                   "total_filas": len(filas), "truncado": truncado, "avisos": avisos, "fuentes": _fuentes()})


def _indices(filas: list[dict], metrica: str) -> None:
    """
    Agrega r["indice"] = valor / mediana móvil centrada de 28 días del mismo lugar. Neutraliza inflación
    y tendencia; la mediana (y no la media) evita que los mismos días atípicos bajen o suban la base.
    """
    por_lugar: dict[int, list[dict]] = {}
    for r in filas:
        por_lugar.setdefault(r["lugar_venta_id"], []).append(r)
    medio = VENTANA_MOVIL // 2
    for serie in por_lugar.values():
        valores = [float(r[metrica]) for r in serie]
        for i, r in enumerate(serie):
            base = statistics.median(valores[max(0, i - medio):i + medio])
            r["indice"] = valores[i] / base if base > 0 else None


def _efecto(filas: list[dict], leer) -> dict:
    grupos: dict[tuple, dict[bool, list[float]]] = {}
    for r in filas:
        valor = leer(r)
        if valor is None or r["indice"] is None:
            continue
        clave = (r["lugar_venta_id"], r["fecha"].weekday())
        grupos.setdefault(clave, {True: [], False: []})[bool(valor)].append(r["indice"])
    suma, peso, dias_con, dias_sin = 0.0, 0, 0, 0
    for g in grupos.values():
        dias_sin += len(g[False])
        if g[True] and g[False]:
            base = statistics.median(g[False])
            if base > 0:
                suma += (statistics.median(g[True]) / base) * len(g[True])
                peso += len(g[True])
                dias_con += len(g[True])
    efecto = round((suma / peso - 1) * 100, 1) if peso else None
    confiable = efecto is not None and dias_con >= MIN_DIAS_CONFIABLE
    return {"efecto_pct": efecto, "dias_con": dias_con, "dias_sin": dias_sin, "confiable": confiable,
            "estado": "confiable" if confiable else "insuficiente"}


def impacto_variables(ctx: ContextoPerfil, desde: str | None = None, hasta: str | None = None,
                      lugar_venta_id: int | None = None, metrica: str = "ventas",
                      temporada: str | None = None) -> str:
    """
    Cuánto cambia la venta diaria con cada variable externa (lluvia, calor extremo, frío, feriado,
    no laborable, fin de semana largo, víspera, día de cobro, aguinaldo, verano, vacaciones de
    invierno, Semana Santa, evento). Compara días con y sin la variable en el mismo lugar y día de
    la semana, sobre un índice (valor del día / mediana móvil de 28 días) que neutraliza inflación y
    tendencia. Usa medianas. metrica: ventas | tickets | unidades.
    Fechas AAAA-MM-DD (por defecto, los 24 meses hasta ayer; máximo 5 años). lugar_venta_id opcional.
    temporada opcional para comparar dentro de un mismo período: verano | vacaciones_invierno |
    semana_santa | fuera_de_temporada. Un efecto con confiable=false (menos de 8 días con la
    variable) es solo una pista: presentalo como hipótesis. Son asociaciones, no causas probadas.
    """
    if metrica not in METRICAS:
        return a_json({"error": f"metrica debe ser una de {list(METRICAS)}"})
    if temporada is not None and temporada not in TEMPORADAS:
        return a_json({"error": f"temporada debe ser una de {list(TEMPORADAS)}"})
    try:
        d, h = _rango(desde, hasta, 730)
    except ValueError as e:
        return a_json({"error": str(e)})
    if (h - d).days + 1 > MAX_DIAS_IMPACTO:
        return a_json({"error": "El rango supera 5 años: acotalo."})
    filas, avisos, dias_por_lugar = _serie_enriquecida(ctx, d, h, lugar_venta_id)
    if not filas:
        return a_json({"error": "No hay ventas en el período pedido.", "avisos": avisos})
    _indices(filas, metrica)  # sobre la serie completa, antes de filtrar por temporada
    if temporada is not None:
        objetivo = None if temporada == "fuera_de_temporada" else temporada
        filas = [r for r in filas if r["temporada"] == objetivo]

    nombres = {r["lugar_venta_id"]: r["lugar_venta"] for r in filas}
    for lid, n in dias_por_lugar.items():
        if n < 365 and lid in nombres:
            avisos.append(f"{nombres[lid]} tiene {n} días de historia en el período (menos de un año): "
                          f"la mayoría de los efectos no son comparables entre estaciones.")

    ranking = [{"variable": v, **_efecto(filas, leer)} for v, leer in VARIABLES.items()]
    ranking.sort(key=lambda e: (not e["confiable"], -abs(e["efecto_pct"] or 0)))
    insuficientes = [e["variable"] for e in ranking if not e["confiable"]]
    if insuficientes:
        avisos.append(f"Con menos de {MIN_DIAS_CONFIABLE} días observados (insuficiente): {', '.join(insuficientes)}.")
    return a_json({
        "periodo": [d, h], "metrica": metrica, "lugar_venta_id": lugar_venta_id, "temporada": temporada,
        "dias_analizados": len(filas), "ranking": ranking, "avisos": avisos, "fuentes": _fuentes(),
        "metodo": (f"Índice diario = {metrica} del día / mediana móvil centrada de {VENTANA_MOVIL} días del "
                   f"mismo lugar (neutraliza inflación y tendencia). efecto_pct = mediana del índice en días con "
                   f"la variable / mediana en días sin ella, del mismo lugar y día de la semana, ponderado por "
                   f"días con la variable. confiable = al menos {MIN_DIAS_CONFIABLE} días con la variable. "
                   f"Las variables se superponen (ej. fin de semana largo en verano): usá `temporada` para aislar."),
    })


def contexto_proximos_dias(ctx: ContextoPerfil, dias: int = 14, lugar_venta_id: int | None = None,
                           desde: str | None = None) -> str:
    """
    Próximos días (máximo 14, desde hoy salvo que se indique `desde` AAAA-MM-DD) por lugar de venta:
    pronóstico del clima, feriado, fin de semana largo, víspera, día de cobro, temporada y eventos,
    más la venta de referencia (promedio de los últimos 8 días equivalentes: mismo lugar y día de la
    semana). Sirve para planificar dotación, stock y promociones. Sin lugar_venta_id incluye los
    lugares con ventas en los últimos 30 días.
    """
    dias = max(1, min(int(dias), MAX_DIAS_PROXIMOS))
    try:
        inicio = fecha(desde, date.today())
    except ValueError as e:
        return a_json({"error": str(e)})
    fin = inicio + timedelta(days=dias - 1)
    avisos: list[str] = []

    historia = _ventas_diarias(ctx, inicio - timedelta(days=63), inicio - timedelta(days=1), lugar_venta_id)
    activos = {lid: l for lid, l in historia.items()
               if lugar_venta_id is not None or max(l["dias"]) >= inicio - timedelta(days=30)}
    if not activos:
        return a_json({"error": "No hay lugares de venta con ventas en los últimos 30 días."})

    referencia: dict[tuple[int, int], dict] = {}
    for lid, l in activos.items():
        for dow in range(7):
            ultimos = sorted((f for f in l["dias"] if f.weekday() == dow), reverse=True)[:8]
            if ultimos:
                referencia[(lid, dow)] = {
                    "ventas": round(statistics.mean(l["dias"][f][0] for f in ultimos), 2),
                    "tickets": round(statistics.mean(l["dias"][f][1] for f in ultimos), 1),
                    "dias_promediados": len(ultimos)}

    cal = CalendarioDias(inicio, fin)
    clima = _clima_por_lugar(activos, inicio, fin, avisos)
    filas = []
    for lid, l in sorted(activos.items()):
        f = inicio
        while f <= fin:
            ref = referencia.get((lid, f.weekday()), {})
            filas.append({"fecha": f, "dia_semana": DIAS_SEMANA[f.weekday()], "lugar_venta_id": lid,
                          "lugar_venta": l["nombre"], **_variables_clima(clima[lid].get(f)),
                          **cal.variables(f, lid),
                          "ventas_referencia": ref.get("ventas"), "tickets_referencia": ref.get("tickets"),
                          "dias_referencia": ref.get("dias_promediados", 0)})
            f += timedelta(days=1)
    columnas = list(filas[0]) if filas else []
    return a_json({"periodo": [inicio, fin], "columnas": columnas, "filas": [[r[c] for c in columnas] for r in filas],
                   "total_filas": len(filas), "truncado": False, "avisos": avisos + cal.todos_los_avisos(),
                   "fuentes": _fuentes(),
                   "nota": "ventas_referencia es el promedio de los últimos 8 días iguales (en ARS corrientes); "
                           "el pronóstico del clima pierde precisión después de 7 días."})
