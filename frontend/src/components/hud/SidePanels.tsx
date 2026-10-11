import { useEffect, useRef, useState } from "react";

import { HudPanel } from "./HudPanel";
import { Chamfer } from "./Chamfer";
import { SERVER_URL } from "../../services/api/chat";
import { playSound } from "../../utils/sound";
import {
  AssistantStatus,
  type AssistantStatusType,
} from "../status/AssistantStatus";
import {
  ChevronRightIcon,
  ChipIcon,
  CloudIcon,
  MemoryIcon,
  SignalIcon,
  ThermoIcon,
} from "../layout/Icons";

export interface SessionStats {
  messages: number;
  lastReplyMs: number | null;
  lastMode: string | null;
}

const random = (min: number, max: number) =>
  Math.round(min + Math.random() * (max - min));

/** CPU / MEM / TEMP values that move a little, more when JARVIS is busy. */
function useLiveStats(busy: boolean) {
  const [stats, setStats] = useState({ cpu: 12, mem: 28, temp: 36 });

  useEffect(() => {
    const timer = setInterval(() => {
      setStats({
        cpu: busy ? random(55, 85) : random(8, 18),
        mem: busy ? random(38, 52) : random(26, 32),
        temp: busy ? random(44, 52) : random(35, 38),
      });
    }, 1800);

    return () => clearInterval(timer);
  }, [busy]);

  return stats;
}

/** Current temperature in Algiers (Open-Meteo, free, no key). */
function useAlgiersWeather() {
  const [weather, setWeather] = useState<string>("—");

  useEffect(() => {
    fetch("https://api.open-meteo.com/v1/forecast?latitude=36.75&longitude=3.06&current=temperature_2m")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((data) => setWeather(`${Math.round(data.current.temperature_2m)}°C`))
      .catch(() => setWeather("—"));
  }, []);

  return weather;
}

/* ================= LEFT ================= */

/** Each capability sends an example question to JARVIS. */
const CAPABILITIES: [string, string][] = [
  ["Knowledge", "What is SOAI?"],
  ["Reasoning", "Which SOAI event is best for a beginner, and why?"],
  ["Problem Solving", "What is 25 * 4?"],
  ["Always Here", "What time is it?"],
];

interface SystemPanelProps {
  status: AssistantStatusType;
  onPrompt: (text: string) => void;
  disabled: boolean;
}

/** Sits in the empty frame of the background picture. */
export function SystemPanel({ status, onPrompt, disabled }: SystemPanelProps) {
  return (
    <HudPanel className="system-panel" corners="tl tr br bl" delay={0}>
      <AssistantStatus status={status} />
      <div className="panel-rule" />

      <ul className="capability-list">
        {CAPABILITIES.map(([name, prompt]) => (
          <li key={name}>
            <button
              className="capability"
              onClick={() => onPrompt(prompt)}
              disabled={disabled}
              title={`Ask: "${prompt}"`}
            >
              <ChevronRightIcon size={14} />
              <span>{name}</span>
              <em>{prompt}</em>
            </button>
          </li>
        ))}
      </ul>

      <div className="slash-bar" aria-hidden="true">
        {Array.from({ length: 14 }, (_, i) => (
          <i key={i} style={{ animationDelay: `${i * 0.08}s` }} />
        ))}
      </div>
    </HudPanel>
  );
}

/** Version info + a small live bar graph. Click to see the stats of this session. */
export function CoreInfo({ busy, session }: { busy: boolean; session: SessionStats }) {
  const [view, setView] = useState<"core" | "session">("core");
  const { cpu, mem } = useLiveStats(busy);
  const bars = [cpu, mem, 64, 42, 80, cpu + 20, 55, mem + 10];

  const toggle = () => {
    playSound("click");
    setView(view === "core" ? "session" : "core");
  };

  return (
    <div
      className="core-info"
      role="button"
      tabIndex={0}
      title="Click to switch view"
      onClick={toggle}
      onKeyDown={(event) => {
        if (event.key === "Enter") toggle();
      }}
    >
      <h3>J.A.R.V.I.S. v3.2.1</h3>
      <p className="panel-sub">SCHOOL OF AI ALGIERS</p>
      <p className="panel-sub">{view === "core" ? "AI CORE" : "THIS SESSION"}</p>

      <Chamfer className="mini-widget" corners="tr bl" cut={10}>
        {view === "core" ? (
          <div className="mini-graph" key="core">
            <div className="mini-bars">
              {bars.map((value, i) => (
                <span key={i} style={{ height: `${Math.min(value, 100)}%` }} />
              ))}
            </div>
            <div className="mini-lines">
              <i style={{ width: `${cpu}%` }} />
              <i style={{ width: `${mem}%` }} />
              <i style={{ width: "86%" }} />
              <i style={{ width: "60%" }} />
            </div>
          </div>
        ) : (
          <div className="session-rows" key="session">
            <div>
              <span>MESSAGES</span>
              <strong>{session.messages}</strong>
            </div>
            <div>
              <span>LAST REPLY</span>
              <strong>{session.lastReplyMs !== null ? `${(session.lastReplyMs / 1000).toFixed(1)} s` : "—"}</strong>
            </div>
            <div>
              <span>MODE</span>
              <strong>{session.lastMode?.toUpperCase() ?? "—"}</strong>
            </div>
          </div>
        )}
      </Chamfer>
    </div>
  );
}

/* ================= RIGHT ================= */

const QUOTES: [string, string][] = [
  ["The best way to predict the future is to invent it.", "ALAN KAY"],
  ["Any sufficiently advanced technology is indistinguishable from magic.", "ARTHUR C. CLARKE"],
  ["We can only see a short distance ahead, but we can see plenty there that needs to be done.", "ALAN TURING"],
  ["Simplicity is prerequisite for reliability.", "EDSGER W. DIJKSTRA"],
];

/** Click for the next quote. */
export function QuoteCard() {
  const [index, setIndex] = useState(0);
  const [text, author] = QUOTES[index];

  return (
    <HudPanel
      className="quote-card"
      variant="bracket"
      delay={1}
      onClick={() => {
        playSound("click");
        setIndex((index + 1) % QUOTES.length);
      }}
      label="Click for another quote"
    >
      <div className="quote-body" key={index}>
        <p>“{text}”</p>
        <span>— {author}</span>
      </div>
      <span className="red-accent" />
    </HudPanel>
  );
}

/** Live TEMP / CPU / MEM / weather. Click to run a diagnostic and ping the backend. */
export function StatsList({ busy, status }: { busy: boolean; status: AssistantStatusType }) {
  const { cpu, mem, temp } = useLiveStats(busy);
  const weather = useAlgiersWeather();
  const [scan, setScan] = useState<number | null>(null);
  const [ping, setPing] = useState<string>("—");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearInterval(timer.current);
  }, []);

  const runDiagnostic = async () => {
    if (scan !== null) return;

    playSound("pulse");
    setScan(0);
    timer.current = setInterval(() => {
      setScan((value) => {
        const next = (value ?? 0) + 5;
        if (next >= 100) {
          if (timer.current) clearInterval(timer.current);
          return null;
        }
        return next;
      });
    }, 60);

    const start = performance.now();
    try {
      await fetch(`${SERVER_URL}/docs`, { mode: "no-cors", cache: "no-store" });
      setPing(`${Math.round(performance.now() - start)} ms`);
    } catch {
      setPing("OFFLINE");
    }
  };

  const rows: [typeof ThermoIcon, string, string][] = [
    [ThermoIcon, "TEMP", `${temp}°C`],
    [ChipIcon, "CPU", `${cpu}%`],
    [MemoryIcon, "MEM", `${mem}%`],
    [SignalIcon, "PING", ping],
    [CloudIcon, "ALG", weather],
  ];

  return (
    <HudPanel
      className={`stats-list ${scan !== null ? "scanning" : ""}`}
      variant="bracket"
      delay={2}
      onClick={runDiagnostic}
      label="Click to run a diagnostic"
    >
      {rows.map(([Icon, name, value]) => (
        <div className={`stats-row ${value === "OFFLINE" ? "bad" : ""}`} key={name}>
          <Icon size={18} />
          <span>{name}</span>
          <strong>{value}</strong>
        </div>
      ))}

      <div className="stats-footer">
        {scan !== null
          ? `DIAGNOSTIC ${scan}%`
          : status === "error"
            ? "CORE UNSTABLE"
            : "ALL SYSTEMS NOMINAL"}
      </div>
    </HudPanel>
  );
}

/** Click to open the location on a map. */
export function LocationList() {
  const rows = ["SOAI HQ", "ESI, ALGIERS, DZ", "36.7050° N", "3.1740° E"];

  return (
    <button
      className="location-list"
      onClick={() => {
        playSound("click");
        window.open("https://www.google.com/maps/search/?api=1&query=36.7050,3.1740", "_blank");
      }}
      title="Open the map"
    >
      {rows.map((row, i) => (
        <span key={row} className={i >= 2 ? "coords" : ""}>
          {i < 2 && <b>+</b>}
          {row}
        </span>
      ))}
    </button>
  );
}
