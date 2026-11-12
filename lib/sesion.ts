import { SignJWT, jwtVerify } from "jose";

// Claims de la sesión que comparten Next (Auth.js) y el backend (agent/auth.py).
export type Sesion = { email?: string | null; name?: string | null; picture?: string | null; [k: string]: unknown };

// La sesión dura una jornada; después hay que volver a entrar con Google.
export const DURACION_SEG = 12 * 60 * 60;

function claves(secret: string | string[]): Uint8Array[] {
  return (Array.isArray(secret) ? secret : [secret]).map((s) => new TextEncoder().encode(s));
}

// Por defecto Auth.js cifra la sesión (JWE) y el backend Python no la puede leer. Acá se firma
// como JWT HS256 con AUTH_SECRET y los claims email y exp, que es lo que valida agent/auth.py.
// La cookie es la de siempre (authjs.session-token, o __Secure- en HTTPS), httpOnly.
export async function firmarSesion(token: Sesion, secret: string | string[], maxAge = DURACION_SEG) {
  if (!token.email) throw new Error("La sesión no tiene email");
  const ahora = Math.floor(Date.now() / 1000);
  return new SignJWT({ email: token.email, name: token.name ?? null, picture: token.picture ?? null })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setIssuedAt(ahora)
    .setExpirationTime(ahora + maxAge)
    .sign(claves(secret)[0]);
}

export async function leerSesion(token: string | undefined, secret: string | string[]): Promise<Sesion | null> {
  if (!token) return null;
  for (const clave of claves(secret)) {
    try {
      const { payload } = await jwtVerify(token, clave, { algorithms: ["HS256"], requiredClaims: ["exp", "email"] });
      return payload as Sesion;
    } catch {
      // probar con la siguiente clave (rotación de AUTH_SECRET)
    }
  }
  return null;
}
