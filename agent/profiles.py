"""
Perfiles (config/perfiles/*.yaml) y usuarios (config/usuarios.yaml).

Un perfil define el prompt, las tablas, las herramientas, la credencial de base y los límites.
Agregar un perfil no requiere código: se escribe su YAML, su prompt y se crea su rol de Postgres.
"""

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from agent.contexto import ContextoPerfil, normalizar_url, validar_nombre_tabla
from agent.tools import registro

RAIZ = Path(__file__).resolve().parent.parent

# Herramientas que leen columnas de ventas y necesitan la tabla principal completa.
HERRAMIENTAS_VENTAS = {"perfil_datos", "resumen_ventas", "comparar_periodos", "clientes_inactivos",
                       "productos_asociados", "proyectar_ventas"}


class ErrorConfiguracion(Exception):
    pass


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Tabla(_Estricto):
    nombre: str
    descripcion: str = ""
    columna_fecha: str | None = None
    columnas: list[str] | None = None  # None = todas
    diccionario: str | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v):
        return validar_nombre_tabla(v)


class BaseDatos(_Estricto):
    credencial_env: str
    tablas: list[Tabla] = Field(min_length=1)


class Reglas(_Estricto):
    excluir_clientes_en_analisis: list[int] = []


class Limites(_Estricto):
    max_filas: int = Field(500, ge=1, le=5000)
    timeout_sql_seg: int = Field(60, ge=1, le=600)
    max_herramientas_por_turno: int = Field(25, ge=1, le=200)
    presupuesto_tokens_por_turno: int = Field(200_000, ge=10_000)


class Perfil(_Estricto):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    nombre: str
    descripcion: str = ""
    modelo: str = "claude-opus-5-5"
    esfuerzo: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    prompt: str
    base_datos: BaseDatos
    herramientas: list[str] = Field(min_length=1)
    reglas: Reglas = Reglas()
    limites: Limites = Limites()

    @field_validator("herramientas")
    @classmethod
    def _herramientas(cls, v):
        desconocidas = [h for h in v if not registro.existe(h)]
        if desconocidas:
            raise ValueError(f"herramientas inexistentes: {desconocidas}")
        if len(set(v)) != len(v):
            raise ValueError("herramientas repetidas")
        if {"generar_artifact", "editar_artifact"} & set(v) and "solicitar_aclaraciones" not in v:
            raise ValueError("generar_artifact y editar_artifact requieren solicitar_aclaraciones")
        return v

    @model_validator(mode="after")
    def _coherencia(self):
        principal = self.base_datos.tablas[0]
        usa_ventas = sorted(HERRAMIENTAS_VENTAS & set(self.herramientas))
        if usa_ventas and principal.columnas is not None:
            raise ValueError(f"{usa_ventas} necesitan todas las columnas de la tabla principal "
                             f"{principal.nombre}; quitá 'columnas' o esas herramientas")
        nombres = [t.nombre for t in self.base_datos.tablas]
        if len(set(nombres)) != len(nombres):
            raise ValueError("tablas repetidas")
        return self

    @property
    def tabla_principal(self) -> str:
        return self.base_datos.tablas[0].nombre

    def tablas_permitidas(self) -> dict[str, frozenset[str] | None]:
        return {t.nombre: (frozenset(c.lower() for c in t.columnas) if t.columnas is not None else None)
                for t in self.base_datos.tablas}

    def system_prompt(self, raiz: Path = RAIZ) -> str:
        """Prompt del perfil + tablas disponibles + diccionarios. Estable: entra en el caché."""
        partes = [(raiz / self.prompt).read_text(encoding="utf-8").strip(), "# Tablas disponibles"]
        for t in self.base_datos.tablas:
            linea = f"- `{t.nombre}`: {t.descripcion}".rstrip(": ")
            if t.columnas is not None:
                linea += f" (solo las columnas: {', '.join(t.columnas)})"
            if t.columna_fecha:
                linea += f". Filtrá por `{t.columna_fecha}`"
            partes.append(linea)
        for t in self.base_datos.tablas:
            if t.diccionario:
                partes.append((raiz / t.diccionario).read_text(encoding="utf-8").strip())
        return "\n\n".join(partes)


class Usuario(_Estricto):
    email: str
    perfiles: list[str] = []
    admin: bool = False
    tope_mensual_usd: float | None = Field(None, ge=0)  # None = el tope general del archivo

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return v.strip().lower()


class _ArchivoUsuarios(_Estricto):
    tope_mensual_usd: float | None = Field(None, ge=0)  # None = sin tope
    usuarios: list[Usuario] = []


# ---------------------------------------------------------------- carga
def _leer_yaml(ruta: Path) -> dict:
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ErrorConfiguracion(f"{ruta}: YAML inválido: {e}") from None
    if not isinstance(datos, dict):
        raise ErrorConfiguracion(f"{ruta}: se esperaba un mapa en la raíz")
    return datos


def _error_validacion(ruta: Path, e: ValidationError) -> ErrorConfiguracion:
    detalles = "; ".join(f"{'.'.join(str(x) for x in err['loc']) or '(raíz)'}: {err['msg']}"
                         for err in e.errors())
    return ErrorConfiguracion(f"{ruta}: {detalles}")


@dataclass(frozen=True)
class Configuracion:
    perfiles: dict[str, Perfil]
    usuarios: dict[str, Usuario]
    raiz: Path
    tope_mensual_usd: float | None = None

    def usuario(self, email: str | None) -> Usuario | None:
        return self.usuarios.get((email or "").strip().lower())

    def perfiles_de(self, usuario: Usuario) -> list[Perfil]:
        if usuario.admin:
            return list(self.perfiles.values())
        return [self.perfiles[p] for p in usuario.perfiles if p in self.perfiles]

    def puede_usar(self, usuario: Usuario, perfil_id: str) -> bool:
        return any(p.id == perfil_id for p in self.perfiles_de(usuario))

    def tope_de(self, usuario: Usuario) -> float | None:
        """Tope de costo mensual en USD: el del usuario, o el general. None = sin tope."""
        return usuario.tope_mensual_usd if usuario.tope_mensual_usd is not None else self.tope_mensual_usd


def cargar_configuracion(raiz: Path = RAIZ) -> Configuracion:
    """Carga y valida todo; ante cualquier error lanza ErrorConfiguracion con archivo y campo."""
    perfiles: dict[str, Perfil] = {}
    for ruta in sorted((raiz / "config/perfiles").glob("*.yaml")):
        try:
            perfil = Perfil.model_validate(_leer_yaml(ruta))
        except ValidationError as e:
            raise _error_validacion(ruta, e) from None
        if perfil.id in perfiles:
            raise ErrorConfiguracion(f"{ruta}: id de perfil repetido: {perfil.id}")
        archivos = [("prompt", perfil.prompt)] + [
            (f"base_datos.tablas[{t.nombre}].diccionario", t.diccionario)
            for t in perfil.base_datos.tablas if t.diccionario]
        for campo, archivo in archivos:
            if not (raiz / archivo).is_file():
                raise ErrorConfiguracion(f"{ruta}: {campo}: no existe el archivo {archivo}")
        perfiles[perfil.id] = perfil
    if not perfiles:
        raise ErrorConfiguracion(f"No hay perfiles en {raiz / 'config/perfiles'}")

    ruta_u = raiz / "config/usuarios.yaml"
    try:
        archivo_u = _ArchivoUsuarios.model_validate(_leer_yaml(ruta_u) if ruta_u.exists() else {})
    except ValidationError as e:
        raise _error_validacion(ruta_u, e) from None
    usuarios: dict[str, Usuario] = {}
    for u in archivo_u.usuarios:
        desconocidos = [p for p in u.perfiles if p not in perfiles]
        if desconocidos:
            raise ErrorConfiguracion(f"{ruta_u}: {u.email}: perfiles inexistentes {desconocidos}")
        if u.email in usuarios:
            raise ErrorConfiguracion(f"{ruta_u}: email repetido: {u.email}")
        usuarios[u.email] = u
    return Configuracion(perfiles=perfiles, usuarios=usuarios, raiz=raiz, tope_mensual_usd=archivo_u.tope_mensual_usd)


# ---------------------------------------------------------------- contexto por perfil
_engines: dict[str, Engine] = {}
_esquemas: dict[tuple[str, str], list[str]] = {}
_lock = threading.Lock()


def engine_para(credencial_env: str) -> Engine:
    """Un engine por variable de credencial, con pool chico (serverless + pooler de Neon)."""
    with _lock:
        if credencial_env not in _engines:
            url = os.environ.get(credencial_env)
            if not url:
                raise ErrorConfiguracion(f"Falta la variable de entorno {credencial_env}")
            _engines[credencial_env] = create_engine(normalizar_url(url), pool_pre_ping=True,
                                                     pool_size=1, max_overflow=1, pool_recycle=300)
        return _engines[credencial_env]


def _columnas_reales(engine: Engine, credencial_env: str, tabla: str) -> list[str]:
    clave = (credencial_env, tabla)
    if clave not in _esquemas:
        esquema, nombre = tabla.split(".")
        with engine.connect() as conn:
            filas = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = :e AND table_name = :t ORDER BY ordinal_position"),
                {"e": esquema, "t": nombre}).all()
        if not filas:
            raise ErrorConfiguracion(f"La tabla {tabla} no existe o el rol de {credencial_env} no la ve")
        _esquemas[clave] = [f[0] for f in filas]
    return _esquemas[clave]


def contexto_para(perfil: Perfil, engine: Engine | None = None) -> ContextoPerfil:
    cred = perfil.base_datos.credencial_env
    engine = engine or engine_para(cred)
    # sql_guard resuelve columnas con el esquema de todas las tablas de la consulta, así que si hay
    # alguna tabla acotada se cargan las columnas reales de todas las del perfil.
    hay_acotadas = any(t.columnas is not None for t in perfil.base_datos.tablas)
    esquema = ({t.nombre: _columnas_reales(engine, cred, t.nombre) for t in perfil.base_datos.tablas}
               if hay_acotadas else None)
    return ContextoPerfil(
        engine=engine,
        tabla=perfil.tabla_principal,
        tablas_permitidas=perfil.tablas_permitidas(),
        esquema_columnas=esquema,
        max_filas=perfil.limites.max_filas,
        timeout_sql_seg=perfil.limites.timeout_sql_seg,
        excluir_clientes_ids=tuple(perfil.reglas.excluir_clientes_en_analisis),
    )
