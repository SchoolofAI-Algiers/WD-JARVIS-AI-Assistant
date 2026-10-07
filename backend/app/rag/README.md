# RAG (SOAI knowledge)

This part lets JARVIS answer questions about SOAI using our own documents instead of guessing.
It finds the parts of the knowledge base that match a question and gives them to the LLM.

How it works, quickly:

1. The markdown files in `knowledge/processed/` are split into small pieces (one `##` section = one piece).
2. Each piece is turned into a vector with EmbeddingGemma (runs locally).
3. The pieces are stored in Weaviate Cloud.
4. When a question comes in, we search Weaviate and return the closest pieces, or nothing if nothing is close enough.

## Setup

Install the requirements:

```
pip install -r requirements.txt
```

Then add these to `backend/.env`:

```
WEAVIATE_URL=...
WEAVIATE_API_KEY=...
HF_TOKEN=...
RAG_MIN_SIMILARITY=0.34
```


For `HF_TOKEN`: create a Hugging Face account, accept the terms on
https://huggingface.co/google/embeddinggemma-300m, then create a "Read" token in
https://huggingface.co/settings/tokens.

The first run downloads the model (around 1 GB), so it takes a bit.

## Your own Weaviate cluster 

1. Go to https://console.weaviate.cloud and create an account.
2. Create a new cluster on the free plan.
3. Open the cluster and copy its REST endpoint URL into `WEAVIATE_URL`.
4. In the same page, create an API key (admin, so we can write to it) and put it in `WEAVIATE_API_KEY`.
5. Fill it with the knowledge base (next section).

You don't need to create anything else, the code creates the collection by itself.
Note: the free plan only accepts the `hfresh` index type, the code already uses it.

## Filling the knowledge base

From `backend/`:

```
python -m app.rag.ingest
```

Run it again whenever a file in `knowledge/processed/` changes. It updates what changed and
removes what was deleted, no duplicates.

## Adding or editing knowledge

Read `knowledge/README.md`. Short version: one topic per `##` section, each section should make
sense on its own, and every file needs a `title` and `source` at the top.

## Tests

From `backend/`:

```
python tests/rag/test_ingest.py       # checks the splitting (no internet needed)
python tests/rag/test_embeddings.py   # checks the model finds the right pieces
python tests/rag/test_retriever.py    # full test with Weaviate, on a separate test collection
```

`test_retriever.py` also prints a suggested value for `RAG_MIN_SIMILARITY` if we add more
documents later.

## Settings you can change in .env

| variable | default | what it does |
|---|---|---|
| `RAG_TOP_K` | 3 | how many pieces are returned |
| `RAG_MIN_SIMILARITY` | 0.34 | below this, a piece is ignored |
| `RAG_ALPHA` | 0.5 | 0 = keyword search, 1 = meaning search |
| `RAG_COLLECTION` | SoaiChunk | Weaviate collection name |
