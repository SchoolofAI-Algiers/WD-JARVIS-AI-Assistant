export type AssistantStatusType =
  | "idle"
  | "listening"
  | "thinking"
  | "tool_call"
  | "error";

interface Props {
  status: AssistantStatusType;
  tool?: string;
}

const LABELS: Record<AssistantStatusType, [string, string]> = {
  idle: ["SYSTEM", "ONLINE"],
  listening: ["SYSTEM", "LISTENING"],
  thinking: ["SYSTEM", "PROCESSING"],
  tool_call: ["RUNNING", "TOOL"],
  error: ["SYSTEM", "OFFLINE"],
};

export function AssistantStatus({ status, tool }: Props) {
  const [label, value] = LABELS[status];

  return (
    <div className={`assistant-status ${status}`} role="status">
      <span className="status-dot" />
      <span>{label}</span>
      <strong>{status === "tool_call" && tool ? tool.toUpperCase() : value}</strong>
    </div>
  );
}
