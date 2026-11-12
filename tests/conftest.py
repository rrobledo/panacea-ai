import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from agent.almacen import AlmacenMemoria, AlmacenPostgres
from agent.contexto import ContextoPerfil
from agent.profiles import Perfil
from agent.tools import registro

RAIZ = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- herramientas simuladas
class Herramientas:
    """Reemplaza resumen_ventas y consultar por funciones que no tocan la base."""

    def __init__(self):
        self.llamadas: list[tuple[str, dict]] = []
        self.falla_consultar: Exception | None = None

    def resumen_ventas(self, ctx, desde: str | None = None, hasta: str | None = None) -> str:
        self.llamadas.append(("resumen_ventas", {"desde": desde, "hasta": hasta}))
        return json.dumps({"periodo": [desde, hasta], "resultado": {"columnas": ["ventas"], "filas": [[100.0]],
                                                                    "total_filas": 1, "truncado": False}})

    def consultar(self, ctx, sql: str) -> str:
        self.llamadas.append(("consultar", {"sql": sql}))
        if self.falla_consultar:
            raise self.falla_consultar
        if "costos" in sql:
            return json.dumps({"error": "Tablas no permitidas para este perfil: public.costos_costos."})
        return json.dumps({"columnas": ["n"], "filas": [[1]], "total_filas": 1, "truncado": False})


@pytest.fixture
def herramientas(monkeypatch):
    h = Herramientas()

    def resumen_ventas(ctx, desde: str | None = None, hasta: str | None = None) -> str:
        """resumen_ventas simulada."""
        return h.resumen_ventas(ctx, desde, hasta)

    def consultar(ctx, sql: str) -> str:
        """consultar simulada."""
        return h.consultar(ctx, sql)

    monkeypatch.setitem(registro.HERRAMIENTAS, "resumen_ventas", resumen_ventas)
    monkeypatch.setitem(registro.HERRAMIENTAS, "consultar", consultar)
    return h


def perfil_prueba(**cambios) -> Perfil:
    datos = {
        "id": "ventas", "nombre": "Analista comercial", "prompt": "prompts/ventas.md",
        "base_datos": {"credencial_env": "DB_URL_VENTAS", "tablas": [{"nombre": "public.panacea_sales_v2"}]},
        "herramientas": ["resumen_ventas", "consultar"],
        "limites": {"max_herramientas_por_turno": 5},
    }
    for k, v in cambios.items():
        datos[k] = v
    return Perfil.model_validate(datos)


@pytest.fixture
def ctx():
    return ContextoPerfil(engine=None, tabla="public.panacea_sales_v2")


# ---------------------------------------------------------------- almacenes
def _postgres_docker():
    """Levanta un Postgres temporal en Docker para probar AlmacenPostgres. None si no se puede."""
    if os.environ.get("TEST_APP_DB_URL"):
        return os.environ["TEST_APP_DB_URL"], None
    nombre = f"panacea-test-{uuid.uuid4().hex[:8]}"
    try:
        subprocess.run(["docker", "run", "-d", "--rm", "--name", nombre, "-e", "POSTGRES_PASSWORD=prueba",
                        "-p", "127.0.0.1::5432", "postgres:16-alpine"],
                       check=True, capture_output=True, timeout=180)
        puerto = subprocess.run(["docker", "port", nombre, "5432/tcp"], check=True, capture_output=True,
                                text=True, timeout=30).stdout.strip().split(":")[-1]
    except (OSError, subprocess.SubprocessError):
        return None, None
    url = f"postgresql+psycopg2://postgres:prueba@127.0.0.1:{puerto}/postgres"
    from sqlalchemy import create_engine, text
    engine = create_engine(url)
    for _ in range(60):
        try:
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
            break
        except Exception:
            time.sleep(1)
    else:
        subprocess.run(["docker", "stop", nombre], capture_output=True)
        return None, None
    return url, nombre


@pytest.fixture(scope="session")
def url_postgres():
    if os.environ.get("SIN_DOCKER"):
        pytest.skip("SIN_DOCKER")
    url, contenedor = _postgres_docker()
    if url is None:
        pytest.skip("No hay Postgres de prueba (Docker no disponible y sin TEST_APP_DB_URL)")
    from sqlalchemy import create_engine
    engine = create_engine(url)
    with engine.begin() as c:
        c.exec_driver_sql((RAIZ / "sql/app/001_esquema.sql").read_text())
    yield url
    if contenedor:
        subprocess.run(["docker", "stop", contenedor], capture_output=True)


@pytest.fixture(params=["memoria", "postgres"])
def almacen(request):
    if request.param == "memoria":
        return AlmacenMemoria()
    from sqlalchemy import create_engine
    engine = create_engine(request.getfixturevalue("url_postgres"))
    with engine.begin() as c:  # cada prueba arranca con el esquema vacío
        c.exec_driver_sql("TRUNCATE app.conversaciones, app.briefs, app.artifacts, app.artifact_versions, "
                          "app.mensajes, app.pasos_herramienta, app.auditoria_sql, app.uso_tokens CASCADE")
    return AlmacenPostgres(engine)
