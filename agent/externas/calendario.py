"""
Variables de calendario por día y lugar de venta.

Combina los feriados de Nager.Date con config/calendario_externo.yaml y calcula fin de semana
largo, víspera, día de cobro, aguinaldo, temporada y eventos locales.
"""

from datetime import date, timedelta

from agent.externas import config
from agent.externas.feriados import feriados_ar
from agent.externas.http import FuenteNoDisponible

DIAS_COBRO = 5            # primeros N días hábiles del mes
INICIO_VERANO = (12, 15)  # 15/12 al 15/03
FIN_VERANO = (3, 15)


def pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo gregoriano anónimo)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(anio, mes, dia)


def _dias(desde: date, hasta: date):
    d = desde
    while d <= hasta:
        yield d
        d += timedelta(days=1)


def _es_verano(f: date) -> bool:
    return (f.month, f.day) >= INICIO_VERANO or (f.month, f.day) <= FIN_VERANO


class CalendarioDias:
    """Calcula las variables de calendario para un rango. Las fallas de Nager.Date van a `avisos`."""

    def __init__(self, desde: date, hasta: date, calendario: config.Calendario | None = None):
        self.desde, self.hasta = desde, hasta
        self.cal = calendario or config.calendario()
        self.avisos: list[str] = []
        self._pendientes: set[str] = set()
        # Margen para detectar bloques de fin de semana largo que cruzan los bordes del rango
        ini, fin = desde - timedelta(days=10), hasta + timedelta(days=10)

        self.feriados: dict[date, str] = {}
        self.anios_sin_feriados: set[int] = set()
        for anio in range(ini.year, fin.year + 1):
            try:
                self.feriados.update(feriados_ar(anio))
            except FuenteNoDisponible as e:
                self.anios_sin_feriados.add(anio)
                if desde.year <= anio <= hasta.year:
                    self.avisos.append(f"Feriados {anio} no disponibles ({e}): feriado, fin de semana largo "
                                       f"y víspera quedan en null para ese año.")

        self.no_laborables: dict[date, str] = {}
        self._estado_no_lab: dict[date, str] = {}
        for nl in self.cal.no_laborables:
            self.no_laborables[nl.fecha] = nl.nombre
            self._estado_no_lab[nl.fecha] = nl.estado
        for anio in range(ini.year, fin.year + 1):
            jueves_santo = pascua(anio) - timedelta(days=3)
            self.no_laborables.setdefault(jueves_santo, "Jueves Santo")

        inhabiles = {f for f in _dias(ini, fin)
                     if f.weekday() >= 5 or f in self.feriados or f in self.no_laborables}
        self._largo: set[date] = set()
        self._vispera: set[date] = set()
        f = ini
        while f <= fin:
            if f not in inhabiles:
                f += timedelta(days=1)
                continue
            bloque = []
            while f in inhabiles:
                bloque.append(f)
                f += timedelta(days=1)
            especial = any(d in self.feriados or d in self.no_laborables for d in bloque)
            if especial and len(bloque) >= 3:
                self._largo.update(bloque)
            if especial:
                self._vispera.add(bloque[0] - timedelta(days=1))
        self._inhabiles = inhabiles
        self._cobro = self._dias_cobro(ini, fin)

    def _dias_cobro(self, ini: date, fin: date) -> set[date]:
        cobro, contados = set(), {}
        for f in _dias(ini.replace(day=1), fin):
            if f in self._inhabiles:
                continue
            clave = (f.year, f.month)
            if contados.get(clave, 0) < DIAS_COBRO:
                cobro.add(f)
                contados[clave] = contados.get(clave, 0) + 1
        return cobro

    def _temporada(self, f: date) -> str | None:
        p = pascua(f.year)
        if p - timedelta(days=3) <= f <= p:
            return "semana_santa"
        for r in self.cal.vacaciones_invierno:
            if r.desde <= f <= r.hasta:
                if r.estado == "a_confirmar":
                    self._pendientes.add(f"vacaciones de invierno {r.desde:%d/%m/%Y}–{r.hasta:%d/%m/%Y}")
                return "vacaciones_invierno"
        return "verano" if _es_verano(f) else None

    def _eventos(self, f: date, lugar_id: int | None) -> list[str]:
        nombres = []
        for ev in self.cal.eventos:
            if ev.desde <= f <= ev.hasta and (ev.lugares is None or lugar_id in ev.lugares):
                nombres.append(ev.nombre)
                if ev.estado == "a_confirmar":
                    self._pendientes.add(f"{ev.nombre} {ev.desde:%d/%m/%Y}–{ev.hasta:%d/%m/%Y}")
        return nombres

    def variables(self, f: date, lugar_id: int | None = None) -> dict:
        sin_feriados = f.year in self.anios_sin_feriados
        if f in self._estado_no_lab and self._estado_no_lab[f] == "a_confirmar":
            self._pendientes.add(f"{self.no_laborables[f]} {f:%d/%m/%Y}")
        eventos = self._eventos(f, lugar_id)
        return {
            "feriado": None if sin_feriados else f in self.feriados,
            "feriado_nombre": self.feriados.get(f) or self.no_laborables.get(f),
            "no_laborable": f in self.no_laborables,
            "fin_de_semana_largo": None if sin_feriados else f in self._largo,
            "vispera_feriado": None if sin_feriados else f in self._vispera,
            "dia_cobro": f in self._cobro,
            "aguinaldo": any(v.mes == f.month and v.desde_dia <= f.day <= v.hasta_dia for v in self.cal.aguinaldo),
            "temporada": self._temporada(f),
            "evento": " + ".join(eventos) if eventos else None,
        }

    def todos_los_avisos(self) -> list[str]:
        avisos = list(self.avisos)
        if self._pendientes:
            avisos.append("Fechas no confirmadas oficialmente: " + "; ".join(sorted(self._pendientes)) + ".")
        return avisos
