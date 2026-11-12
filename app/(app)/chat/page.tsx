import { Chat } from "@/components/Chat";

export default async function NuevaConversacion({ searchParams }: { searchParams: Promise<{ nueva?: string }> }) {
  const { nueva } = await searchParams;
  return <Chat key={nueva ?? "nueva"} />;
}
