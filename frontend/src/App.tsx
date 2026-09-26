import { useState } from "react";
import { sendMessage } from "./services/api/chat";
import { ChatWindow } from "./components/chat/ChatWindow";
import { ChatInput } from "./components/chat/ChatInput";
import { EmptyChat } from "./components/chat/EmptyChat";
import {
  AssistantStatus,
  type AssistantStatusType,
} from "./components/status/AssistantStatus";
import { VoiceButton } from "./components/voice/VoiceButton";
import { VoiceVisualizer } from "./components/voice/VoiceVisualizer";
import type { ChatMessage } from "./types/chat";
import "./App.css";

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<AssistantStatusType>("idle");
  const [listening, setListening] = useState(false);

  const handleSend = async (content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((previous) => [...previous, userMessage]);
    setStatus("thinking");

    try {
      const response = await sendMessage({
        conversation_id: "test-123",
        message: content,
      });

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.message,
        timestamp: new Date(),
      };

      setMessages((previous) => [...previous, assistantMessage]);
      setStatus("idle");
    } catch (error) {
      console.error(error);
      setStatus("error");

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Unable to connect to JARVIS.",
          timestamp: new Date(),
        },
      ]);
    }
  };

  const handleVoice = () => {
    setListening((previous) => !previous);
    setStatus(listening ? "idle" : "listening");
  };

  return (
    <main className="jarvis">
      <header className="jarvis-header">
        <div>
          <h1 className="jarvis-title">J.A.R.V.I.S.</h1>
          <span className="jarvis-subtitle">
            JUST A RATHER VERY INTELLIGENT SYSTEM
          </span>
        </div>

        <AssistantStatus status={status} />
      </header>

      <section className="assistant-area">
        {messages.length === 0 ? (
          <EmptyChat />
        ) : (
          <ChatWindow messages={messages} />
        )}

        <VoiceVisualizer active={listening} />
      </section>

      <footer className="chat-footer">
        <ChatInput
          onSend={handleSend}
          disabled={status === "thinking"}
        />

        <VoiceButton
          listening={listening}
          onClick={handleVoice}
        />
      </footer>
    </main>
  );
}

export default App;