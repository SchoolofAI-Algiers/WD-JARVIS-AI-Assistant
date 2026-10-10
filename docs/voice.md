# J.A.R.V.I.S. voice integration

## 1. What it does

Lets the user talk to J.A.R.V.I.S. and hear the answer: **record → transcribe → Assistant Core → reply → speak**.
It adds a voice layer around the existing assistant; it contains no assistant logic. Text and voice share one
conversation history. Supported languages: English, French, Arabic.

## 2. Architecture

```
 Browser (React)                                Backend (FastAPI)
 ───────────────                                ─────────────────
 🎙 click → MediaRecorder
 ■ click → POST /api/v1/voice/turn ──────────▶ routes/voice.py → VoicePipeline (app/voice/pipeline.py)
            audio + conversation_id               1. validate audio (size)
                                                  2. STT   faster-whisper            → transcript
                                                  3. assistant.process(conversation_id, message)
                                                         ↑ the same call POST /chat makes
                                                  4. TTS   Edge → Piper → pyttsx3    (first that works)
 plays reply (<audio>, base64 data: URL) ◀──────  JSON: transcript, reply_text, metadata, speech

 typed message → POST /api/v1/chat (unchanged) → then POST /api/v1/voice/speak to voice the reply
```

| Piece | File |
|---|---|
| Endpoints | `app/api/routes/voice.py` |
| Orchestration, error handling | `app/voice/pipeline.py` |
| Speech-to-text | `app/voice/stt.py` (faster-whisper) |
| Text-to-speech chain | `app/voice/tts.py` |
| Assistant bridge | `AssistantCoreAdapter` → `app.core.assistant.assistant.process` |
| Language guess (en/fr/ar) | `app/core/language.py` |
| Frontend | `src/services/api/voice.ts`, `src/hooks/useVoiceTurn.ts`, `App.tsx` |

**Conversation id.** The frontend creates one id at load and sends it with every `/chat` and `/voice/turn`
request, so memory is shared; **New conversation** creates a new random id and discards late voice replies.

## 3. Setup

```bash
cd backend
pip install -r requirements.txt     # faster-whisper, edge-tts, pyttsx3, piper-tts, av, python-multipart
python -m piper.download_voices en_GB-alan-medium fr_FR-tom-medium ar_JO-kareem-medium --download-dir voices
uvicorn app.main:app --reload --port 8000 --env-file .env

cd ../frontend && npm install && npm run dev      # http://localhost:5173 
```

* Piper voice files are **not committed** (large, per-voice licenses); `backend/voices/` is git-ignored.
* Whisper downloads its model on first use. The microphone needs a secure context (`localhost` qualifies).


* Make sure to download Windows offline voices for all three languages in case of going offline.
* `.env` is not read by the voice layer itself: start uvicorn with `--env-file .env` and restart after edits.

### Configuration (`backend/.env`, all optional)

| Variable | Default | Meaning |
|---|---|---|
| `VOICE_TTS_PROVIDERS` | `edge,pyttsx3` | speech engine order; recommended `edge,piper,pyttsx3` |
| `VOICE_TTS_PROVIDER_TIMEOUT_S` / `VOICE_TTS_TIMEOUT_S` | `8` / `20` | per engine / whole TTS step (use `30` / `40` with Piper) |
| `VOICE_PIPER_DIR` | `backend/voices` | Piper voice files |
| `VOICE_STT_MODEL_SIZE` | `base` | Whisper size (`tiny`…`medium`) |
| `VOICE_STT_LANGUAGE` | auto | force the STT language |
| `VOICE_STT_MIN_CONFIDENCE` | `0.40` | below this → `low_confidence` |
| `VOICE_MIN_AUDIO_BYTES` / `VOICE_MAX_AUDIO_BYTES` | 1 000 / 10 MiB | audio size limits |
| `VOICE_ASSISTANT_TIMEOUT_S` | `30` | Assistant Core timeout |

## 4. Endpoints (base `http://localhost:8000/api/v1`)

| Endpoint | Purpose |
|---|---|
| `POST /chat` | existing text chat: `{conversation_id, message}` → `{message, metadata, …}` |
| `POST /voice/turn` | one spoken turn. `multipart/form-data`: `audio` (required), `conversation_id`, `language` (force STT language), `speak` (default `true`) |
| `POST /voice/speak` | speak given text only: `{text, language?, conversation_id?}`; does not call the core or touch memory |
| `GET /voice/health` | STT/TTS availability and whether the Whisper model is loaded |

`/voice/turn` and `/voice/speak` return a `VoiceTurnResult`:

```jsonc
{ "ok": true, "conversation_id": "…",
  "transcript": { "text": "…", "language": "en", "confidence": 0.62, "provider": "faster-whisper" },
  "reply_text": "…", "metadata": { },                       // metadata identical to /chat
  "speech": { "audio": "<base64>", "mime_type": "audio/wav", "provider": "piper", "voice": "en_GB-alan-medium" },
  "degraded": false, "needs_retry": false, "error": null, "timings_ms": { "total_ms": 0 } }
```

Failures are **HTTP 200 with `ok: false`** and an `error.code` (`empty_audio`, `audio_too_large`, `audio_unreadable`,
`no_speech`, `low_confidence`, `stt_unavailable`/`stt_timeout`, `assistant_unavailable`/`assistant_timeout`,
`tts_unavailable`/`tts_timeout`, `internal_error`). `degraded: true` = the text reply is valid but no audio could be
produced. A failed turn is not written to memory. A missing `audio` part is a standard `422`.

## 5. Audio formats

* **Input:** whatever PyAV/FFmpeg can decode. The browser records the first supported of `audio/webm;codecs=opus`,
  `webm`, `ogg;codecs=opus`, `mp4` (Chrome/Edge/Firefox → WebM/Ogg, Safari → MP4). Size: 1 000 B – 10 MiB.
* **Output:** Edge → `audio/mpeg` (MP3); Piper and pyttsx3 → `audio/wav`. Always standard base64 in `speech.audio`,
  played as `data:<mime_type>;base64,<audio>`. Replies are shortened for speech (default 600 characters); the full
  text is in `reply_text`.

## 6. Speech engines (the male J.A.R.V.I.S. voice)

| Engine | Needs | Voices |
|---|---|---|
| `edge` | internet | `en-GB-RyanNeural`, `fr-FR-HenriNeural`, `ar-DZ-IsmaelNeural` — best quality |
| `piper` | `piper-tts` + voice files, offline | `en_GB-alan`, `fr_FR-tom` (or `fr_FR-gilles-low`), `ar_JO-kareem` |
| `pyttsx3` | nothing (OS voices) | installed Windows voice for the language, male preferred (David); no Arabic or French voice → no audio |

The first engine that works wins; a failing engine is skipped for 30 s. `speech.provider`/`speech.voice` show which one
spoke. Piper models are preloaded in the background at server start.

## 7. How the frontend uses it

* `useVoiceTurn`: click 🎙 to record, click ■ to send → `sendVoiceTurn(blob, conversationId)`. Status labels:
  `listening → thinking → speaking → idle`. The microphone is released after each recording.
* The transcript becomes the user bubble and `reply_text` the assistant bubble; `speech` is played with `<audio>`.
  Speaking or typing again interrupts playback, so two replies never overlap.
* A typed message goes through `/chat`, then `speakText(reply, conversationId)` → `/voice/speak`.
* Errors (`ok:false`, mic refused, unsupported browser, server unreachable) appear as assistant notices in the chat.
* The API URL is hard-coded to `http://localhost:8000/api/v1`.

## 8. Tests and diagnostics (run from `backend/`)

```bash
python -m pytest tests/voice -v              # no models, network or microphone needed
python tests/voice/diagnose_tts.py   # which engine really speaks en/fr/ar (reads backend/.env)
python tests/voice/diagnose_piper.py        # Piper load/speak timings + sample .wav files
```

## 9. Limitations and assumptions

* **Languages:** only `en`, `fr`, `ar` have voices and detection; other languages are spoken by the English voice.
* **Reply text** comes from the Assistant Core, which is still a placeholder: it only localizes the prefix
  (`JARVIS received:` / `JARVIS a reçu :` / `استلم جارفيس:`). Replies become fully multilingual once `LLMService`
  is wired into the core.
* **Edge TTS** uses an unofficial Microsoft endpoint and may be refused on some networks (`403`); Piper is the
  reliable fallback. Piper voices are less natural than Edge's, and Arabic/French quality should be checked by ear.
* **Memory** is an in-process dict: lost on restart, not shared across workers.
* Typed-text language guess is a word/accent heuristic and can be wrong for very short text.
* Real Whisper, microphone and browser audio are not covered by the automated tests (fakes and mocks are used).
* Whisper loads on the first utterance after a server start (not preloaded).