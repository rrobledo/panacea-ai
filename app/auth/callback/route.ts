import { NextResponse, type NextRequest } from "next/server";

import { COOKIE_LOGIN, COOKIE_SESION, destinoSeguro, leerSesion } from "@/lib/sesion";
import { secretoSesion } from "@/lib/sesionServidor";
import { usuarioPermitido } from "@/lib/usuarios";

// Vuelta del login de panacea-produccion-backend: ?token=JWT o ?error=...
// Valida el token, controla el email contra config/usuarios.yaml y lo guarda en una cookie httpOnly
// (así no queda en localStorage ni en la URL, y los reportes que se abren en otra pestaña la reciben).
export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams;
  const iniciado = req.cookies.get(COOKIE_LOGIN)?.value;
  const ir = (ruta: string) => {
    const res = NextResponse.redirect(new URL(ruta, req.nextUrl.origin));
    res.cookies.delete({ name: COOKIE_LOGIN, path: "/auth" });
    return res;
  };

  if (params.get("error")) return ir("/login?error=Google");
  if (!iniciado) return ir("/login?error=Vencido"); // no se inició acá, o pasaron más de 10 minutos

  const token = params.get("token");
  const sesion = await leerSesion(token, secretoSesion());
  if (!token || !sesion) return ir("/login?error=Token");
  if (!(await usuarioPermitido(sesion.email))) return ir("/login?error=AccessDenied");

  const res = ir(destinoSeguro(iniciado));
  res.cookies.set(COOKIE_SESION, token, {
    httpOnly: true, sameSite: "lax", secure: req.nextUrl.protocol === "https:", path: "/",
    maxAge: Math.max(0, sesion.exp - Math.floor(Date.now() / 1000)),
  });
  return res;
}
