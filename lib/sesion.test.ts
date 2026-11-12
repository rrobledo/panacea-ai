import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { test } from "node:test";

import { destinoSeguro, firmarSesion, leerSesion } from "./sesion.ts";

const SECRETO = "s".repeat(40);

test("lee el token del backend de login; rechaza otra clave, vencido o sin email", async () => {
  const token = await firmarSesion({ sub: "7", email: "ana@example.com", role: "user" }, SECRETO);
  assert.equal((await leerSesion(token, SECRETO))?.email, "ana@example.com");
  assert.equal((await leerSesion(token, ["n".repeat(40), SECRETO]))?.email, "ana@example.com"); // rotación
  assert.equal(await leerSesion(token, "x".repeat(40)), null);
  assert.equal(await leerSesion(await firmarSesion({ email: "a@b.c" }, SECRETO, -120), SECRETO), null);
  assert.equal(await leerSesion("basura", SECRETO), null);
  await assert.rejects(firmarSesion({ sub: "1" }, SECRETO));
});

test("destino seguro: solo rutas internas", () => {
  assert.equal(destinoSeguro("/chat/abc"), "/chat/abc");
  assert.equal(destinoSeguro("//evil.com"), "/");
  assert.equal(destinoSeguro("https://evil.com"), "/");
  assert.equal(destinoSeguro("/\\evil.com"), "/");
  assert.equal(destinoSeguro(null), "/");
});

const PYTHON = ".venv/bin/python";
test("el backend Python acepta el token", { skip: !existsSync(PYTHON) && "sin .venv" }, async () => {
  const token = await firmarSesion({ sub: "7", email: "Ana@Example.com", role: "user" }, SECRETO);
  const email = execFileSync(PYTHON, ["-c", "import sys; from agent.auth import email_de_token; print(email_de_token(sys.argv[1]))", token],
                             { env: { ...process.env, AUTH_SECRET: SECRETO }, encoding: "utf-8" }).trim();
  assert.equal(email, "ana@example.com");
});
