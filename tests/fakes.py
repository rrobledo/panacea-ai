"""Cliente de Anthropic simulado: respuestas con guion y registro de cada llamada."""

import copy
import json
from types import SimpleNamespace

from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaThinkingBlock, BetaToolUseBlock, BetaUsage


def texto(t):
    return BetaTextBlock.model_construct(type="text", text=t, citations=None)


def pensamiento(firma="firma-1"):
    return BetaThinkingBlock.model_construct(type="thinking", thinking="", signature=firma)


def tool_use(tid, nombre, entrada):
    return BetaToolUseBlock.model_construct(type="tool_use", id=tid, name=nombre, input=entrada)


def mensaje(*bloques, stop="end_turn", entrada=1000, salida=100, cache_lectura=0, modelo="claude-opus-5-5"):
    usage = BetaUsage.model_construct(input_tokens=entrada, output_tokens=salida,
                                      cache_read_input_tokens=cache_lectura, cache_creation_input_tokens=0)
    return BetaMessage.model_construct(id="msg_x", type="message", role="assistant", model=modelo,
                                       content=list(bloques), stop_reason=stop, stop_sequence=None, usage=usage)


class Falla:
    """Paso del guion que lanza una excepción (opcionalmente después de emitir texto)."""

    def __init__(self, excepcion, texto_previo=""):
        self.excepcion, self.texto_previo = excepcion, texto_previo


class _Stream:
    def __init__(self, paso):
        self.paso = paso

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        if isinstance(self.paso, Falla):
            if self.paso.texto_previo:
                yield SimpleNamespace(type="text", text=self.paso.texto_previo)
            raise self.paso.excepcion
        for b in self.paso.content:
            if b.type == "text":
                yield SimpleNamespace(type="text", text=b.text)
            elif b.type == "tool_use":
                yield SimpleNamespace(type="input_json", partial_json=json.dumps(b.input))

    def get_final_message(self):
        return self.paso


class ClienteFalso:
    def __init__(self, *guion):
        self.guion = list(guion)
        self.llamadas: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **params):
        self.llamadas.append(copy.deepcopy(params))
        if not self.guion:
            raise AssertionError("El modelo fue llamado más veces que las previstas")
        paso = self.guion.pop(0)
        if callable(paso):  # respuesta que depende del pedido (ej. usar un id que devolvió una herramienta)
            paso = paso(params)
        return _Stream(paso)
