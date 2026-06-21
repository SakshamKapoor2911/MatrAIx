# Wikipedia Persona Seed Demo

This is a static browser demo for the Wikipedia/Wikidata persona seed pipeline.
It runs public Wikidata and English Wikipedia API calls directly from the
browser, so it does not need a backend, Claude Code, or API keys.

## Local Run

From this directory:

```bash
python3 -m http.server 8899
```

Then open:

```text
http://127.0.0.1:8899/
```

## Temporary Online Preview

For a private repository, run the local server above and expose it with a
temporary tunnel:

```bash
npx --yes localtunnel --port 8899
```

Share the returned `https://*.loca.lt` URL while the local server and tunnel are
running.

For a public repository, the same HTML file can also be opened through an HTML
preview service:

```text
https://htmlpreview.github.io/?https://github.com/MatrAIx-ai/MatrAIx/blob/codex/wiki-persona-seed-pipeline/personas/existing_data_curation/demo/index.html
```

For a more stable demo link, deploy this folder as a static site through GitHub
Pages, Netlify, Vercel, or a Hugging Face Static Space.

## Demo Scope

- Supports known Wikidata QIDs and name search.
- Supports both `real_person` and `fictional_character`.
- Shows Wikipedia summary, Wikidata evidence, seed JSON, and a Claude-style
  prompt.
- Uses deterministic field drafting only. The production curation step should
  still run `scripts/assign_wikipedia_persona_fields.py --backend claude_code`
  for Claude Code-based assignment.
