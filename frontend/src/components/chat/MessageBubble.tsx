import type { ChatMessage } from "../../types/chat";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const time = message.timestamp.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={`message ${message.role}`}>
      <div className="message-header">
        <strong>
          {message.role === "user" ? "YOU" : "JARVIS"}
        </strong>

        <span className="message-time">{time}</span>
      </div>

      <p>{message.content}</p>
    </div>
  );
}