import { redirect } from "next/navigation";

import { Shell } from "@/components/Shell";
import { sesionActual } from "@/lib/sesionServidor";

// Toda la app requiere sesión. El backend vuelve a validar la cookie y el email en cada pedido.
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const sesion = await sesionActual();
  if (!sesion) redirect("/login");
  return <Shell email={sesion.email.toLowerCase()}>{children}</Shell>;
}
