import { useState, type FormEvent } from "react";

import { SendIcon, SparkIcon } from "../layout/Icons";

interface Props {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: Props) {
  const [value, setValue] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();

    const content = value.trim();
    if (!content || disabled) return;

    onSend(content);
    setValue("");
  };

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <span className="chat-input-spark">
        <SparkIcon />
      </span>

      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        id="chat-input-field"
        placeholder="Ask JARVIS..."
        aria-label="Message"
        autoFocus
      />

      <button
        type="submit"
        className="send-button"
        disabled={disabled || !value.trim()}
        aria-label="Send"
      >
        <SendIcon />
      </button>
    </form>
  );
}
