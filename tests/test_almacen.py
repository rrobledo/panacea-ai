from datetime import timedelta

import pytest
from sqlalchemy import create_engine, text

from agent import almacen as mod
from agent.almacen import AlmacenMemoria, AlmacenPostgres, ConversacionOcupada, Paso
from tests.conftest import RAIZ


def test_orden_y_listado(almacen):
    a = almacen.crear_conversacion("ana@example.com", "ventas", "primera")
    b = almacen.crear_conversacion("ana@example.com", "ventas", "segunda")
    almacen.crear_conversacion("otro@example.com", "ventas", "ajena")
    almacen.agregar_mensaje(a.id, "user", [{"type": "text", "text": "hola"}])
    assert almacen.agregar_mensaje(a.id, "assistant", [{"type": "text", "text": "ñandú"}]) == 1
    assert almacen.mensajes(a.id)[1] == {"role": "assistant", "content": [{"type": "text", "text": "ñandú"}]}
    assert [c.id for c in almacen.conversaciones_de("ana@example.com")] == [a.id, b.id]
    assert len(almacen.conversaciones_de(None)) == 3


def test_paso_no_se_sobrescribe(almacen):
    cid = almacen.crear_conversacion("ana@example.com", "ventas", "x").id
    almacen.guardar_paso(cid, Paso("t", "consultar", {"sql": "SELECT 1"}, "uno", False, 5))
    almacen.guardar_paso(cid, Paso("t", "consultar", {"sql": "SELECT 1"}, "dos", True, 9))
    assert almacen.pasos(cid)["t"].resultado == "uno"


def test_id_inexistente(almacen):
    assert almacen.conversacion("00000000-0000-0000-0000-000000000000") is None
    assert almacen.conversacion("no-es-uuid") is None


def test_lease_vencido_memoria(monkeypatch):
    a = AlmacenMemoria()
    cid = a.crear_conversacion("ana@example.com", "ventas", "x").id
    a.tomar_turno(cid)
    monkeypatch.setattr(mod, "LEASE", timedelta(seconds=-1))
    a.tomar_turno(cid)  # el turno anterior se considera cortado


def test_lease_vencido_postgres(url_postgres):
    engine = create_engine(url_postgres)
    a = AlmacenPostgres(engine)
    cid = a.crear_conversacion("ana@example.com", "ventas", "x").id
    a.tomar_turno(cid)
    with pytest.raises(ConversacionOcupada):
        a.tomar_turno(cid)
    with engine.begin() as c:
        c.execute(text("UPDATE app.conversaciones SET latido = now() - interval '10 minutes' WHERE id = :id"),
                  {"id": cid})
    a.tomar_turno(cid)


def test_migracion_idempotente(url_postgres):
    engine = create_engine(url_postgres)
    with engine.begin() as c:
        c.exec_driver_sql((RAIZ / "sql/app/001_esquema.sql").read_text())
        assert c.execute(text("SELECT count(*) FROM app.migraciones")).scalar() == 1
