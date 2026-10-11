import { useRef, type CSSProperties, type KeyboardEvent, type MouseEvent, type ReactNode } from "react";

import { Chamfer } from "./Chamfer";

interface Props {
  children: ReactNode;
  className?: string;
  /**
   * "glass": chamfered glass card.
   * "bracket": no background, only HUD bracket lines.
   * "slot": sits on a frame already drawn in the background picture (lights up on hover, no tilt).
   */
  variant?: "glass" | "bracket" | "slot";
  /** Cut corners for the glass variant, e.g. "tr bl br". */
  corners?: string;
  /** Order in the boot animation (0, 1, 2...). */
  delay?: number;
  /** Makes the whole card clickable. */
  onClick?: () => void;
  /** Tooltip / accessible label for clickable cards. */
  label?: string;
  style?: CSSProperties;
}

/**
 * HUD card: tilts towards the mouse, a light follows the cursor,
 * and it can be clicked (mouse or keyboard).
 */
export function HudPanel({
  children,
  className = "",
  variant = "glass",
  corners = "tr bl br",
  delay = 0,
  onClick,
  label,
  style,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const fullStyle = { ...style, "--delay": `${0.2 + delay * 0.12}s` } as CSSProperties;
  const tilt = variant !== "slot";

  const handleMove = (event: MouseEvent<HTMLDivElement>) => {
    const element = ref.current;
    if (!element) return;

    const box = element.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width;
    const y = (event.clientY - box.top) / box.height;

    element.style.setProperty("--mx", `${x * 100}%`);
    element.style.setProperty("--my", `${y * 100}%`);
    if (tilt) {
      element.style.setProperty("--rx", `${(0.5 - y) * 8}deg`);
      element.style.setProperty("--ry", `${(x - 0.5) * 10}deg`);
    }
  };

  const handleLeave = () => {
    ref.current?.style.setProperty("--rx", "0deg");
    ref.current?.style.setProperty("--ry", "0deg");
  };

  const handleKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (onClick && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <div
      ref={ref}
      className={`hud-panel ${variant} ${onClick ? "clickable" : ""} ${className}`}
      style={fullStyle}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      onClick={onClick}
      onKeyDown={handleKey}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      title={label}
      aria-label={label}
    >
      {variant !== "bracket" ? (
        <Chamfer corners={variant === "slot" ? "tl tr br bl" : corners} cut={variant === "slot" ? 14 : 18}>
          <span className="hud-cursor-light" />
          {children}
        </Chamfer>
      ) : (
        <>
          <span className="bracket top" />
          <span className="bracket side" />
          <span className="bracket bottom" />
          <span className="hud-cursor-light" />
          {children}
        </>
      )}
    </div>
  );
}
