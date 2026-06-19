# Existing Data Curation

This folder curates external persona datasets for MatrAIx persona construction.

## Sources

| Source | Claimed Dimensions | Access |
| --- | --- | --- |
| NVIDIA Nemotron Personas USA | 21 | Hugging Face dataset: `nvidia/Nemotron-Personas-USA` |
| Tencent PersonaHub (elite) | 2 | Hugging Face dataset: `proj-persona/PersonaHub` (`elite_persona`) |
| OASIS Reddit user data | 6 | GitHub raw JSON file |
| Apple ML-PRIMEX | 43 | GitHub raw CSV file |

Manifests live in `manifests/`.

## Fetch Script

Use `scripts/fetch_sources.py` from this directory.

### 1) Sample-first fetch (recommended default)

```bash
cd /home/yuexing/MatrAIx/personas/existing_data_curation
python scripts/fetch_sources.py --source all --mode sample --sample-rows 1000
```

This will:
- sample `Nemotron` and `PersonaHub` into JSONL files
- fully download the OASIS JSON and ML-PRIMEX CSV

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

## Output Layout

Downloads are stored under `raw/`:

- `raw/nemotron_personas_usa/`
- `raw/tencent_personahub/`
- `raw/oasis/user_data_36.json`
- `raw/apple_ml_primex/primexdata.csv`

`raw/` is git-ignored by default.
