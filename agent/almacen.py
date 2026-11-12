"""
Persistencia de conversaciones: historial solo-agregado, pasos de herramientas y estado del turno.

Dos implementaciones con la misma interfaz: AlmacenPostgres (esquema app, producción) y
AlmacenMemoria (pruebas y desarrollo local).
"""

import json
import threading
import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine

# Un turno en curso que no avanzó en este tiempo se considera cortado y se puede retomar.
LEASE = timedelta(minutes=5)
# Los filtros por fecha de la galería usan la fecha local de la empresa.
ZONA = ZoneInfo("America/Argentina/Cordoba")


class ConversacionOcupada(Exception):
    """Hay otro turno en curso en la misma conversación."""


@dataclass(frozen=True)
class Conversacion:
    id: str
    usuario: str
    perfil: str
    titulo: str
    estado: str
    tool_use_pendiente: dict | None
    creada: datetime
    actualizada: datetime


@dataclass(frozen=True)
class Paso:
    tool_use_id: str
    nombre: str
    argumentos: dict
    resultado: str
    es_error: bool
    duracion_ms: int


@dataclass(frozen=True)
class Brief:
    id: str
    conversacion_id: str
    tool_use_id: str
    contenido: dict
    respuestas: dict | None
    estado: str
    creado: datetime


@dataclass(frozen=True)
class Artifact:
    id: str
    titulo: str
    tipo: str
    perfil: str
    autor: str
    conversacion_id: str | None
    brief_id: str | None
    fijado: bool
    version_actual: int
    creado: datetime
    actualizado: datetime


@dataclass(frozen=True)
class Version:
    artifact_id: str
    version: int
    html: str
    nota: str
    contenido: dict
    datos_fuente: list
    tool_use_id: str | None
    creado: datetime


@dataclass(frozen=True)
class FiltroArtifacts:
    perfiles: frozenset[str] | None = None  # visibles para el usuario; None = todos (admin)
    texto: str | None = None                # búsqueda en el título
    perfil: str | None = None
    autor: str | None = None
    tipo: str | None = None
    desde: date | None = None               # fecha local de la última actualización, inclusive
    hasta: date | None = None
    limite: int = 100


@dataclass(frozen=True)
class RegistroConsulta:
    usuario: str
    perfil: str
    conversacion_id: str | None
    herramienta: str
    sql: str | None
    parametros: dict | None
    duracion_ms: int
    filas: int | None
    error: str | None


@dataclass(frozen=True)
class RegistroUso:
    usuario: str
    perfil: str
    conversacion_id: str | None
    modelo: str
    entrada: int
    salida: int
    cache_lectura: int
    cache_escritura: int
    costo_usd: float
    creado: datetime = field(default_factory=lambda: _ahora())


AGRUPACIONES = ("usuario", "perfil", "mes")
_CAMPOS_USO = ("entrada", "salida", "cache_lectura", "cache_escritura")


def _fila_uso(clave) -> dict:
    return {"clave": clave, "llamadas": 0, **{c: 0 for c in _CAMPOS_USO}, "costo_usd": 0.0,
            "consultas": 0, "consultas_con_error": 0}


def _mes(dt: datetime) -> str:
    return dt.astimezone(ZONA).strftime("%Y-%m")


def _es_uuid(v: str | None) -> bool:
    try:
        uuid.UUID(str(v))
        return True
    except ValueError:
        return False


class Almacen(Protocol):
    def crear_conversacion(self, usuario: str, perfil: str, titulo: str) -> Conversacion: ...
    def conversacion(self, conv_id: str) -> Conversacion | None: ...
    def conversaciones_de(self, usuario: str | None, limite: int = 50) -> list[Conversacion]: ...
    def mensajes(self, conv_id: str) -> list[dict]: ...
    def agregar_mensaje(self, conv_id: str, rol: str, contenido) -> int: ...
    def guardar_paso(self, conv_id: str, paso: Paso) -> None: ...
    def pasos(self, conv_id: str) -> dict[str, Paso]: ...
    def tomar_turno(self, conv_id: str) -> None: ...
    def latido(self, conv_id: str) -> None: ...
    def soltar_turno(self, conv_id: str, estado: str = "lista", tool_use_pendiente: dict | None = None) -> None: ...
    # briefs
    def crear_brief(self, conv_id: str, tool_use_id: str, contenido: dict, respuestas: dict,
                    estado: str = "aprobado") -> Brief: ...
    def brief(self, brief_id: str) -> Brief | None: ...
    # artifacts
    def crear_artifact(self, *, titulo: str, tipo: str, perfil: str, autor: str, conversacion_id: str | None,
                       brief_id: str | None, html: str, contenido: dict, datos_fuente: list,
                       tool_use_id: str | None) -> Artifact: ...
    def agregar_version(self, artifact_id: str, *, html: str, nota: str, contenido: dict, datos_fuente: list,
                        tool_use_id: str | None, titulo: str | None = None) -> Artifact: ...
    def artifact(self, artifact_id: str) -> Artifact | None: ...
    def version(self, artifact_id: str, n: int | None = None) -> Version | None: ...
    def versiones(self, artifact_id: str) -> list[Version]: ...
    def version_de_tool_use(self, tool_use_id: str) -> Version | None: ...
    def buscar_artifacts(self, filtro: FiltroArtifacts) -> list[Artifact]: ...
    def fijar(self, artifact_id: str, fijado: bool) -> None: ...
    # auditoría y uso
    def registrar_consulta(self, r: "RegistroConsulta") -> None: ...
    def registrar_uso(self, r: "RegistroUso") -> None: ...
    def costo_desde(self, usuario: str, desde: datetime) -> float: ...
    def uso_agrupado(self, desde: datetime, hasta: datetime, por: str) -> list[dict]: ...


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- memoria
@dataclass
class _ConvMem:
    conv: Conversacion
    mensajes: list[dict] = field(default_factory=list)
    pasos: dict[str, Paso] = field(default_factory=dict)
    latido: datetime | None = None


class AlmacenMemoria:
    def __init__(self):
        self._datos: dict[str, _ConvMem] = {}
        self._briefs: dict[str, Brief] = {}
        self._artifacts: dict[str, Artifact] = {}
        self._versiones: dict[str, list[Version]] = {}
        self._consultas: list[tuple[datetime, RegistroConsulta]] = []
        self._usos: list[RegistroUso] = []
        self._lock = threading.RLock()

    def crear_conversacion(self, usuario, perfil, titulo):
        ahora = _ahora()
        c = Conversacion(str(uuid.uuid4()), usuario, perfil, titulo, "lista", None, ahora, ahora)
        with self._lock:
            self._datos[c.id] = _ConvMem(c)
        return c

    def conversacion(self, conv_id):
        d = self._datos.get(conv_id)
        return d.conv if d else None

    def conversaciones_de(self, usuario, limite=50):
        convs = [d.conv for d in self._datos.values() if usuario is None or d.conv.usuario == usuario]
        return sorted(convs, key=lambda c: c.actualizada, reverse=True)[:limite]

    def mensajes(self, conv_id):
        return json.loads(json.dumps(self._datos[conv_id].mensajes))  # copia profunda

    def agregar_mensaje(self, conv_id, rol, contenido):
        with self._lock:
            d = self._datos[conv_id]
            d.mensajes.append({"role": rol, "content": json.loads(json.dumps(contenido))})
            d.conv = replace(d.conv, actualizada=_ahora())
            return len(d.mensajes) - 1

    def guardar_paso(self, conv_id, paso):
        with self._lock:
            self._datos[conv_id].pasos.setdefault(paso.tool_use_id, paso)

    def pasos(self, conv_id):
        return dict(self._datos[conv_id].pasos)

    def tomar_turno(self, conv_id):
        with self._lock:
            d = self._datos[conv_id]
            if d.conv.estado == "en_curso" and d.latido and _ahora() - d.latido < LEASE:
                raise ConversacionOcupada(conv_id)
            d.conv = replace(d.conv, estado="en_curso")
            d.latido = _ahora()

    def latido(self, conv_id):
        self._datos[conv_id].latido = _ahora()

    def soltar_turno(self, conv_id, estado="lista", tool_use_pendiente=None):
        with self._lock:
            d = self._datos[conv_id]
            d.conv = replace(d.conv, estado=estado, tool_use_pendiente=tool_use_pendiente, actualizada=_ahora())
            d.latido = None


    # ------------------------------------------------ briefs y artifacts
    def crear_brief(self, conv_id, tool_use_id, contenido, respuestas, estado="aprobado"):
        b = Brief(str(uuid.uuid4()), conv_id, tool_use_id, _copia(contenido), _copia(respuestas), estado, _ahora())
        with self._lock:
            self._briefs[b.id] = b
        return b

    def brief(self, brief_id):
        return self._briefs.get(str(brief_id))

    def crear_artifact(self, *, titulo, tipo, perfil, autor, conversacion_id, brief_id, html, contenido,
                       datos_fuente, tool_use_id):
        ahora = _ahora()
        a = Artifact(str(uuid.uuid4()), titulo, tipo, perfil, autor, conversacion_id, brief_id, False, 1,
                     ahora, ahora)
        with self._lock:
            self._artifacts[a.id] = a
            self._versiones[a.id] = [Version(a.id, 1, html, "", _copia(contenido), _copia(datos_fuente),
                                             tool_use_id, ahora)]
        return a

    def agregar_version(self, artifact_id, *, html, nota, contenido, datos_fuente, tool_use_id, titulo=None):
        with self._lock:
            a = self._artifacts[artifact_id]
            ahora = _ahora()
            a = replace(a, version_actual=a.version_actual + 1, actualizado=ahora, titulo=titulo or a.titulo)
            self._artifacts[a.id] = a
            self._versiones[a.id].append(Version(a.id, a.version_actual, html, nota, _copia(contenido),
                                                 _copia(datos_fuente), tool_use_id, ahora))
        return a

    def artifact(self, artifact_id):
        return self._artifacts.get(str(artifact_id))

    def version(self, artifact_id, n=None):
        vs = self._versiones.get(str(artifact_id), [])
        if n is None:
            return vs[-1] if vs else None
        return next((v for v in vs if v.version == n), None)

    def versiones(self, artifact_id):
        return list(self._versiones.get(str(artifact_id), []))

    def version_de_tool_use(self, tool_use_id):
        return next((v for vs in self._versiones.values() for v in vs if v.tool_use_id == tool_use_id), None)

    def buscar_artifacts(self, filtro):
        def pasa(a: Artifact) -> bool:
            dia = a.actualizado.astimezone(ZONA).date()
            return ((filtro.perfiles is None or a.perfil in filtro.perfiles)
                    and (not filtro.texto or filtro.texto.lower() in a.titulo.lower())
                    and (not filtro.perfil or a.perfil == filtro.perfil)
                    and (not filtro.autor or a.autor == filtro.autor)
                    and (not filtro.tipo or a.tipo == filtro.tipo)
                    and (not filtro.desde or dia >= filtro.desde)
                    and (not filtro.hasta or dia <= filtro.hasta))
        res = sorted((a for a in self._artifacts.values() if pasa(a)), key=lambda a: a.actualizado, reverse=True)
        res.sort(key=lambda a: not a.fijado)  # estable: fijados primero, cada grupo por fecha
        return res[:filtro.limite]

    def fijar(self, artifact_id, fijado):
        with self._lock:
            a = self._artifacts[artifact_id]
            self._artifacts[a.id] = replace(a, fijado=fijado)


    # ------------------------------------------------ auditoría y uso
    def registrar_consulta(self, r):
        with self._lock:
            self._consultas.append((_ahora(), r))

    def registrar_uso(self, r):
        with self._lock:
            self._usos.append(r)

    def costo_desde(self, usuario, desde):
        return round(sum(u.costo_usd for u in self._usos if u.usuario == usuario and u.creado >= desde), 6)

    def uso_agrupado(self, desde, hasta, por):
        assert por in AGRUPACIONES
        clave = (lambda r, dt: _mes(dt)) if por == "mes" else (lambda r, dt: getattr(r, por))
        filas: dict[str, dict] = {}
        for u in self._usos:
            if desde <= u.creado < hasta:
                f = filas.setdefault(clave(u, u.creado), _fila_uso(clave(u, u.creado)))
                f["llamadas"] += 1
                for c in _CAMPOS_USO:
                    f[c] += getattr(u, c)
                f["costo_usd"] = round(f["costo_usd"] + u.costo_usd, 6)
        for dt, r in self._consultas:
            if desde <= dt < hasta:
                f = filas.setdefault(clave(r, dt), _fila_uso(clave(r, dt)))
                f["consultas"] += 1
                f["consultas_con_error"] += r.error is not None
        return sorted(filas.values(), key=lambda f: (-f["costo_usd"], f["clave"]))


def _copia(obj):
    return json.loads(json.dumps(obj)) if obj is not None else None


# ---------------------------------------------------------------- postgres
_COLS = "id::text, usuario, perfil, titulo, estado, tool_use_pendiente, creada, actualizada"


def _conv(fila) -> Conversacion:
    return Conversacion(*fila)


class AlmacenPostgres:
    def __init__(self, engine: Engine):
        self.engine = engine

    def crear_conversacion(self, usuario, perfil, titulo):
        with self.engine.begin() as c:
            fila = c.execute(text(f"INSERT INTO app.conversaciones (usuario, perfil, titulo) "
                                  f"VALUES (:u, :p, :t) RETURNING {_COLS}"),
                             {"u": usuario, "p": perfil, "t": titulo[:200]}).one()
        return _conv(fila)

    def conversacion(self, conv_id):
        try:
            uuid.UUID(conv_id)
        except ValueError:
            return None
        with self.engine.connect() as c:
            fila = c.execute(text(f"SELECT {_COLS} FROM app.conversaciones WHERE id = :id"),
                             {"id": conv_id}).first()
        return _conv(fila) if fila else None

    def conversaciones_de(self, usuario, limite=50):
        filtro = "WHERE usuario = :u" if usuario is not None else ""
        with self.engine.connect() as c:
            filas = c.execute(text(f"SELECT {_COLS} FROM app.conversaciones {filtro} "
                                   "ORDER BY actualizada DESC LIMIT :l"), {"u": usuario, "l": limite}).all()
        return [_conv(f) for f in filas]

    def mensajes(self, conv_id):
        with self.engine.connect() as c:
            filas = c.execute(text("SELECT rol, contenido FROM app.mensajes WHERE conversacion_id = :id "
                                   "ORDER BY orden"), {"id": conv_id}).all()
        return [{"role": r, "content": contenido} for r, contenido in filas]

    def agregar_mensaje(self, conv_id, rol, contenido):
        # El PK (conversacion_id, orden) impide que dos escrituras concurrentes tomen el mismo orden.
        with self.engine.begin() as c:
            orden = c.execute(text(
                "INSERT INTO app.mensajes (conversacion_id, orden, rol, contenido) "
                "SELECT :id, COALESCE(MAX(orden) + 1, 0), :rol, CAST(:contenido AS jsonb) "
                "FROM app.mensajes WHERE conversacion_id = :id RETURNING orden"),
                {"id": conv_id, "rol": rol, "contenido": json.dumps(contenido, ensure_ascii=False)}).scalar_one()
            c.execute(text("UPDATE app.conversaciones SET actualizada = now(), latido = now() WHERE id = :id"),
                      {"id": conv_id})
        return orden

    def guardar_paso(self, conv_id, paso):
        with self.engine.begin() as c:
            c.execute(text(
                "INSERT INTO app.pasos_herramienta (conversacion_id, tool_use_id, nombre, argumentos, "
                "resultado, es_error, duracion_ms) VALUES (:id, :t, :n, CAST(:a AS jsonb), :r, :e, :d) "
                "ON CONFLICT DO NOTHING"),
                {"id": conv_id, "t": paso.tool_use_id, "n": paso.nombre,
                 "a": json.dumps(paso.argumentos, ensure_ascii=False), "r": paso.resultado,
                 "e": paso.es_error, "d": paso.duracion_ms})

    def pasos(self, conv_id):
        with self.engine.connect() as c:
            filas = c.execute(text("SELECT tool_use_id, nombre, argumentos, resultado, es_error, duracion_ms "
                                   "FROM app.pasos_herramienta WHERE conversacion_id = :id"),
                              {"id": conv_id}).all()
        return {f[0]: Paso(*f) for f in filas}

    def tomar_turno(self, conv_id):
        with self.engine.begin() as c:
            ok = c.execute(text(
                "UPDATE app.conversaciones SET estado = 'en_curso', latido = now() WHERE id = :id "
                "AND (estado <> 'en_curso' OR latido IS NULL OR latido < now() - make_interval(secs => :s)) "
                "RETURNING id"), {"id": conv_id, "s": LEASE.total_seconds()}).first()
        if not ok:
            raise ConversacionOcupada(conv_id)

    def latido(self, conv_id):
        with self.engine.begin() as c:
            c.execute(text("UPDATE app.conversaciones SET latido = now() WHERE id = :id"), {"id": conv_id})

    def soltar_turno(self, conv_id, estado="lista", tool_use_pendiente=None):
        with self.engine.begin() as c:
            c.execute(text(
                "UPDATE app.conversaciones SET estado = :e, tool_use_pendiente = CAST(:t AS jsonb), "
                "latido = NULL, actualizada = now() WHERE id = :id"),
                {"id": conv_id, "e": estado,
                 "t": json.dumps(tool_use_pendiente) if tool_use_pendiente is not None else None})

    # ------------------------------------------------ briefs y artifacts
    def crear_brief(self, conv_id, tool_use_id, contenido, respuestas, estado="aprobado"):
        with self.engine.begin() as c:
            fila = c.execute(text(
                "INSERT INTO app.briefs (conversacion_id, tool_use_id, contenido, respuestas, estado) "
                "VALUES (:c, :t, CAST(:co AS jsonb), CAST(:r AS jsonb), :e) "
                f"RETURNING {_COLS_BRIEF}"),
                {"c": conv_id, "t": tool_use_id, "co": _js(contenido), "r": _js(respuestas), "e": estado}).one()
        return Brief(*fila)

    def brief(self, brief_id):
        if not _es_uuid(brief_id):
            return None
        with self.engine.connect() as c:
            fila = c.execute(text(f"SELECT {_COLS_BRIEF} FROM app.briefs WHERE id = :id"), {"id": brief_id}).first()
        return Brief(*fila) if fila else None

    def crear_artifact(self, *, titulo, tipo, perfil, autor, conversacion_id, brief_id, html, contenido,
                       datos_fuente, tool_use_id):
        with self.engine.begin() as c:
            fila = c.execute(text(
                "INSERT INTO app.artifacts (titulo, tipo, perfil, autor, conversacion_id, brief_id) "
                f"VALUES (:ti, :tp, :p, :a, :c, :b) RETURNING {_COLS_ART}"),
                {"ti": titulo, "tp": tipo, "p": perfil, "a": autor, "c": conversacion_id, "b": brief_id}).one()
            self._insertar_version(c, fila[0], 1, html, "", contenido, datos_fuente, tool_use_id)
        return Artifact(*fila)

    def agregar_version(self, artifact_id, *, html, nota, contenido, datos_fuente, tool_use_id, titulo=None):
        # El UPDATE bloquea la fila: dos ediciones simultáneas obtienen números consecutivos.
        with self.engine.begin() as c:
            fila = c.execute(text(
                "UPDATE app.artifacts SET version_actual = version_actual + 1, actualizado = now(), "
                f"titulo = COALESCE(:ti, titulo) WHERE id = :id RETURNING {_COLS_ART}"),
                {"id": artifact_id, "ti": titulo}).one()
            self._insertar_version(c, artifact_id, fila[8], html, nota, contenido, datos_fuente, tool_use_id)
        return Artifact(*fila)

    @staticmethod
    def _insertar_version(c, artifact_id, n, html, nota, contenido, datos_fuente, tool_use_id):
        c.execute(text(
            "INSERT INTO app.artifact_versions (artifact_id, version, html, nota, contenido, datos_fuente, "
            "tool_use_id) VALUES (:a, :n, :h, :no, CAST(:co AS jsonb), CAST(:d AS jsonb), :t)"),
            {"a": artifact_id, "n": n, "h": html, "no": nota, "co": _js(contenido), "d": _js(datos_fuente),
             "t": tool_use_id})

    def artifact(self, artifact_id):
        if not _es_uuid(artifact_id):
            return None
        with self.engine.connect() as c:
            fila = c.execute(text(f"SELECT {_COLS_ART} FROM app.artifacts WHERE id = :id"),
                             {"id": artifact_id}).first()
        return Artifact(*fila) if fila else None

    def version(self, artifact_id, n=None):
        if not _es_uuid(artifact_id):
            return None
        filtro = "AND version = :n" if n is not None else ""
        with self.engine.connect() as c:
            fila = c.execute(text(f"SELECT {_COLS_VER} FROM app.artifact_versions WHERE artifact_id = :a "
                                  f"{filtro} ORDER BY version DESC LIMIT 1"), {"a": artifact_id, "n": n}).first()
        return Version(*fila) if fila else None

    def versiones(self, artifact_id):
        if not _es_uuid(artifact_id):
            return []
        with self.engine.connect() as c:
            filas = c.execute(text(f"SELECT {_COLS_VER} FROM app.artifact_versions WHERE artifact_id = :a "
                                   "ORDER BY version"), {"a": artifact_id}).all()
        return [Version(*f) for f in filas]

    def version_de_tool_use(self, tool_use_id):
        with self.engine.connect() as c:
            fila = c.execute(text(f"SELECT {_COLS_VER} FROM app.artifact_versions WHERE tool_use_id = :t"),
                             {"t": tool_use_id}).first()
        return Version(*fila) if fila else None

    def buscar_artifacts(self, filtro):
        condiciones, params = [], {"l": filtro.limite, "z": ZONA.key}
        if filtro.perfiles is not None:
            condiciones.append("perfil = ANY(:perfiles)")
            params["perfiles"] = sorted(filtro.perfiles)
        if filtro.texto:
            condiciones.append("titulo ILIKE :texto")
            params["texto"] = "%" + filtro.texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        for campo in ("perfil", "autor", "tipo"):
            if getattr(filtro, campo):
                condiciones.append(f"{campo} = :{campo}")
                params[campo] = getattr(filtro, campo)
        if filtro.desde:
            condiciones.append("(actualizado AT TIME ZONE :z)::date >= :desde")
            params["desde"] = filtro.desde
        if filtro.hasta:
            condiciones.append("(actualizado AT TIME ZONE :z)::date <= :hasta")
            params["hasta"] = filtro.hasta
        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
        with self.engine.connect() as c:
            filas = c.execute(text(f"SELECT {_COLS_ART} FROM app.artifacts {where} "
                                   "ORDER BY fijado DESC, actualizado DESC LIMIT :l"), params).all()
        return [Artifact(*f) for f in filas]

    def fijar(self, artifact_id, fijado):
        with self.engine.begin() as c:
            c.execute(text("UPDATE app.artifacts SET fijado = :f WHERE id = :id"), {"id": artifact_id, "f": fijado})


    # ------------------------------------------------ auditoría y uso
    def registrar_consulta(self, r):
        with self.engine.begin() as c:
            c.execute(text(
                "INSERT INTO app.auditoria_sql (usuario, perfil, conversacion_id, herramienta, sql, parametros, "
                "duracion_ms, filas, error) VALUES (:u, :p, :c, :h, :s, CAST(:pa AS jsonb), :d, :f, :e)"),
                {"u": r.usuario, "p": r.perfil, "c": r.conversacion_id, "h": r.herramienta, "s": r.sql,
                 "pa": json.dumps(r.parametros, ensure_ascii=False, default=str) if r.parametros is not None else None,
                 "d": r.duracion_ms, "f": r.filas, "e": r.error})

    def registrar_uso(self, r):
        with self.engine.begin() as c:
            c.execute(text(
                "INSERT INTO app.uso_tokens (usuario, perfil, conversacion_id, modelo, entrada, salida, "
                "cache_lectura, cache_escritura, costo_usd, creado) VALUES (:u, :p, :c, :m, :e, :s, :cl, :ce, :co, :t)"),
                {"u": r.usuario, "p": r.perfil, "c": r.conversacion_id, "m": r.modelo, "e": r.entrada,
                 "s": r.salida, "cl": r.cache_lectura, "ce": r.cache_escritura, "co": r.costo_usd, "t": r.creado})

    def costo_desde(self, usuario, desde):
        with self.engine.connect() as c:
            v = c.execute(text("SELECT COALESCE(SUM(costo_usd), 0) FROM app.uso_tokens "
                               "WHERE usuario = :u AND creado >= :d"), {"u": usuario, "d": desde}).scalar_one()
        return float(v)

    def uso_agrupado(self, desde, hasta, por):
        assert por in AGRUPACIONES
        clave = "to_char(creado AT TIME ZONE :z, 'YYYY-MM')" if por == "mes" else por
        params = {"d": desde, "h": hasta, "z": ZONA.key}
        filas: dict[str, dict] = {}
        with self.engine.connect() as c:
            for k, n, e, s, cl, ce, co in c.execute(text(
                    f"SELECT {clave}, count(*), SUM(entrada), SUM(salida), SUM(cache_lectura), "
                    f"SUM(cache_escritura), SUM(costo_usd) FROM app.uso_tokens "
                    f"WHERE creado >= :d AND creado < :h GROUP BY 1"), params):
                filas[k] = {**_fila_uso(k), "llamadas": n, "entrada": int(e), "salida": int(s),
                            "cache_lectura": int(cl), "cache_escritura": int(ce), "costo_usd": round(float(co), 6)}
            for k, n, err in c.execute(text(
                    f"SELECT {clave}, count(*), count(error) FROM app.auditoria_sql "
                    f"WHERE creado >= :d AND creado < :h GROUP BY 1"), params):
                f = filas.setdefault(k, _fila_uso(k))
                f["consultas"], f["consultas_con_error"] = n, err
        return sorted(filas.values(), key=lambda f: (-f["costo_usd"], f["clave"]))

_COLS_BRIEF = "id::text, conversacion_id::text, tool_use_id, contenido, respuestas, estado, creado"
_COLS_ART = ("id::text, titulo, tipo, perfil, autor, conversacion_id::text, brief_id::text, fijado, "
             "version_actual, creado, actualizado")
_COLS_VER = "artifact_id::text, version, html, nota, contenido, datos_fuente, tool_use_id, creado"


def _js(obj) -> str | None:
    return json.dumps(obj, ensure_ascii=False) if obj is not None else None

