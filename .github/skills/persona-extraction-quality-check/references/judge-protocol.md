# Persona Judge Protocol

This protocol operationalizes the canonical rubric without changing its scoring anchors.

## Reviewer isolation

A reviewer receives exactly one persona packet. Do not use aggregate statistics, other personas, or other judges' decisions as evidence. The packet's `source_profile` is the only ground truth for substantive scoring.

## Field inspection

Inspect every object in `extracted_persona.fields` in its original order.

For each non-null/supported field, assess:

- **Value:** correct bucket, borderline bucket, wrong, or contradicted.
- **Evidence:** actually present in the source; supports the selected value; preserves number, rank direction, time frame, and negation.
- **Description:** faithful, mildly exaggerated, invented, contradicted, or unavailable.
- **Assignment type:** note obvious mislabels, but do not replace M7 with assignment-type correctness unless the run configuration explicitly requests that rubric variant.

For `unsupported` or null fields, verify whether the source actually contains clear support. A false unsupported/null decision is a coverage miss under M5.

Output only flagged field findings, but count every inspected field. “No issues” is valid only when `checked_field_count` equals `extracted_field_count`.

## Record-level inspection

After field inspection:

- **M4:** list emitted attributes not adequately supported by the source.
- **M5:** list clearly stated source facts that should map to persona attributes but were missed. Do not penalize the extraction for information the schema cannot represent.
- **M6:** list contradictions across fields, including age/generation/life stage, employment/role, language, region, technology usage, and mutually incompatible preferences.
- **M7:** judge whether the complete extraction supports faithful role-play of this exact source respondent.

## Score discipline

- Use only integer scores 1–5, except M3 may be `"n/a"` when no description exists.
- Score 5 means a careful reviewer would flag nothing material.
- A plausible inference is not automatically grounded. Explain whether it is direct, same-construct inference, or cross-construct speculation.
- Do not lower M5 merely because the schema has 1,290 dimensions; score only clearly stated and representable facts.
- Do not reward verbosity.
- Do not infer quality from extraction confidence.
- Reasons must cite field IDs plus source columns or short source values.

## Required JSON output

Return one JSON object and no Markdown fences.

```json
{
  "schema_version": "1.0",
  "run_id": "<from task>",
  "persona_id": "<exact packet persona_id>",
  "identity": {
    "response_id": "<string or null>",
    "row_index": "<integer or null>"
  },
  "judge": {
    "requested_model": "<requested display name>",
    "actual_model": "<actual display name>",
    "reviewer_instance": "<optional worker/run identifier>"
  },
  "audit": {
    "extracted_field_count": 0,
    "checked_field_count": 0,
    "non_null_field_count": 0,
    "unsupported_or_null_field_count": 0,
    "description_present": true,
    "complete_field_pass": true
  },
  "flagged_fields": [
    {
      "ordinal": 0,
      "field_id": "<id>",
      "value": "<value or null>",
      "metrics": ["M1", "M2"],
      "severity": "minor|moderate|major",
      "finding": "<concise finding>",
      "source_citation": "<source column and short value, or 'not present'>"
    }
  ],
  "record_findings": {
    "overclaims": [
      {"field_id": "<id>", "finding": "<why unsupported>"}
    ],
    "missed_attributes": [
      {"source_column": "<column>", "source_value": "<short value>", "candidate_field_id": "<id or null>", "finding": "<what was missed>"}
    ],
    "contradictions": [
      {"field_ids": ["<id1>", "<id2>"], "finding": "<conflict>"}
    ]
  },
  "metrics": {
    "M1_value": {"score": 5, "reason": "<field-grounded reason>"},
    "M2_evidence": {"score": 5, "reason": "<source-grounded reason>"},
    "M3_description": {"score": "n/a", "reason": "no description field"},
    "M4_overclaim": {"score": 5, "reason": "<record-level reason>"},
    "M5_coverage": {"score": 5, "reason": "<record-level reason>"},
    "M6_consistency": {"score": 5, "reason": "<cross-field reason>"},
    "M7_overall": {"score": 5, "reason": "<whole-person reason>"}
  },
  "adjudication": {
    "recommended": false,
    "reason": ""
  }
}
```

## Self-check before returning

1. Confirm exactly one persona was reviewed.
2. Confirm every extracted field was inspected.
3. Confirm `checked_field_count == extracted_field_count`.
4. Confirm M1–M7 follow the canonical rubric rather than a custom scale.
5. Confirm all cited source claims are actually present in the packet.
6. Confirm the actual model name is truthful.
7. Confirm output parses as JSON.
