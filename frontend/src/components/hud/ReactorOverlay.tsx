import { useState } from "react";

import type { AssistantStatusType } from "../status/AssistantStatus";
import { scene } from "../../utils/place";

interface Props {
  status: AssistantStatusType;
  onActivate: () => void;
}

const C = 320; // center of the 640 x 640 overlay
const TICKS = Array.from({ length: 60 }, (_, i) => i * 6);

const polar = (r: number, deg: number) => {
  const a = ((deg - 90) * Math.PI) / 180;
  return [C + r * Math.cos(a), C + r * Math.sin(a)];
};

const arc = (r: number, a: number, b: number) => {
  const [x1, y1] = polar(r, a);
  const [x2, y2] = polar(r, b);
  return `M ${x1} ${y1} A ${r} ${r} 0 ${b - a > 180 ? 1 : 0} 1 ${x2} ${y2}`;
};

/**
 * Animated layer drawn exactly on top of the core in the background picture:
 * rotating rings, a light sweep and a pulsing glow. Click it for a shockwave.
 */
export function ReactorOverlay({ status, onActivate }: Props) {
  const [waves, setWaves] = useState<number[]>([]);
  const busy = status === "thinking" || status === "tool_call";

  const activate = () => {
    const id = Date.now();
    setWaves((current) => [...current, id]);
    setTimeout(() => setWaves((current) => current.filter((w) => w !== id)), 1400);
    onActivate();
  };

  return (
    <div
      className={`reactor ${busy ? "busy" : ""} ${status === "error" ? "error" : ""} ${status === "listening" ? "listening" : ""}`}
      style={scene(1040 - 320, 285 - 320, 640, 640)}
      aria-hidden="true"
    >
      <div className="reactor-glow" />
      <div className="reactor-sweep" />

      <svg viewBox="0 0 640 640">
        <defs>
          <path id="textRing" d={`M ${C} ${C} m -252 0 a 252 252 0 1 1 504 0 a 252 252 0 1 1 -504 0`} />
        </defs>

        <circle className="rx-ring rx-outer" cx={C} cy={C} r={302} />

        <g className="rx-ring rx-ticks">
          {TICKS.map((deg) => {
            const [x1, y1] = polar(268, deg);
            const [x2, y2] = polar(deg % 30 === 0 ? 256 : 262, deg);
            return <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2} />;
          })}
        </g>

        <g className="rx-ring rx-arcs">
          <path d={arc(232, 10, 70)} />
          <path d={arc(232, 130, 190)} />
          <path d={arc(232, 250, 310)} />
        </g>

        <g className="rx-ring rx-inner-arcs">
          <path d={arc(176, 40, 120)} />
          <path d={arc(176, 220, 300)} />
        </g>

        <text className="rx-text">
          <textPath href="#textRing" startOffset="0">
            ANALYZING · PROCESSING · SOAI KNOWLEDGE · NEURAL CORE ACTIVE · ANALYZING · PROCESSING ·
          </textPath>
        </text>

        {waves.map((id) => (
          <circle key={id} className="rx-wave" cx={C} cy={C} r={150} />
        ))}
      </svg>

      <button
        className="reactor-hit"
        onClick={activate}
        aria-label="Activate the core"
        title="Activate the core"
        tabIndex={0}
      />
    </div>
  );
}

/** Pulsing light, rotating dashes and sparks on the platform of the background picture. */
export function PlatformOverlay({ status }: { status: AssistantStatusType }) {
  const busy = status === "thinking" || status === "tool_call";

  return (
    <div className={`platform-fx ${busy ? "busy" : ""}`} style={scene(685, 600, 700, 150)} aria-hidden="true">
      <svg viewBox="0 0 700 150">
        <defs>
          <radialGradient id="pfGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="35%" stopColor="#9fe0ff" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#3aa7f0" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse className="pf-glow" cx="350" cy="72" rx="300" ry="36" fill="url(#pfGlow)" />
        <ellipse className="pf-dash" cx="350" cy="74" rx="335" ry="44" />
        <ellipse className="pf-dash inner" cx="350" cy="70" rx="200" ry="22" />
        <ellipse className="pf-core" cx="350" cy="68" rx="70" ry="9" />
      </svg>

      <div className="pf-sparks">
        {Array.from({ length: 14 }, (_, i) => (
          <span key={i} style={{ left: `${30 + i * 2.9}%`, animationDelay: `${(i * 0.37) % 3}s` }} />
        ))}
      </div>
    </div>
  );
}

/** Shimmer on the vertical light beam between the platform and the core. */
export function BeamOverlay({ status }: { status: AssistantStatusType }) {
  const busy = status === "thinking" || status === "tool_call";
  return <div className={`beam-fx ${busy ? "busy" : ""}`} style={scene(1000, 300, 80, 380)} aria-hidden="true" />;
}
