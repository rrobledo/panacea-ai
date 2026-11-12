import type { NextConfig } from "next";

// /api/* va al backend FastAPI:
// en desarrollo, a uvicorn en el puerto 8000; en Vercel, a la función Python api/index.py.
// FastAPI recibe la ruta original (/api/chat, /api/profiles, ...).
const BACKEND_DEV = process.env.BACKEND_DEV_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  // El login controla los emails contra config/usuarios.yaml: el archivo tiene que viajar con la función.
  outputFileTracingIncludes: { "/**": ["./config/usuarios.yaml"] },
  // La compresión de `next start` retiene los eventos SSE del chat.
  compress: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.NODE_ENV === "development" ? `${BACKEND_DEV}/api/:path*` : "/api/",
      },
    ];
  },
};

export default config;
