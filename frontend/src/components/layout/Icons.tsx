/* Small line icons used across the interface. */

interface IconProps {
  size?: number;
}

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
});

export function ChatIcon({ size = 22 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M12 3.5c5 0 9 3.4 9 7.7s-4 7.7-9 7.7c-1 0-2-.1-2.9-.4L4.5 20.5l1.3-3.7C4.1 15.4 3 13.4 3 11.2 3 6.9 7 3.5 12 3.5Z" />
      <path d="M8 10h8M8 13.5h5" />
    </svg>
  );
}

export function ChevronRightIcon({ size = 18 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}

export function DotsIcon({ size = 18 }: IconProps) {
  return (
    <svg {...base(size)} fill="currentColor" stroke="none">
      <circle cx="5" cy="12" r="1.7" />
      <circle cx="12" cy="12" r="1.7" />
      <circle cx="19" cy="12" r="1.7" />
    </svg>
  );
}

export function GearIcon({ size = 22 }: IconProps) {
  return (
    <svg {...base(size)}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </svg>
  );
}

export function SendIcon({ size = 22 }: IconProps) {
  return (
    <svg {...base(size)} fill="currentColor" stroke="none">
      <path d="M21.3 2.7c.4.4.5.9.3 1.4l-6.6 16.5c-.4 1-1.8 1-2.2 0l-2.6-6.1-6.1-2.6c-1-.4-1-1.8 0-2.2L20 3c.5-.2 1-.1 1.3.3Z" />
    </svg>
  );
}

export function MicIcon({ size = 24 }: IconProps) {
  return (
    <svg {...base(size)}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M9 21h6" />
    </svg>
  );
}

export function StopIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)} fill="currentColor" stroke="none">
      <rect x="6" y="6" width="12" height="12" rx="2.5" />
    </svg>
  );
}

export function SparkIcon({ size = 22 }: IconProps) {
  return (
    <svg {...base(size)} fill="currentColor" stroke="none">
      <path d="M10 2.5 11.6 8a3 3 0 0 0 2 2L19 11.6l-5.4 1.6a3 3 0 0 0-2 2L10 20.7l-1.6-5.5a3 3 0 0 0-2-2L1 11.6 6.4 10a3 3 0 0 0 2-2L10 2.5Z" />
      <path d="M19 1.5 19.7 4l2.3.7-2.3.7-.7 2.4-.7-2.4-2.3-.7 2.3-.7.7-2.5Z" />
    </svg>
  );
}

export function SunIcon({ size = 54 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={1.3}>
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2v2.6M12 19.4V22M2 12h2.6M19.4 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" />
    </svg>
  );
}

export function CloudIcon({ size = 54 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={1.3}>
      <path d="M7 18.5h10.5a4 4 0 0 0 .4-8 6 6 0 0 0-11.4 1.7A3.2 3.2 0 0 0 7 18.5Z" />
    </svg>
  );
}

export function RainIcon({ size = 54 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={1.3}>
      <path d="M7 15h10.5a4 4 0 0 0 .4-8 6 6 0 0 0-11.4 1.7A3.2 3.2 0 0 0 7 15Z" />
      <path d="m8 18-1 2.5M12 18l-1 2.5M16 18l-1 2.5" />
    </svg>
  );
}

export function BookIcon({ size = 14 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15Z" />
      <path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5" />
    </svg>
  );
}

export function BoltIcon({ size = 14 }: IconProps) {
  return (
    <svg {...base(size)} fill="currentColor" stroke="none">
      <path d="M13.5 2 4 13.5h6.5L9.5 22 20 9.5h-6.5L13.5 2Z" />
    </svg>
  );
}

export function ThermoIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M10 4a2 2 0 1 1 4 0v10.3a4 4 0 1 1-4 0V4Z" />
      <path d="M12 9v7" />
    </svg>
  );
}

export function ChipIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <rect x="6" y="6" width="12" height="12" rx="1.5" />
      <rect x="9.5" y="9.5" width="5" height="5" />
      <path d="M9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5" />
    </svg>
  );
}

export function MemoryIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <rect x="3" y="6" width="18" height="11" rx="1.5" />
      <path d="M7 10v3M10.5 10v3M14 10v3M17.5 10v3M6 17v2.5M18 17v2.5" />
    </svg>
  );
}

export function SignalIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M4 18h2M9 18v-4M14 18v-8M19 18V6" />
    </svg>
  );
}
