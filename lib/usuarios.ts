import { readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";

// Misma fuente que el backend: un email que no figura en config/usuarios.yaml no entra.
// El backend vuelve a controlarlo en cada pedido, así que quitar a alguien del archivo le corta
// el acceso aunque tenga una sesión abierta.
const RUTA = path.join(process.cwd(), "config", "usuarios.yaml");

export function normalizarEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function emailsPermitidos(contenido: string): Set<string> {
  const datos = parse(contenido) as { usuarios?: { email?: unknown }[] } | null;
  const emails = (datos?.usuarios ?? [])
    .map((u) => (typeof u?.email === "string" ? normalizarEmail(u.email) : ""))
    .filter(Boolean);
  return new Set(emails);
}

export async function usuarioPermitido(email: string): Promise<boolean> {
  const contenido = await readFile(RUTA, "utf-8");
  return emailsPermitidos(contenido).has(normalizarEmail(email));
}
