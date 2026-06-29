# Attributes

This application folder contains the persona attribute curation pipeline and
derived candidate-pool outputs used for the AI Persona project.

## Contents

- `attributes/`: scripts and methodology notes for building, normalizing,
  deduplicating, and organizing persona attribute candidates.
- `candidate_pool_outputs/`: generated candidate-pool outputs, normalization
  reports, category assignments, graph seeds, and LLM adjudication artifacts.
- `dataset/`: lightweight reference files copied from the local data workspace.

## Large Local Data

The original local workspace also contains raw downloaded datasets under
`dataset/` totaling more than 240 GB. Those files are intentionally not checked
into Git because they exceed normal GitHub repository limits. Recreate or
download those raw sources outside the repository when rerunning the full
pipeline.
