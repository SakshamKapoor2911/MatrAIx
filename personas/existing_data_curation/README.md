# Existing Data Curation

This folder curates external persona datasets and reference-only literature sources for MatrAIx persona construction.

## Sources

Dataset manifests live in `manifests/`.

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

## Reference Sources (Didn't Get Added to Sources)

These manifests are grounding sources for later schema and attribute curation, but they have not yet been converted into `personas/dimensions+new.json`. Questionnaire items should still be converted into construct-level attribute labels before they are used as candidate attributes.

| Source | Claimed Constructs / Variables | Intended Use |
| --- | --- | --- |
| HEXACO-PI-R | 6 domains + 25 facets | Personality trait grounding |
| Facet MAP | 70 Big Five facet labels | Fine-grained personality traits |
| IPIP constructs and item pool | 276 scale labels; 3319 item pool entries | Public-domain trait construct and item reference |
| DeepPersona | 12 top-level categories; long-tail persona attribute taxonomy | Candidate attribute coverage and subcategory grounding; requires review before becoming dimensions |
| SCOPE-Persona | 135 protocol fields | Sociopsychological persona protocol reference |
| GSS cumulative codebook | 6518 variables | Official social survey grounding |
| World Values Survey Wave 7 | 153 questionnaire items | Values, beliefs, trust, politics, religion, and social attitudes |
| ACS PUMS | Curated demographic/population variables | Official demographic grounding layer |
| McAdams Three Levels of Personality | 3 theoretical levels | Schema theory and narrative identity grounding |
| Primal World Beliefs | World-belief constructs | Worldview grounding |
| BIS/BAS | Behavioral inhibition and activation constructs | Motivation and affective disposition grounding |
| Grit / perseverance | Perseverance and long-term effort constructs | Motivation and persistence grounding |
| Growth mindset | Malleability-of-ability belief construct | Cognitive and motivation grounding |

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

`raw/` is git-ignored by default.
