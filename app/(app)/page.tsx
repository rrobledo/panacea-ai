"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useApp } from "@/components/AppContext";

// "/" abre la última conversación del perfil elegido, o una nueva.
export default function Inicio() {
  const { conversaciones, perfil } = useApp();
  const router = useRouter();

  useEffect(() => {
    if (conversaciones === null) return;
    const ultima = conversaciones.find((c) => c.perfil === perfil.id);
    router.replace(ultima ? `/chat/${ultima.id}` : "/chat");
  }, [conversaciones, perfil.id, router]);

  return <div className="h-full grid place-items-center text-muted" aria-busy="true">Cargando…</div>;
}
