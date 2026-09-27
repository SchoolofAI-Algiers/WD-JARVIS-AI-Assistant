import { useState } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    if (!value.trim() || disabled) {
      return;
    }

    onSend(value.trim());
    setValue("");
  };

  return (
    <div className="chat-input">
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            handleSubmit();
          }
        }}
        placeholder={
          disabled
            ? "JARVIS is processing..."
            : "Ask JARVIS..."
        }
        disabled={disabled}
      />

      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
      >
        {disabled ? "..." : "Send"}
      </button>
    </div>
  );
}