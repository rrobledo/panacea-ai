import "server-only";

import { cookies } from "next/headers";

import { COOKIE_SESION, leerSesion, type Sesion } from "@/lib/sesion";

// Backend que hace el login con Google (el mismo de panacea-compras).
export const BACKEND_LOGIN = (process.env.AUTH_BACKEND_URL || "https://panacea-produccion-backend.vercel.app")
  .replace(/\/+$/, "");

export function secretoSesion(): string {
  const s = process.env.AUTH_SECRET;
  if (!s) throw new Error("Falta AUTH_SECRET (el SECRET_KEY de panacea-produccion-backend)");
  return s;
}

/** Sesión de la cookie, o null si no hay o no es válida. */
export async function sesionActual(): Promise<Sesion | null> {
  const token = (await cookies()).get(COOKIE_SESION)?.value;
  return leerSesion(token, secretoSesion());
}
