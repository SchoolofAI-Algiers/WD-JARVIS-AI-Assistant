# SOAI knowledge base

This folder is what J.A.R.V.I.S. knows about SOAI. Only **approved** information goes here.

```
knowledge/
├── raw/         sources as collected (PDF exports, copied docs, notes) — never indexed
└── processed/   clean Markdown files, one topic per file — this is what gets indexed
```

## Adding or editing a document

1. Put the original material in `raw/` (keep it for traceability).
2. Copy `processed/_TEMPLATE.md` to a new file, e.g. `processed/projects/jarvis.md`
   (sub-folders are fine; files starting with `_` are ignored).
3. Fill the front matter and write the content (rules below).
4. Check the chunks: `cd backend && python -m app.rag.ingest --dry-run`
5. Index: `python -m app.rag.ingest`

## Front matter

```yaml
---
title: J.A.R.V.I.S. project        # required
source: SOAI technical doc 2026    # required — where the info comes from (shown as the source)
category: projects                 # projects | events | team | rules | faq | club ...
lang: fr                           # language of the text
updated: 2026-10-01
---
```

## Writing rules (this is what makes retrieval work)

- **One `## heading` = one chunk.** Each section answers one thing (a project, an event, a rule, a role).
- **Self-contained sections.** Repeat the subject: "The J.A.R.V.I.S. project uses…", not "It uses…".
  Write dates in full. Avoid "see above".
- **100–300 words per section.** Longer sections are split on paragraphs automatically, but it's
  better to split them yourself into clear sub-topics.
- **FAQ:** one `## Q: …?` heading per question, the answer below it.
- **Lists of many items** (events, members): one section per item or per small group.
- **Tables:** rewrite as sentences.
- **No personal data** that isn't needed (phone numbers, private emails...).
- Use `###` freely inside a section: only `##` starts a new chunk.

The chunk id is `<file path>#<heading>` (e.g. `projects/jarvis#team`). Renaming a heading
changes the id.
