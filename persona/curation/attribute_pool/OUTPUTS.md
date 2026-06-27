# Attribute Pool Outputs

The original MatrAIx attribute-pool work includes large generated outputs such
as normalized JSONL pools, graph files, LLM adjudication prompts, and CSV
exports.

Those files were intentionally excluded from this curated import because several
are tens of megabytes each and are generated artifacts rather than source code.

Excluded examples from MatrAIx:

- `persona/attribute_pool/outputs/normalized/candidate_pool_raw_extended_normalized.jsonl`
- `persona/attribute_pool/outputs/step5_embedding_llm_dedup/embedding_retrieved_pairs.csv`
- `persona/attribute_pool/outputs/normalized/candidate_pool_raw_extended_normalized.csv`
- `persona/attribute_pool/dataset/scope_structured.jsonl`
- `persona/attribute_pool/outputs/candidate_pool_raw_extended.jsonl`

If these artifacts are needed, use one of:

- external dataset storage
- Git LFS after maintainer approval
- small fixtures derived from the large outputs
- regenerated outputs from the scripts in `scripts/`

Do not add generated `outputs/` files to normal PRs. PRs that update this
pipeline should describe the command used, the source inputs, and the resulting
artifact location.
