// Lector de Server-Sent Events para las respuestas de /api/chat y /api/clarify.
// EventSource no sirve: solo hace GET y no manda cuerpo.

export type EventoSSE = { tipo: string; [clave: string]: unknown };

/** Separa los bloques completos del buffer y devuelve [eventos, resto sin terminar]. */
export function separarBloques(buffer: string): [EventoSSE[], string] {
  const eventos: EventoSSE[] = [];
  const normal = buffer.replace(/\r\n/g, "\n");
  const partes = normal.split("\n\n");
  const resto = partes.pop() ?? "";
  for (const bloque of partes) {
    const datos = bloque
      .split("\n")
      .filter((l) => l.startsWith("data:"))
      .map((l) => l.slice(5).replace(/^ /, ""))
      .join("\n");
    if (datos) eventos.push(JSON.parse(datos) as EventoSSE);
  }
  return [eventos, resto];
}

export async function* leerEventos(respuesta: Response): AsyncGenerator<EventoSSE> {
  if (!respuesta.body) return;
  const lector = respuesta.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await lector.read();
    if (done) break;
    buffer += value;
    const [eventos, resto] = separarBloques(buffer);
    buffer = resto;
    yield* eventos;
  }
  const [finales] = separarBloques(buffer + "\n\n");
  yield* finales;
}
