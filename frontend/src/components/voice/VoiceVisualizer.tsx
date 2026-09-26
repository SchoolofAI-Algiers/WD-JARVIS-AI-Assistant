//This is just a visual placeholder. We can connect the real audio state later.

interface Props {
  active: boolean;
}

export function VoiceVisualizer({ active }: Props) {
  if (!active) return null;

  return (
    <div className="voice-visualizer" aria-label="Listening">
      <span />
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}