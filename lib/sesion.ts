import { SignJWT, jwtVerify } from "jose";

// El login lo hace panacea-produccion-backend, igual que en panacea-compras: devuelve un JWT HS256
// firmado con su SECRET_KEY (claims sub, email, role, exp). Next lo guarda tal cual en esta cookie
// httpOnly y el backend FastAPI (agent/auth.py) lo valida con el mismo secreto (AUTH_SECRET).
export const COOKIE_SESION = "panacea.sesion";
// Cookie de corta vida que marca un login iniciado en este navegador; guarda a dónde volver.
export const COOKIE_LOGIN = "panacea.login";

export type Sesion = { email: string; sub?: string; role?: string; exp: number; [k: string]: unknown };

function claves(secret: string | string[]): Uint8Array[] {
  return (Array.isArray(secret) ? secret : [secret]).filter(Boolean).map((s) => new TextEncoder().encode(s));
}

export async function leerSesion(token: string | undefined | null, secret: string | string[]): Promise<Sesion | null> {
  if (!token) return null;
  for (const clave of claves(secret)) {
    try {
      const { payload } = await jwtVerify(token, clave, {
        algorithms: ["HS256"], requiredClaims: ["exp", "email"], clockTolerance: 30,
      });
      if (typeof payload.email !== "string" || !payload.email.includes("@")) return null;
      return payload as Sesion;
    } catch {
      // probar con la siguiente clave (rotación del secreto)
    }
  }
  return null;
}

/** Emite un token como el de panacea-produccion-backend. Solo para pruebas y el backend de demostración. */
export async function firmarSesion(claims: { email?: string; sub?: string; role?: string }, secret: string,
                                   duracionSeg = 7 * 24 * 3600) {
  if (!claims.email) throw new Error("La sesión no tiene email");
  const ahora = Math.floor(Date.now() / 1000);
  return new SignJWT({ ...claims }).setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setExpirationTime(ahora + duracionSeg).sign(claves(secret)[0]);
}

/** Solo rutas internas: evita redirecciones abiertas a otros sitios. */
export function destinoSeguro(destino: unknown): string {
  return typeof destino === "string" && destino.startsWith("/") && !destino.startsWith("//") && !destino.includes("\\")
    ? destino : "/";
}
