# Tools

## What the tools do

The tools component handles rule-detected productivity requests without asking the language model to interpret or perform them. It includes reminders, notes, schedule events, workspace actions, arithmetic, UTC date/time, and current weather. Tool results are converted into user-facing text and returned with metadata identifying the result type and, for tool turns, the tool name.

## Flow and conversation context

```text
POST /api/v1/chat
  -> chat route
  -> Assistant.process
       -> ToolRouter.detect_tool
       -> matching: ToolRouter.execute -> tool -> format response
       -> no match: ContextBuilder.build -> Assistant._generate_response
  -> save user and assistant text in conversation memory
  -> ChatResponse JSON
```

The route is `backend/app/api/routes/chat.py`; the assistant is in `backend/app/core/assistant.py`; routing and parsing are in `backend/app/tools/router.py`. Tool classes are in `backend/app/tools/`. The chat endpoint currently uses `Assistant._generate_response`, a lightweight local response implementation; the tool branch happens before this generation path. Non-tool turns pass bounded context to it.

`ConversationMemory` in `backend/app/memory/conversation.py` stores an in-process list of `ChatMessage` objects per `conversation_id`. Each conversation retains the latest 20 messages. `ContextBuilder` in `backend/app/memory/context.py` adds the current user message if it is not already the last history item, then keeps at most 20 messages including that current message. Different IDs have separate histories; this memory is not durable across process restarts. Tool turns are also saved as a user message and the formatted assistant response, so later non-tool context can include them.

## Tools and behavior

All SQLite-backed tools share `backend/app/tools/storage.py`. Tool methods return dictionaries or lists internally; the assistant normally turns them into plain text for the chat API.

| Tool | Example phrases and purpose | Return and validation |
| --- | --- | --- |
| Reminders | `Remind me tomorrow at 6 PM to call home`; `Show pending reminders`; `Complete reminder #1` | Create returns `{id, text, due_at, completed}`; list returns pending rows; completion returns a boolean. Empty text is rejected. Optional due times must be local ISO date/time without a timezone. Router parsing recognizes today/tomorrow and `at H[:MM] [am/pm]`; omitted times create undated reminders. |
| Notes | `Take a note: test`; `Show my notes`; `Search my notes about project` | Create returns `{id, text}`; list/search return rows including `created_at`. Empty note and empty search text raise `ValueError`. Search uses SQLite `LIKE`. |
| Schedule | `Add a meeting tomorrow at 3 PM`; `What do I have tomorrow?` | Create returns `{id, title, starts_at}`; list returns event rows for a date. Creation requires a parseable time and non-empty title. Dates support today/tomorrow or `YYYY-MM-DD` (default today); times accept 12-hour or 24-hour forms. Stored times are local and have no timezone offset. |
| Workspace | `Open VS Code`; `Open the project folder`; `Open https://example.com` | Internal result is an action dictionary (`application`, `workspace`, or `url`); assistant formats it as text. Application allowlist: `notepad`, `vs code`, `chrome`. Applications and folder opening are Windows-only. Folder paths are resolved relative to the configured project workspace and must remain inside it and point to an existing directory. URLs must be HTTP(S), include a hostname, contain no username/password or whitespace, and use a valid optional port. Successful actions launch the application/folder/browser, so they were not invoked during verification. |
| Calculator | `Calculate 2 + 2`; `What is 12 divided by 3?` | Internal result contains expression and numeric result; assistant returns `expression = result`. Arithmetic is evaluated from a restricted AST supporting numeric constants, `+ - * / % **`, and unary signs; unsupported nodes/operators and invalid expressions raise calculator errors. |
| Date/time | `What time is it?`; `What's today's date?` | Internal result is `{iso, date, time}` in UTC; assistant returns the UTC date and time. |
| Weather | `Weather in Algiers`; `What's the weather in Oran?` | Internal result includes city, country, temperature, humidity, weather code, wind speed, and timezone; assistant formats a summary. City lookup and forecast use Open-Meteo via `requests`. Missing locations and service/data failures raise `WeatherError`. A city not extracted from a recognized prefix defaults to Algiers. |

The router uses ordered keyword and regular-expression checks: reminders, notes, schedule, workspace, calculator, date/time, then weather. A message that matches multiple categories takes the first match. Detection is rule-based, so phrase collisions and unsupported phrasings are possible. Reminder and schedule date/time parsing uses the host's local date/time assumptions; displayed date/time tool output is UTC.

## Storage and setup

SQLite creates `reminders`, `notes`, and `events` tables on connection. Set `JARVIS_TOOLS_DB` to choose a database file; otherwise the path is `backend/data/assistant_tools.sqlite3`. Its parent directory is created automatically. Tests set this variable to a temporary database. Tools use Python's standard-library SQLite and other standard-library modules; weather additionally uses the already declared `requests` dependency. No separate tool framework is used.

From `backend/`, run the tools tests with:

```sh
python -m pytest tests/tools -q
```

The full backend suite command is `python -m pytest -q`; it also includes integration tests outside the tools area.

## Chat API examples

Requests go to `POST /api/v1/chat`, with JSON fields `conversation_id` and `message`. Every successful route response has `conversation_id`, `status`, `message`, and `metadata`. Errors caught by the assistant are represented in the response body with HTTP 200 and `status: "complete"`; they are not HTTP error responses.

Successful note tool request:

```json
{"conversation_id":"probe-note","message":"Take a note: integration probe"}
```

Response:

```json
{"conversation_id":"probe-note","status":"complete","message":"Note saved.","metadata":{"type":"tool","tool":"notes"}}
```

Tool validation error request:

```json
{"conversation_id":"probe-error","message":"Add a meeting tomorrow"}
```

Response:

```json
{"conversation_id":"probe-error","status":"complete","message":"I couldn't process that request: Please include an event time, such as 'at 3 PM'.","metadata":{"type":"error","tool":"schedule"}}
```

Normal non-tool request:

```json
{"conversation_id":"probe-normal","message":"Hello"}
```

Response:

```json
{"conversation_id":"probe-normal","status":"complete","message":"Hello. How can I assist you?","metadata":{"type":"mock"}}
```

These are actual responses captured through FastAPI `TestClient` with `JARVIS_TOOLS_DB` set to a temporary file. They match the backend assertions and the frontend type in `frontend/src/services/api/chat.ts`, which accepts a string `message` and `metadata` with a string `type` plus additional fields. Tool metadata uses `{type: "tool", tool: <name>}`; handled tool exceptions use `{type: "error", tool: <name>}`; non-tool responses use `{type: "mock"}`.

## Adding a tool

1. Add the tool implementation in a module under `backend/app/tools/`, following the existing class and module singleton pattern. Use `storage.connect()` for SQLite-backed data.
2. Import the tool in `backend/app/tools/router.py`, add an ordered intent check in `ToolRouter.detect_tool`, then add its execution branch in `ToolRouter.execute`.
3. Add user-facing result formatting for its result in `Assistant._format_tool_response` in `backend/app/core/assistant.py`. `Assistant.process` already routes detected tools before context/generation and supplies generic tool/error metadata.
4. Add focused tool and assistant/API tests under `backend/tests/tools/` (and core tests if assistant behavior needs coverage). Use a temporary `JARVIS_TOOLS_DB`; mock external calls and side effects.
5. Update this document to reflect the implemented phrases, result shape, validation, setup, and limitations.

## Limitations

- Intent detection is a fixed ordered ruleset, not model-based intent classification; overlapping keywords can route unexpectedly.
- Workspace application and folder launches only work on Windows. App launch depends on the allowlisted executable being available. URL opening launches a browser on successful use.
- Reminders and schedule entries are stored, but there is no background notification or reminder delivery service in these tools.
- Reminder and schedule parsing is deliberately narrow and supports only the formats described above; timezone conversion is not performed.
- Weather depends on the external Open-Meteo services and network availability.
- Conversation history is in process memory, while reminders, notes, and schedule rows persist in SQLite.
- The assistant currently catches exceptions from tool execution/formatting and returns a readable error body with HTTP 200. The API status remains `complete` for that case.
