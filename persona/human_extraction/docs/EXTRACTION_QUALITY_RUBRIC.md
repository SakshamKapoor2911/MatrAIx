# Persona Extraction: Extraction-Quality Rubric

**Purpose.** Score how well an automatic extraction (the Qwen3.6-35B persona extractor) turned a
*source profile* into structured persona *fields*. One rubric, two raters: an **LLM judge** and
**human annotators** apply the *same* seven metrics and the *same* 1–5 Likert scale, so their scores
are directly comparable and we can measure agreement. This formalizes the manual-scoring approach
sketched in `BENCHMARK.md` §8 and drives the 100-persona extraction-quality human validation
(sample, score, majority vote).

**Unit of scoring.** One extracted persona record at a time. The rater sees two things:

- the **source profile** (the ground truth; everything is judged against this), and
- the **extracted fields**, each with `field_id`, `value`, `evidence`, `assignment_type`, `confidence`.

**Order of work (top to bottom):**

1. **Step 1 (quality of what it extracted, field by field):** M1 value → M2 evidence → M3 description
2. **Step 2 (did it extract the right set, whole record):** M4 over-claim → M5 coverage
3. **Step 3 (coherence & gut check):** M6 consistency → M7 overall

Each metric looks at a **different part** of the record: M1–M3 judge the `value` / `evidence` /
`description` fields, M4–M5 judge the *set* of attributes, M6 judges *across* fields, and M7 judges
the whole.

## The 1–5 Likert scale (shared by every metric)

| Score | Meaning | Rule of thumb |
|:--:|---|---|
| **5** | No problem | nothing a careful reader would flag |
| **4** | Minor issue | cosmetic; does not mislead |
| **3** | Moderate issue | a few clear errors; usable only with caution |
| **2** | Major issue | many or serious errors; misleading |
| **1** | Completely wrong | unusable for this person |

Each metric below spells out the five levels concretely. Use `n/a` when a metric does not apply to a
record (for example, M3 when the record has no `description` field).

## Metrics

### Step 1: quality of what it extracted (look at each field)

**M1. Value accuracy** (for attributes the profile supports, is the `value` in the right bucket?)
- **5:** almost all values correct
- **4:** one or two borderline-bucket slips, nothing that misleads
- **3:** several values in the wrong bucket
- **2:** many wrong, some plainly contradict the profile
- **1:** values broadly contradict the profile
- *Example:* profile says "born 1809, died 1865", so `age_bracket = 55–64` fits (56 at death) and scores 5; `age_bracket = 25–34` is a wrong bucket and pulls M1 down.

**M2. Evidence grounding** (is each `evidence` a real span from the profile that supports the value?)
- **5:** quotes are present in the profile and genuinely support the value
- **4:** mostly grounded; a couple of weak-but-not-wrong quotes
- **3:** some evidence weak, loose, or only tangentially related
- **2:** much evidence fabricated or mismatched to its value
- **1:** evidence largely missing or fabricated
- *Example:* for `urbanicity = Rural`, evidence "Born in a one-room log cabin in Kentucky" supports it (5); evidence "led the United States" says nothing about rural/urban, so it is mismatched and scores low.

**M3. Description faithfulness** (does any `description` / free text invent or exaggerate?)
- **5:** concrete, accurate, traceable to the profile
- **4:** minor vagueness, no invention
- **3:** some vague or mildly exaggerated detail
- **2:** notable invented or exaggerated detail
- **1:** fabricates detail or contradicts the profile
- *Example:* description "self-educated frontier lawyer" is traceable to the profile (5); "beloved by all Americans, never told a lie" exaggerates beyond it and scores low.
- *(score `n/a` if this record has no `description` field)*

### Step 2: did it extract the right set (step back to the whole record)

**M4. No over-claiming** (did it assign values to attributes the profile does *not* support?)
- **5:** nothing invented; unsupported attributes left null
- **4:** a single thin-evidence call
- **3:** a few over-claims on thin evidence
- **2:** several hallucinated attributes
- **1:** many hallucinated attributes
- *Example:* the profile never mentions marriage, so `demo_marital_status = null (unsupported)` is correct (5); filling `demo_marital_status = Married` with no evidence is an over-claim and scores low.

**M5. Coverage** (did it miss attributes the profile clearly states?)
- **5:** almost everything the profile states is captured
- **4:** caught the obvious, missed one or two
- **3:** got the obvious, missed some
- **2:** missed a lot of clearly stated attributes
- **1:** misses most of what the profile states
- *Example:* the profile clearly states his occupation ("became a lawyer", "president"); capturing `occupation` scores well, leaving it empty despite that clear statement lowers coverage.
- *(judge on the full record, not on a short field excerpt)*

### Step 3: coherence & gut check

**M6. Internal consistency** (do fields contradict each other? age ↔ generation ↔ life_stage, job ↔ region, …)
- **5:** fully coherent, all fields fit one person
- **4:** one very mild tension
- **3:** one or two mild tensions
- **2:** a clear contradiction between fields
- **1:** fields clearly contradict each other
- *Example:* `age_bracket = 55–64` with `life_stage = Adolescent`, or `region = North America` with `nationality = Japanese`, are contradictions and score low; fields that all fit one person score 5.

**M7. Overall fidelity** (could you faithfully role-play this person from the record?)
- **5:** faithful and usable as-is
- **4:** broadly right, a couple of harmless errors
- **3:** broadly right, several misleading errors
- **2:** distorted in important ways
- **1:** seriously distorted, not this person
- *Example:* from the example record below you could plausibly role-play a 19th-century American statesman (5); if half the fields were wrong or invented, you would be role-playing a different person, which scores low.

> **Note on M7.** It is a deliberate summary gut-check, so it will correlate with M1–M6. For a more
> *independent* seventh signal, swap it for **Assignment-type correctness**: is each field labeled
> `direct` / `summary_inference` / `structured_claim` / `unsupported` correctly? (same 1–5 scale).

## How the two raters use this rubric

**LLM judge.** Give it the source profile, the extracted fields, and this rubric, and require a
**structured** result: one JSON object, one entry per metric, each with a `score` and a short `reason`
that cites the field(s) or profile span that drove it.

```json
{
  "M1_value":       {"score": 5, "reason": "..."},
  "M2_evidence":    {"score": 4, "reason": "..."},
  "M3_description": {"score": "n/a", "reason": "no description field"},
  "M4_overclaim":   {"score": 5, "reason": "..."},
  "M5_coverage":    {"score": 3, "reason": "..."},
  "M6_consistency": {"score": 5, "reason": "..."},
  "M7_overall":     {"score": 4, "reason": "..."}
}
```

**Human annotators.** Same seven scores per record, entered in a scoring sheet (one row per record).
For the 100-persona validation, put **≥2 annotators on each record** and take the **majority vote**, so
we can:
- measure **inter-rater reliability** among humans (e.g. quadratic-weighted κ or Krippendorff's α), and
- **calibrate the LLM judge against humans** (per-metric agreement and correlation on the same records).

## Worked example (calibration anchor)

> ⚠️ **Illustrative placeholder, not a sampled validation record.** This repo does not yet ship the
> Qwen-extracted persona dataset, so the record below is a minimal, hand-checked example (a real
> Wikipedia source profile with real extraction fields) whose only job is to anchor the scale. Replace
> it with a **sampled real Qwen extraction** once that dataset is available; the full extractor output
> also carries a `description` field and the complete ~1,290-attribute record, which this cut-down
> example does not show.

**Source profile** (ground truth):

> Abraham Lincoln (February 12, 1809 – April 15, 1865) was the 16th president of the United States,
> serving from 1861 until his assassination in 1865. Born into poverty in a one-room log cabin in
> Kentucky, he became a lawyer and Whig Party leader, led the Union through the Civil War, and
> abolished slavery with the Emancipation Proclamation.

**Extracted fields:**

| field_id | value | evidence | assignment_type | conf |
|---|---|---|---|:--:|
| age_bracket | 55–64 | (February 12, 1809 - April 15, 1865) | structured_claim | 0.40 |
| region | North America | the 16th president of the United States | structured_claim | 0.96 |
| gender_identity | Man | He led the United States | direct | 0.95 |
| urbanicity | Rural | Born in a one-room log cabin in Kentucky | summary_inference | 0.45 |
| demo_marital_status | *(null)* | *(empty)* | unsupported | 0.00 |

**Scores** (one line each, scored honestly against the anchors above):

| metric | score | note |
|---|:--:|---|
| M1 Value accuracy | 5 | every value matches the profile |
| M2 Evidence grounding | 5 | each quote is taken verbatim from the profile |
| M3 Description faithfulness | n/a | this cut-down record has no `description` field |
| M4 No over-claiming | 5 | nothing invented; `demo_marital_status` correctly left null |
| M5 Coverage | n/a | judge on the full record, not the five fields shown |
| M6 Internal consistency | 5 | all fields fit one coherent person |
| M7 Overall fidelity | 5 | faithful and fully grounded, no hallucination |
