# treiver — prompt → persona attributes

A **treiver** (trait-retriever) turns one free-text description of a person into
structured **attributes** — `(dimension_id, value)` pairs from the PersonaWorld
dimension taxonomy (`persona/schema/dimensions.json`, 1290 dimensions / 6347
values). A persona is one value per dimension; the treiver recovers a subset of
those assignments from the prompt.

It's a small **RAG** pipeline with two algorithms as two stages:

```
prompt ──▶ [1] regex retrieval ──▶ candidate dimensions ──▶ [2] LLM judge ──▶ attributes
                  │                                               │
                  └──────────────── regex attributes ─────────────┘
```

1. **Regex retrieval** — for each dimension, match the prompt against patterns
   built from its allowed values (plus a tiny curated alias list). A dimension
   that matches becomes a *candidate*. This is the retriever: it narrows 1290
   dimensions to a handful. It's also usable standalone (offline, deterministic,
   no API key) — high precision, low recall.
2. **LLM judge** — Claude (`claude-opus-4-8`, structured outputs) sees the prompt
   and only the candidate dimensions with their allowed values, and per
   dimension picks the single best value, quotes the evidence, and rates
   confidence — or returns `null` when the prompt gives no real support (so it
   doesn't over-claim).

Both stages emit records with the field shape from
`note/persona-extraction-note.md` (`dimension_id`, `value`, `evidence`, plus
`method` and `confidence`), so the output feeds the extraction-quality rubric
directly.

## Why topic-gating matters

1043 of 1290 dimensions share a *generic* value set — `Expert/Proficient/…`,
`Love/Like/…`, `High/Low/…`. The word "expert" alone doesn't say *what* someone
is expert in, so for those dimensions the regex stage also requires the
dimension's **topic** (from its label, e.g. "Data science") to appear before
proposing it. Without this, one "expert" would light up all 143 familiarity
dimensions. The ~250 dimensions with distinctive values (age brackets, regions)
match on the value alone.

## Recall: `include_topic_only`

The regex stage is literal, so "senior python developer" surfaces no
proficiency-value hit for `prog_python`. With `use_llm=True`, the treiver widens
the candidate set to include dimensions whose *topic* is mentioned even without
a value word, so the judge can still rule on them. Regex-only output stays
conservative (value hit required).

## Usage

```python
from persona.extraction import Treiver

t = Treiver()                                  # loads the bundled schema

# Stage 1 only — offline, deterministic, no API key:
result = t.match("a retired nurse in rural Kentucky")
for a in result.attributes:
    print(a.dimension_id, "=", a.value, f"[{a.method} {a.confidence}]")

# Stages 1 + 2 — Claude judge over the regex candidates (needs `anthropic` + API key):
result = t.match("a retired nurse in rural Kentucky", use_llm=True)
```

CLI:

```bash
python -m persona.extraction "a retired nurse in rural Kentucky, born 1950"
python -m persona.extraction --llm "senior python developer who loves astronomy"
echo "young woman, expert in data science" | python -m persona.extraction --json
```

## Dependencies

The regex stage has no extra dependencies and runs fully offline. The optional
stages import lazily, so nothing is required unless you actually use them:

- **Embedding retrieval** — `sentence-transformers` (local model, offline). Only
  loaded when the judge runs with `use_embed=True` (the default).
- **LLM judge** — `anthropic` and a model credential. Only loaded when you call
  `--llm` / `use_llm=True`. The judge backend is pluggable (`--backend`).

## Layout

| file | role |
|---|---|
| `schema.py` | load & index `dimensions.json` |
| `regex_matcher.py` | regex retrieval + topic gating |
| `embed_retriever.py` | semantic retrieval (local embeddings) |
| `llm_judge.py` | LLM judge (structured outputs) |
| `treiver.py` | orchestrator, `Attribute` / `MatchResult`, merge |
| `__main__.py` | CLI |
| `tests/test_treiver.py` | unit tests (judge tested with a fake client) |
```
