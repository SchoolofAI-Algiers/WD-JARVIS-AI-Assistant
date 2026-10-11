import { useEffect, useRef, useState, type PointerEvent } from "react";
import { useVoiceTurn } from "./hooks/UseVoiceTurn";

import { sendMessage } from "./services/api/chat";

import { ChatWindow } from "./components/chat/ChatWindow";
import { ChatInput } from "./components/chat/ChatInput";
import { EmptyChat } from "./components/chat/EmptyChat";
import { ConversationSidebar } from "./components/chat/ConversationSidebar";
import { ErrorMessage } from "./components/chat/ErrorMessage";

import type { AssistantStatusType } from "./components/status/AssistantStatus";

import { VoiceButton } from "./components/voice/VoiceButton";
import { VoiceVisualizer } from "./components/voice/VoiceVisualizer";

import { OptionalImage } from "./components/layout/OptionalImage";
import { Chamfer } from "./components/hud/Chamfer";
import { Clock } from "./components/hud/Clock";
import { BootScreen } from "./components/hud/BootScreen";
import { Ripples, type Ripple } from "./components/hud/Ripples";
import { BeamOverlay, PlatformOverlay, ReactorOverlay } from "./components/hud/ReactorOverlay";
import {
  CoreInfo,
  LocationList,
  QuoteCard,
  StatsList,
  SystemPanel,
  type SessionStats,
} from "./components/hud/SidePanels";

import { IMAGES } from "./config/images";
import { scene } from "./utils/place";
import { playSound, setSoundEnabled } from "./utils/sound";
import { loadSettings, saveSettings, type Settings } from "./utils/settings";
import type { ChatMessage, Conversation } from "./types/chat";

import "./App.css";

function createConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    messages: [],
    updatedAt: new Date(),
  };
}

function App() {
  const [conversations, setConversations] = useState<Conversation[]>(() => [
    createConversation(),
  ]);
  const [activeId, setActiveId] = useState(conversations[0].id);
  const [status, setStatus] = useState<AssistantStatusType>("idle");
  // const [listening, setListening] = useState(false);
  const [failed, setFailed] = useState<{ conversationId: string; content: string } | null>(null);
  const [session, setSession] = useState<SessionStats>({
    messages: 0,
    lastReplyMs: null,
    lastMode: null,
  });
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [booting, setBooting] = useState(settings.boot);
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const stageRef = useRef<HTMLDivElement>(null);

  const active = conversations.find((c) => c.id === activeId) ?? conversations[0];
  const isProcessing = status === "thinking" || status === "tool_call";

  const voice = useVoiceTurn({
  conversationId: active.id,

  onStatus: setStatus,

  onTurn: (result) => {
    if (!result.ok) {
      setFailed({
        conversationId: active.id,
        content: result.error?.message ?? "Voice interaction failed.",
      });
      return;
    }

    // Add the user's transcribed speech to the conversation.
    if (result.transcript?.text) {
      addMessage(active.id, {
        id: crypto.randomUUID(),
        role: "user",
        content: result.transcript.text,
        timestamp: new Date(),
      });
    }

    // Add the assistant's reply to the conversation.
    if (result.reply_text) {
      addMessage(active.id, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.reply_text,
        timestamp: new Date(),
      });
    }
  },

  onProblem: (message) => {
    console.error("[JARVIS] Voice problem:", message);

    setFailed({
      conversationId: active.id,
      content: message,
    });
  },
});


const listening = voice.listening;

  useEffect(() => {
    setSoundEnabled(settings.sound);
    saveSettings(settings);
  }, [settings]);

  /* ---------------- chat ---------------- */

  const addMessage = (conversationId: string, message: ChatMessage) => {
    setConversations((previous) =>
      previous.map((conversation) =>
        conversation.id !== conversationId
          ? conversation
          : {
              ...conversation,
              title:
                conversation.messages.length === 0 && message.role === "user"
                  ? message.content.slice(0, 32)
                  : conversation.title,
              messages: [...conversation.messages, message],
              updatedAt: new Date(),
            }
      )
    );
  };

  const sendToAssistant = async (conversationId: string, content: string) => {
    setFailed(null);
    setStatus("thinking");
    const start = performance.now();

    try {
      const response = await sendMessage({
        conversation_id: conversationId,
        message: content,
      });

      const { metadata } = response;

      setSession((previous) => ({
        messages: previous.messages + 1,
        lastReplyMs: performance.now() - start,
        lastMode: metadata.type,
      }));

      addMessage(conversationId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.message,
        timestamp: new Date(),
        sources: metadata.type === "rag" ? metadata.sources ?? [] : undefined,
        tool: metadata.type === "tool" && metadata.tool ? String(metadata.tool) : undefined,
      });

      playSound("reply");
      setStatus("idle");
    } catch (requestError) {
      console.error(requestError);
      playSound("error");
      setStatus("error");
      setFailed({ conversationId, content });
    }
  };

  const handleSend = async (content: string) => {
    if (isProcessing) return;

    playSound("send");
    addMessage(active.id, {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    });

    await sendToAssistant(active.id, content);
  };

  const handleRetry = async () => {
    if (failed) {
      await sendToAssistant(failed.conversationId, failed.content);
    }
  };

  const handleVoice = () => {
  playSound("click");
  void voice.toggle();
};

  const handleNewChat = () => {
    playSound("click");

    // Reuse the current conversation if it's still empty.
    if (active.messages.length === 0) return;

    const conversation = createConversation();
    setConversations((previous) => [conversation, ...previous]);
    setActiveId(conversation.id);
    setStatus("idle");
    voice.cancel();
    setFailed(null);
  };

  const handleSelect = (id: string) => {
    playSound("click");
    setActiveId(id);
    setFailed(null);
    if (status === "error") setStatus("idle");
  };

  /* ---------------- keyboard shortcuts ---------------- */

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const typing = (event.target as HTMLElement).tagName === "INPUT";

      if (event.key === "/" && !typing) {
        event.preventDefault();
        document.getElementById("chat-input-field")?.focus();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        handleNewChat();
      } else if (event.key === "Escape") {
        (document.activeElement as HTMLElement | null)?.blur();
        if (listening) handleVoice();
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  /* ---------------- scene effects ---------------- */

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const stage = stageRef.current;
    if (!stage) return;

    const box = stage.getBoundingClientRect();
    stage.style.setProperty("--cx", `${event.clientX - box.left}px`);
    stage.style.setProperty("--cy", `${event.clientY - box.top}px`);
  };

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    const stage = stageRef.current;
    if (!stage || (event.target as HTMLElement).closest("input, .settings-menu")) return;

    const box = stage.getBoundingClientRect();
    const ripple = { id: Date.now() + Math.random(), x: event.clientX - box.left, y: event.clientY - box.top };

    setRipples((current) => [...current.slice(-6), ripple]);
    setTimeout(() => setRipples((current) => current.filter((r) => r.id !== ripple.id)), 900);
  };

  const empty = active.messages.length === 0;
  const showError = failed && failed.conversationId === active.id;

  return (
    <div
      className="app"
      ref={stageRef}
      data-status={status}
      data-motion={settings.motion ? "on" : "off"}
      onPointerMove={handlePointerMove}
      onPointerDown={handlePointerDown}
    >
      {/* the picture, filling the screen ("cover"), and what is pinned to it */}
      <div className="scene">
        <img className="scene-bg" src={IMAGES.background} alt="" draggable={false} />
        <img className="scene-sharp" src={IMAGES.background} alt="" draggable={false} />
        <div className="scene-haze" />

        <BeamOverlay status={status} />
        <PlatformOverlay status={status} />
        <ReactorOverlay status={status} onActivate={() => playSound("pulse")} />

        {empty ? (
          <>
            <EmptyChat />
            {showError && (
              <div className="floating-error" style={scene(780, 610, 520)}>
                <ErrorMessage onRetry={handleRetry} />
              </div>
            )}
          </>
        ) : (
          <ChatWindow
            messages={active.messages}
            status={status}
            footer={showError ? <ErrorMessage onRetry={handleRetry} /> : null}
          />
        )}

        <VoiceVisualizer active={listening} />
      </div>

      <div className="cursor-light" aria-hidden="true" />

      {/* HUD anchored to the screen edges */}
      <ConversationSidebar
        conversations={conversations}
        activeId={active.id}
        online={status !== "error"}
        settings={settings}
        onSettingsChange={setSettings}
        onNewChat={handleNewChat}
        onSelect={handleSelect}
      />

      <header className="stage-header">
        <OptionalImage
          src={IMAGES.headerLogo}
          className="header-logo"
          fallback={<span className="org-badge">SOAI</span>}
        />
        <span className="brand-divider" />
        <div>
          <h1 className="stage-title">J.A.R.V.I.S.</h1>
          <span className="stage-subtitle">JUST A RATHER VERY INTELLIGENT SYSTEM</span>
        </div>
      </header>

      <div className="org-block">
        <OptionalImage
          src={IMAGES.orgLogo}
          className="org-logo"
          fallback={
            <div className="org-mark">
              <strong>SCHOOL OF AI</strong>
              <span>ALGIERS · BUILDING THE FUTURE WITH AI</span>
            </div>
          }
        />
        <Clock />
      </div>

      <div className="hud-left">
        <SystemPanel status={status} onPrompt={handleSend} disabled={isProcessing} />
        <CoreInfo busy={isProcessing} session={session} />
      </div>

      <div className="hud-right">
        <QuoteCard />
        <StatsList busy={isProcessing} status={status} />
        <LocationList />
      </div>

      <footer className="stage-footer">
        <Chamfer className="input-frame" corners="tl bl tr br" cut={22}>
          <ChatInput onSend={handleSend} disabled={isProcessing} />
        </Chamfer>
        <VoiceButton listening={listening} onClick={handleVoice} />
      </footer>

      <div className="stage-signature">
        SOAI · J.A.R.V.I.S.
        <span className="signature-stripes">
          <i />
          <i />
          <i />
          <i />
        </span>
      </div>

      <Ripples ripples={ripples} />

      {booting && <BootScreen onDone={() => setBooting(false)} />}
    </div>
  );
}

export default App;
