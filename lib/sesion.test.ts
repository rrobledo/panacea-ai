import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { test } from "node:test";

import { firmarSesion, leerSesion } from "./sesion.ts";

const SECRETO = "s".repeat(40);

test("firma y lee la sesión; rechaza otra clave o un token vencido", async () => {
  const token = await firmarSesion({ email: "ana@example.com", name: "Ana" }, SECRETO);
  assert.equal((await leerSesion(token, SECRETO))?.email, "ana@example.com");
  assert.equal((await leerSesion(token, ["n".repeat(40), SECRETO]))?.email, "ana@example.com"); // rotación
  assert.equal(await leerSesion(token, "x".repeat(40)), null);
  assert.equal(await leerSesion(await firmarSesion({ email: "a@b.c" }, SECRETO, -60), SECRETO), null);
  await assert.rejects(firmarSesion({ name: "sin email" }, SECRETO));
});

const PYTHON = ".venv/bin/python";
test("el backend Python acepta la cookie que firma Next", { skip: !existsSync(PYTHON) && "sin .venv" }, async () => {
  const token = await firmarSesion({ email: "ana@example.com" }, SECRETO);
  const email = execFileSync(PYTHON, ["-c", "import sys; from agent.auth import email_de_token; print(email_de_token(sys.argv[1]))", token],
                             { env: { ...process.env, AUTH_SECRET: SECRETO }, encoding: "utf-8" }).trim();
  assert.equal(email, "ana@example.com");
});
