"use client";

import { LogOut, Menu, MessageSquarePlus, ShieldX, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { salir } from "@/app/acciones";
import { Contexto, type ContextoApp } from "@/components/AppContext";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ErrorApi, obtener, type Conversacion, type DatosUsuario } from "@/lib/api";

const CLAVE_PERFIL = "panacea.perfil";

function leerPerfilGuardado(): string | null {
  try {
    return localStorage.getItem(CLAVE_PERFIL);
  } catch {
    return null;
  }
}

function fechaCorta(iso: string): string {
  const d = new Date(iso);
  const hoy = new Date();
  return d.toDateString() === hoy.toDateString()
    ? d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" });
}

function BotonSalir({ compacto = false }: { compacto?: boolean }) {
  return (
    <form action={salir}>
      <button
        type="submit"
        title="Salir"
        className={
          compacto
            ? "grid place-items-center size-9 rounded-lg text-fg-2 hover:bg-surface-2 hover:text-fg"
            : "inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 hover:border-accent"
        }
      >
        <LogOut className="size-[18px]" aria-hidden="true" />
        {compacto ? <span className="sr-only">Salir</span> : "Salir"}
      </button>
    </form>
  );
}

function Pantalla({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <main className="min-h-full grid place-items-center px-4 py-10">
      <div className="w-full max-w-md rounded-xl border border-line bg-surface p-6 grid gap-4">
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <ShieldX className="size-5 text-bad" aria-hidden="true" /> {titulo}
        </h1>
        {children}
      </div>
    </main>
  );
}

export function Shell({ email, children }: { email: string; children: React.ReactNode }) {
  const router = useRouter();
  const ruta = usePathname();
  const [datos, setDatos] = useState<DatosUsuario | null>(null);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [perfilId, setPerfilId] = useState<string | null>(null);
  const [conversaciones, setConversaciones] = useState<Conversacion[] | null>(null);
  const [menuAbierto, setMenuAbierto] = useState(false);

  useEffect(() => {
    obtener<DatosUsuario>("/api/profiles")
      .then((d) => {
        setDatos(d);
        const guardado = leerPerfilGuardado();
        setPerfilId(d.perfiles.some((p) => p.id === guardado) ? guardado : (d.perfiles[0]?.id ?? null));
      })
      .catch((e) => setError(e instanceof ErrorApi ? e : new ErrorApi(0, "No se pudo conectar con el servidor")));
  }, []);

  const refrescarConversaciones = useCallback(() => {
    obtener<{ conversaciones: Conversacion[] }>("/api/conversaciones")
      .then((r) => setConversaciones(r.conversaciones))
      .catch(() => setConversaciones((c) => c ?? []));
  }, []);

  useEffect(() => {
    if (datos) refrescarConversaciones();
  }, [datos, refrescarConversaciones]);

  useEffect(() => setMenuAbierto(false), [ruta]);

  const elegirPerfil = useCallback((id: string) => {
    setPerfilId(id);
    try {
      localStorage.setItem(CLAVE_PERFIL, id);
    } catch {
      // sin almacenamiento
    }
  }, []);

  const contexto = useMemo<ContextoApp | null>(() => {
    const perfil = datos?.perfiles.find((p) => p.id === perfilId);
    return datos && perfil ? { datos, perfil, elegirPerfil, conversaciones, refrescarConversaciones } : null;
  }, [datos, perfilId, elegirPerfil, conversaciones, refrescarConversaciones]);

  if (error?.status === 403) {
    return (
      <Pantalla titulo="Sin acceso">
        <p className="text-fg-2">
          {email} no tiene acceso a la aplicación. Pedile a un administrador que te agregue.
        </p>
        <BotonSalir />
      </Pantalla>
    );
  }
  if (error) {
    return (
      <Pantalla titulo="No se pudo cargar la aplicación">
        <p className="text-fg-2">{error.message}</p>
        <button type="button" onClick={() => window.location.reload()} className="justify-self-start rounded-lg border border-line px-4 py-2 hover:border-accent">
          Reintentar
        </button>
      </Pantalla>
    );
  }
  if (datos && datos.perfiles.length === 0) {
    return (
      <Pantalla titulo="Sin perfiles asignados">
        <p className="text-fg-2">Tu usuario no tiene perfiles. Pedile a un administrador que te asigne uno.</p>
        <BotonSalir />
      </Pantalla>
    );
  }
  if (!contexto) {
    return <div className="h-full grid place-items-center text-muted" aria-busy="true">Cargando…</div>;
  }

  const multiplesPerfiles = contexto.datos.perfiles.length > 1;
  const nombrePerfil = (id: string) => contexto.datos.perfiles.find((p) => p.id === id)?.nombre ?? id;

  return (
    <Contexto.Provider value={contexto}>
      <div className="h-full grid grid-rows-[56px_1fr]">
        <header className="flex items-center gap-2 border-b border-line bg-surface px-3 sm:px-4">
          <button
            type="button"
            onClick={() => setMenuAbierto((v) => !v)}
            aria-label={menuAbierto ? "Cerrar conversaciones" : "Abrir conversaciones"}
            aria-expanded={menuAbierto}
            className="md:hidden grid place-items-center size-9 rounded-lg text-fg-2 hover:bg-surface-2"
          >
            {menuAbierto ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
          </button>
          <Link href="/" className="font-bold tracking-tight whitespace-nowrap">
            <span className="text-accent">Panacea</span> <span className="hidden sm:inline">· Agente</span>
          </Link>

          <div className="ml-2 min-w-0">
            {multiplesPerfiles ? (
              <label className="flex items-center gap-2 text-sm">
                <span className="sr-only">Perfil</span>
                <select
                  value={contexto.perfil.id}
                  onChange={(e) => elegirPerfil(e.target.value)}
                  className="max-w-[44vw] truncate rounded-lg border border-line bg-surface px-2 py-1.5 text-sm hover:border-accent"
                  title={contexto.perfil.descripcion}
                >
                  {contexto.datos.perfiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <span className="text-sm text-fg-2 truncate" title={contexto.perfil.descripcion}>
                {contexto.perfil.nombre}
              </span>
            )}
          </div>

          <div className="ml-auto flex items-center gap-1">
            <span className="hidden lg:inline text-sm text-muted mr-2 truncate max-w-56" title={email}>
              {email}
            </span>
            <ThemeToggle />
            <BotonSalir compacto />
          </div>
        </header>

        <div className="relative min-h-0 grid md:grid-cols-[272px_1fr]">
          <aside
            className={`${menuAbierto ? "flex" : "hidden"} md:flex absolute md:static inset-0 z-20 flex-col min-h-0 border-r border-line bg-surface`}
            aria-label="Conversaciones"
          >
            <div className="p-3">
              <button
                type="button"
                onClick={() => router.push(`/chat?nueva=${Date.now()}`)}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-accent text-accent-fg px-3 py-2 font-medium hover:opacity-90"
              >
                <MessageSquarePlus className="size-[18px]" aria-hidden="true" /> Nueva conversación
              </button>
            </div>
            <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
              {conversaciones === null ? (
                <p className="px-3 py-2 text-sm text-muted">Cargando…</p>
              ) : conversaciones.length === 0 ? (
                <p className="px-3 py-2 text-sm text-muted">Todavía no hay conversaciones.</p>
              ) : (
                <ul className="grid gap-0.5">
                  {conversaciones.map((c) => {
                    const activa = ruta === `/chat/${c.id}`;
                    return (
                      <li key={c.id}>
                        <Link
                          href={`/chat/${c.id}`}
                          aria-current={activa ? "page" : undefined}
                          className={`block rounded-lg px-3 py-2 ${activa ? "bg-accent-soft" : "hover:bg-surface-2"}`}
                        >
                          <span className="block truncate text-sm">{c.titulo || "Sin título"}</span>
                          <span className="flex gap-2 text-xs text-muted">
                            <span>{fechaCorta(c.actualizada)}</span>
                            {multiplesPerfiles && <span className="truncate">· {nombrePerfil(c.perfil)}</span>}
                            {c.estado === "esperando_aclaracion" && <span className="text-warn">· espera tu respuesta</span>}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </nav>
          </aside>
          <main className="min-h-0 min-w-0">{children}</main>
        </div>
      </div>
    </Contexto.Provider>
  );
}
