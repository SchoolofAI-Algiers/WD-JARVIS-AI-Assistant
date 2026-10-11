export interface Ripple {
  id: number;
  x: number;
  y: number;
}

/** Holographic rings that appear where you click on the scene. */
export function Ripples({ ripples }: { ripples: Ripple[] }) {
  return (
    <div className="ripples" aria-hidden="true">
      {ripples.map((ripple) => (
        <span key={ripple.id} style={{ left: ripple.x, top: ripple.y }}>
          <i />
          <i />
        </span>
      ))}
    </div>
  );
}
