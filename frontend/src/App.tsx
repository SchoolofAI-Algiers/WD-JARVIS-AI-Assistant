import { useState } from "react";
import { sendMessage } from "./services/api/chat";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!message.trim() || loading) return;

    setLoading(true);

    try {
      const data = await sendMessage({
        conversation_id: "test-123",
        message,
      });

      setResponse(data.message);
      setMessage("");
    } catch (error) {
      console.error(error);
      setResponse("Unable to connect to JARVIS.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <h1>J.A.R.V.I.S.</h1>

      <input
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            handleSend();
          }
        }}
        placeholder="Ask JARVIS..."
      />

      <button onClick={handleSend} disabled={loading}>
        {loading ? "Thinking..." : "Send"}
      </button>

      {response && <p>{response}</p>}
    </main>
  );
}

export default App;