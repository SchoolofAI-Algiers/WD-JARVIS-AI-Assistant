import type { CSSProperties } from "react";

/*
 * The background picture (1824 x 862) is drawn like CSS "cover": it fills the
 * whole screen and is scaled by --s. Elements that must stay on a spot of the
 * picture (the core, the platform, the chat panel) are placed in picture pixels
 * with scene(); they move and scale with the picture on every screen size.
 *
 * Everything else (sidebar, side panels, input) is anchored to the screen edges
 * in CSS and sized with --u.
 */
export const s = (n: number) => `calc(var(--s) * ${n})`;

export function scene(x: number, y: number, width?: number, height?: number): CSSProperties {
  return {
    left: s(x),
    top: s(y),
    width: width !== undefined ? s(width) : undefined,
    height: height !== undefined ? s(height) : undefined,
  };
}
