interface Props {
  listening: boolean;
  onClick: () => void;
}

export function VoiceButton({ listening, onClick }: Props) {
  return (
    <button
      className={`voice-button ${listening ? "listening" : ""}`}
      onClick={onClick}
      aria-label={listening ? "Stop listening" : "Start listening"}
    >
      {listening ? "■" : "🎙"}
    </button>
  );
}