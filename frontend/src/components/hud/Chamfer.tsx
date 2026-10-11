import type { CSSProperties, ReactNode } from "react";

import { useSize } from "../../utils/useSize";

type Corner = "tl" | "tr" | "br" | "bl";

interface Props {
  children?: ReactNode;
  className?: string;
  /** Size of the cut corners in px. */
  cut?: number;
  /** Which corners are cut, e.g. "tr bl". */
  corners?: string;
}

function outline(width: number, height: number, cut: number, corners: Set<Corner>) {
  const points: [number, number][] = [];

  if (corners.has("tl")) points.push([cut, 0]);
  else points.push([0, 0]);

  if (corners.has("tr")) points.push([width - cut, 0], [width, cut]);
  else points.push([width, 0]);

  if (corners.has("br")) points.push([width, height - cut], [width - cut, height]);
  else points.push([width, height]);

  if (corners.has("bl")) points.push([cut, height], [0, height - cut]);
  else points.push([0, height]);

  if (corners.has("tl")) points.push([0, cut]);

  return points;
}

/**
 * Glass box with cut ("chamfered") corners and a glowing outline,
 * like the HUD panels in the design.
 */
export function Chamfer({ children, className = "", cut = 16, corners = "tr bl" }: Props) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  const set = new Set(corners.split(" ") as Corner[]);
  const points = outline(width, height, cut, set);

  const clip = `polygon(${points.map(([x, y]) => `${x}px ${y}px`).join(", ")})`;

  // short bright segments on the cut corners
  const accents: [number, number, number, number][] = [];
  if (set.has("tl")) accents.push([0, cut, cut, 0]);
  if (set.has("tr")) accents.push([width - cut, 0, width, cut]);
  if (set.has("br")) accents.push([width, height - cut, width - cut, height]);
  if (set.has("bl")) accents.push([cut, height, 0, height - cut]);

  return (
    <div ref={ref} className={`chamfer ${className}`} style={{ "--cut": `${cut}px` } as CSSProperties}>
      {width > 0 && (
        <>
          <div className="chamfer-fill" style={{ clipPath: clip }} />
          <svg className="chamfer-line" width={width} height={height} aria-hidden="true">
            <polygon points={points.map((p) => p.join(",")).join(" ")} />
            {accents.map(([x1, y1, x2, y2], i) => (
              <line key={i} className="chamfer-accent" x1={x1} y1={y1} x2={x2} y2={y2} />
            ))}
          </svg>
        </>
      )}
      <div className="chamfer-content">{children}</div>
    </div>
  );
}
