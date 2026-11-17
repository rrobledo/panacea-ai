"""cambiar_programacion: propuesta sin escribir, confirmación exigida por el código, UPDATE controlado."""

import json
from datetime import date

import pytest

from agent.almacen import AlmacenMemoria
from agent.contexto import ContextoPerfil
from agent.tools import programacion
from agent.tools.programacion import CambioPlan, EntradaProgramacion, cambiar_programacion
from agent.tools.reportes import ContextoTurno

HOY = date(2026, 11, 16)
PRODUCTOS = {45: ("Medialunas", True), 50: ("Facturas", True), 99: ("Producto viejo", False)}
# (id fila, producto, fecha, plan, prod)
PROGRAMACION = [(1001, 45, date(2026, 11, 17), 120, None), (1002, 50, date(2026, 11, 17), 80, None),
                (1003, 45, date(2026, 11, 18), 100, None), (1004, 99, date(2026, 11, 17), 10, None)]


class Base:
    def __init__(self):
        self.prog = {r[0]: list(r) for r in PROGRAMACION}

    def __call__(self, ctx, sql, params=None, max_filas=None):
        if "costos_productos" in sql:
            filas = [[i, n, h] for i, (n, h) in PRODUCTOS.items() if i in params["ids"]]
        else:
            filas = [list(r) for r in self.prog.values()
                     if r[1] in params["ids"] and params["d"] <= r[2] <= params["h"]]
        return {"columnas": [], "filas": filas, "total_filas": len(filas), "truncado": False}


class Escritura:
    """Engine falso: registra los UPDATE y los aplica sobre la Base si el plan actual coincide."""

    def __init__(self, base):
        self.base, self.updates, self.commits = base, [], 0

    def begin(self):
        motor = self

        class Tx:
            def __enter__(self):
                self.pendientes = []
                return self

            def execute(self, sql, params=None):
                s = str(sql)
                if s.startswith("UPDATE"):
                    fila = motor.base.prog.get(params["id"])
                    ok = fila is not None and fila[3] == params["actual"]
                    if ok:
                        self.pendientes.append((params["id"], params["plan"]))
                    return type("R", (), {"first": lambda _self: (params["id"],) if ok else None})()
                return type("R", (), {"first": lambda _self: None})()

            def __exit__(self, tipo, *a):
                if tipo is None:
                    for rid, plan in self.pendientes:
                        motor.base.prog[rid][3] = plan
                    motor.updates += self.pendientes
                    motor.commits += 1
                return False
        return Tx()


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setattr(programacion, "_hoy", lambda: HOY)
    base = Base()
    monkeypatch.setattr(programacion, "ejecutar", base)
    escritura = Escritura(base)
    auditoria = []
    almacen = AlmacenMemoria()
    conv = almacen.crear_conversacion("ana@example.com", "produccion", "x")
    ctx = ContextoPerfil(engine=None, tabla="public.costos_programacion",
                         auditor=lambda **r: auditoria.append(r))

    def tc(historia, con_escritura=True):
        return ContextoTurno(almacen, conv, "produccion", "Producción", "tu", historia, {}, frozenset(),
                             datos=ctx, escritura=(lambda: escritura) if con_escritura else None)
    return tc, base, escritura, auditoria


def entrada(cambios, codigo=None):
    return EntradaProgramacion(cambios=[CambioPlan(**c) for c in cambios], codigo_confirmacion=codigo)


CAMBIOS = [{"producto_id": 45, "fecha": "2026-11-17", "plan": 150}, {"producto_id": 50, "fecha": "2026-11-17", "plan": 60}]


def historia_con(propuesta: str, respuesta_usuario: str | None):
    h = [{"role": "user", "content": [{"type": "text", "text": "Subí las medialunas del martes"}]},
         {"role": "assistant", "content": [{"type": "tool_use", "id": "p1", "name": "cambiar_programacion", "input": {}}]},
         {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "p1", "content": propuesta}]},
         {"role": "assistant", "content": [{"type": "text", "text": "¿Confirmás?"}]}]
    if respuesta_usuario is not None:
        h.append({"role": "user", "content": [{"type": "text", "text": respuesta_usuario}]})
    h.append({"role": "assistant", "content": [{"type": "tool_use", "id": "p2", "name": "cambiar_programacion", "input": {}}]})
    return h


def test_propuesta_no_escribe(entorno):
    tc, base, escritura, auditoria = entorno
    r = json.loads(cambiar_programacion(tc([]), entrada(CAMBIOS)))
    assert r["estado"] == "propuesta" and len(r["codigo_confirmacion"]) == 8
    filas = [dict(zip(r["columnas"], f)) for f in r["cambios"]]
    assert [(f["producto"], f["plan_actual"], f["plan_nuevo"]) for f in filas] == [("Facturas", 80, 60), ("Medialunas", 120, 150)]
    assert escritura.updates == [] and auditoria == []


def test_aplica_con_confirmacion_del_usuario(entorno):
    tc, base, escritura, auditoria = entorno
    propuesta = cambiar_programacion(tc([]), entrada(CAMBIOS))
    codigo = json.loads(propuesta)["codigo_confirmacion"]
    r = json.loads(cambiar_programacion(tc(historia_con(propuesta, "Sí, dale")), entrada(CAMBIOS, codigo)))
    assert r["estado"] == "aplicado" and r["cambios_aplicados"] == 2
    assert base.prog[1001][3] == 150 and base.prog[1002][3] == 60 and escritura.commits == 1
    assert auditoria[-1]["error"] is None and auditoria[-1]["filas"] == 2
    assert auditoria[-1]["parametros"]["usuario"] == "ana@example.com"


def test_sin_respuesta_del_usuario_no_escribe(entorno):
    tc, base, escritura, _ = entorno
    propuesta = cambiar_programacion(tc([]), entrada(CAMBIOS))
    codigo = json.loads(propuesta)["codigo_confirmacion"]
    # El modelo intenta aplicar en el mismo turno, sin que el usuario haya respondido.
    r = json.loads(cambiar_programacion(tc(historia_con(propuesta, None)), entrada(CAMBIOS, codigo)))
    assert "Falta la confirmación" in r["error"] and escritura.updates == []
    # Un código inventado tampoco sirve.
    r = json.loads(cambiar_programacion(tc(historia_con(propuesta, "sí")), entrada(CAMBIOS, "ABCDEF12")))
    assert "no coinciden" in r["error"] and escritura.updates == []


def test_cambios_distintos_a_la_propuesta(entorno):
    tc, base, escritura, _ = entorno
    propuesta = cambiar_programacion(tc([]), entrada(CAMBIOS))
    codigo = json.loads(propuesta)["codigo_confirmacion"]
    otros = [dict(CAMBIOS[0], plan=999), CAMBIOS[1]]
    r = json.loads(cambiar_programacion(tc(historia_con(propuesta, "sí")), entrada(otros, codigo)))
    assert "no coinciden" in r["error"] and escritura.updates == []


def test_plan_modificado_por_otro_entre_propuesta_y_confirmacion(entorno):
    tc, base, escritura, auditoria = entorno
    propuesta = cambiar_programacion(tc([]), entrada(CAMBIOS))
    codigo = json.loads(propuesta)["codigo_confirmacion"]
    base.prog[1002][3] = 85  # alguien lo cambió desde la app de producción
    r = json.loads(cambiar_programacion(tc(historia_con(propuesta, "sí")), entrada(CAMBIOS, codigo)))
    assert "no coinciden" in r["error"] and escritura.updates == [] and base.prog[1001][3] == 120


def test_validaciones(entorno):
    tc, *_ = entorno
    def error(cambios):
        return json.loads(cambiar_programacion(tc([]), entrada(cambios)))["error"]
    assert "desde hoy" in error([{"producto_id": 45, "fecha": "2026-11-15", "plan": 1}])
    assert "inexistentes" in error([{"producto_id": 7, "fecha": "2026-11-17", "plan": 1}])
    assert "deshabilitados" in error([{"producto_id": 99, "fecha": "2026-11-17", "plan": 1}])
    assert "No hay fila" in error([{"producto_id": 50, "fecha": "2026-11-20", "plan": 1}])
    assert "repetidos" in error([CAMBIOS[0], CAMBIOS[0]])
    r = json.loads(cambiar_programacion(tc([]), entrada([{"producto_id": 45, "fecha": "2026-11-17", "plan": 120}])))
    assert r["estado"] == "sin_cambios"


def test_perfil_sin_escritura(entorno):
    tc, *_ = entorno
    r = json.loads(cambiar_programacion(tc([], con_escritura=False), entrada(CAMBIOS)))
    assert "no tiene permiso" in r["error"]


def test_entrada_valida():
    with pytest.raises(Exception):
        EntradaProgramacion(cambios=[CambioPlan(producto_id=45, fecha="2026-11-17", plan=-1)])
    with pytest.raises(Exception):
        EntradaProgramacion(cambios=CAMBIOS, codigo_confirmacion="x' OR 1=1")
