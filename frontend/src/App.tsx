import { useState } from "react";
import { sendMessage } from "./services/api/chat";
import { ChatWindow } from "./components/chat/ChatWindow";
import { ChatInput } from "./components/chat/ChatInput";
import type { ChatMessage } from "./types/chat";
import "./App.css";

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((previous) => [...previous, userMessage]);
    setLoading(true);

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
    } catch (error) {
      console.error(error);

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Unable to connect to JARVIS.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="jarvis">
      <header className="jarvis-header">
        <h1 className="jarvis-title">J.A.R.V.I.S.</h1>

        <div className="jarvis-status">
          <span className="status-dot" />
          ONLINE
        </div>
      </header>

      <ChatWindow messages={messages} />

      {loading && (
        <div className="jarvis-status">
          JARVIS IS THINKING...
        </div>
      )}

      <ChatInput onSend={handleSend} disabled={loading} />
    </main>
  );
}

export default App;