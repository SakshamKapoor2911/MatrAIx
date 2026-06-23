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
| Amazon Reviews 2023 | n/a | Category-level JSONL.GZ review and metadata files from McAuley Lab |

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

## Amazon Reviews 2023 Persona Workflow

For a cloud-built team artifact, use
`modal_amazon_user_index.py`. The current recommended path uses the Modal
Volume `amazon-reviews-user-index` as the source of truth, so downstream work no
longer needs to rescan raw category-indexed review files.

Prepared Modal artifacts:

| Artifact | Prefix | Purpose |
|---|---|---|
| Per-user summary stats | `amazon_reviews_2018_2023_user_stats` | One row per user per category, used for pool filtering |
| Eligible user pool | `amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000` | Users with >=30 reviews, verified purchase share >=0.7, and >=2000 review-text characters |
| Eligible user-indexed reviews | `amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000` | Review rows for eligible users, bucketed by `sha1(user_id)[:2]` |
| Stricter eligible user pool | `amazon_reviews_2018_2023_eligible_users_min30_verified70_text3000` | Derived from the >=2000 pool with >=3000 review-text characters |
| Stricter eligible user-indexed reviews | `amazon_reviews_2018_2023_user_buckets_min30_verified70_text3000` | Derived from the >=2000 user-indexed reviews for the stricter eligible pool |
| Product metadata index | `amazon_reviews_2023_metadata_by_parent_asin_bucket_v2` | Product metadata bucketed by `sha1(parent_asin)[:2]` |

Current recommended persona-construction path:

1. Use the stricter eligible pool with `>=30` reviews, verified-purchase share
   `>=0.70`, and `>=3000` review-text characters.
2. Export histories from the matching stricter user-indexed review parquet.
3. Split each user's retained review/rating rows temporally: earliest 80% for
   persona construction, latest 20% for validation.
4. Include product metadata during export so inference can link each text review
   to compact product name/category context.
5. Save reusable review memory before schema extraction, then map that memory to
   the current `dimensions+new.json` schema and optionally export persona YAML.

Install and authenticate Modal locally, using the account/workspace for the
`cs231n-final-project` project:

```bash
python3 -m pip install modal
modal setup
```

### Build or Refresh Modal Artifacts

These commands are only needed when rebuilding the shared artifacts.

Build per-user 2018-2023 summary stats:

```bash
modal run modal_amazon_user_index.py::build_user_stats \
  --categories all \
  --start-year 2018 \
  --end-year 2023
```

Reduce the stats into an eligible user pool:

```bash
modal run modal_amazon_user_index.py::build_eligible_users \
  --min-reviews 30 \
  --min-verified-share 0.7 \
  --min-text-chars 2000
```

Build review-level user-indexed Parquet only for eligible users:

```bash
modal run modal_amazon_user_index.py::build_categories \
  --categories all \
  --start-year 2018 \
  --end-year 2023 \
  --eligible-prefix amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000 \
  --output-prefix amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000
```

Derive the stricter >=3000 text-character pool from the existing >=2000 pool:

```bash
modal run modal_amazon_user_index.py::derive_eligible_users \
  --source-prefix amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000 \
  --output-prefix amazon_reviews_2018_2023_eligible_users_min30_verified70_text3000 \
  --min-reviews 30 \
  --min-verified-share 0.7 \
  --min-text-chars 3000
```

Derive matching review-level user-indexed Parquet from the existing >=2000
review index:

```bash
modal run modal_amazon_user_index.py::derive_user_buckets \
  --source-review-prefix amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000 \
  --eligible-prefix amazon_reviews_2018_2023_eligible_users_min30_verified70_text3000 \
  --output-prefix amazon_reviews_2018_2023_user_buckets_min30_verified70_text3000
```

Build product metadata indexed by `parent_asin` bucket:

```bash
modal run modal_amazon_user_index.py::build_metadata \
  --categories all \
  --output-prefix amazon_reviews_2023_metadata_by_parent_asin_bucket_v2
```

Review index layout:

```text
bucket=ab/category=Books/part-000000.parquet
bucket=ab/category=Electronics/part-000000.parquet
```

Metadata index layout:

```text
bucket=ab/source_category=Books/part-000000.parquet
bucket=ab/source_category=Electronics/part-000000.parquet
```

### Export Candidate Histories

First export candidate users from the same eligible-user pool used to build the
review index. This keeps the candidate list and review index aligned:

```bash
modal run modal_amazon_user_index.py::export_candidate_users \
  --eligible-prefix amazon_reviews_2018_2023_eligible_users_min30_verified70_text3000 \
  --top-n 100 \
  --min-history-days 365 \
  --output raw/amazon_reviews_2023/candidates/eligible_candidates_top100.jsonl
```

The tracked `samples/amazon_reviews_2023/candidate_users_top100.jsonl` file is
a lightweight collaborator sample from an earlier candidate pool. It is useful
for code smoke tests, but newly generated candidates should come from the
current eligible-user prefix. Full candidate pools and retrieved review
histories stay under `raw/` and are intentionally ignored by Git.

Export selected users from the Modal user-indexed review artifact into the local
JSONL format expected by the inference script:

```bash
modal run modal_amazon_user_index.py::export_user_histories \
  --candidate-users raw/amazon_reviews_2023/candidates/eligible_candidates_top100.jsonl \
  --top-n 100 \
  --review-prefix amazon_reviews_2018_2023_user_buckets_min30_verified70_text3000 \
  --temporal-train-fraction 0.8 \
  --output raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl
```

By default, the export removes reviews that are primarily about fulfillment,
shipping, damaged packaging, wrong/missing items, returns, or compensated/template
review disclosures. The export writes a sidecar summary such as
`user_histories.jsonl.filter_summary.json` with removed-review counts by
category, by user, by user/category, and by matched phrase. Use
`--no-filter-fulfillment-reviews` only for debugging or ablations.

After filtering, each exported user history is split per user by timestamp over
all retained review/rating rows, including rating rows with empty review text.
The earliest `--temporal-train-fraction` share, 0.8 by default, is written to
`reviews` for persona construction. The latest held-out share is written to
`validation_reviews` for downstream validation. `category_review_stats` is
computed from the construction split, including per-category row counts, rating
counts, rating distributions, and average ratings. The export also saves
`validation_category_review_stats`; the sidecar summary includes per-user and
aggregate stats for both splits, plus text-review, rating, and rating-only row
counts. The inference script passes only the construction-split stats as
additional behavioral context for persona extraction.

Export product metadata as a separate compact sidecar after user histories are
retrieved. This keeps retrieval fast and makes metadata enrichment optional:

```bash
modal run modal_amazon_user_index.py::export_history_metadata \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --output raw/amazon_reviews_2023/persona_dimension_inference/user_histories.product_metadata.jsonl
```

The sidecar contains only product title, main category, source category, and
category path keyed by `parent_asin` and source category. Long descriptions,
features, details, price, and store fields are omitted. The older one-step
`export_user_histories --include-metadata` option is still available for small
debugging runs, but it joins metadata during retrieval and can add substantial
I/O latency.

### Amazon Review to 1,339-Dimension Schema Inference

Use `scripts/infer_amazon_review_dimensions.py` to infer values from
`personas/dimensions+new.json` where the exported review history directly
supports the schema attribute. The prompt is conservative: unsupported
dimensions are omitted, sensitive demographics are not inferred from product
stereotypes, and every returned value must include review evidence.

Inspect prompts without calling the API:

```bash
python scripts/infer_amazon_review_dimensions.py \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --product-metadata-sidecar raw/amazon_reviews_2023/persona_dimension_inference/user_histories.product_metadata.jsonl \
  --inference-mode evidence_profile \
  --max-users 2 \
  --dimensions-per-call 40 \
  --dry-run
```

The recommended inference mode is `evidence_profile`. It first compresses each
review history into a compact, evidence-cited profile using broad Amazon-review
evidence categories from `amazon_review_evidence_mapping.json`, then maps that
profile to the persona schema. This avoids resending the same raw reviews for
every schema batch. Evidence profiles are written to
`raw/amazon_reviews_2023/persona_dimension_inference/evidence_profiles.jsonl`
and can be reused across resumed schema-mapping runs.
If `--product-metadata-sidecar` is supplied, the evidence profile also sees
compact product name/category context for each reviewed item. Histories exported
with the older `--include-metadata` option continue to work; the sidecar loader
only fills reviews that do not already include product metadata.

The evidence profile file is the reusable review memory. It is written before
the granular schema extraction step and can be addressed with either
`--evidence-profiles-output` or the clearer alias `--review-memory-output`.
When the 1,339-dimension schema changes, rerun the script with the same review
memory path and do not pass `--overwrite-profiles`; the script will reuse the
saved review summaries and only redo schema mapping. Regenerate review memory
only when the review histories, product metadata, broad evidence mapping, or
summary prompt behavior changes.

Inference outputs include `review_corpus_stats` for the construction split:
row count, text-review count, rating count, rating-only row count, total review
text characters, date span, category counts, and rating-only product/category
summary stats. In `evidence_profile` mode, only rows with review text are sent
as `review_evidence`; rating-only rows are represented through aggregate rating,
product-name, and product-category stats in `construction_corpus_summary`. Users
with very large construction text histories are summarized in temporal windows
before schema mapping. By default, windowing triggers when construction review
text exceeds `--window-summary-threshold-chars 120000`; each window is capped by
`--window-summary-max-chars 60000` and `--window-summary-max-rows 200`, and the
combined window memory keeps up to `--max-window-evidence-items 100` evidence
items.

Run OpenAI inference with the optimized evidence-profile pipeline:

```bash
export OPENAI_API_KEY=...
python scripts/infer_amazon_review_dimensions.py \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --product-metadata-sidecar raw/amazon_reviews_2023/persona_dimension_inference/user_histories.product_metadata.jsonl \
  --inference-mode evidence_profile \
  --schema-path ../dimensions+new.json \
  --model "${OPENAI_LLM_MODEL:-gpt-5.4-mini}" \
  --dimensions-per-call 40 \
  --window-summary-threshold-chars 120000 \
  --max-window-evidence-items 100 \
  --review-memory-output raw/amazon_reviews_2023/persona_dimension_inference/evidence_profiles.jsonl \
  --max-users 100 \
  --output raw/amazon_reviews_2023/persona_dimension_inference/inferred_dimensions.jsonl \
  --yaml-output raw/amazon_reviews_2023/persona_dimension_inference/inferred_dimensions.yaml
```

The primary inference output remains JSONL for resumable runs, with one user row
per line. Each row includes `user_id`, run metadata, `review_corpus_stats`,
optional `evidence_profile`, `inferred_attributes`, and `rejected_attributes`.
Use `--yaml-output` to write a persona YAML file matching the
`personas/Jun20_1k_persona_description/personas.yaml` structure:
top-level `metadata`, then `personas`, where each persona has `id`, `name`,
`title`, `description`, and a `dimensions` map of `dimension_id: value`.
Only validated inferred attributes are exported to `dimensions`.

Inferred attribute values are validated before writing: the script rejects any
model output whose `value` is not one of that dimension's allowed `values` in
`personas/dimensions+new.json`. Rejected values remain in `rejected_attributes`
in the JSONL output and are omitted from the YAML `dimensions` map.

Use `--overwrite-profiles` only when you want to pay to regenerate compact
review memory instead of reusing the existing profile cache. Use
`--no-amazon-default-schema-filter` if you intentionally want to test every
selected schema dimension, including categories that Amazon reviews usually
cannot support.

For cheaper pilots, restrict the schema surface first:

```bash
python scripts/infer_amazon_review_dimensions.py \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --inference-mode evidence_profile \
  --dimension-categories "Interests: Hobbies,Interests: Topics,Behavior: Preferences,Expertise: Domains" \
  --max-users 20 \
  --dry-run
```

The original direct raw-review batching path is still available with
`--inference-mode raw_reviews`, but it is more expensive because each schema
batch receives the same review context again.

Render a readable Markdown report from inference JSONL outputs:

```bash
python scripts/render_amazon_inference_report.py \
  --inference-output raw/amazon_reviews_2023/persona_dimension_inference/inferred_dimensions_pilot_2users_dpc100.jsonl \
  --evidence-profiles raw/amazon_reviews_2023/persona_dimension_inference/evidence_profiles_pilot_2users_dpc100.jsonl \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories_top100.jsonl \
  --dimensions-per-call 100 \
  --output samples/amazon_reviews_2023/persona_dimension_inference/pilot_2users_dpc100_readable.md
```

The report groups inferred attributes by schema category, includes the compact
evidence profile, and estimates cost from serialized prompt/output character
counts when `--user-histories` is provided. Exact billed token usage requires
persisted API usage metadata.

### V1 Persona Validation: Temporal Rating Holdout

Use `scripts/evaluate_amazon_persona_rating_holdout.py` to prepare the first
simple persona-validation benchmark from a current temporal-split
`user_histories.jsonl` export. The script assigns users to loose cohorts from
construction-split rating behavior only:

- `harsh_low`
- `high_variance`
- `mostly_5`
- `balanced_mixed`

It writes a labeled scoring target file, a blind product-context-only target file
for persona prediction, cohort/user summaries, and a Markdown report with MAE and
within-1-star rates for built-in non-personalized baselines.

```bash
python scripts/evaluate_amazon_persona_rating_holdout.py \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --output-dir raw/amazon_reviews_2023/persona_rating_holdout_eval
```

The blind prediction target file is
`raw/amazon_reviews_2023/persona_rating_holdout_eval/prediction_targets.jsonl`.
It excludes held-out review title, held-out review text, and true rating. Persona
prediction outputs can be scored by writing JSONL rows with `target_id` and
`predicted_rating`, then running:

```bash
python scripts/evaluate_amazon_persona_rating_holdout.py \
  --user-histories raw/amazon_reviews_2023/persona_dimension_inference/user_histories.jsonl \
  --predictions raw/amazon_reviews_2023/persona_rating_holdout_eval/persona_predictions.jsonl \
  --prediction-method-name persona_dims_summary \
  --output-dir raw/amazon_reviews_2023/persona_rating_holdout_eval
```

### Legacy Local Raw-Streaming Tools

`scripts/fetch_amazon_reviews_2023.py`,
`scripts/analyze_amazon_reviews_2023.py`, and
`scripts/retrieve_amazon_user_histories.py` are still available for small local
pilots or debugging raw source files. They stream category-level `.jsonl.gz`
files directly and are much slower for repeated candidate retrieval than the
Modal user-indexed workflow above.

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

## Output Layout

Downloads are stored under `raw/`:

- `raw/nemotron_personas_usa/`
- `raw/tencent_personahub/`
- `raw/google_synthetic_persona_chat/`
- `raw/oasis/user_data_36.json`
- `raw/apple_ml_primex/primexdata.csv`
- `raw/pandora_big5/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/synthlabs_persona/` (gated; sample JSONL, or `data/*.parquet` in full mode)
- `raw/amazon_reviews_2023/` (category samples, user histories, optional metadata, or raw `.jsonl.gz` files)
- `raw/personachat_facebook/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/horizonbench_mental_state_graphs/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/wildchat_allenai/` (sample JSONL, or `data/*.parquet` in full mode)
- `raw/literature_references/reference_registry.json`
- `raw/literature_references/reference_registry.jsonl`
- `raw/{reference_source_id}/`

`raw/` is git-ignored by default.
