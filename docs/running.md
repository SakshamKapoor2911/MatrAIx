# Running PersonaBench

This guide documents the curated PersonaBench `main` workflow after the
MatrAIx migration. It uses only paths that exist in clean `main`; raw MatrAIx
snapshots, generated jobs, and full persona datasets are intentionally excluded.

## Prerequisites

- Python 3.12.
- [`uv`](https://docs.astral.sh/uv/) for local virtual environments.
- Node.js 20.19.0 or newer for the optional viewer frontend in `apps/viewer/`.
- Docker for Harbor task execution.
- Optional model API keys for non-oracle agents, usually via `.env` or shell
  exports such as `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.

## Install

Use the **wide install** in [README.md — Step 1](../README.md#step-1--clone-and-install)
from the repository root (root package, `persona-eval`, `harbor-langsmith`,
`rewardkit`, `simpleqa`, and test deps). That is the default for new
contributors.

Minimal install (core Harbor only, no optional packages):

```bash
uv venv --python 3.12
uv pip install -e .
uv pip install pytest pytest-asyncio
```

## Verify The Checkout

Run the curated Python test suite after installing the optional packages above:

```bash
PYTHONPATH=.:environment/runtime:packages/persona-eval/src:application/persona_eval \
  uv run pytest tests/ \
    packages/harbor-langsmith/tests/ \
    packages/rewardkit/tests/ \
    application/persona_eval/backend/tests/ \
    tests/environment/test_application_tasks.py
```

If you only installed the root package, run the core tests:

```bash
uv run pytest tests/
```

Run Ruff:

```bash
uv run ruff check .
```

## Run The No-Key Smoke Task

This checks the Harbor runtime, Docker task build, oracle agent path, and
minimal example task. It does not require model API keys.

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

The task lives at `examples/tasks/hello-world/`. Generated job outputs go under
`jobs/` by default and should not be committed.

## Run A Persona Application Example

The curated application recipes use the checked-in sample persona dataset under
`persona/datasets/bench-dev-sample/`.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

Other curated local recipes live in `configs/jobs/example-job-recipe/`.
Computer-use and web recipes may require additional local platform, browser, or
agent setup; start with the survey or smoke recipes when validating a fresh
checkout.

## Inspect Results

Use the Harbor viewer after a job exists:

```bash
uv run harbor view jobs --build
```

The viewer frontend source lives in `apps/viewer/`; generated frontend build
output and job artifacts should stay out of git.

To work on the viewer itself:

```bash
cd apps/viewer
npm ci
npm run typecheck
npm run dev
```

The viewer pins its tested local runtime in `apps/viewer/.node-version` and
`apps/viewer/.nvmrc`. CI uses the same version file before running
`npm run typecheck`.

## Run The SimpleQA Adapter

Install the adapter package:

```bash
uv pip install -e environment/adapters/simpleqa
```

Generate a small local SimpleQA task sample:

```bash
uv run simpleqa --output-dir environment/adapters/simpleqa/_generated/simpleqa --limit 50 --overwrite
```

Run the adapter-local recipe:

```bash
uv run harbor run -c environment/adapters/simpleqa/run_simpleqa.yaml
```

SimpleQA downloads the public OpenAI SimpleQA CSV. LLM judge evaluation requires
`OPENAI_API_KEY`. Generated adapter data belongs under
`environment/adapters/simpleqa/_generated/` and should not be committed.

## External Artifacts

Full generated persona datasets, attribute-pool outputs, and historical MatrAIx
jobs are not in clean `main`. Their upload checklist and HuggingFace path slots
are tracked in `migration/matraix/README.md`.

After those artifacts are uploaded, update the relevant module README with the
published URL before adding recipes that depend on them.
