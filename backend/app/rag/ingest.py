"""Load knowledge/processed/*.md, split into chunks, embed, and index into Weaviate."""

from __future__ import annotations

import argparse
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.rag.models import Chunk

logger = logging.getLogger(__name__)

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
H2_RE = re.compile(r"^##\s+(.+?)\s*#*\s*$")
REQUIRED_FIELDS = ("title", "source")
MIN_WORDS_WARNING = 15


class KnowledgeFormatError(ValueError):
    pass


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", text).strip("-") or "section"


def word_count(text: str) -> int:
    return len(text.split())


def parse_markdown(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    m = FRONT_MATTER_RE.match(raw)
    if not m:
        raise KnowledgeFormatError(f"{path}: missing '---' front matter block at the top")
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        raise KnowledgeFormatError(f"{path}: front matter must be key: value pairs")
    missing = [f for f in REQUIRED_FIELDS if not str(meta.get(f, "")).strip()]
    if missing:
        raise KnowledgeFormatError(f"{path}: missing required front matter field(s): {', '.join(missing)}")
    return meta, raw[m.end():]


def _split_sections(body: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    in_code = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("# "):
            continue  
        m = None if in_code else H2_RE.match(line)
        if m:
            sections.append((m.group(1).strip(), []))
        else:
            sections[-1][1].append(line)
    return [(h, "\n".join(lines).strip()) for h, lines in sections
            if "\n".join(lines).strip() or h is not None]


def _split_long(text: str, max_words: int) -> list[str]:
    if word_count(text) <= max_words:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    parts, current = [], []
    for p in paragraphs:
        if current and word_count("\n\n".join(current + [p])) > max_words:
            parts.append("\n\n".join(current))
            current = []
        current.append(p)
    if current:
        parts.append("\n\n".join(current))
    return parts


def chunk_document(meta: dict, body: str, doc_path: str, max_words: int = 300) -> list[Chunk]:
    base_id = doc_path[:-3] if doc_path.endswith(".md") else doc_path
    used: dict[str, int] = {}
    chunks: list[Chunk] = []
    for heading, text in _split_sections(body):
        if not text:
            continue  # heading with no content
        slug = slugify(heading) if heading else "intro"
        used[slug] = used.get(slug, 0) + 1
        if used[slug] > 1:
            slug = f"{slug}-{used[slug]}"
        parts = _split_long(text, max_words)
        for i, part in enumerate(parts, start=1):
            cid = f"{base_id}#{slug}" + (f"-part{i}" if len(parts) > 1 else "")
            chunks.append(Chunk(
                id=cid,
                text=part,
                title=str(meta["title"]).strip(),
                section=heading,
                source=str(meta["source"]).strip(),
                category=str(meta.get("category") or "").strip() or None,
                lang=str(meta.get("lang") or "").strip() or None,
                updated=str(meta.get("updated") or "").strip() or None,
                doc_path=doc_path,
            ))
    return chunks


def iter_knowledge_files(knowledge_dir: Path) -> list[Path]:
    return sorted(p for p in knowledge_dir.rglob("*.md")
                  if not p.name.startswith("_") and p.name.lower() != "readme.md")


def load_knowledge(knowledge_dir: Path, max_words: int = 300) -> list[Chunk]:
    if not knowledge_dir.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {knowledge_dir}")
    chunks: list[Chunk] = []
    for path in iter_knowledge_files(knowledge_dir):
        meta, body = parse_markdown(path)
        rel = path.relative_to(knowledge_dir).as_posix()
        chunks.extend(chunk_document(meta, body, rel, max_words))
    ids = [c.id for c in chunks]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise KnowledgeFormatError(f"Duplicate chunk ids: {sorted(dupes)}")
    return chunks


@dataclass
class IndexReport:
    files: int
    chunks: int
    upserted: int
    deleted: int
    total_in_store: int


def build_index(chunks: list[Chunk], embedder, store, *, reset: bool = False) -> IndexReport:
    store.ensure_collection(dim=embedder.dim, model_name=embedder.name, reset=reset)
    vectors = embedder.embed_documents(chunks) if chunks else []
    upserted = store.upsert(chunks, vectors) if chunks else 0
    deleted = store.delete_except(c.id for c in chunks)
    return IndexReport(files=len({c.doc_path for c in chunks}), chunks=len(chunks),
                       upserted=upserted, deleted=deleted, total_in_store=store.count())


def print_chunks(chunks: list[Chunk], max_words: int) -> None:
    print(f"{'id':55} {'words':>5}  heading")
    for c in chunks:
        n = word_count(c.text)
        flag = "  <- long" if n > max_words else ("  <- very short" if n < MIN_WORDS_WARNING else "")
        print(f"{c.id[:55]:55} {n:5}  {c.heading[:60]}{flag}")
    print(f"\n{len(chunks)} chunks from {len({c.doc_path for c in chunks})} files")


def main(argv: list[str] | None = None) -> int:
    from app.rag.config import get_settings

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Index the SOAI knowledge base into Weaviate")
    parser.add_argument("--dir", type=Path, default=settings.knowledge_dir)
    parser.add_argument("--dry-run", action="store_true", help="only load and chunk, print the result")
    parser.add_argument("--reset", action="store_true", help="drop and recreate the collection")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        chunks = load_knowledge(args.dir, settings.max_chunk_words)
    except (KnowledgeFormatError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print_chunks(chunks, settings.max_chunk_words)
    if args.dry_run:
        return 0

    from app.rag.embeddings import build_embedder
    from app.rag.vector_store import build_store

    embedder = build_embedder(settings)
    store = build_store(settings)
    try:
        report = build_index(chunks, embedder, store, reset=args.reset)
    finally:
        store.close()
    print(f"\nIndexed {report.upserted} chunks, removed {report.deleted} stale, "
          f"{report.total_in_store} now in '{settings.collection}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())