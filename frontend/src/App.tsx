import { useState } from "react";
import { sendMessage } from "./services/api/chat";

import { ChatWindow } from "./components/chat/ChatWindow";
import { ChatInput } from "./components/chat/ChatInput";
import { EmptyChat } from "./components/chat/EmptyChat";
import { ConversationSidebar } from "./components/chat/ConversationSidebar";
import { SourceList } from "./components/chat/SourceList";
import { ErrorMessage } from "./components/chat/ErrorMessage";

import {
  AssistantStatus,
  type AssistantStatusType,
} from "./components/status/AssistantStatus";

import { VoiceButton } from "./components/voice/VoiceButton";
import { VoiceVisualizer } from "./components/voice/VoiceVisualizer";
import { ToolActivity } from "./components/tools/ToolActivity";

import type { ChatMessage } from "./types/chat";

import "./App.css";

interface Source {
  title: string;
  url?: string;
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] =
    useState<AssistantStatusType>("idle");
  const [listening, setListening] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState(false);
  const [lastMessage, setLastMessage] = useState<string | null>(
    null
  );

  const sendToAssistant = async (content: string) => {
    setError(false);
    setLastMessage(content);
    setSources([]);
    setActiveTool(null);

    const lowerMessage = content.toLowerCase();

    let detectedTool: string | null = null;

    /*
     * Temporary frontend simulation.
     * This will later be replaced by backend metadata.
     */
    if (
      lowerMessage.includes("calculate") ||
      lowerMessage.includes("×") ||
      lowerMessage.includes("multiply")
    ) {
      detectedTool = "CALCULATOR";
    } else if (lowerMessage.includes("weather")) {
      detectedTool = "WEATHER";
    }

    if (detectedTool) {
      setActiveTool(detectedTool);
      setStatus("tool_call");
    } else {
      setStatus("thinking");
    }

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

      setMessages((previous) => [
        ...previous,
        assistantMessage,
      ]);

      /*
       * Temporary RAG simulation.
       */
      if (
        lowerMessage.includes("soai") ||
        lowerMessage.includes("what is soai")
      ) {
        setSources([
          {
            title: "SOAI Overview",
          },
          {
            title: "SOAI Architecture",
          },
        ]);
      }

      setStatus("idle");

      if (detectedTool) {
        setTimeout(() => {
          setActiveTool(null);
        }, 1500);
      }
    } catch (requestError) {
      console.error(requestError);

      setStatus("error");
      setActiveTool(null);
      setSources([]);
      setError(true);
    }
  };

  const handleSend = async (content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((previous) => [...previous, userMessage]);

    await sendToAssistant(content);
  };

  const handleRetry = async () => {
    if (!lastMessage) {
      return;
    }

    await sendToAssistant(lastMessage);
  };

  const handleVoice = () => {
    const nextListening = !listening;

    setListening(nextListening);
    setStatus(nextListening ? "listening" : "idle");
  };

  const handleNewChat = () => {
    setMessages([]);
    setStatus("idle");
    setListening(false);
    setActiveTool(null);
    setSources([]);
    setError(false);
    setLastMessage(null);
  };

  const isProcessing =
    status === "thinking" ||
    status === "tool_call";

  return (
    <div className="app-shell">
      <ConversationSidebar onNewChat={handleNewChat} />

      <main className="jarvis">
        <header className="jarvis-header">
          <div>
            <h1 className="jarvis-title">J.A.R.V.I.S.</h1>

            <span className="jarvis-subtitle">
              JUST A RATHER VERY INTELLIGENT SYSTEM
            </span>
          </div>

          <AssistantStatus
            status={status}
            tool={activeTool ?? undefined}
          />
        </header>

        <section className="assistant-area">
          {activeTool && (
            <ToolActivity
              tool={activeTool}
              description="Processing your request..."
            />
          )}

          {error ? (
            <ErrorMessage onRetry={handleRetry} />
          ) : messages.length === 0 ? (
            <EmptyChat />
          ) : (
            <ChatWindow messages={messages} />
          )}

          <SourceList sources={sources} />

          <VoiceVisualizer active={listening} />
        </section>

        <footer className="chat-footer">
          <ChatInput
            onSend={handleSend}
            disabled={isProcessing}
          />

          <VoiceButton
            listening={listening}
            onClick={handleVoice}
          />
        </footer>
      </main>
    </div>
  );
}

export default App;