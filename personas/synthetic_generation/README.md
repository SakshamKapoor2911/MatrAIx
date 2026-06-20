# Persona Task 2.2 — Synthetic Generation (DRAFT)

Generate synthetic personas for **MatrAIxPersona** by combining attributes from
[`../dimensions.json`](../dimensions.json) and expanding them into full personas with
multiple LLMs (GPT / Claude / DeepSeek / Qwen / open-source), seeded by real-world
priors. Output feeds Task 3.

## Draft methodology

Two stages:

1. **Heuristic combination** — assign attribute values from `dimensions.json` into a
   structured persona "skeleton", using rules + real-world priors so the combination is
   coherent and demographically realistic (not random / contradictory).
2. **Synthetic generation** — condition strong LLMs on the skeleton to produce the full
   persona: structured fields + a natural-language profile.

Conventions:
- **Prompts split by domain** — one base prompt + per-domain overlays (one owner each).
- **Inference is multi-provider via LiteLLM** — one `model` string; `api_base` only for self-hosted.
- **Output = JSON** (dimensions + narrative + provenance), handed to Task 3.

**⚠️ Open decision (team):** how the ~1,276 dimension values get assigned in stage 1 —
*heuristic-heavy* (rules sample all values, LLM only writes the narrative), *LLM-heavy*
(rules fix a few anchors, LLM fills the rest), or *hybrid*. Code currently uses an
LLM-heavy stub so the pipeline runs; this is the main thing to settle.

## Prompt Design Idea

A persona prompt has **two layers** so the work splits cleanly and each domain tunes
independently:

- **Base prompt** (`prompts/base_persona.yaml`, *system*) — shared by all domains. Turns a
  skeleton into ONE coherent, behaviorally-faithful person: a **named, first-person narrative**
  (values + lived experience + how they act) plus the structured dimensions and provenance.
- **Domain overlay** (`prompts/domains/<domain>.yaml`, appended to *user*) — one per domain:
  which dims to emphasize, 1–3 **situational probes** ("how would they act when…") to make
  domain behavior concrete, and domain guardrails.

Assembled at generation time:

```
SYSTEM = base_persona.content
USER   = <domain> overlay  +  skeleton (assigned dimension values, JSON)  +  "return one persona as JSON"
```

**Why split by domain?** parallel ownership (one person per `<domain>.yaml`, shared base +
contract → no collisions); quality (different domains care about different dims); maintainable
(small base + focused overlays beat one giant all-domains prompt).

**Design principles (from the persona literature):**
- **Named + first-person / interview style** — give the persona a name and write in their voice; measurably reduces stereotyping and improves alignment. *(Prompt-Makes-Persona, 2507.16076)*
- **Behavior from values / personality / identity, not demographics** — demographics explain only ~1.5% of behavioral variance and add bias; derive behavior from sociopsychological traits, not demographic clichés. *(SCOPE, 2601.07110)*
- **Narrative = values + lived experience + how they'd act**, not a restatement of the fields. *(SPIRIT, 2603.27056)*
- **Don't chase diversity by cramming attributes** — extra fine-grained detail barely helps; pass a focused core + an explicit length cap. *(Lexical Diversity, 2505.17390)*
- **Resist the "average user"** — commit to rare combinations; don't soften to the modal persona. *(Persona Generators, 2602.03545)*

**Not the prompt's job:**
- **Diversity / coverage** → the sampling layer (dedup + weighted sampling); the prompt only nudges (last principle).
- **Which core dims to pass** → the skeleton step (the open decision above), upstream of the prompt.

> current draft gives each persona one domain — read "domain" as the application focus being *emphasized*, not an exclusive label.

## Code structure

```
synthetic_generation/
├── config/config.yaml           # model registry (litellm model string + api_base if self-hosted); NO secrets
├── prompts/
│   ├── base_persona.yaml         # base generation prompt
│   └── domains/_template.yaml    # per-domain overlay template → copy to <domain>.yaml
├── inference/
│   ├── client.py                 # multi-provider LLM client (LiteLLM)
│   └── generate.py               # CLI: skeleton → prompt → model → persona JSON
└── outputs/                      # generated personas (gitignored)
```

## Getting started

```bash
pip install litellm pyyaml
export OPENAI_API_KEY=...          # or DEEPSEEK_API_KEY / ANTHROPIC_API_KEY / ...
cp prompts/domains/_template.yaml prompts/domains/<domain>.yaml   # write your domain overlay
python inference/generate.py --domain <domain> --model gpt-4o --n 3
```

## TODO

- [ ] Settle the open decision above; implement `build_skeleton()` accordingly (+ wire Task 1 ACS skeleton).
- [ ] Formal persona JSON Schema + output validation in `generate.py`.
- [ ] First domain overlays + a small batch per model → hand to Task 3.
