# GSS (General Social Survey) → MatrAIx 1,290 dimensions

Maps the **75,699** respondents of the raw NORC GSS 1972–2024 cumulative file
(`gss7224_r3.dta`, release 3) to the MatrAIx schema using **deterministic rules only — no LLM or
API**. GSS is a fully coded survey, so the observed (rule-based) layer *is* the whole extraction.

The crosswalk — `persona/curation/existing_data/scripts/crosswalks/gss.py` — maps 18 source variables
to their exact schema dimensions; every value is a direct survey response (`provenance: observed`).
Coarse / withheld / ambiguous codes resolve to `null`, never guessed. Richer than the thinned
submission GSS: exact integer age (65+ split resolved), `educ` distinguishing Primary…Doctorate, a
7-point `polviews`, and the `fefam` attitude item → `att_traditional_gender_roles`.

Source: NORC GSS, publicly released for research — <https://gss.norc.org/>.

## Download

Get `gss7224_r3.dta` (Stata) from the GSS Data Explorer / NORC — the 1972–2024 cross-sectional
cumulative file, release 3.

## Run (rule-based, no LLM)

Read the `.dta` with decoded labels, then apply the crosswalk + §8 through the **shared toolkit**
(no bespoke engine — reuses `crosswalk_engine` #235 and `postprocess_engine` #246):

```python
import pandas as pd, gzip, json
from crosswalk_engine import apply_crosswalk          # observed / rule layer (#235)
from postprocess_engine import load_schema, normalize  # §8 normalization (#246)
from crosswalks.gss import CROSSWALK                    # this PR

order, allowed = load_schema("persona/schema/dimensions.json")
df = pd.read_stata("gss7224_r3.dta", convert_categoricals=True)
with gzip.open("gss/extraction_v1/shard_00.jsonl.gz", "wt") as f:
    for i, row in df.iterrows():
        observed, _, _ = apply_crosswalk(row, CROSSWALK, allowed)   # 18 exact dims
        fields = normalize([], order, allowed, observed=observed)   # §8 → 1,290 fields
        f.write(json.dumps({"user_id": f"gss-{i:06d}", "fields": fields,
                            "observed": observed}) + "\n")
```

(Once #267 lands this is one command: `run_pipeline.py --observed-only --dataset crosswalks/gss.py`.)

## Validate — must be 0 errors

```bash
python persona/human_extraction/scripts/validate_extraction.py \
    --input gss/extraction_v1/shard_00.jsonl.gz --schema persona/schema/dimensions.json
```

## Statistics (release 3)

- Personas / unique users: **75,699 / 75,699**
- Fields per persona: 1,290
- Mean grounded (`direct`) dims per persona: **~14.6**
- Invalid values / assignments / lengths: **0**
- No LLM / API / cost

Output is published to `MatrAIx2026/MatrAIx-1290-extractions/gss/` (JSONL, 5 shards + manifest).
