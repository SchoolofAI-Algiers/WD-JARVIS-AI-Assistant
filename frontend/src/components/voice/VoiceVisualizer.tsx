// This is just a visual placeholder. We can connect the real audio state later.

interface Props {
  active: boolean;
}

const BARS = 24;

export function VoiceVisualizer({ active }: Props) {
  if (!active) return null;

  return (
    <div className="voice-visualizer" aria-label="Listening">
      <span className="voice-label">LISTENING</span>
      <div className="voice-bars">
        {Array.from({ length: BARS }, (_, i) => (
          <span key={i} style={{ animationDelay: `${(i % 8) * 0.08}s` }} />
        ))}
      </div>
    </div>
  );
}
