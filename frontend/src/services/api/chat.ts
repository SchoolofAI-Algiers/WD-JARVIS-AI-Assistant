export interface ChatRequest {
  conversation_id: string;
  message: string;
}

export interface ChatResponse {
  conversation_id: string;
  status: string;
  message: string;
  metadata: {
    type: string;
    [key: string]: unknown;
  };
}

const API_URL = "http://localhost:8000/api/v1";

export async function sendMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}