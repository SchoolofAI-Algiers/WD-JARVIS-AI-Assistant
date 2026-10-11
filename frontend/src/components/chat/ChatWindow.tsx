import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import type { ChatMessage } from "../../types/chat";
import { formatTime } from "../../utils/time";
import { scene } from "../../utils/place";
import { Chamfer } from "../hud/Chamfer";
import type { AssistantStatusType } from "../status/AssistantStatus";
import { ToolActivity } from "../tools/ToolActivity";
import { SourceList } from "./SourceList";

interface Props {
  messages: ChatMessage[];
  status: AssistantStatusType;
  /** Shown under the messages (e.g. the error card). */
  footer?: ReactNode;
}

/* Messages already typed out once, so they don't re-type when you switch conversations. */
const typedMessages = new Set<string>();

/** Types the assistant answer out letter by letter, like a HUD readout. */
function TypedText({ id, text, onProgress }: { id: string; text: string; onProgress: () => void }) {
  const alreadyTyped = typedMessages.has(id);
  const [shown, setShown] = useState(alreadyTyped ? text.length : 0);

  useEffect(() => {
    if (alreadyTyped) return;

    const step = Math.max(1, Math.ceil(text.length / 120));
    const timer = setInterval(() => {
      setShown((current) => {
        const next = Math.min(text.length, current + step);
        if (next >= text.length) {
          clearInterval(timer);
          typedMessages.add(id);
        }
        return next;
      });
    }, 16);

    return () => clearInterval(timer);
  }, [alreadyTyped, id, text]);

  useEffect(onProgress, [shown, onProgress]);

  return (
    <p className="message-text">
      {text.slice(0, shown)}
      {shown < text.length && <span className="caret" />}
    </p>
  );
}

/** Glass chat panel placed over the core of the background picture. */
export function ChatWindow({ messages, status, footer }: Props) {
  const windowRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    const element = windowRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, []);

  useEffect(scrollToBottom, [messages.length, status, scrollToBottom]);

  const busy = status === "thinking" || status === "tool_call";

  return (
    <div className="chat-area" style={scene(735, 92, 612, 545)}>
      <Chamfer className="chat-panel" corners="tl tr br bl" cut={20}>
        <div className="chat-header">
          <span className={`chat-core ${busy ? "busy" : ""}`} />
          <div>
            <h2>J.A.R.V.I.S.</h2>
            <span>{busy ? "Analyzing your request…" : "At your service."}</span>
          </div>
        </div>

        <div className="chat-window" ref={windowRef}>
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-header">
                <strong>{message.role === "user" ? "YOU" : "J.A.R.V.I.S."}</strong>
                <span className="message-time">{formatTime(message.timestamp)}</span>
              </div>

              {message.role === "assistant" ? (
                <TypedText id={message.id} text={message.content} onProgress={scrollToBottom} />
              ) : (
                <p className="message-text">{message.content}</p>
              )}

              {message.tool && <ToolActivity tool={message.tool} description="Exact result computed by a tool" />}
              {message.sources && <SourceList sources={message.sources} />}
            </div>
          ))}

          {busy && (
            <div className="message assistant thinking">
              <div className="message-header">
                <strong>J.A.R.V.I.S.</strong>
              </div>
              <div className="typing">
                <span />
                <span />
                <span />
                <em>Processing</em>
              </div>
            </div>
          )}

          {footer}
        </div>
      </Chamfer>
    </div>
  );
}
