"use server";

import { signIn, signOut } from "@/auth";

export async function entrarConGoogle(formData: FormData) {
  const destino = formData.get("destino");
  // select_account: Google deja elegir la cuenta (útil después de un acceso denegado).
  await signIn("google", { redirectTo: typeof destino === "string" && destino.startsWith("/") ? destino : "/" },
               { prompt: "select_account" });
}

export async function salir() {
  await signOut({ redirectTo: "/login" });
}
