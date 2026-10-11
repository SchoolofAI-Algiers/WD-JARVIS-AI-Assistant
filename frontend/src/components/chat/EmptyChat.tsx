import { scene } from "../../utils/place";

/** Title under the core of the background picture. */
export function EmptyChat() {
  return (
    <div className="empty-chat" style={scene(737, 470, 600)}>
      <h2 className="hero-title">J.A.R.V.I.S.</h2>
      <p className="hero-question">How can I assist you?</p>
      <span className="hero-hint">
        Ask me about SOAI, calculations, weather, dates, and more.
      </span>
    </div>
  );
}
