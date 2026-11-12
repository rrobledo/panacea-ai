import assert from "node:assert/strict";
import { test } from "node:test";

import type { Item } from "./api.ts";
import { aclaracionPendiente, aplicarEvento, responderAclaracion } from "./chat.ts";
import type { EventoSSE } from "./sse.ts";

const aplicar = (eventos: EventoSSE[], inicio: Item[] = []) => eventos.reduce(aplicarEvento, inicio);

test("textos, pasos y reinicio", () => {
  const items = aplicar([
    { tipo: "texto", texto: "Miro " },
    { tipo: "herramienta_inicio", id: "t1", nombre: "resumen_ventas", argumentos: "{}" },
    { tipo: "herramienta_fin", id: "t1", nombre: "resumen_ventas", duracion_ms: 120, es_error: false, filas: 3 },
    { tipo: "texto", texto: "Octubre " },
    { tipo: "reinicio" },
    { tipo: "texto", texto: "Octubre: $100." },
    { tipo: "fin" },
  ]);
  assert.deepEqual(items.map((i) => i.tipo), ["agente", "paso", "agente"]);
  assert.deepEqual(items[1], { tipo: "paso", id: "t1", nombre: "resumen_ventas", argumentos: "{}", duracion_ms: 120,
                               es_error: false, filas: 3, en_curso: false });
  assert.equal((items[2] as { texto: string }).texto, "Octubre: $100.");
});

test("un corte deja los pasos terminados", () => {
  const items = aplicar([{ tipo: "herramienta_inicio", id: "t1", nombre: "consultar", argumentos: "" }, { tipo: "fin" }]);
  assert.equal(items[0].tipo === "paso" && items[0].en_curso, false);
});

test("aclaraciones: se muestran como tarjeta y se responden", () => {
  const brief = { titulo: "T", objetivo: "O", periodo: "P", secciones: [], metricas: [], audiencia: "A" };
  let items = aplicar([
    { tipo: "herramienta_inicio", id: "c1", nombre: "solicitar_aclaraciones", argumentos: "" },
    { tipo: "aclaraciones", tool_use_id: "c1", brief, preguntas: [] },
    { tipo: "fin" },
  ]);
  assert.deepEqual(items.map((i) => i.tipo), ["aclaraciones"]);
  assert.equal(aclaracionPendiente(items)?.id, "c1");
  items = responderAclaracion(items, "c1", { decision: "aprobado", respuestas: [] });
  assert.equal(aclaracionPendiente(items), null);
  items = aplicar([{ tipo: "artifact", id: "a1", version: 1, titulo: "Ventas", url: "/artifacts/a1" }], items);
  assert.deepEqual(items[1], { tipo: "artifact", id: "a1", version: 1, titulo: "Ventas", url: "/artifacts/a1" });
});
