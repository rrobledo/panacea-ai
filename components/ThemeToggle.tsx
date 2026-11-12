"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type Tema = "system" | "light" | "dark";
const SIGUIENTE: Record<Tema, Tema> = { system: "light", light: "dark", dark: "system" };
const ETIQUETA: Record<Tema, string> = { system: "Tema del sistema", light: "Tema claro", dark: "Tema oscuro" };

export function ThemeToggle() {
  const [tema, setTema] = useState<Tema>("system");

  useEffect(() => {
    const t = document.documentElement.dataset.theme;
    setTema(t === "light" || t === "dark" ? t : "system");
  }, []);

  function cambiar() {
    const nuevo = SIGUIENTE[tema];
    setTema(nuevo);
    try {
      if (nuevo === "system") {
        delete document.documentElement.dataset.theme;
        localStorage.removeItem("panacea.tema");
      } else {
        document.documentElement.dataset.theme = nuevo;
        localStorage.setItem("panacea.tema", nuevo);
      }
    } catch {
      // sin almacenamiento: el tema dura hasta recargar
    }
  }

  const Icono = tema === "light" ? Sun : tema === "dark" ? Moon : Monitor;
  return (
    <button
      type="button"
      onClick={cambiar}
      title={`${ETIQUETA[tema]} (cambiar)`}
      aria-label={`${ETIQUETA[tema]}. Cambiar tema`}
      className="grid place-items-center size-9 rounded-lg text-fg-2 hover:bg-surface-2 hover:text-fg"
    >
      <Icono className="size-[18px]" aria-hidden="true" />
    </button>
  );
}
