import assert from "node:assert/strict";
import { test } from "node:test";

import { unirDictado } from "./dictado.ts";

test("une lo dictado con lo escrito, con un espacio", () => {
  assert.equal(unirDictado("", "hola"), "hola");
  assert.equal(unirDictado("Ventas de", "octubre "), "Ventas de octubre");
  assert.equal(unirDictado("Ventas de ", "octubre"), "Ventas de octubre");
  assert.equal(unirDictado("Ventas", "  "), "Ventas");
});
