"""Variables externas: configuración, fuentes (HTTP simulado), calendario y herramientas (base simulada)."""

import json
import shutil
from datetime import date, timedelta

import pytest
import yaml

from agent.externas import config, http
from agent.externas.calendario import CalendarioDias, pascua
from agent.externas.clima import clima_diario
from agent.externas.config import ErrorConfigExterna, cargar_calendario, cargar_lugares
from agent.externas.feriados import feriados_ar
from agent.externas.http import FuenteNoDisponible
from agent.profiles import ErrorConfiguracion, cargar_configuracion
from agent.tools import externas, registro
from tests.conftest import RAIZ

FERIADOS_2026 = [("2026-11-23", "Día de la Soberanía Nacional"), ("2026-12-08", "Inmaculada Concepción"),
                 ("2026-12-25", "Navidad"), ("2026-10-12", "Diversidad Cultural"), ("2026-04-03", "Viernes Santo")]
LLUVIA = {date(2026, 10, d) for d in (2, 6, 7, 13, 14, 16, 20, 21, 23, 27, 28, 30)}


class Red:
    """Reemplaza el GET real. Registra las URL pedidas; `caidas` simula hosts que no responden."""

    def __init__(self):
        self.pedidos: list[tuple[str, dict]] = []
        self.caidas: set[str] = set()

    def __call__(self, url, params=None):
        self.pedidos.append((url, dict(params or {})))
        for host in self.caidas:
            if host in url:
                raise FuenteNoDisponible(f"{host}: ConnectTimeout")
        if "nager" in url:
            anio = url.rstrip("/").split("/")[-2]
            return [{"date": f, "localName": n, "global": True, "types": ["Public"]}
                    for f, n in FERIADOS_2026 if f.startswith(anio)]
        if "archive" in url:
            ini, fin = date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])
        else:
            hoy = date.today()
            ini, fin = hoy - timedelta(days=params["past_days"]), hoy + timedelta(days=params["forecast_days"] - 1)
        dias = [ini + timedelta(days=i) for i in range((fin - ini).days + 1)]
        return {"daily": {"time": [d.isoformat() for d in dias],
                          "temperature_2m_max": [25.0 for _ in dias],
                          "temperature_2m_min": [12.0 for _ in dias],
                          "precipitation_sum": [8.0 if d in LLUVIA else 0.0 for d in dias],
                          "weather_code": [63 if d in LLUVIA else 1 for d in dias]}}


@pytest.fixture
def red(monkeypatch):
    http.limpiar_cache()
    r = Red()
    monkeypatch.setattr(http, "_get_json", r)
    yield r
    http.limpiar_cache()


class Base:
    """Ventas diarias simuladas: {(lugar_id, fecha): (ventas, tickets, unidades)}."""

    NOMBRES = {1: "Villa Allende", 2: "Carlos Paz", 4: "Villa General Belgrano", 0: "Dietetica", 9: "Nuevo"}

    def __init__(self, filas):
        self.filas = filas

    def __call__(self, ctx, sql, params=None, max_filas=None):
        res = [[lid, self.NOMBRES[lid], f.isoformat(), *v] for (lid, f), v in sorted(self.filas.items())
               if params["d"] <= f <= params["h"] and ("l" not in params or params["l"] == lid)]
        return {"columnas": [], "filas": res, "total_filas": len(res), "truncado": False}


@pytest.fixture
def base(monkeypatch):
    def instalar(filas):
        b = Base(filas)
        monkeypatch.setattr(externas, "ejecutar", b)
        return b
    return instalar


def dias(desde: date, hasta: date):
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]


# ---------------------------------------------------------------- configuración
@pytest.fixture
def raiz(tmp_path):
    for d in ("config", "prompts"):
        shutil.copytree(RAIZ / d, tmp_path / d)
    return tmp_path


def editar(raiz, archivo, cambio):
    ruta = raiz / archivo
    datos = yaml.safe_load(ruta.read_text())
    cambio(datos)
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True))


def test_configuracion_real():
    lugares = cargar_lugares().por_id()
    assert lugares[2].lat == pytest.approx(-31.4241) and not lugares[0].ubicado
    cal = cargar_calendario()
    assert any(e.nombre == "Oktoberfest" and e.lugares == [4] for e in cal.eventos)


@pytest.mark.parametrize("cambio,fragmento", [
    (lambda d: d["lugares"].append(dict(d["lugares"][1])), "ids repetidos"),
    (lambda d: d["lugares"][1].update(lat=-131.0), "lugares.1.lat"),
    (lambda d: d["lugares"][1].pop("lon"), "lat y lon van juntas"),
])
def test_lugares_invalidos(raiz, cambio, fragmento):
    editar(raiz, "config/lugares_venta.yaml", cambio)
    with pytest.raises(ErrorConfigExterna) as e:
        cargar_lugares(raiz)
    assert "lugares_venta.yaml" in str(e.value) and fragmento in str(e.value)


def test_evento_con_lugar_sin_catalogar(raiz):
    editar(raiz, "config/calendario_externo.yaml", lambda d: d["eventos"][0].update(lugares=[42]))
    with pytest.raises(ErrorConfigExterna, match=r"eventos\.0\.lugares.*\[42\]"):
        cargar_calendario(raiz)


def test_config_invalida_frena_el_arranque(raiz):
    editar(raiz, "config/calendario_externo.yaml", lambda d: d["no_laborables"][0].update(estado="tal_vez"))
    with pytest.raises(ErrorConfiguracion, match=r"calendario_externo\.yaml.*no_laborables\.0\.estado"):
        cargar_configuracion(raiz)


# ---------------------------------------------------------------- fuentes
def test_feriados_y_cache(red):
    assert feriados_ar(2026)[date(2026, 11, 23)] == "Día de la Soberanía Nacional"
    feriados_ar(2026)
    assert len([u for u, _ in red.pedidos if "nager" in u]) == 1


def test_feriados_caidos(red):
    red.caidas.add("nager")
    with pytest.raises(FuenteNoDisponible):
        feriados_ar(2026)
    red.caidas.clear()
    assert feriados_ar(2026)  # el error no quedó en caché


def test_clima_historico_y_reciente(red):
    hoy = date.today()
    c = clima_diario(-31.29, -64.29, date(2026, 10, 1), date(2026, 10, 31), hoy=max(hoy, date(2026, 11, 14)))
    assert len(c) == 31 and c[date(2026, 10, 2)]["lluvia_mm"] == 8.0
    assert all("archive" in u for u, _ in red.pedidos)
    red.pedidos.clear()
    futuro = clima_diario(-31.29, -64.29, hoy, hoy + timedelta(days=30))
    assert max(futuro) == hoy + timedelta(days=15)  # tope del pronóstico
    assert any("forecast" in u for u, _ in red.pedidos)


def test_clima_con_clave_comercial(red, monkeypatch):
    monkeypatch.setenv("OPEN_METEO_API_KEY", "k")
    clima_diario(-31.29, -64.29, date(2025, 1, 1), date(2025, 1, 5), hoy=date(2026, 11, 14))
    url, params = red.pedidos[0]
    assert url.startswith("https://customer-archive-api.open-meteo.com") and params["apikey"] == "k"


# ---------------------------------------------------------------- calendario
def test_fin_de_semana_largo_y_vispera(red):
    c = CalendarioDias(date(2026, 11, 18), date(2026, 12, 10))
    v = {f: c.variables(f, 2) for f in dias(date(2026, 11, 18), date(2026, 12, 10))}
    assert [v[date(2026, 11, d)]["fin_de_semana_largo"] for d in (20, 21, 22, 23, 24)] == [False, True, True, True, False]
    assert v[date(2026, 11, 20)]["vispera_feriado"] and v[date(2026, 11, 23)]["feriado"]
    assert v[date(2026, 12, 7)]["no_laborable"] and not v[date(2026, 12, 7)]["feriado"]
    assert all(v[date(2026, 12, d)]["fin_de_semana_largo"] for d in (5, 6, 7, 8))
    assert [f.day for f in v if f.month == 12 and v[f]["dia_cobro"]] == [1, 2, 3, 4, 9]
    assert not v[date(2026, 11, 25)]["fin_de_semana_largo"]


def test_semana_santa_y_temporadas(red):
    assert pascua(2026) == date(2026, 4, 5) and pascua(2027) == date(2027, 3, 28)
    c = CalendarioDias(date(2026, 4, 1), date(2026, 7, 20))
    jueves = c.variables(date(2026, 4, 2))
    assert jueves["no_laborable"] and jueves["temporada"] == "semana_santa"
    assert c.variables(date(2026, 7, 8))["temporada"] == "vacaciones_invierno"
    assert c.variables(date(2026, 6, 20))["aguinaldo"]
    assert CalendarioDias(date(2026, 1, 10), date(2026, 1, 10)).variables(date(2026, 1, 10))["temporada"] == "verano"


def test_evento_solo_en_su_localidad(red):
    c = CalendarioDias(date(2026, 10, 9), date(2026, 10, 12))
    assert c.variables(date(2026, 10, 10), 4)["evento"] == "Oktoberfest"
    assert c.variables(date(2026, 10, 10), 1)["evento"] is None


def test_fecha_a_confirmar_va_a_avisos(red):
    c = CalendarioDias(date(2027, 10, 1), date(2027, 10, 3))
    c.variables(date(2027, 10, 2), 4)
    assert any("no confirmadas" in a and "Oktoberfest" in a for a in c.todos_los_avisos())


def test_sin_feriados_quedan_en_null(red):
    red.caidas.add("nager")
    c = CalendarioDias(date(2026, 11, 20), date(2026, 11, 24))
    v = c.variables(date(2026, 11, 23))
    assert v["feriado"] is None and v["fin_de_semana_largo"] is None and v["vispera_feriado"] is None
    assert v["dia_cobro"] is not None
    assert any("Feriados 2026 no disponibles" in a for a in c.todos_los_avisos())


# ---------------------------------------------------------------- herramientas
def test_ventas_con_contexto(red, base, ctx):
    filas = {(2, f): (1000.0, 10, 20.0) for f in dias(date(2026, 10, 1), date(2026, 10, 31)) if f.day != 15}
    filas.update({(0, date(2026, 10, 5)): (500.0, 1, 2.0)})
    base(filas)
    r = json.loads(externas.ventas_con_contexto(ctx, desde="2026-10-01", hasta="2026-10-31"))
    cols = r["columnas"]
    cp = [dict(zip(cols, f)) for f in r["filas"] if f[cols.index("lugar_venta_id")] == 2]
    assert len(cp) == 31
    dia15 = next(f for f in cp if f["fecha"] == "2026-10-15")
    assert dia15["ventas"] == 0 and dia15["tickets"] == 0
    assert next(f for f in cp if f["fecha"] == "2026-10-02")["dia_lluvioso"] is True
    assert next(f for f in cp if f["fecha"] == "2026-10-12")["feriado"] is True
    dietetica = [dict(zip(cols, f)) for f in r["filas"] if f[cols.index("lugar_venta_id")] == 0]
    assert dietetica[0]["lluvia_mm"] is None
    assert any("Lugar de venta 0 no tiene coordenadas" in a for a in r["avisos"])
    assert r["fuentes"] and not r["truncado"]


def test_ventas_con_contexto_limites(red, base, ctx):
    base({})
    assert "400 días" in json.loads(externas.ventas_con_contexto(ctx, desde="2024-01-01", hasta="2026-01-01"))["error"]
    filas = {(lid, f): (1.0, 1, 1.0) for lid in (1, 2) for f in dias(date(2026, 1, 1), date(2026, 12, 31))}
    base(filas)
    r = json.loads(externas.ventas_con_contexto(ctx, desde="2026-01-01", hasta="2026-10-31"))
    assert r["truncado"] and r["total_filas"] == ctx.max_filas


def test_lugar_sin_catalogar(red, base, ctx):
    base({(9, date(2026, 10, 1)): (1.0, 1, 1.0)})
    r = json.loads(externas.ventas_con_contexto(ctx, desde="2026-10-01", hasta="2026-10-01"))
    assert any("9 no está en config/lugares_venta.yaml" in a for a in r["avisos"])


def test_clima_caido_no_corta_la_herramienta(red, base, ctx):
    red.caidas.add("open-meteo")
    base({(2, date(2026, 10, 1)): (1.0, 1, 1.0)})
    r = json.loads(externas.ventas_con_contexto(ctx, desde="2026-10-01", hasta="2026-10-01"))
    fila = dict(zip(r["columnas"], r["filas"][0]))
    assert fila["temp_max"] is None and fila["feriado"] is False
    assert any("Clima no disponible para Carlos Paz" in a for a in r["avisos"])


def test_impacto_mide_la_lluvia(red, base, ctx):
    # Villa Allende vende 1000 por día y la mitad cuando llueve
    filas = {(1, f): (500.0 if f in LLUVIA else 1000.0, 10, 10.0) for f in dias(date(2026, 9, 1), date(2026, 11, 10))}
    base(filas)
    r = json.loads(externas.impacto_variables(ctx, desde="2026-09-01", hasta="2026-11-10", lugar_venta_id=1))
    lluvia = next(e for e in r["ranking"] if e["variable"] == "dia_lluvioso")
    assert lluvia["dias_con"] == len(LLUVIA) and lluvia["confiable"]
    assert lluvia["efecto_pct"] == pytest.approx(-50, abs=6)
    assert r["ranking"][0]["variable"] == "dia_lluvioso"
    semana_santa = next(e for e in r["ranking"] if e["variable"] == "semana_santa")
    assert semana_santa["estado"] == "insuficiente"
    assert any("menos de un año" in a for a in r["avisos"]) and "mediana móvil" in r["metodo"]


def test_impacto_validaciones(red, base, ctx):
    base({})
    assert "metrica" in json.loads(externas.impacto_variables(ctx, metrica="margen"))["error"]
    assert "temporada" in json.loads(externas.impacto_variables(ctx, temporada="otoño"))["error"]
    assert "No hay ventas" in json.loads(externas.impacto_variables(ctx, desde="2026-01-01", hasta="2026-02-01"))["error"]


def test_contexto_proximos_dias(red, base, ctx):
    inicio = date(2026, 11, 14)
    filas = {(2, f): (float(f.weekday() + 1) * 100, 5, 5.0) for f in dias(inicio - timedelta(days=63), inicio - timedelta(days=1))}
    filas[(1, inicio - timedelta(days=50))] = (1.0, 1, 1.0)  # inactivo hace más de 30 días: no aparece
    base(filas)
    r = json.loads(externas.contexto_proximos_dias(ctx, dias=20, desde="2026-11-14"))
    filas_r = [dict(zip(r["columnas"], f)) for f in r["filas"]]
    assert len(filas_r) == 14 and {f["lugar_venta_id"] for f in filas_r} == {2}
    lunes = next(f for f in filas_r if f["fecha"] == "2026-11-23")
    assert lunes["fin_de_semana_largo"] and lunes["feriado"] and lunes["ventas_referencia"] == 100.0
    assert lunes["dias_referencia"] == 8


def test_registradas_en_ambos_canales():
    nombres = {"ventas_con_contexto", "impacto_variables", "contexto_proximos_dias"}
    assert nombres <= set(registro.HERRAMIENTAS)
    assert nombres <= set(cargar_configuracion().perfiles["ventas"].herramientas)
    defs = {d["name"]: d for d in registro.definiciones(sorted(nombres))}
    assert "lugar_venta_id" in defs["impacto_variables"]["input_schema"]["properties"]
