// Cómo cada evento SSE del turno modifica la lista de elementos del chat. Función pura (sin React),
// para poder probarla aparte.

import type { Brief, Item, Pregunta, RespuestaAclaracion } from "./api.ts";
import type { EventoSSE } from "./sse.ts";

const OCULTAS = new Set(["solicitar_aclaraciones"]); // se muestra como tarjeta, no como paso

export function aplicarEvento(items: Item[], ev: EventoSSE): Item[] {
  const ultimo = items[items.length - 1];
  switch (ev.tipo) {
    case "texto":
      if (ultimo?.tipo === "agente") return [...items.slice(0, -1), { ...ultimo, texto: ultimo.texto + String(ev.texto) }];
      return [...items, { tipo: "agente", texto: String(ev.texto) }];
    case "reinicio":
      // El modelo reintenta la llamada: se descarta el texto parcial de este intento.
      return ultimo?.tipo === "agente" ? items.slice(0, -1) : items;
    case "herramienta_inicio":
      if (OCULTAS.has(String(ev.nombre))) return items;
      return [...items, {
        tipo: "paso", id: String(ev.id), nombre: String(ev.nombre), argumentos: String(ev.argumentos ?? ""),
        duracion_ms: null, es_error: null, en_curso: true,
      }];
    case "herramienta_fin":
      return items.map((it) =>
        it.tipo === "paso" && it.id === ev.id
          ? { ...it, en_curso: false, duracion_ms: Number(ev.duracion_ms), es_error: Boolean(ev.es_error),
              filas: typeof ev.filas === "number" ? ev.filas : null }
          : it);
    case "aclaraciones":
      return [...items, {
        tipo: "aclaraciones", id: String(ev.tool_use_id), brief: ev.brief as Brief,
        preguntas: (ev.preguntas as Pregunta[]) ?? [], respuesta: null,
      }];
    case "artifact":
      return [...items, { tipo: "artifact", id: String(ev.id), version: Number(ev.version), titulo: String(ev.titulo),
                          url: String(ev.url) }];
    case "aviso":
      return [...items, { tipo: "aviso", texto: String(ev.mensaje) }];
    case "error":
      return [...items, { tipo: "error", texto: String(ev.mensaje) }];
    case "fin":
      // Un corte deja pasos sin terminar: ya no están en curso.
      return items.map((it) => (it.tipo === "paso" && it.en_curso ? { ...it, en_curso: false } : it));
    default:
      return items;
  }
}

/** Marca una aclaración como respondida (al aprobar, ajustar o escribir un mensaje libre). */
export function responderAclaracion(items: Item[], toolUseId: string, respuesta: RespuestaAclaracion): Item[] {
  return items.map((it) => (it.tipo === "aclaraciones" && it.id === toolUseId ? { ...it, respuesta } : it));
}

export function aclaracionPendiente(items: Item[]): Extract<Item, { tipo: "aclaraciones" }> | null {
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i];
    if (it.tipo === "aclaraciones") return it.respuesta == null ? it : null;
  }
  return null;
}
