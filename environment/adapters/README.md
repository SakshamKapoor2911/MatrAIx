# Environment Adapters

Adapters convert external benchmarks into Harbor-compatible task directories.
They belong under `environment/adapters/<adapter-name>/` because they are
runtime integration code, not Persona schema or application task definitions.

## Layout

Each adapter should keep its code and generated outputs local to its own
directory:

```text
environment/adapters/
  manifest.schema.json
  <adapter-name>/
    README.md
    manifest.toml
    pyproject.toml
    src/<package-name>/
    _generated/       ignored local output
```

Generated tasks, downloaded datasets, trajectories, screenshots, videos, and
historical job outputs do not belong in git. Put them under the adapter-local
`_generated/` directory while developing, then upload selected artifacts to
external storage and link them from documentation.

## Manifest

Every adapter must include `manifest.toml` with:

- source repository, path, and commit
- target path in Playground
- package name and Python package import name
- owner or original author
- external data and credential requirements
- smoke commands that validate the adapter without writing to shared paths
- excluded source paths, especially lockfiles and generated outputs
- status: `enabled`, `experimental`, or `archived`

Use `manifest.schema.json` as the contract for required fields.

## Contribution Rules

- Do not add a top-level `adapters/` directory.
- Do not write generated benchmark data to top-level `datasets/` or `jobs/`.
- Keep optional adapter dependencies inside the adapter package.
- Add focused tests under `tests/environment/` for path policy, packaging, and
  lightweight smoke behavior.
- Import adapters in small, reviewable PRs instead of bulk-copying the full
  MatrAIx adapter tree.

## Current Adapters

- `simpleqa/`: experimental OpenAI SimpleQA adapter migrated from
  `MatrAIx-ai/MatrAIx/adapters/simpleqa`.
