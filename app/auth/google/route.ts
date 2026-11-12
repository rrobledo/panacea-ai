import { NextResponse, type NextRequest } from "next/server";

import { COOKIE_LOGIN, destinoSeguro } from "@/lib/sesion";
import { BACKEND_LOGIN } from "@/lib/sesionServidor";

// Arranca el login con Google en panacea-produccion-backend, igual que panacea-compras. El backend
// vuelve a /auth/callback?token=... (esa URL tiene que estar en su FRONTEND_URLS).
export function GET(req: NextRequest) {
  const origen = (process.env.APP_URL || req.nextUrl.origin).replace(/\/+$/, "");
  const url = new URL("/auth/google", BACKEND_LOGIN);
  url.searchParams.set("redirect_uri", `${origen}/auth/callback`);

  const res = NextResponse.redirect(url);
  // Marca que el login se inició en este navegador: el callback no acepta tokens que no pidió.
  res.cookies.set(COOKIE_LOGIN, destinoSeguro(req.nextUrl.searchParams.get("destino")), {
    httpOnly: true, sameSite: "lax", secure: origen.startsWith("https://"), path: "/auth", maxAge: 10 * 60,
  });
  return res;
}
