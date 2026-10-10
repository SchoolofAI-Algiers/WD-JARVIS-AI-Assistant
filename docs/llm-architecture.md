# LLM architecture

J.A.R.V.I.S. separates assistant orchestration from LLM access:

- **Assistant** decides whether a request is a tool request or normal
  conversation.
- **LLMService** prepares conversation context and prompts.
- **LLMClient** calls providers, normalizes responses, and manages fallbacks.

## Request flow

```text
POST /api/v1/chat
        |
        v
Assistant.process(conversation_id, message)
        |
        +-- tool_router detects a tool
        |       `-- execute and format result (no LLM call)
        |
        `-- LLMService.generate_response(...)
                |
                +-- read conversation history
                +-- build system and user prompts
                `-- LLMClient.generate(...)
                        |
                        +-- Groq primary
                        +-- Gemini fallback
                        `-- Gemini fallback
```

The main files are:

| Component | Role |
| --- | --- |
| [`assistant.py`](../backend/app/core/assistant.py) | Routes tools or normal chat, stores messages, and returns metadata. |
| [`service.py`](../backend/app/core/llm/service.py) | Reads history, builds prompts, and calls the client. |
| [`client.py`](../backend/app/core/llm/client.py) | Calls providers in order and returns validated text. |
| [`prompts.py`](../backend/app/core/llm/prompts.py) | Defines assistant behavior and prompt formatting. |
| [`conversation.py`](../backend/app/memory/conversation.py) | Stores the latest 20 messages per conversation. |

The application creates shared `assistant` and `llm_service` instances. Both
`LLMService` and `LLMClient` accept injected dependencies, allowing tests to
use fake clients and isolated memory without making provider requests.

## Integration with the Assistant

[`POST /api/v1/chat`](../backend/app/api/routes/chat.py) validates the
conversation ID and message, then calls `Assistant.process`.

1. `Assistant` checks `tool_router` first. Supported tool requests are
   executed and formatted directly.
2. For other messages, `Assistant` calls
   `LLMService.generate_response`.
3. `LLMService` reads the conversation history, builds the prompts, and passes
   them to `LLMClient.generate`.
4. `LLMClient` returns the first successful, non-empty response.
5. `Assistant` stores the user message and response in memory.

The LLM path is text-only and non-streaming. Conversation memory is
process-local, capped at 20 messages, and cleared when the backend restarts.
The current message is included in the prompt before it is stored.

An LLM response uses metadata such as:

```json
{
  "conversation_id": "demo",
  "status": "complete",
  "message": "Hello. How can I help?",
  "metadata": { "type": "llm" }
}
```

If all providers fail, `LLMClient` raises `LLMError`; the Assistant returns an
error response with `metadata.type = "error"` and
`metadata.source = "llm"`. Tool responses use `metadata.type = "tool"`.

## LLMClient

`LLMClient` loads environment variables with `load_dotenv()`, creates provider
clients lazily, and supports either injected clients or API keys.

### Provider order

| Order | Client | Model | Required key |
| --- | --- | --- | --- |
| 1 | Groq | `openai/gpt-oss-120b` | `GROQ_API_KEY` |
| 2 | Google Gemini | `gemini-3.5-flash-lite` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| 3 | Google Gemini | `gemini-3.8-flash` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |

The `openai/` prefix is part of the model name exposed by Groq; the
implementation does not use an OpenAI client.

For each provider, `generate`:

1. rejects an empty prompt;
2. sends the system instruction and user prompt;
3. extracts text from the provider response;
4. rejects an empty response and tries the next provider.

When every provider fails, the raised `LLMError` includes the provider failure
details. `generate` defaults to `temperature=0.5` and
`max_output_tokens=4096`. Gemini responses are requested as plain text and
automatic function calling is disabled.

`generate_response` is a compatibility alias. It currently retains the older
defaults (`temperature=0.7`, `max_output_tokens=1024`) before delegating to
`generate`; normal application calls use `generate` through `LLMService`.

## Prompt architecture

`LLMService` builds two prompts:

- **System prompt:** defines J.A.R.V.I.S.'s identity, supported languages,
  response style, safety rules, and SOAI grounding rules. It also injects the
  local date/time, voice-mode status, retrieved context, and formatted history.
- **User prompt:** wraps previous messages and the current message in
  `<conversation_context>` and `<current_user_message>` sections.

The prompt template has a `{retrieved_context}` placeholder. The current
`LLMService` does not call the RAG retriever, so normal chat receives no
retrieved SOAI context unless that integration is added. RAG code and settings
are under [`backend/app/rag`](../backend/app/rag).

## Configuration and setup

### 1. Install dependencies

From the repository root in PowerShell:

```powershell
cd .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The LLM packages are already declared in
[`requirements.txt`](../backend/requirements.txt).

### 2. Configure provider keys

Create `backend/.env` from [`.env.example`](../.env.example) and set one or
both providers:

```dotenv
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

Use `GOOGLE_API_KEY` instead of `GEMINI_API_KEY` if preferred. One valid key
is enough to generate responses; both keys enable the complete fallback chain.
Never commit real credentials.

### 3. Start the API

From the `backend` directory with the virtual environment active:

```powershell
uvicorn app.main:app --reload
```

Endpoints:

- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/api/v1/chat`

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{\"conversation_id\":\"demo\",\"message\":\"Hello\"}'
```

## Testing


[`tests/core/test_llm.py`](../backend/tests/core/test_llm.py) is an interactive
manual harness rather than a normal pytest test. To test live provider
connectivity, run it directly:

```powershell
python tests/core/test_llm.py
```

That command requires valid API credentials and network access. Use `/clear`
to reset its conversation and `/exit` to stop.


