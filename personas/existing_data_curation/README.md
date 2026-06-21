# Existing Data Curation

This folder curates external persona datasets and reference-only literature sources for MatrAIx persona construction.

## Sources

Dataset manifests live in `manifests/`.

### Persona Datasets

| Source | Claimed Dimensions | Access |
| --- | --- | --- |
| NVIDIA Nemotron Personas USA | 21 | Hugging Face dataset: `nvidia/Nemotron-Personas-USA` |
| Tencent PersonaHub (elite) | 2 | Hugging Face dataset: `proj-persona/PersonaHub` (`elite_persona`) |
| Google Synthetic-Persona-Chat | 3 CSV persona/conversation fields | Hugging Face dataset: `google/Synthetic-Persona-Chat` |
| OASIS Reddit user data | 6 | GitHub raw JSON file |
| Apple ML-PRIMEX | 43 | GitHub raw CSV file |
| TakeLab PANDORA (Big5 subset) | 6 | Hugging Face dataset: `jingjietan/pandora-big5` |
| SynthLabs PERSONA | 33 | Hugging Face dataset: `SynthLabsAI/PERSONA` (**gated**: accept terms + set `HF_TOKEN`) |
| Facebook PersonaChat | 2 | Hugging Face dataset: `facebook/persona-chat` |
| HorizonBench (mental_state_graphs) | 30 | Hugging Face dataset: `stellalisy/HorizonBench` (`mental_state_graphs` config) |
| AllenAI WildChat (1M) | 3 | Hugging Face dataset: `allenai/WildChat-1M` |

### Grounding Sources (Merged into `personas/dimensions+new.json`)

These psychometric, survey, and theoretical frameworks have been integrated as reference sources in the `dimensions+new.json` schema. Questionnaire items are converted to construct-level attribute labels.

| Source | Constructs/Variables | Type | Use in Schema |
| --- | --- | --- | --- |
| Big Five / BFI-2 | 20 | Psychometric | Domain and facet traits |
| HEXACO-PI-R | 31 | Psychometric | 6 domains + 25 facets for personality trait grounding |
| Facet MAP | 70 | Psychometric | Fine-grained Big Five facet labels |
| IPIP constructs and item pool | 276 | Psychometric | Trait construct reference and item pool |
| Schwartz Basic Values | 10 | Theory/Survey | Core value priorities |
| Self-Determination Theory | 3 | Theory | Autonomy, competence, relatedness motivation |
| Moral Foundations Theory | 6 | Theory | Moral and worldview dimensions |
| Need for Cognition | 1 | Psychometric | Cognitive motivation (effortful thinking preference) |
| Need for Closure | 1 | Psychometric | Cognitive style (ambiguity tolerance) |
| DOSPERT risk attitudes | 5 | Psychometric | Domain-specific risk orientation |
| Attachment style | 2 | Psychometric | Adult attachment dimensions (anxiety, avoidance) |
| Interpersonal circumplex | 2 | Theory | Interpersonal style axes (dominance, warmth) |
| Primal World Beliefs | 26 | Psychometric | Worldview constructs (safe, enticing, alive) |
| BIS/BAS | 4 | Psychometric | Behavioral inhibition and activation |
| Grit / perseverance | 2 | Psychometric | Persistence and long-term effort |
| Growth mindset | 1 | Theory | Malleability-of-ability beliefs |
| McAdams Three Levels of Personality | 3 | Theory | Schema framework (traits, adaptations, narrative) |
| DeepPersona | 12 | Taxonomy | Candidate attribute coverage and subcategories |
| SCOPE-Persona | 135 | Protocol | Sociopsychological persona schema reference |
| GSS cumulative codebook | 6518 | Survey | Official social survey grounding |
| World Values Survey Wave 7 | 153 | Survey | Values, beliefs, politics, religion, social attitudes |
| ACS PUMS | 135 | Population Data | Official demographic grounding |
| Wikipedia Biographical Data | 10 | Real People Data | Birth date/place, nationality, occupation, education, positions, awards |

### Real-World Biographical Data (from Wikipedia & Wikidata)

Dimensions sourced from real people biographical data extracted from Wikipedia infoboxes and Wikidata properties. These ground persona simulation in actual patterns from 6M+ Wikipedia articles covering real individuals.

| Source | Dimensions | Data Format | Access | Coverage |
| --- | --- | --- | --- | --- |
| **wiki_bio** (michaelauli) | 10 new | Biography infoboxes + Wikidata P-codes | [Hugging Face: michaelauli/wiki_bio](https://huggingface.co/datasets/michaelauli/wiki_bio) | 728K entries |
| **wikipedia-persons-masked** (rcds) | 10 (via extraction) | Full Wikipedia text + sentences | [Hugging Face: rcds/wikipedia-persons-masked](https://huggingface.co/datasets/rcds/wikipedia-persons-masked) | 70k people pages |
| **structured-wikipedia** (Wikimedia) | 10 (via extraction) | Structured articles, infoboxes, Wikidata QIDs | [Hugging Face: wikimedia/structured-wikipedia](https://huggingface.co/datasets/wikimedia/structured-wikipedia) | 6M+ articles |
| **Wikidata** (Wikimedia Foundation) | 10 (via properties) | Linked data / RDF triples | [Wikidata.org Query Service](https://query.wikidata.org) | 100M+ entities |

#### Extracted Biographical Dimensions (10 total):

1. **wiki_birth_date** — Birth date (decades); Wikidata P569
2. **wiki_birth_place** — Geographic birthplace; Wikidata P19
3. **wiki_nationality** — Country of citizenship; Wikidata P27
4. **wiki_occupation** — Primary profession/field; Wikidata P106
5. **wiki_field_of_work** — Academic/professional discipline; Wikidata P101
6. **wiki_position_held** — Official roles (CEO, President, Minister, etc.); Wikidata P39
7. **wiki_education_level** — Highest education attained; Wikidata P69
8. **wiki_awards_recognition** — Major prizes/distinctions; Wikidata P166
9. **wiki_marital_status** — Marriage/partnership status; Wikidata P26
10. **wiki_political_affiliation** — Political party/ideology; Wikidata P102

#### Data Quality Notes:

- **High coverage (85-95%)**: Demographics (birth, nationality, occupation)
- **Medium coverage (55-81%)**: Professional/education (positions, awards, field)
- **Low coverage (48-62%)**: Social/political (marital status, political affiliation)
- **Inference-required (0%)**: Derived traits (OCEAN personality, socioeconomic status)

#### Integration Rationale:

Real-world biographical grounding provides:
- **Authenticity**: Patterns from 6M+ real people, not synthetic or survey-based
- **Diversity**: Global coverage across occupations, nationalities, time periods
- **Completeness**: Infobox structure enables systematic extraction
- **Linkability**: Wikidata QIDs enable cross-reference with other knowledge graphs

See `from_real_people.md` for dataset discovery notes and resource links.

## Eliza's Proposed Persona Schema Categories and Theoretical Basis

The category structure below is Eliza Fan's current proposal, not a finalized project schema. The proposal is theory-grounded rather than copied from any single dataset, and is documented in [`persona_schema_theoretical_basis.md`](../attribute_pool/docs/persona_schema_theoretical_basis.md) and [`persona_schema_theoretical_basis_zh.md`](../attribute_pool/docs/persona_schema_theoretical_basis_zh.md): McAdams provides the high-level person model; trait psychology, values research, social identity theory, population surveys, and person-situation interaction provide category-specific grounding.

| Proposed Category | Theoretical / Source Grounding | Why It Is Proposed |
| --- | --- | --- |
| Demographics & Population Grounding | Social Identity Theory; ACS/Census/IPUMS; Nemotron; SCOPE | Grounds personas in population-level variables and social position without treating demographics as deterministic behavior proxies. |
| Life Context & Constraints | McAdams characteristic adaptations; ACS/GSS; DeepPersona physical and health context | Captures lived constraints such as household, health, resources, and life circumstances that shape choices and opportunities. |
| Personality Traits | Big Five/BFI-2; HEXACO; Facet MAP; IPIP | Provides validated trait and facet constructs instead of vague invented personality labels. |
| Values, Goals & Motivations | McAdams Level 2 adaptations; Schwartz Basic Values; Self-Determination Theory; WVS | Explains priorities, motives, and tradeoffs that can differ even when demographics and traits look similar. |
| Worldview, Beliefs & Attitudes | WVS; GSS; Moral Foundations Theory; Primal World Beliefs; PrimeX | Captures political, moral, religious, institutional, and social beliefs that drive judgment and response patterns. |
| Cognitive & Capability Profile | Cognitive style constructs; Need for Cognition; Need for Closure; education/learning sources | Represents knowledge, skills, literacy, decision style, and preference for effortful thinking. |
| Behavioral Patterns & Preferences | McAdams characteristic adaptations; person-situation interaction; GSS/WVS behavior items; DeepPersona lifestyle/media categories | Captures repeated habits, routines, media use, consumption, and preference patterns. |
| Social Identity, Relationships & Community | Social Identity Theory; Attachment Style; Interpersonal Circumplex; GSS/WVS social trust items | Represents group belonging, interpersonal tendencies, community ties, and relationship style. |
| Narrative Identity & Life History | McAdams narrative identity; SCOPE identity narratives; DeepPersona life story/background | Adds continuity, personal history, and meaning-making beyond static traits or demographics. |
| Domain-Specific Overlays | Person-situation interaction; SCOPE simulation logic; application-specific benchmarks | Lets task-specific modules add attributes for finance, health, education, coding, or other simulations without bloating the core schema. |

## Sources and Reasons Added to Dimensions (Eliza)

| Source | Added Dimensions | Reason Added |
| --- | ---: | --- |
| Big Five / BFI-2 | 20 | Adds a high-quality personality trait backbone with 5 domains and validated facet-level constructs. |
| Schwartz Basic Values | 10 | Adds core value priorities that affect decisions, preferences, tradeoffs, and moral judgment without duplicating personality traits. |
| Self-Determination Theory | 3 | Adds basic motivation needs that explain autonomy-seeking, competence-seeking, and relatedness-seeking behavior. |
| Moral Foundations Theory | 6 | Adds moral/worldview dimensions useful for political, social, and ethical reasoning differences across personas. |
| Need for Cognition | 1 | Adds a compact cognitive motivation dimension for how much a persona enjoys effortful thinking and deep explanation. |
| Need for Closure | 1 | Adds a cognitive style dimension for ambiguity tolerance, certainty preference, and decisiveness under uncertainty. |
| DOSPERT risk attitudes | 5 | Adds domain-specific risk orientation instead of treating risk tolerance as one generic trait. |
| Attachment style | 2 | Adds interpersonal relationship tendencies using the common adult attachment dimensions of anxiety and avoidance. |
| Interpersonal circumplex | 2 | Adds broad interpersonal style axes for dominance/agency and warmth/communion. |

## Literature & Proposed Persona Frameworks (For Future Expansion)

The following frameworks from research papers and domain experts propose additional dimension candidates that could extend the schema beyond current sources. These are documented for future curation:

### Personality & Character Frameworks

| Source | Dimensions | Notes |
| --- | --- | --- |
| **BFI-2 Facets** | 15 facets across 5 domains | Extraversion (Sociability, Assertiveness, Energy); Agreeableness (Compassion, Respectfulness, Trust); Conscientiousness (Organization, Productiveness, Responsibility); Negative Emotionality (Anxiety, Depression, Volatility); Open-Mindedness (Curiosity, Aesthetic Sensitivity, Creative Imagination) |
| **16 Personalities (16P)** | 16 types | From Personality Database (PDb); complements Big Five with type-level categorization |
| **Dark Triad + Dirty Dozen** | 6-12 constructs | Narcissism, Machiavellianism, Psychopathy (Dark Triad); Dishonesty, Grandiosity, Aggressiveness, etc. (Dirty Dozen) |
| **InCharacter Paper** | 14 personality tests | Comprehensive assessment including Big Five, 16P, Dark Triad, Dirty Dozen |

### Character-Driven Persona Dimensions

| Source | Framework | Dimensions |
| --- | --- | --- |
| **CharacterGPT** | Character Narrative | Personality, Physical Description, Motivations, Backstory, Emotions, Relationships, Growth & Change, Conflict |
| **Character is Destiny Paper** | Decision-Making | Personality & Traits, Emotions & Psychological State, Social Relationships, Values & Beliefs, Desires & Goals |
| **Character is Destiny Paper** | Plot-Driven | External Conflicts, Tasks & Goals, Puzzles & Secrets, Pursuits & Escapes, Exploration & Discovery, Power & Control, Intrigue & Betrayal |

### Domain-Specific Persona Models

| Source | Domain | Key Dimensions |
| --- | --- | --- |
| **SimsChat** | Conversational Agents | Career, Aspiration, Traits, Skills, + Personal Aspects (name, gender, tone, personality), Social Backgrounds (relationships, family dynamics), Emotion, Conversation Topic |
| **Information Design for Personas (4 Domains)** | UX/Healthcare/Market Research/Social Media | Demographics, Personality, Activity, Interests, Challenges, Environment, Hobbies, Physical Health, Mental Health, Behavioral Health, Income |

### Temporal & Context-Dependent Dimensions

These frameworks highlight dimensions that should vary by context or time:

| Dimension Category | Notes |
| --- | --- |
| **Emotional State** | Varies by context, interaction, and time (SimsChat, Character is Destiny) |
| **Conversation Topic** | Dynamically chosen based on persona state and social context |
| **Growth & Change** | Temporal evolution of personality, relationships, and goals over narrative arc |
| **Conflict States** | External and internal conflicts that drive decision-making and persona behavior |

## Future Curation Priorities

Based on the above literature, candidates for next-phase expansion:

1. **BFI-2 Facets** (15) — High-fidelity Big Five breakdown already cited in behavioral research
2. **16 Personalities (16P)** — Complements existing MBTI with validated type taxonomy
3. **Dark Triad / Dirty Dozen** (6-12) — Shadow personality dimensions for nuanced behavioral modeling
4. **Temporal Dimensions** — Emotional state, growth, conflict as dynamic rather than static
5. **Domain-Specific Overlays** — Per-domain extensions (career, conversation topic, etc.) beyond core schema

## Fetch Script

Use `scripts/fetch_sources.py` from this directory.

### 1) Sample-first fetch

```bash
cd personas/existing_data_curation
python scripts/fetch_sources.py --source all --mode sample --sample-rows 1000
```

This will:
- sample `Nemotron`, `PersonaHub`, and `Synthetic-Persona-Chat` into JSONL files
- fully download the OASIS JSON and ML-PRIMEX CSV

`Synthetic-Persona-Chat` sample mode streams **Part 1 train only**. Use full mode for all four CSV files: Part 1 train/valid/test plus Part 2.

### 2) Full Nemotron download

```bash
python scripts/fetch_sources.py --source nemotron --mode full
```

### 3) Full PersonaHub download

Small PersonaHub files:

```bash
python scripts/fetch_sources.py --source personahub --mode full --personahub-config persona
```

Elite PersonaHub shards are very large (8-16GB each). Download one explicit part:

```bash
python scripts/fetch_sources.py \
  --source personahub \
  --mode full \
  --personahub-config elite_persona \
  --personahub-elite-part 1
```

Or all elite parts (~300GB+):

```bash
python scripts/fetch_sources.py \
  --source personahub \
  --mode full \
  --personahub-config elite_persona \
  --personahub-elite-part all
```

### 4) Synthetic-Persona-Chat fetch

Sample Part 1 train rows into JSONL:

```bash
python scripts/fetch_sources.py --source synthetic_persona_chat --mode sample --sample-rows 1000
```

Full download of all four CSV files:

```bash
python scripts/fetch_sources.py --source synthetic_persona_chat --mode full
```

After fetch, the script logs row counts and checks the three expected CSV column names.

### 5) Gated source: PERSONA

`SynthLabsAI/PERSONA` is gated. First accept the terms on the [HF dataset page](https://huggingface.co/datasets/SynthLabsAI/PERSONA), then export a token. It is excluded from `--source all`, so fetch it explicitly:

```bash
export HF_TOKEN=hf_...   # token for an account that accepted the terms
python scripts/fetch_sources.py --source synthpersona --mode sample --sample-rows 1000
```

### 6) Literature and theory references

This source creates a registry from reference-only manifests:

```bash
python scripts/fetch_sources.py --source literature_references --mode sample
```

`sample` mode only writes metadata registries. `full` mode also attempts best-effort HTML snapshots of each source URL when the source permits it.

### 7) Reference source snapshots

Reference manifests can also be fetched individually by manifest id. This is required for sources that have been added to `personas/dimensions+new.json` and is available for the remaining reference sources as well.

```bash
python scripts/fetch_sources.py --source bfi2_big_five_inventory_2 --mode sample
python scripts/fetch_sources.py --source schwartz_basic_values --mode sample
python scripts/fetch_sources.py --source need_for_cognition --mode sample
python scripts/fetch_sources.py --source need_for_closure --mode sample
```

For manifests with explicit `download.sample_urls`, `sample` mode downloads those core instrument/reference pages. Otherwise it snapshots the manifest's primary source URL. `full` mode also tries supplemental URLs listed in `download.full_urls`.


## Wikipedia Persona Seed Pipeline

This two-stage workflow converts real people and fictional characters from
Wikipedia/Wikidata into evidence-grounded persona seed records, then uses a local
LLM runner to map those records onto selected persona template keys.

The workflow is inspired by BenchFlow-style local agent execution: deterministic
code prepares the data/evidence, and a coding-agent subscription such as Claude
Code is used only for the bounded interpretation step.

### Candidate pool size

These are upstream candidate-pool estimates, not rows already generated by this
repo. The scripts only process the entities listed in the input JSONL file.

| Pool | Approximate size | Estimation method | Notes |
| --- | ---: | --- | --- |
| English Wikipedia real people | 2.16M biography articles | [WikiProject Biography](https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Biography) reported 2,156,747 in-scope articles on 2026-06-21 | Practical proxy for real-person English summaries; article-level count, not a deduplicated persona dataset |
| English Wikipedia fictional characters | 29.8K Wikidata entities | Wikidata Query Service count for `P31/P279* = fictional character (Q95074)` with an English Wikipedia sitelink on 2026-06-21 | Covers fictional characters across literature, games, film, TV, comics, etc.; excludes character lists and entities without Wikidata character typing |
| Wikidata real people | 13.57M entities | Wikidata Query Service count for `P31 = human (Q5)` on 2026-06-21 | Wider theoretical pool; many entries do not have an English Wikipedia summary |
| Wikidata fictional characters | 124.3K entities | Wikidata Query Service count for `P31/P279* = fictional character (Q95074)` on 2026-06-21 | Wider theoretical pool across languages/projects; quality and summary availability vary |

The strict English-Wikipedia count for real people is expensive as a live
SPARQL aggregation, so the English real-person row uses WikiProject Biography as
a practical proxy. For reproducible large-scale counts, prefer Wikidata or
Wikipedia dumps over repeated live aggregate queries.

### 1) Fetch Wikipedia/Wikidata seed records

Use known Wikidata QIDs when possible:

```bash
python scripts/fetch_wikipedia_persona_seeds.py \
  --input examples/wikipedia_persona_seed_entities_sample.jsonl \
  --output outputs/wiki_persona_seeds_sample.jsonl \
  --overwrite
```

Input rows can represent real people or fictional characters:

```json
{"qid": "Q937", "entity_type": "real_person", "name": "Albert Einstein"}
{"qid": "Q4653", "entity_type": "fictional_character", "name": "Sherlock Holmes"}
```

Rows may also provide only a name. In that case the script searches Wikidata and
validates the expected entity type:

```json
{"name": "Lara Croft", "entity_type": "fictional_character"}
```

The seed output follows the existing persona YAML shape (`metadata`, `persona`,
`dimensions`) but is written as JSONL for curation. Fields without direct
Wikipedia/Wikidata evidence, such as Big Five traits or socioeconomic band, are
left as `null` rather than inferred.

### 2) Assign persona fields with Claude Code subscription

If your Claude Code subscription includes CLI access, install Claude Code, sign
in locally, and ensure the `claude` command is on your `PATH`:

```bash
claude --version
```

Then run the field assignment step:

```bash
python scripts/assign_wikipedia_persona_fields.py \
  --input outputs/wiki_persona_seeds_sample.jsonl \
  --output outputs/wiki_persona_field_assignments_sample.jsonl \
  --target-fields source_entity_type,domain,subject_specialty,role_function,known_for_or_source_work,creator,highest_education,intent,personality_big5_openness \
  --backend claude_code \
  --overwrite
```

The script invokes Claude Code through `claude -p`; no Anthropic API key is
stored in the repository. If your executable is not named `claude`, pass
`--claude-bin /path/to/claude` using a local path outside committed files.

The assignment output preserves the original seed record and adds
`persona.llm_field_assignments`. Each assignment includes `value`,
`evidence_quotes`, `confidence`, and `assignment_type` (`direct`,
`structured_claim`, `summary_inference`, or `unsupported`). Values are written
back to `persona.dimensions` only when confidence passes `--min-confidence`; by
default, existing deterministic values are not overwritten.

Use `--backend dry_run` to test the file flow without calling Claude Code.

### 3) Browser demo

A static demo is available at `demo/index.html`. It calls public Wikidata and
English Wikipedia APIs directly from the browser, loads the live matrAIx persona
schema from `https://matraix.ai/dimensions.js?v=3`, then renders the persona
seed, source evidence, all persona keys, and a Claude-style prompt without
requiring any API key:

```bash
cd personas/existing_data_curation/demo
python3 -m http.server 8899
```

Open `http://127.0.0.1:8899/`. After the PR branch is pushed, the same file can
be exposed temporarily for demos:

```bash
npx --yes localtunnel --port 8899
```

Share the returned `https://*.loca.lt` URL while both the local server and
tunnel are running. If the repository is public, the file can also be shown
through an HTML preview service:

```text
https://htmlpreview.github.io/?https://github.com/MatrAIx-ai/MatrAIx/blob/codex/wiki-persona-seed-pipeline/personas/existing_data_curation/demo/index.html
```

## Output Layout

Downloads are stored under `raw/`:

- `raw/nemotron_personas_usa/`
- `raw/tencent_personahub/`
- `raw/google_synthetic_persona_chat/`
- `raw/oasis/user_data_36.json`
- `raw/apple_ml_primex/primexdata.csv`
- `raw/pandora_big5/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/synthlabs_persona/` (gated; sample JSONL, or `data/*.parquet` in full mode)
- `raw/personachat_facebook/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/horizonbench_mental_state_graphs/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/wildchat_allenai/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/literature_references/reference_registry.json`
- `raw/literature_references/reference_registry.jsonl`
- `raw/{reference_source_id}/`
- `outputs/wiki_persona_seeds*.jsonl` (generated Wikipedia persona seeds; git-ignored)
- `outputs/wiki_persona_field_assignments*.jsonl` (LLM-assigned Wikipedia persona fields; git-ignored)

`raw/` and `outputs/` are git-ignored by default.
