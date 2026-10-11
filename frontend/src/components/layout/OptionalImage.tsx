import { useState, type ReactNode } from "react";

interface Props {
  src: string;
  alt?: string;
  className?: string;
  /** Shown while the image loads, or instead of it if the file doesn't exist. */
  fallback: ReactNode;
}

export function OptionalImage({ src, alt = "", className = "", fallback }: Props) {
  const [state, setState] = useState<"loading" | "ok" | "missing">("loading");

  if (state === "missing") return <>{fallback}</>;

  return (
    <>
      {state === "loading" && fallback}
      <img
        src={src}
        alt={alt}
        className={className}
        style={state === "loading" ? { display: "none" } : undefined}
        onLoad={() => setState("ok")}
        onError={() => setState("missing")}
      />
    </>
  );
}
