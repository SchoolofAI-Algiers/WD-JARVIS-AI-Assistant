import { useEffect, useState } from "react";

import { SERVER_URL } from "../../services/api/chat";
import { playSound } from "../../utils/sound";

interface Props {
  onDone: () => void;
}

const STEPS = [
  "INITIALIZING NEURAL CORE",
  "LOADING SOAI KNOWLEDGE BASE",
  "CALIBRATING VOICE INTERFACE",
  "CONNECTING TO BACKEND",
];

/** Short start-up sequence. Click or press a key to skip. */
export function BootScreen({ onDone }: Props) {
  const [step, setStep] = useState(0);
  const [backend, setBackend] = useState<"…" | "OK" | "OFFLINE">("…");
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    playSound("boot");

    fetch(`${SERVER_URL}/docs`, { mode: "no-cors", cache: "no-store" })
      .then(() => setBackend("OK"))
      .catch(() => setBackend("OFFLINE"));

    const timer = setInterval(() => {
      setStep((s) => {
        if (s >= STEPS.length) {
          clearInterval(timer);
          return s;
        }
        return s + 1;
      });
    }, 420);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (step < STEPS.length) return;
    const leave = setTimeout(() => setLeaving(true), 500);
    const done = setTimeout(onDone, 1100);
    return () => {
      clearTimeout(leave);
      clearTimeout(done);
    };
  }, [step, onDone]);

  useEffect(() => {
    const skip = () => onDone();
    window.addEventListener("keydown", skip);
    return () => window.removeEventListener("keydown", skip);
  }, [onDone]);

  const progress = Math.min(100, (step / STEPS.length) * 100);

  return (
    <div className={`boot ${leaving ? "leaving" : ""}`} onClick={onDone}>
      <div className="boot-ring">
        <span />
        <span />
        <span />
        <strong>{Math.round(progress)}%</strong>
      </div>

      <h2>J.A.R.V.I.S.</h2>

      <ul>
        {STEPS.map((label, i) => (
          <li key={label} className={i < step ? "done" : i === step ? "current" : ""}>
            <span>{label}</span>
            <b>{i < step ? (i === STEPS.length - 1 ? backend : "OK") : i === step ? "…" : ""}</b>
          </li>
        ))}
      </ul>

      <div className="boot-bar">
        <i style={{ width: `${progress}%` }} />
      </div>

      <p>Click to skip</p>
    </div>
  );
}
