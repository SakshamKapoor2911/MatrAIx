# SimpleQA Adapter

This adapter converts OpenAI SimpleQA into Harbor-compatible task directories.
It was migrated from `MatrAIx-ai/MatrAIx/adapters/simpleqa` into the
Playground environment module so external benchmark adapters do not create a
top-level adapter tree.

SimpleQA is a short-form factuality benchmark with 4,326 fact-seeking
questions. The adapter fetches the public SimpleQA CSV, writes task directories,
and grades answers with an LLM judge. Runtime evaluation requires
`OPENAI_API_KEY`.

## Repository Layout

```text
environment/adapters/simpleqa/
  README.md
  manifest.toml
  pyproject.toml
  run_simpleqa.yaml
  simpleqa_oracle.yaml
  simpleqa_parity_claude_opus4_6.yaml
  parity_experiment.json
  adapter_metadata.json
  src/simpleqa/
    adapter.py
    main.py
    task-template/
      task.toml
      instruction.md
      environment/Dockerfile
      solution/solve.sh
      tests/test.sh
      tests/llm_judge.py
  _generated/       ignored local output
```

The source `uv.lock` is intentionally excluded. Generated datasets should stay
under `_generated/` and should not be committed.

## Install

From the Playground repository root:

```bash
python -m pip install -e environment/adapters/simpleqa
```

## Generate Tasks

Generate a small local sample:

```bash
simpleqa --output-dir environment/adapters/simpleqa/_generated/simpleqa --limit 50 --overwrite
```

Generate the full benchmark locally:

```bash
simpleqa --output-dir environment/adapters/simpleqa/_generated/simpleqa_full --overwrite
```

Generated task directories follow the Harbor task layout:

```text
simpleqa-0/
  task.toml
  instruction.md
  environment/Dockerfile
  solution/solve.sh
  tests/test.sh
  tests/llm_judge.py
  tests/ground_truth.json
```

## Run Evaluation

Run the adapter-local sample recipe:

```bash
harbor run -c environment/adapters/simpleqa/run_simpleqa.yaml
```

Run the recorded parity recipe:

```bash
harbor run -c environment/adapters/simpleqa/simpleqa_parity_claude_opus4_6.yaml
```

Run the oracle recipe against the full generated dataset:

```bash
harbor run -c environment/adapters/simpleqa/simpleqa_oracle.yaml
```

Job outputs are written by Harbor according to the recipe's `jobs_dir`. Do not
commit historical `jobs/` output; upload selected artifacts externally and link
them from the migration artifact README.

## External Inputs

- SimpleQA CSV:
  `https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv`
- `OPENAI_API_KEY`: required for LLM judge evaluation.
- Agent provider keys: required only for non-oracle agent runs.

## Parity Notes

The imported parity metadata compares this adapter with OpenAI's official
`simple-evals` setup on the first 50 tasks. The recorded configuration used
`claude-code@2.1.32` with `claude-opus-4-6` and an LLM judge. See
`parity_experiment.json` for the detailed run metadata.

The source README reported these aggregate results:

| Agent | Model | Metric | Runs | Dataset Size | Original | Adapter |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| claude-code@2.1.32 | claude-opus-4-6 | Accuracy | 3 | 50 | 0.967 +/- 0.018 | 0.947 +/- 0.007 |

Most recorded mismatches were attributed to non-interactive TTY shell behavior,
agent timeouts, or incorrect answers. Changing the judge model can change
verification behavior.

## Citation

```bibtex
@misc{wei2024measuringshortformfactualitylarge,
  title={Measuring short-form factuality in large language models},
  author={Jason Wei and Nguyen Karina and Hyung Won Chung and Yunxin Joy Jiao and Spencer Papay and Amelia Glaese and John Schulman and William Fedus},
  year={2024},
  eprint={2411.04368},
  archivePrefix={arXiv},
  primaryClass={cs.CL},
  url={https://arxiv.org/abs/2411.04368}
}
```

## Provenance

- Source repository: `MatrAIx-ai/MatrAIx`
- Source path: `adapters/simpleqa`
- Source commit: `e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0`
- Original adapter author: Issa Sugiura
