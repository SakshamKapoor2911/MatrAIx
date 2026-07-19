Amazon Review Persona Inference Protocol

This protocol runs the Amazon Reviews 2023 persona inference pipeline inside the
offline collaboration runner. It does not use the Wikipedia field-extraction
prompt. Instead, the range runner applies the two-stage Amazon pipeline:

1. Build compact review memory from the construction split in `reviews`.
2. Map that review memory to allowed values in `persona/schema/dimensions.json`.

Rules:
- Use only the construction split in `reviews` for persona construction.
- Do not use `validation_reviews` for persona construction.
- Omit unsupported dimensions instead of guessing.
- Use product metadata only to interpret reviewed items.
- Do not infer sensitive demographics, health, family, socioeconomic,
  political, religious, or identity attributes unless review text explicitly
  states them.
- Every accepted inferred attribute must cite construction-review evidence.
- Every accepted value must be one of the allowed values for that schema
  dimension.

The executable prompts are defined in
`scripts/infer_amazon_review_dimensions.py` because this protocol is a
two-stage pipeline rather than a single prompt.
