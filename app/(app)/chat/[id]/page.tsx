import { Chat } from "@/components/Chat";

export default async function ConversacionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <Chat key={id} conversacionId={id} />;
}
