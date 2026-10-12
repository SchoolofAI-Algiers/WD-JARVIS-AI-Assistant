# J.A.R.V.I.S. AI Assistant

**J.A.R.V.I.S.** is an AI assistant developed by the **School of AI Algiers (SOAI)**. The project brings together a web interface, a FastAPI backend, conversational AI components, SOAI knowledge retrieval, productivity tools, and voice interaction.

The goal is to provide a single assistant experience for asking questions, retrieving SOAI-related information, managing simple productivity tasks, and interacting by text or voice.

## Features

- **Text chat** through a React frontend and FastAPI API.
- **Voice conversations:** record speech in the browser, transcribe it with faster-whisper, pass the transcript to the assistant, and optionally play a spoken response.
- **Text-to-speech providers:** Edge TTS, Piper, and `pyttsx3`, tried in configured order.
- **Speech recognition:** faster-whisper, with English, French, and Arabic language support in the documented voice configuration.
- **Productivity tools:** reminders, notes, schedule events, calculator, date/time, weather, and selected workspace actions.
- **SOAI knowledge retrieval (RAG):** a documented pipeline for indexing SOAI documents and retrieving relevant passages using Weaviate and local embeddings.
- **LLM provider fallback:** the documented `LLMClient` tries Groq and Google Gemini providers in sequence.
- **Conversation context:** recent messages are kept in process memory; tool data such as notes, reminders, and events is stored in SQLite.
- **Automated tests** for backend components, tools, RAG, and voice behavior using test doubles where applicable.

## Architecture overview

```text
                         Browser (React / TypeScript)
                       ┌──────────────────────────────┐
                       │ Text chat                    │
                       │ Microphone recording          │
                       │ Voice playback                │
                       └──────────────┬───────────────┘
                                      │ HTTP
                                      ▼
                            FastAPI backend
                       ┌──────────────────────────────┐
                       │ /api/v1/chat                 │
                       │ /api/v1/voice/turn           │
                       │ /api/v1/voice/speak          │
                       │ /api/v1/voice/health         │
                       └──────────────┬───────────────┘
                                      ▼
                              Assistant Core
                       ┌──────────────┴───────────────┐
                       │ Tool routing                 │
                       │ Conversation context         │
                       │ LLM / knowledge components   │
                       └──────────────┬───────────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             ▼                        ▼                        ▼
       Productivity tools        LLM providers             SOAI RAG
       SQLite / Open-Meteo       Groq / Gemini             Weaviate
                                                            + embeddings

Voice turn:
Browser audio → faster-whisper → assistant → reply text → TTS → browser playback
```

### Main components

| Component | Responsibility |
|---|---|
| `backend/app/api/routes/` | HTTP API routes for chat and voice. |
| `backend/app/core/assistant.py` | Assistant orchestration, tool handling, and response metadata. |
| `backend/app/core/llm/service.py` | Conversation history and prompt construction for the LLM path. |
| `backend/app/core/llm/client.py` | Provider calls, response validation, and provider fallback. |
| `backend/app/core/llm/prompts.py` | System prompt and prompt formatting. |
| `backend/app/tools/` | Rule-based tool detection, execution, and tool storage. |
| `backend/app/memory/` | In-process conversation memory and context construction. |
| `backend/app/rag/` | SOAI document ingestion, embeddings, vector storage, and retrieval. |
| `backend/app/voice/` | Voice pipeline, speech-to-text, text-to-speech, and assistant adapter. |
| `frontend/src/` | React UI, API clients, voice hook, and interface components. |

## Technology stack

- **Backend:** Python, FastAPI, Uvicorn
- **Frontend:** React, TypeScript, Vite
- **LLM providers:** Groq and Google Gemini (as documented in the LLM client)
- **Speech-to-text:** faster-whisper
- **Text-to-speech:** Edge TTS, Piper, `pyttsx3`
- **Knowledge retrieval:** Weaviate Cloud and EmbeddingGemma
- **Tool persistence:** SQLite
- **Weather data:** Open-Meteo

## Requirements

Install the following before running the application:

- Python and pip
- Node.js and npm
- Git
- API credentials for at least one configured LLM provider, if using that provider-backed generation path
- A Weaviate Cloud cluster and Hugging Face token if enabling SOAI RAG
- Microphone permission in the browser for voice input

Some voice and RAG dependencies download models on first use. Allow sufficient disk space and time for these downloads. Piper voice files are not committed to the repository.

## Getting started

The commands below assume a local development environment and the repository layout shown in the team documentation.

### 1. Configure the backend

From the repository root, create and activate a virtual environment.

**Windows PowerShell:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Configure environment variables

Create `backend/.env` and add only the credentials and settings for the components you intend to use. Do not commit this file or share real API keys.

Example LLM configuration:

```dotenv
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

`GOOGLE_API_KEY` may be used instead of `GEMINI_API_KEY`, according to the LLM client documentation. One valid provider key may be enough for a response; configuring both enables the documented fallback chain.

For RAG, configure the Weaviate endpoint and key, and the Hugging Face token required to download EmbeddingGemma:

```dotenv
WEAVIATE_URL=your_weaviate_rest_endpoint
WEAVIATE_API_KEY=your_weaviate_api_key
HF_TOKEN=your_hugging_face_read_token
RAG_MIN_SIMILARITY=0.34
```

Voice settings are optional. The documented defaults and examples include:

| Variable | Documented default | Purpose |
|---|---:|---|
| `VOICE_TTS_PROVIDERS` | `edge,pyttsx3` | TTS provider order. The voice notes recommend `edge,piper,pyttsx3` when Piper is installed. |
| `VOICE_TTS_PROVIDER_TIMEOUT_S` | `8` | Per-provider timeout. |
| `VOICE_TTS_TIMEOUT_S` | `20` | Overall TTS timeout. |
| `VOICE_PIPER_DIR` | `backend/voices` | Directory containing Piper voice files. |
| `VOICE_STT_MODEL_SIZE` | `base` | faster-whisper model size. |
| `VOICE_STT_LANGUAGE` | automatic | Optionally force the transcription language. |
| `VOICE_STT_MIN_CONFIDENCE` | `0.40` | Minimum confidence threshold. |
| `VOICE_MIN_AUDIO_BYTES` | `1000` | Minimum accepted audio size. |
| `VOICE_MAX_AUDIO_BYTES` | `10 MiB` | Maximum accepted audio size. |
| `VOICE_ASSISTANT_TIMEOUT_S` | `30` | Assistant call timeout for a voice turn. |
| `RAG_TOP_K` | `3` | Maximum retrieved chunks passed to the LLM. |
| `RAG_MIN_SIMILARITY` | `0.34` | Minimum retrieval similarity threshold. |
| `RAG_ALPHA` | `0.5` | Hybrid search balance: `0` keyword-focused, `1` meaning-focused. |
| `RAG_COLLECTION` | `SoaiChunk` | Weaviate collection name. |
| `JARVIS_TOOLS_DB` | `backend/data/assistant_tools.sqlite3` | Optional SQLite database path for tools. |

The voice documentation notes that Uvicorn should be started with `--env-file .env` when relying on that file:

```bash
uvicorn app.main:app --reload --port 8000 --env-file .env
```

Restart the backend after changing environment variables.

### 3. Start the backend

From the `backend/` directory, with the virtual environment activated:

```bash
uvicorn app.main:app --reload --port 8000 --env-file .env
```

The API should be available at `http://localhost:8000`. The health endpoint is:

```text
GET http://localhost:8000/health
```

FastAPI's interactive API documentation is normally available at `http://localhost:8000/docs`.

### 4. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (the team documentation uses `http://localhost:5173`).

The frontend's voice API client is documented as using `http://localhost:8000/api/v1`. If your backend runs at another address or port, update the API URL in the frontend configuration/code.

## Chat and API

The API base path is:

```text
http://localhost:8000/api/v1
```

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/chat` | Send a typed message to the assistant. |
| `POST` | `/voice/turn` | Submit recorded audio for transcription, assistant processing, and optional speech generation. |
| `POST` | `/voice/speak` | Generate spoken audio from supplied text without running the assistant core. |
| `GET` | `/voice/health` | Check voice subsystem availability and Whisper model state. |

### Text chat example

Request:

```json
{
  "conversation_id": "demo",
  "message": "Hello"
}
```

Example request using `curl`:

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"demo","message":"Hello"}'
```

The documented chat response contains `conversation_id`, `status`, `message`, and `metadata`. Metadata may identify a tool response, an LLM/RAG response, or another response path, depending on the active implementation.

### Voice interaction

`POST /voice/turn` accepts `multipart/form-data` with:

- `audio` — recorded audio (required)
- `conversation_id` — conversation identifier
- `language` — optional forced transcription language
- `speak` — whether to generate spoken output (defaults to `true` in the voice documentation)

The response includes fields such as:

- `ok` — whether the turn succeeded
- `transcript` — recognized text and transcription metadata
- `reply_text` — assistant response text
- `metadata` — response metadata
- `speech` — generated audio metadata and base64 audio, when available
- `degraded` — indicates that text succeeded but speech output was unavailable
- `error` — structured error details, when applicable
- `timings_ms` — timing information

The frontend records audio using the browser's `MediaRecorder`, sends it to the backend, displays the transcript and reply, and plays generated speech when available. The browser must grant microphone permission. `localhost` is considered a secure context by modern browsers.

## Voice engines

The documented voice pipeline uses the first working configured TTS provider.

| Provider | Network | Notes |
|---|---|---|
| Edge TTS | Requires internet | Uses neural voices, including documented English, French, and Algerian Arabic voices. Network restrictions may cause failures. |
| Piper | Offline after setup | Requires the Piper package and downloaded voice files. |
| `pyttsx3` | Local OS voices | Uses installed system voices; language availability depends on the operating system. |

The voice documentation lists example Piper voice downloads:

```bash
python -m piper.download_voices \
  en_GB-alan-medium \
  fr_FR-tom-medium \
  ar_JO-kareem-medium \
  --download-dir voices
```

Run the command from the backend environment, and check the current Piper package documentation if its CLI differs by installed version. Voice model files are large and are not committed to the repository.

The documented browser recording formats include WebM/Opus, Ogg/Opus, or MP4 depending on browser support. The backend uses PyAV/FFmpeg decoding. Generated audio is returned as standard base64 with a MIME type; Edge output is documented as MP3, while Piper and `pyttsx3` output is documented as WAV.

## Productivity tools

The tool router uses ordered keyword and regular-expression checks. The documented tools include:

| Tool | Example request | Notes |
|---|---|---|
| Reminders | `Remind me tomorrow at 6 PM to call home` | Creates and lists reminders and can mark them complete. There is no background notification/delivery service documented. |
| Notes | `Take a note: review the project` | Saves, lists, and searches notes. Search uses SQLite `LIKE`. |
| Schedule | `Add a meeting tomorrow at 3 PM` | Creates and lists events; creation requires a parseable time. |
| Workspace | `Open VS Code` | Allowlisted applications and folders are Windows-only. URL opening supports validated HTTP(S) URLs. |
| Calculator | `Calculate 12 divided by 3` | Evaluates a restricted set of arithmetic operations. |
| Date/time | `What's today's date?` | The tool reports UTC date and time. |
| Weather | `Weather in Algiers` | Uses Open-Meteo; requires network access. An unrecognized city may default to Algiers. |

Tool detection is rule-based, not model-based intent classification. The router checks categories in a fixed order, so overlapping keywords or unsupported phrasing may produce unexpected routing.

Tool records are stored in SQLite. By default, the documented database path is `backend/data/assistant_tools.sqlite3`; set `JARVIS_TOOLS_DB` to choose another location. The database's parent directory is created automatically.

## SOAI knowledge base (RAG)

The documented RAG component indexes approved SOAI Markdown documents and retrieves relevant passages to provide grounded answers about the organization, its events, departments, projects, and FAQs.

### Retrieval pipeline

1. Markdown files in `knowledge/processed/` are split into chunks, generally one `##` section per chunk.
2. EmbeddingGemma generates embeddings locally.
3. Chunks are stored in a Weaviate Cloud collection named `SoaiChunk` by default.
4. A question is searched using hybrid retrieval (keyword and semantic search).
5. The best matching chunks above the similarity threshold are formatted into context for the LLM.
6. Response metadata can include sources when retrieved knowledge is used.

The documented defaults are `RAG_TOP_K=3`, `RAG_MIN_SIMILARITY=0.34`, and `RAG_ALPHA=0.5`.

### Knowledge base layout

```text
knowledge/
├── README.md
├── raw/                 # Original source material; not indexed
└── processed/           # Approved Markdown files that are indexed
    ├── _TEMPLATE.md
    ├── soai_overview.md
    ├── soai_activities.md
    ├── soai_projects.md
    └── soai_faq.md
```

Each processed document should have front matter such as:

```yaml
---
title: SOAI Algiers Frequently Asked Questions
source: School of AI Algiers
category: faq
lang: en
---
```

Each `##` heading becomes a chunk with a generated ID. Sections over 300 words are split into parts. Files beginning with `_` are ignored by ingestion.

### Configure and ingest

Create a Weaviate Cloud cluster and set `WEAVIATE_URL` and `WEAVIATE_API_KEY` in `backend/.env`. Accept the EmbeddingGemma model terms on Hugging Face and create a read token for `HF_TOKEN`. The model download is approximately 1 GB according to the team documentation.

From `backend/`:

```bash
python -m app.rag.ingest
```

Run ingestion again after editing processed knowledge files. The documented ingestion process updates changed chunks and removes deleted ones. Use a full reset only when needed, such as after changing the embedding model.

**Integration note:** The supplied team documents disagree about whether the normal chat path currently invokes the RAG retriever and `LLMService` or uses a lightweight local/mock response path. The RAG and LLM components are documented here, but confirm the current `Assistant.process` implementation before assuming retrieval is active in a deployment.

## Conversation memory and persistence

- Conversation history is stored in process memory and retains up to the latest 20 messages per conversation.
- Different `conversation_id` values maintain separate histories.
- In-process conversation history is lost when the backend restarts and is not shared between multiple workers.
- Reminders, notes, and schedule entries are persisted in SQLite.
- The voice layer uses the same conversation ID as text chat so both interaction modes can share history when they use the same assistant/memory instance.
- A failed voice turn is documented as not being written to conversation memory.

## Testing

Run commands from `backend/` with the virtual environment activated.

### Full backend suite

```bash
python -m pytest -q
```

### Tool tests

```bash
python -m pytest tests/tools -q
```

### Voice tests

```bash
python -m pytest tests/voice -v
```

The voice tests use mocks and do not require a real microphone, downloaded models, or live network access. Real browser audio, microphone permissions, and live Whisper behavior are not fully covered by automated tests.

### RAG tests and checks

```bash
python tests/rag/test_ingest.py
python tests/rag/test_embeddings.py
python tests/rag/test_retriever.py
python tests/rag/check_chat_rag.py
```

The chat/RAG check requires the server and configured test collection to be available. The team also documents `backend/tests/core/test_llm.py` as an interactive manual harness rather than a regular pytest test; run it directly only when valid provider credentials and network access are configured:

```bash
python tests/core/test_llm.py
```

## Troubleshooting

### The microphone button does not start recording

- Allow microphone access for the frontend in your browser.
- Use `localhost` or another secure context.
- Check browser support for `MediaRecorder`.
- Inspect the browser console for permission or recording errors.

### Voice input works but no audio reply plays

- Check `GET /api/v1/voice/health`.
- Confirm at least one configured TTS provider is available.
- For Edge TTS, check internet access and network restrictions.
- For Piper, confirm the model files exist in the configured voice directory.
- For `pyttsx3`, confirm the operating system has a suitable installed voice.

### LLM responses fail

- Confirm that at least one provider API key is set correctly.
- Check network access and provider availability.
- Never commit credentials to Git.

### SOAI answers lack organization-specific context

- Confirm the RAG environment variables and Weaviate cluster.
- Run ingestion after updating `knowledge/processed/`.
- Check that the query retrieves chunks above the configured similarity threshold.
- Verify that the active assistant chat path actually calls the retriever.

### Workspace tools do not open applications

The documented application and folder launch behavior is Windows-only. Applications must be included in the allowlist and available on the machine.

## Known limitations

- Conversation memory is temporary and process-local.
- Tool detection relies on ordered rules and can misclassify ambiguous phrasing.
- Reminder and schedule tools do not provide a background notification service.
- Workspace application and folder launches are Windows-only.
- Weather depends on Open-Meteo and network availability.
- Voice quality and language availability depend on installed engines and voice models.
- Edge TTS may be unavailable on some networks; offline Piper requires model downloads.
- Real microphone/browser audio and live Whisper behavior are not fully tested by the automated suite.
- The supplied internal documentation describes conflicting active paths for non-tool chat and RAG integration; confirm the code path before deploying or documenting production behavior.

## Security notes

- Keep `.env` files, API keys, Weaviate credentials, and Hugging Face tokens out of version control.
- Do not commit downloaded voice models or other large/private artifacts unless their licensing and repository policy allow it.
- Validate and review workspace actions before using the application in a sensitive environment.

## Contributing

1. Create a feature branch.
2. Make a focused change.
3. Add or update tests for the behavior.
4. Run the relevant backend tests and frontend build.
5. Update the README when setup steps, endpoints, tools, configuration, or limitations change.
6. Open a pull request with a clear summary and testing notes.
