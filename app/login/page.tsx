import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { ShieldX } from "lucide-react";

import { destinoSeguro } from "@/lib/sesion";
import { sesionActual } from "@/lib/sesionServidor";

export const metadata: Metadata = { title: "Entrar" };

function LogoGoogle() {
  return (
    <svg viewBox="0 0 48 48" className="size-5" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

const ERRORES: Record<string, string> = {
  Google: "Google no completó el inicio de sesión. Probá de nuevo.",
  Vencido: "El inicio de sesión tardó demasiado o empezó en otra pestaña. Probá de nuevo.",
  Token: "No se pudo validar la sesión. Probá de nuevo; si sigue fallando, avisale a un administrador.",
};

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string; destino?: string }> }) {
  const { error, destino } = await searchParams;
  if (!error && (await sesionActual())) redirect("/");
  const denegado = error === "AccessDenied";

  return (
    <main className="min-h-full grid place-items-center px-4 py-10">
      <div className="w-full max-w-sm grid gap-6">
        <div className="grid gap-2 text-center">
          <span className="font-mono text-xs tracking-[0.08em] uppercase text-accent">Panacea</span>
          <h1 className="text-2xl font-bold">Agente de análisis</h1>
          <p className="text-fg-2">Ventas, clientes, reportes y proyecciones.</p>
        </div>

        {denegado ? (
          <div role="alert" className="rounded-xl border border-line bg-surface p-5 grid gap-3">
            <div className="flex items-center gap-2 font-semibold text-bad">
              <ShieldX className="size-5" aria-hidden="true" /> Acceso denegado
            </div>
            <p className="text-sm text-fg-2">
              Tu cuenta de Google no tiene acceso a la aplicación. Pedile a un administrador que agregue tu email,
              o entrá con otra cuenta.
            </p>
          </div>
        ) : error ? (
          <p role="alert" className="rounded-lg bg-bad-soft text-bad text-sm px-4 py-3">
            {ERRORES[error] ?? "No se pudo iniciar sesión. Probá de nuevo."}
          </p>
        ) : null}

        {/* Ruta de servidor: redirige al login de panacea-produccion-backend (navegación completa). */}
        <form action="/auth/google" method="get">
          <input type="hidden" name="destino" value={destinoSeguro(destino)} />
          <button
            type="submit"
            className="w-full flex items-center justify-center gap-3 rounded-lg border border-line bg-surface px-4 py-3 font-medium hover:border-accent transition-colors"
          >
            <LogoGoogle /> {denegado ? "Entrar con otra cuenta" : "Entrar con Google"}
          </button>
        </form>
      </div>
    </main>
  );
}
