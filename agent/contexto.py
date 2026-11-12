"""Contexto de ejecución de las herramientas: qué tabla, con qué conexión y con qué límites."""

import logging
import re
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.engine import Engine

log = logging.getLogger("panacea.contexto")
_TABLA_RE = re.compile(r"[a-zA-Z_]\w*\.[a-zA-Z_]\w*")


def normalizar_url(url: str) -> str:
    """Neon/Vercel/Heroku entregan "postgres://", que SQLAlchemy 2 no reconoce."""
    return re.sub(r"^postgres(ql)?://", "postgresql+psycopg2://", url)


def validar_nombre_tabla(tabla: str) -> str:
    if not _TABLA_RE.fullmatch(tabla):
        raise ValueError(f"La tabla debe tener el formato esquema.tabla: {tabla!r}")
    return tabla.lower()


@dataclass(frozen=True)
class ContextoPerfil:
    """
    engine               conexión con la credencial del perfil (rol de solo lectura).
    tabla                tabla principal de ventas, formato esquema.tabla.
    tablas_permitidas    {esquema.tabla: columnas permitidas | None (todas)} para `consultar`.
                         None = sin restricción de tablas (comportamiento del servidor MCP local).
    esquema_columnas     {esquema.tabla: [todas sus columnas reales]}. Obligatorio si alguna
                         tabla permitida tiene columnas acotadas.
    excluir_clientes_ids IDs de clientes genéricos (ventas de mostrador por sucursal) que se
                         excluyen siempre en los análisis de clientes.
    auditor              auditor(sql=, parametros=, duracion_ms=, filas=, error=) por cada consulta
                         ejecutada o rechazada. Lo fija el loop de la app por herramienta; None en MCP.
    """

    engine: Engine
    tabla: str
    tablas_permitidas: dict[str, frozenset[str] | None] | None = None
    esquema_columnas: dict[str, list[str]] | None = None
    max_filas: int = 500
    timeout_sql_seg: int = 60
    excluir_clientes_ids: tuple[int, ...] = ()
    auditor: Callable[..., None] | None = field(default=None, compare=False, repr=False)

    def auditar(self, **registro) -> None:
        """Registra una consulta; un fallo de auditoría nunca corta la herramienta."""
        if self.auditor is None:
            return
        try:
            self.auditor(**registro)
        except Exception:
            log.exception("no se pudo registrar la auditoría de SQL")

    def __post_init__(self):
        object.__setattr__(self, "tabla", validar_nombre_tabla(self.tabla))
        if self.tablas_permitidas is not None:
            normal = {validar_nombre_tabla(t): (frozenset(c.lower() for c in cols) if cols is not None else None)
                      for t, cols in self.tablas_permitidas.items()}
            object.__setattr__(self, "tablas_permitidas", normal)

    @property
    def esquema(self) -> str:
        return self.tabla.split(".")[0]

    @property
    def nombre_tabla(self) -> str:
        return self.tabla.split(".")[1]
