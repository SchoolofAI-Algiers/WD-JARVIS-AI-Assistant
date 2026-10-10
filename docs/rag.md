# RAG — SOAI knowledge

## What it does

The RAG lets JARVIS answer questions about SOAI (events, departments, projects, FAQ) from our own
documents instead of guessing. For each message, it looks for the most relevant parts of the
knowledge base and gives them to the LLM, which writes the answer. If nothing relevant is found, the
LLM answers normally without SOAI context.

## Architecture

Two parts:

**Ingestion** (run once, and again when the knowledge changes)

```
knowledge/processed/*.md
  -> split into chunks (one ## section = one chunk)
  -> each chunk turned into a vector with EmbeddingGemma (runs locally)
  -> stored in Weaviate Cloud (collection SoaiChunk)
```

**Retrieval** (every message that isn't a tool request)

```
question
  -> hybrid search in Weaviate (keywords + meaning)
  -> keep chunks with similarity >= 0.34, best 3
  -> chunks inserted in the LLM system prompt ({retrieved_context})
  -> LLM answer + sources in the response metadata
```

How it connects to the rest of JARVIS:

- `app/core/assistant.py`: if no tool matches, it calls `retrieve(message)`, then
  `llm_service.generate_response(..., retrieved_context=format_context(chunks))`.
- `app/core/llm/prompts.py`: `build_system_prompt()` puts the chunks in `SYSTEM_PROMPT`.
- The chat response (`POST /api/v1/chat`) has `metadata.type = "rag"` and `metadata.sources` when
  the knowledge base was used, `"llm"` when it wasn't.

Code is in `backend/app/rag/`:

| file | role |
|---|---|
| `config.py` | settings from `.env` |
| `ingest.py` | reads the markdown, makes the chunks, fills Weaviate |
| `embeddings.py` | loads EmbeddingGemma, makes the vectors |
| `vector_store.py` | everything that talks to Weaviate |
| `retriever.py` | `retrieve()`, `format_context()`, `get_sources()` |


## Knowledge base structure

```
knowledge/
├── README.md          writing rules
├── raw/               original material, not indexed
└── processed/         what gets indexed
    ├── _TEMPLATE.md        copy it for a new file (files starting with _ are ignored)
    ├── soai_overview.md    the club and its departments
    ├── soai_activities.md  events (Welcome Day, hAIck, AI Camp, AI Summit...)
    ├── soai_projects.md    research projects
    └── soai_faq.md         common questions, one ## per question
```

Each file starts with:

```yaml
---
title: SOAI Algiers Frequently Asked Questions   # required
source: School of AI Algiers                     # required, shown in the sources
category: faq
lang: en
---
```

Each `## heading` becomes one chunk, with an id like `soai_faq#what-is-haick`. Sections over 300
words are cut in parts.

## Setup

Dependencies are in `requirements.txt` (`sentence-transformers`, `weaviate-client`,
`python-dotenv`...).

In `backend/.env`:

```
WEAVIATE_URL=...
WEAVIATE_API_KEY=...
HF_TOKEN=...
RAG_MIN_SIMILARITY=0.34
```

- Weaviate: create a free cluster on https://console.weaviate.cloud
  (copy the REST endpoint and an admin API key). The code creates the collection.
- HF_TOKEN: accept the terms on https://huggingface.co/google/embeddinggemma-300m, then create a
  "Read" token in your Hugging Face settings. The model (~1 GB) downloads on first use.

Other settings (optional):

| variable | default | meaning |
|---|---|---|
| `RAG_TOP_K` | 3 | max chunks given to the LLM |
| `RAG_MIN_SIMILARITY` | 0.34 | below this, a chunk is ignored |
| `RAG_ALPHA` | 0.5 | 0 = keywords only, 1 = meaning only |
| `RAG_COLLECTION` | SoaiChunk | Weaviate collection name |

## Ingestion

From `backend/`:

```
python -m app.rag.ingest
```

It prints the chunks, computes the vectors and saves them. Running it again is safe: changed chunks
are updated, deleted ones are removed, nothing is duplicated. `--reset` rebuilds everything (only
needed if the embedding model changes).

## Updating the knowledge base

1. Edit a file in `knowledge/processed/` or copy `_TEMPLATE.md`. Only approved information.
2. One topic per `##`, each section understandable alone ("hAIck is..." not "It is..."), 100–300 words.
   Use the words people really ask with ("club", "join", "beginner").
3. `python -m app.rag.ingest`
4. Ask the question in the chat or run the checks below. No server restart needed.

## Tests

From `backend/`:

```
python tests/rag/test_ingest.py               # chunking, offline
python tests/rag/test_embeddings.py           # the model finds the right chunks (EN/FR/AR)
python tests/rag/test_retriever.py            # full retrieval on a test collection
python tests/rag/check_chat_rag.py            # server running: chat really uses the RAG 
```