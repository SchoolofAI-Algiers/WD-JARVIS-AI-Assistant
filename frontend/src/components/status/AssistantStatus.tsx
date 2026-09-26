export type AssistantStatusType =
  | "idle"
  | "listening"
  | "thinking"
  | "retrieving"
  | "tool_call"
  | "speaking"
  | "error";

interface Props {
  status: AssistantStatusType;
  tool?: string;
}

const statusText: Record<AssistantStatusType, string> = {
  idle: "READY",
  listening: "LISTENING",
  thinking: "THINKING",
  retrieving: "RETRIEVING KNOWLEDGE",
  tool_call: "USING TOOL",
  speaking: "SPEAKING",
  error: "ERROR",
};

export function AssistantStatus({ status, tool }: Props) {
  return (
    <div className={`assistant-status ${status}`}>
      <span className="status-dot" />

      <span>
        {statusText[status]}
        {status === "tool_call" && tool ? ` · ${tool}` : ""}
      </span>
    </div>
  );
}