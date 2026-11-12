import assert from "node:assert/strict";
import { test } from "node:test";

import { emailsPermitidos } from "./usuarios.ts";

test("emails de usuarios.yaml, sin distinguir mayúsculas", () => {
  const e = emailsPermitidos("tope_mensual_usd: 50\nusuarios:\n  - { email: ' Ana@Example.com ', perfiles: [ventas] }\n  - { perfiles: [] }\n");
  assert.deepEqual([...e], ["ana@example.com"]);
  assert.deepEqual([...emailsPermitidos("usuarios: []")], []);
  assert.deepEqual([...emailsPermitidos("")], []);
});
