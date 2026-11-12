import type { Metadata, Viewport } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Agente Panacea", template: "%s · Agente Panacea" },
  description: "Análisis comercial y reportes de Panacea",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

// Aplica el tema elegido antes de pintar, para que no parpadee.
const TEMA = `try{var t=localStorage.getItem("panacea.tema");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: TEMA }} />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
