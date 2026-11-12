import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { Shell } from "@/components/Shell";

// Toda la app requiere sesión. El backend vuelve a validar la cookie y el email en cada pedido.
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const sesion = await auth();
  const email = sesion?.user?.email;
  if (!email) redirect("/login");
  return <Shell email={email}>{children}</Shell>;
}
