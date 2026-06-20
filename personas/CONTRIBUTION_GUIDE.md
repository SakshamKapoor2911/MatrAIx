# Contributing to MatrAIx Persona Dimensions

Complete guide for adding new datasets and persona dimensions to `dimensions+new.json` with full attribution tracking.

---

## Quick Start (5 Steps)

1. **Create manifest** — `manifests/{source_id}.json` with dataset metadata
2. **Add fetch function** — Update `scripts/fetch_sources.py` with download logic
3. **Update README** — Add row to `existing_data_curation/README.md`
4. **Add dimensions** — Entries in `dimensions+new.json` with full `source_origin` metadata
5. **Set attribution** — Add your GitHub username to `contributor_github` field

---

## File Structure

```
/home/yuexing/MatrAIx/personas/
├── dimensions+new.json                      ← Main dimension file (1,316 dims)
├── CONTRIBUTION_GUIDE.md                    ← This file
├── DIMENSIONS_ADDITIONS_SUMMARY.md           ← Example of complete addition
│
└── existing_data_curation/
    ├── README.md                            ← Data source overview
    ├── HORIZONBENCH_DIMENSIONS.txt          ← Reference list
    ├── manifests/                           ← 10 manifest JSON files
    │   ├── personachat_facebook.json
    │   ├── horizonbench_mental_state_graphs.json
    │   ├── wildchat_allenai.json
    │   └── ...7 more sources
    └── scripts/
        └── fetch_sources.py                 ← Download script
```

---

## Step 1: Create Manifest File

Each dataset needs a manifest in `existing_data_curation/manifests/{source_id}.json`.

**File Format:**

```json
{
  "id": "unique_source_id",
  "source": {
    "type": "huggingface_dataset|github_raw_file",
    "repo_id": "org/repo-name",
    "url": "https://...",
    "config": "optional_hf_config_name"
  },
  "dimensions_claimed": 5,
  "format": "parquet|csv|json|jsonl",
  "license": "cc-by-4.0",
  "gated": false,
  "notes": "Optional description of the dataset."
}
```

**Example: HorizonBench mental_state_graphs**

```json
{
  "id": "horizonbench_mental_state_graphs",
  "source": {
    "type": "huggingface_dataset",
    "repo_id": "stellalisy/HorizonBench",
    "url": "https://huggingface.co/datasets/stellalisy/HorizonBench",
    "config": "mental_state_graphs"
  },
  "dimensions_claimed": 30,
  "format": "parquet",
  "license": "cc-by-4.0",
  "notes": "HorizonBench: Long-Horizon Personalization with Evolving Preferences (Li et al., arXiv:2604.17283, April 2026). 360 user timelines, 1.6M conversation turns."
}
```

---

## Step 2: Add Fetch Function

Add a function to `existing_data_curation/scripts/fetch_sources.py`.

**Add constants at top:**
```python
MYNEWDATASET_REPO = "org/dataset-name"
MYNEWDATASET_CONFIG = "optional_config"  # if HF dataset has multiple configs
```

**Add fetch function:**
```python
def fetch_mynewdataset(args: argparse.Namespace, target_root: Path) -> None:
    out_dir = target_root / "mynewdataset_slug"
    ensure_dir(out_dir)

    if args.mode == "full":
        log("Fetching full MyNewDataset (all parquet shards).")
        snapshot_download(
            repo_id=MYNEWDATASET_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return

    sample_out = out_dir / f"mynewdataset_sample_{args.sample_rows}.jsonl"
    save_jsonl_sample(
        repo_id=MYNEWDATASET_REPO,
        output_path=sample_out,
        sample_rows=args.sample_rows,
        token=args.hf_token,
        config_name=MYNEWDATASET_CONFIG,
    )
```

**Register in main():**

1. Add to `--source` argument choices:
```python
choices=["all", "nemotron", "...", "mynewdataset"]
```

2. Add to `source_to_runner` mapping:
```python
source_to_runner = {
    "nemotron": fetch_nemotron,
    # ...
    "mynewdataset": fetch_mynewdataset,
}
```

3. Add to `selected_sources` list (for "all" mode):
```python
selected_sources = (
    ["nemotron", "personahub", "oasis", "ml_primex", "synthetic_persona_chat", "pandora", "personachat", "horizonbench", "wildchat", "mynewdataset"]
    if args.source == "all"
    else [args.source]
)
```

---

## Step 3: Update README

Add a row to the **Sources** table in `existing_data_curation/README.md`:

```markdown
| My New Dataset | 5 | Hugging Face dataset: `org/dataset-name` |
```

---

## Step 4: Add Dimensions to dimensions+new.json

Create dimension entries with full source traceability.

**Schema:**

```json
{
  "id": "unique_dimension_id",
  "label": "DatasetName_DimensionName",
  "category": "External Curation",
  "description": "Human-readable description of this dimension.",
  "values": ["Unknown"],
  "source_origin": {
    "source_id": "manifest_id",
    "source_name": "Human-readable source name",
    "source_type": "huggingface_dataset|github_raw_file",
    "huggingface_repo": "org/repo",
    "huggingface_url": "https://huggingface.co/datasets/org/repo",
    "paper_url": "https://arxiv.org/abs/XXXX.XXXXX",
    "manifest_file": "personas/existing_data_curation/manifests/manifest_id.json",
    "fetch_script": "personas/existing_data_curation/scripts/fetch_sources.py",
    "config": "hf_config_name",
    "column_name": "original_column_name_in_dataset",
    "license": "cc-by-4.0",
    "contributor_github": "your-github-username",
    "added_date": "YYYY-MM-DD",
    "note": "Optional notes"
  }
}
```

**Field Explanations:**

| Field | Required | Purpose |
|-------|----------|---------|
| `id` | ✅ | Unique ID (snake_case, no spaces) |
| `label` | ✅ | Format: `DatasetName_DimensionName` |
| `category` | ✅ | Use "External Curation" for new external datasets |
| `description` | ✅ | What this dimension represents (1-2 sentences) |
| `values` | ✅ | Use `["Unknown"]` initially; populate later |
| `source_origin.source_id` | ✅ | ID from manifest file |
| `source_origin.source_name` | ✅ | Human-readable dataset name |
| `source_origin.source_type` | ✅ | "huggingface_dataset" or "github_raw_file" |
| `source_origin.huggingface_repo` | ✅ | HF repo ID (e.g., "org/dataset") |
| `source_origin.huggingface_url` | ✅ | Full URL to HF dataset |
| `source_origin.paper_url` | ✅ | arXiv or DOI URL |
| `source_origin.manifest_file` | ✅ | Path to manifest file |
| `source_origin.fetch_script` | ✅ | Path to fetch script |
| `source_origin.config` | ⚠️ | Only if HF dataset has multiple configs |
| `source_origin.column_name` | ✅ | Original column/field name in dataset |
| `source_origin.license` | ✅ | SPDX license string |
| `source_origin.contributor_github` | ✅ | **Your GitHub username** |
| `source_origin.added_date` | ✅ | YYYY-MM-DD |
| `source_origin.note` | ⚠️ | Privacy considerations, caveats, etc. |

**Example (1 HorizonBench dimension):**

```json
{
  "id": "horizonbench_dimension_4",
  "label": "HorizonBench_Communication_Intimacy",
  "category": "External Curation",
  "description": "Preference evolution domain tracking how users prefer communication intimacy level.",
  "values": ["Unknown"],
  "source_origin": {
    "source_id": "horizonbench_mental_state_graphs",
    "source_name": "HorizonBench (mental_state_graphs)",
    "source_type": "huggingface_dataset",
    "huggingface_repo": "stellalisy/HorizonBench",
    "huggingface_url": "https://huggingface.co/datasets/stellalisy/HorizonBench",
    "paper_url": "https://arxiv.org/abs/2604.17283",
    "manifest_file": "personas/existing_data_curation/manifests/horizonbench_mental_state_graphs.json",
    "fetch_script": "personas/existing_data_curation/scripts/fetch_sources.py",
    "config": "mental_state_graphs",
    "column_name": "communication_intimacy",
    "license": "cc-by-4.0",
    "contributor_github": "yuexing",
    "added_date": "2026-06-20"
  }
}
```

---

## Step 5: Update targetDimensions

Update the top-level field in `dimensions+new.json`:

```json
{
  "schemaVersion": "2.0",
  "targetDimensions": 1350,  // increment this to new total
  "dimensions": [...]
}
```

---

## Automation: Add Multiple Dimensions

For bulk additions, use a Python script:

```python
#!/usr/bin/env python3
import json
from datetime import date
from pathlib import Path

dimensions_file = Path("dimensions+new.json")
with open(dimensions_file, "r", encoding="utf-8") as f:
    data = json.load(f)

new_dimensions = [
    {
        "id": "mynew_dim_1",
        "label": "MyDataset_Dimension1",
        "category": "External Curation",
        "description": "...",
        "values": ["Unknown"],
        "source_origin": {
            "source_id": "mynewdataset",
            "source_name": "My New Dataset",
            "source_type": "huggingface_dataset",
            "huggingface_repo": "org/dataset",
            "huggingface_url": "https://...",
            "paper_url": "https://arxiv.org/abs/...",
            "manifest_file": "personas/existing_data_curation/manifests/mynewdataset.json",
            "fetch_script": "personas/existing_data_curation/scripts/fetch_sources.py",
            "column_name": "dim_1",
            "license": "cc-by-4.0",
            "contributor_github": "your-username",
            "added_date": str(date.today()),
        }
    }
    # ... more dimensions
]

data["dimensions"].extend(new_dimensions)
data["targetDimensions"] = len(data["dimensions"])

with open(dimensions_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Added {len(new_dimensions)} dimensions")
```

---

## Attribution: contributor_github Field

Every dimension includes your GitHub username:

```json
"contributor_github": "your-github-username"
```

This enables:
- **Tracking** — Find all your contributions
- **Attribution** — Proper credit in the codebase
- **Accountability** — Audit trail for dimensions
- **Impact** — Measure your contribution to MatrAIx

**Query to find all YOUR dimensions:**
```bash
jq '.dimensions[] | select(.source_origin.contributor_github == "your-username")' dimensions+new.json
```

**Count your contributions:**
```bash
jq '[.dimensions[] | select(.source_origin.contributor_github == "your-username")] | length' dimensions+new.json
```

**See all contributors and their counts:**
```bash
jq '[.dimensions[] | .source_origin.contributor_github] | group_by(.) | map({contributor: .[0], count: length})' dimensions+new.json
```

---

## Real-World Example: HorizonBench

This is what we did in June 2026. Follow this pattern for your dataset.

### 1. Manifest File
**File:** `manifests/horizonbench_mental_state_graphs.json`
```json
{
  "id": "horizonbench_mental_state_graphs",
  "source": {
    "type": "huggingface_dataset",
    "repo_id": "stellalisy/HorizonBench",
    "url": "https://huggingface.co/datasets/stellalisy/HorizonBench",
    "config": "mental_state_graphs"
  },
  "dimensions_claimed": 30,
  "format": "parquet",
  "license": "cc-by-4.0",
  "notes": "HorizonBench: Long-Horizon Personalization with Evolving Preferences..."
}
```

### 2. Fetch Function
**In:** `scripts/fetch_sources.py`
```python
HORIZONBENCH_REPO = "stellalisy/HorizonBench"
HORIZONBENCH_CONFIG = "mental_state_graphs"

def fetch_horizonbench(args: argparse.Namespace, target_root: Path) -> None:
    out_dir = target_root / "horizonbench_mental_state_graphs"
    ensure_dir(out_dir)

    if args.mode == "full":
        log("Fetching full HorizonBench mental_state_graphs dataset...")
        snapshot_download(
            repo_id=HORIZONBENCH_REPO,
            repo_type="dataset",
            local_dir=str(out_dir),
            allow_patterns=["README.md", "data/*.parquet"],
            token=args.hf_token,
            resume_download=True,
            max_workers=args.max_workers,
        )
        return

    sample_out = out_dir / f"horizonbench_mental_state_graphs_sample_{args.sample_rows}.jsonl"
    save_jsonl_sample(
        repo_id=HORIZONBENCH_REPO,
        config_name=HORIZONBENCH_CONFIG,
        output_path=sample_out,
        sample_rows=args.sample_rows,
        token=args.hf_token,
    )
```

### 3. README Update
**Added to:** `existing_data_curation/README.md`
```markdown
| HorizonBench (mental_state_graphs) | 30 | Hugging Face dataset: `stellalisy/HorizonBench` (`mental_state_graphs` config) |
```

### 4. Dimensions
**Added 30 dimension entries to:** `dimensions+new.json`

Each one like:
```json
{
  "id": "horizonbench_dimension_4",
  "label": "HorizonBench_Communication_Intimacy",
  "category": "External Curation",
  "description": "Preference evolution domain...",
  "values": ["Unknown"],
  "source_origin": {
    "source_id": "horizonbench_mental_state_graphs",
    "source_name": "HorizonBench (mental_state_graphs)",
    "source_type": "huggingface_dataset",
    "huggingface_repo": "stellalisy/HorizonBench",
    "huggingface_url": "https://huggingface.co/datasets/stellalisy/HorizonBench",
    "paper_url": "https://arxiv.org/abs/2604.17283",
    "manifest_file": "personas/existing_data_curation/manifests/horizonbench_mental_state_graphs.json",
    "fetch_script": "personas/existing_data_curation/scripts/fetch_sources.py",
    "config": "mental_state_graphs",
    "column_name": "communication_intimacy",
    "license": "cc-by-4.0",
    "contributor_github": "yuexing",
    "added_date": "2026-06-20"
  }
}
```

### 5. Update targetDimensions
```json
{ "targetDimensions": 1316 }  // was 1282
```

### Result
✅ 30 dimensions added  
✅ Full source traceability  
✅ Fetch script works  
✅ Attribution tracked  
✅ All queryable by contributor

See `DIMENSIONS_ADDITIONS_SUMMARY.md` for the complete record.

---

## Pre-Submission Checklist

Before submitting a pull request:

- [ ] Manifest file created and valid JSON (`jq . manifests/{source_id}.json`)
- [ ] Fetch function added to `fetch_sources.py`
- [ ] Fetch function registered in `--source` choices
- [ ] Fetch function added to `source_to_runner` mapping
- [ ] Fetch function added to `selected_sources` list
- [ ] Python syntax valid (`python -m py_compile scripts/fetch_sources.py`)
- [ ] `existing_data_curation/README.md` updated with new source row
- [ ] Dimensions added to `dimensions+new.json`
- [ ] Each dimension has full `source_origin` metadata
- [ ] Each dimension has `contributor_github` set to your GitHub username
- [ ] Each dimension has `added_date` set (YYYY-MM-DD format)
- [ ] JSON syntax valid (`jq . dimensions+new.json`)
- [ ] `targetDimensions` field updated to new total
- [ ] Dimension counts verified (original + new = total)
- [ ] Created summary document (optional but recommended)

---

## Queries & Examples

**Find all dimensions from HorizonBench:**
```bash
jq '.dimensions[] | select(.source_origin.source_id == "horizonbench_mental_state_graphs")' dimensions+new.json
```

**Count dimensions from HorizonBench:**
```bash
jq '[.dimensions[] | select(.source_origin.source_id == "horizonbench_mental_state_graphs")] | length' dimensions+new.json
```

**Find all dimensions by contributor yuexing:**
```bash
jq '.dimensions[] | select(.source_origin.contributor_github == "yuexing") | .label' dimensions+new.json
```

**List all contributors and their dimension counts:**
```bash
jq '[.dimensions[] | .source_origin.contributor_github] | group_by(.) | map({contributor: .[0], count: length})' dimensions+new.json
```

**Export all dimensions as TSV (for spreadsheet):**
```bash
jq -r '.dimensions[] | "\(.id)\t\(.label)\t\(.source_origin.source_name)\t\(.source_origin.contributor_github)\t\(.source_origin.added_date)"' dimensions+new.json | column -t
```

---

## Common Issues

**Q: What if I don't have the exact dimension values?**
A: Use `["Unknown"]` as placeholder. Plan to enumerate values later.

**Q: Can I contribute dimensions to an existing dataset?**
A: Yes! Create new dimensions with your `contributor_github`. Each person can add their own.

**Q: What if I made a mistake in my submission?**
A: Create a new dimension with a corrected label/description and note the predecessor.

**Q: How do I verify my dimensions were added?**
A: Run the query:
```bash
jq '.dimensions[] | select(.source_origin.contributor_github == "your-username") | length' dimensions+new.json
```

**Q: Can I download/fetch data from my contributed dataset?**
A: Yes! After fetch function is merged:
```bash
cd existing_data_curation
python scripts/fetch_sources.py --source yourdataset --mode sample
```

---

## Next Steps After First Contribution

1. Review `DIMENSIONS_ADDITIONS_SUMMARY.md` for a complete example
2. Check `existing_data_curation/HORIZONBENCH_DIMENSIONS.txt` for reference format
3. Study other manifests in `existing_data_curation/manifests/`
4. Explore other fetch functions in `existing_data_curation/scripts/fetch_sources.py`
5. Help document and deduplicate dimensions (future work)

---

## Questions?

1. **How do I find the exact column names?** → Check the dataset card on HuggingFace or read the paper
2. **What license should I use?** → Check the dataset's official license (CC-BY-4.0, ODC-BY, etc.)
3. **Should I add metadata notes?** → Yes, especially for privacy considerations or data quality caveats
4. **Can I edit someone else's dimension?** → No; create a new version with your name instead

---

**Last updated:** 2026-06-20  
**Current contributors:** yuexing (40 dimensions)  
**Total dimensions:** 1,316
