# Existing Data Curation

This folder curates external persona datasets for MatrAIx persona construction.

## Sources

| Source | Claimed Dimensions | Access |
| --- | --- | --- |
| NVIDIA Nemotron Personas USA | 21 | Hugging Face dataset: `nvidia/Nemotron-Personas-USA` |
| Tencent PersonaHub (elite) | 2 | Hugging Face dataset: `proj-persona/PersonaHub` (`elite_persona`) |
| Google Synthetic-Persona-Chat | 3 | CSV columns | Hugging Face dataset: `google/Synthetic-Persona-Chat` |
| OASIS Reddit user data | 6 | GitHub raw JSON file |
| Apple ML-PRIMEX | 43 | GitHub raw CSV file |
| TakeLab PANDORA (Big5 subset) | 6 | Hugging Face dataset: `jingjietan/pandora-big5` |
| SynthLabs PERSONA | 33 | Hugging Face dataset: `SynthLabsAI/PERSONA` (**gated** — accept terms + set `HF_TOKEN`) |
| Amazon Reviews 2023 | n/a | Category-level JSONL.GZ review and metadata files from McAuley Lab |

Manifests live in `manifests/`.

## Fetch Script

Use `scripts/fetch_sources.py` from this directory.

### 1) Sample-first fetch (recommended default)

```bash
cd /home/yuexing/MatrAIx/personas/existing_data_curation
python scripts/fetch_sources.py --source all --mode sample --sample-rows 1000
```

This will:
- sample `Nemotron`, `PersonaHub`, and `Synthetic-Persona-Chat` into JSONL files
- fully download the OASIS JSON and ML-PRIMEX CSV

`Synthetic-Persona-Chat` sample mode streams **Part 1 train only** (same pattern as Nemotron sample). Use full mode for all four CSV files (Part 1 train/valid/test plus Part 2).

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

Sample Part 1 train rows into JSONL (default 1000 rows):

```bash
python scripts/fetch_sources.py --source synthetic_persona_chat --mode sample --sample-rows 1000
```

Full download of all four CSV files (Part 1 splits plus Part 2):

```bash
python scripts/fetch_sources.py --source synthetic_persona_chat --mode full
```

After fetch, the script logs row counts and checks the three expected CSV column names.

### 5) Gated source: PERSONA

`SynthLabsAI/PERSONA` is gated. First accept the terms on the
[HF dataset page](https://huggingface.co/datasets/SynthLabsAI/PERSONA), then
export a token. It is excluded from `--source all`, so fetch it explicitly:

```bash
export HF_TOKEN=hf_...   # token for an account that accepted the terms
python scripts/fetch_sources.py --source synthpersona --mode sample --sample-rows 1000
```

## Amazon Reviews 2023 Retrieval

Use `scripts/fetch_amazon_reviews_2023.py` for the Amazon Reviews 2023 pivot.
The script streams category-level `.jsonl.gz` files and writes reviewer-level
histories for persona construction/evaluation.

List supported categories:

```bash
python scripts/fetch_amazon_reviews_2023.py --list-categories
```

Small pilot sample from one category:

```bash
python scripts/fetch_amazon_reviews_2023.py \
  --categories All_Beauty \
  --max-reviews-per-category 10000 \
  --min-user-reviews 3 \
  --max-users 1000
```

Pilot sample across application-relevant categories:

```bash
python scripts/fetch_amazon_reviews_2023.py \
  --categories Software,Electronics,Office_Products,Beauty_and_Personal_Care,Health_and_Household \
  --max-reviews-per-category 50000 \
  --min-user-reviews 5 \
  --max-users 5000 \
  --include-metadata
```

Full raw download for selected categories:

```bash
python scripts/fetch_amazon_reviews_2023.py \
  --mode full \
  --categories Software,Electronics \
  --include-metadata
```

Amazon output layout:

- `raw/amazon_reviews_2023/reviews/*_sample_*.jsonl`
- `raw/amazon_reviews_2023/metadata/meta_*_sample.jsonl`
- `raw/amazon_reviews_2023/user_histories/user_histories_*.jsonl`
- `raw/amazon_reviews_2023/raw_gz/*.jsonl.gz` for full downloads
- `raw/amazon_reviews_2023/manifest.json`

### Amazon Reviewer Pool Exploration

Use `scripts/analyze_amazon_reviews_2023.py` to find reviewers with enough
behavior for persona construction: many reviews, multiple categories, long
history span, and enough review text.

Example exploratory run:

```bash
python scripts/analyze_amazon_reviews_2023.py \
  --categories All_Beauty,Software,Office_Products,Electronics,Books \
  --start-year 2018 \
  --end-year 2023 \
  --min-reviews 30 \
  --min-categories 2 \
  --min-history-days 730 \
  --min-text-chars 5000 \
  --min-verified-share 0.7 \
  --top-n 0
```

Write a reusable all-user aggregate checkpoint while scanning:

```bash
python scripts/analyze_amazon_reviews_2023.py \
  --categories Sports_and_Outdoors,Health_and_Household \
  --start-year 2018 \
  --end-year 2023 \
  --min-reviews 30 \
  --min-categories 2 \
  --min-history-days 365 \
  --min-text-chars 5000 \
  --min-verified-share 0.7 \
  --top-n 0 \
  --write-user-state \
  --output-dir raw/amazon_reviews_2023/exploration/sports_health_2018_2023
```

Merge one or more aggregate checkpoints without rescanning remote category files:

```bash
python scripts/analyze_amazon_reviews_2023.py \
  --merge-only \
  --load-user-state raw/amazon_reviews_2023/exploration/base_2018_2023/all_user_stats.jsonl.gz \
  --load-user-state raw/amazon_reviews_2023/exploration/sports_health_2018_2023/all_user_stats.jsonl.gz \
  --categories Books,Kindle_Store,Movies_and_TV,Electronics,Office_Products,Home_and_Kitchen,Clothing_Shoes_and_Jewelry,Sports_and_Outdoors,Health_and_Household \
  --min-reviews 30 \
  --min-categories 2 \
  --min-history-days 365 \
  --min-text-chars 5000 \
  --min-verified-share 0.7 \
  --top-n 0 \
  --write-user-state \
  --output-dir raw/amazon_reviews_2023/exploration/base_plus_sports_health_2018_2023
```

Outputs:

- `raw/amazon_reviews_2023/exploration/summary.json`
- `raw/amazon_reviews_2023/exploration/candidate_users.jsonl`
- `raw/amazon_reviews_2023/exploration/all_user_stats.jsonl.gz` when `--write-user-state` is set

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

`raw/` is git-ignored by default.
