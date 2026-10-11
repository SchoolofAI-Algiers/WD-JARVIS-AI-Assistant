/*
 * Tiny HUD sound effects made with the Web Audio API (no audio files).
 * They only play when sound is enabled in the settings.
 */
type SoundName = "click" | "send" | "reply" | "error" | "boot" | "pulse";

let context: AudioContext | null = null;
let enabled = false;

export function setSoundEnabled(value: boolean) {
  enabled = value;
}

function tone(frequency: number, start: number, duration: number, type: OscillatorType = "sine", volume = 0.05, endFrequency?: number) {
  if (!context) return;

  const oscillator = context.createOscillator();
  const gain = context.createGain();
  const t = context.currentTime + start;

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, t);
  if (endFrequency) oscillator.frequency.exponentialRampToValueAtTime(endFrequency, t + duration);

  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(volume, t + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + duration);

  oscillator.connect(gain).connect(context.destination);
  oscillator.start(t);
  oscillator.stop(t + duration + 0.02);
}

export function playSound(name: SoundName) {
  if (!enabled) return;

  try {
    // Create the audio context only when a sound is requested.
    context ??= new AudioContext();

    // Resume it if the browser suspended it.
    if (context.state === "suspended") {
      void context.resume().catch((error) => {
        console.warn("HUD sound could not resume:", error);
      });
    }
  } catch (error) {
    console.warn("HUD sound is unavailable:", error);
    return;
  }


  switch (name) {
    case "click":
      tone(1800, 0, 0.05, "triangle", 0.03);
      break;
    case "send":
      tone(600, 0, 0.12, "sine", 0.05, 1400);
      break;
    case "reply":
      tone(880, 0, 0.08, "sine", 0.04);
      tone(1320, 0.08, 0.12, "sine", 0.04);
      break;
    case "error":
      tone(220, 0, 0.25, "sawtooth", 0.03, 140);
      break;
    case "boot":
      tone(200, 0, 0.6, "sine", 0.05, 1200);
      tone(1200, 0.6, 0.2, "triangle", 0.03);
      break;
    case "pulse":
      tone(120, 0, 0.4, "sine", 0.08, 60);
      tone(900, 0.02, 0.15, "triangle", 0.02, 1800);
      break;
  }
}
