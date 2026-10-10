import { useState } from "react";
import { sendMessage } from "./services/api/chat";
import type { VoiceTurnResponse } from "./services/api/voice";
import { useVoiceTurn } from "./hooks/UseVoiceTurn";

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
  // One id per conversation, shared by text and voice turns. Only
  // "New conversation" replaces it.
  const [conversationId, setConversationId] = useState(() =>
    crypto.randomUUID()
  );
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState(false);
  const [lastMessage, setLastMessage] = useState<string | null>(
    null
  );

  const addAssistantMessage = (content: string) => {
    setMessages((previous) => [
      ...previous,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content,
        timestamp: new Date(),
      },
    ]);
  };

  const handleVoiceTurn = (result: VoiceTurnResponse) => {
    setError(false);
    setSources([]);
    setActiveTool(null);

    const heard = result.transcript?.text;

    if (heard) {
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: heard,
          timestamp: new Date(),
        },
      ]);
    }

    // On a friendly failure reply_text already holds the message to show.
    addAssistantMessage(result.reply_text);
  };

  const voice = useVoiceTurn({
    conversationId,
    onStatus: setStatus,
    onTurn: handleVoiceTurn,
    onProblem: addAssistantMessage,
  });

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
        conversation_id: conversationId,
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

      // Typed message: answer out loud as well (voice turns are already spoken by the hook).
      void voice.speak(response.message);

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
    voice.stopPlayback();

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

  const handleNewChat = () => {
    voice.cancel();
    setConversationId(crypto.randomUUID());
    setMessages([]);
    setStatus("idle");
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

          <VoiceVisualizer active={voice.listening} />
        </section>

        <footer className="chat-footer">
          <ChatInput
            onSend={handleSend}
            disabled={isProcessing}
          />

          <VoiceButton
            listening={voice.listening}
            onClick={voice.toggle}
          />
        </footer>
      </main>
    </div>
  );
}

export default App;