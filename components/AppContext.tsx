"use client";

import { createContext, useContext } from "react";

import type { Conversacion, DatosUsuario, Perfil } from "@/lib/api";

export type ContextoApp = {
  datos: DatosUsuario;
  perfil: Perfil;
  elegirPerfil: (id: string) => void;
  conversaciones: Conversacion[] | null;
  refrescarConversaciones: () => void;
};

export const Contexto = createContext<ContextoApp | null>(null);

export function useApp(): ContextoApp {
  const c = useContext(Contexto);
  if (!c) throw new Error("useApp fuera de <Shell>");
  return c;
}
