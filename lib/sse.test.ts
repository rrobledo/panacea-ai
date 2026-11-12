import assert from "node:assert/strict";
import { test } from "node:test";

import { leerEventos, separarBloques } from "./sse.ts";

test("separa bloques completos y deja el resto", () => {
  const [ev, resto] = separarBloques('event: texto\ndata: {"tipo":"texto","texto":"Ho"}\n\nevent: fin\ndata: {"tipo":"f');
  assert.deepEqual(ev, [{ tipo: "texto", texto: "Ho" }]);
  assert.equal(resto, 'event: fin\ndata: {"tipo":"f');
});

test("lee un stream cortado en pedazos arbitrarios", async () => {
  const sse = 'event: conversacion\ndata: {"tipo":"conversacion","id":"c1"}\n\n' +
    'event: texto\ndata: {"tipo":"texto","texto":"ñandú\\n"}\n\nevent: fin\ndata: {"tipo":"fin"}\n\n';
  const bytes = new TextEncoder().encode(sse);
  const cuerpo = new ReadableStream({
    start(c) {
      for (let i = 0; i < bytes.length; i += 7) c.enqueue(bytes.slice(i, i + 7)); // corta caracteres multibyte
      c.close();
    },
  });
  const eventos = [];
  for await (const e of leerEventos(new Response(cuerpo))) eventos.push(e);
  assert.deepEqual(eventos.map((e) => e.tipo), ["conversacion", "texto", "fin"]);
  assert.equal(eventos[1].texto, "ñandú\n");
});
