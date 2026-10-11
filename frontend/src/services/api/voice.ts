// Mirrors app.voice.models.VoiceTurnResult (backend/app/voice/models.py) and the
// POST /api/v1/voice/turn route (backend/app/api/routes/voice.py).

export interface TranscriptionResult {
  text: string;
  language: string | null;
  confidence: number | null;
  duration_s: number | null;
  provider: string;
}

export interface SpeechResult {
  /** STANDARD base64 text (not base64url). */
  audio: string;
  mime_type: string;
  provider: string;
  voice: string | null;
  spoken_text: string;
  truncated: boolean;
}

export interface VoiceErrorInfo {
  code: string;
  /** Safe to show to the user. */
  message: string;
  retryable: boolean;
}

export interface VoiceTurnResponse {
  ok: boolean;
  conversation_id: string | null;
  transcript: TranscriptionResult | null;
  /** Assistant reply, or the friendly error message when ok is false. */
  reply_text: string;
  /** Same metadata the Assistant Core returns to /chat. */
  metadata: { type?: string; [key: string]: unknown };
  speech: SpeechResult | null;
  /** Reply is valid but spoken output is unavailable (text only). */
  degraded: boolean;
  needs_retry: boolean;
  error: VoiceErrorInfo | null;
  timings_ms: Record<string, number>;
}

const API_URL = "http://localhost:8000/api/v1";

export async function sendVoiceTurn(
  audio: Blob,
  conversationId: string
): Promise<VoiceTurnResponse> {
  const form = new FormData();
  // The backend only reads the part's content-type, but a filename is required
  // for multipart file fields.
  form.append("audio", audio, "utterance");
  form.append("conversation_id", conversationId);

  // No Content-Type header: the browser must add the multipart boundary itself.
  const response = await fetch(`${API_URL}/voice/turn`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Calls POST /voice/speak: it only synthesises speech and does not call the Assistant Core.
 * For Latin-script text the backend defaults to the English voice unless `language`
 * ("en" | "fr" | "ar") is given; Arabic script is detected automatically.
 */
export async function speakText(
  text: string,
  conversationId: string,
  language?: string
): Promise<VoiceTurnResponse> {
  const response = await fetch(`${API_URL}/voice/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      conversation_id: conversationId,
      ...(language ? { language } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}