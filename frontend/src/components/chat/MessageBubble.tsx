import type { ChatMessage } from "../../types/chat";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  return (
    <div className={`message ${message.role}`}>
      <strong>{message.role === "user" ? "YOU" : "JARVIS"}</strong>
      <p>{message.content}</p>
    </div>
  );
}