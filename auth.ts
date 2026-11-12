import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

import { DURACION_SEG, firmarSesion, leerSesion } from "@/lib/sesion";
import { normalizarEmail, usuarioPermitido } from "@/lib/usuarios";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google], // AUTH_GOOGLE_ID y AUTH_GOOGLE_SECRET
  session: { strategy: "jwt", maxAge: DURACION_SEG },
  jwt: {
    encode: ({ token, secret, maxAge }) => firmarSesion(token ?? {}, secret, maxAge),
    decode: ({ token, secret }) => leerSesion(token, secret),
  },
  pages: { signIn: "/login", error: "/login" },
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider !== "google" || !profile?.email || profile.email_verified !== true) return false;
      return usuarioPermitido(profile.email); // false → /login?error=AccessDenied
    },
    jwt({ token }) {
      if (token.email) token.email = normalizarEmail(token.email);
      return token;
    },
  },
});
