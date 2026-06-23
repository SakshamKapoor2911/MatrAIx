# Environment setup (RecAI native, Python 3.9)

The recommender runs Microsoft RecAI in-process with the **native SASRec** ranker
(`unirec`). That pins the toolchain, so create a dedicated virtualenv.

## Why Python 3.9

`unirec==0.0.1a4` pins `torch<=1.13.1`, which has no wheels for Python 3.12+.
Python 3.9 is the supported target: torch 1.13.1 CPU wheels exist, `unirec`
installs cleanly, and the era-matched `pandas` / `pandasql` work together.

## Install (reproducible)

The commands below use [`uv`](https://github.com/astral-sh/uv); plain
`python -m venv` + `pip` works too. Run from the **repository root** and adjust
the venv path to wherever you keep it (the app's launchers take `VENV=/path/to/venv`).

```bash
# 1. Python 3.9 venv
uv python install 3.9
uv venv --python 3.9 .venv

APP=applications/recommendation_chatbot_eval

# 2. torch 1.13.1 CPU first (before requirements.txt, which pulls a cu113 build)
uv pip install --python .venv/bin/python "torch==1.13.1" \
  --index-url https://download.pytorch.org/whl/cpu

# 3. RecAI engine deps
uv pip install --python .venv/bin/python -r "$APP/recai/InteRecAgent/requirements.txt"

# 4. Re-pin torch to the CPU build (requirements.txt overrides it with cu113)
uv pip install --python .venv/bin/python "torch==1.13.1" \
  --index-url https://download.pytorch.org/whl/cpu

# 5. Pin huggingface_hub / accelerate for sentence-transformers 2.2.2 compatibility
#    (st 2.2.2 needs hub<0.17's cached_download; accelerate 1.2.x needs hub>=0.22 — conflict)
uv pip install --python .venv/bin/python "huggingface_hub>=0.14,<0.17" "accelerate<0.20"

# 6. Backend (FastAPI / pydantic v2 / uvicorn)
uv pip install --python .venv/bin/python -r "$APP/backend/requirements.txt"
```

On first real run, sentence-transformers downloads `thenlper/gte-base` (~833 MB)
into your HuggingFace cache (`~/.cache/huggingface` by default; override with
`HF_HOME` if your home dir is space-constrained).

## Key pins

| Package | Version | Note |
|---|---|---|
| Python | 3.9.x | |
| torch | 1.13.1+cpu | re-pinned in step 4 (requirements.txt installs the cu113 build) |
| unirec | 0.0.1a4 | native SASRec ranker |
| sentence-transformers | 2.2.2 | exact pin |
| huggingface_hub | <0.17 (e.g. 0.16.4) | deviation: st 2.2.2 uses the removed `cached_download` API |
| transformers | 4.27.4 | deviation: compatible with hub <0.17 |
| accelerate | <0.20 (e.g. 0.19.0) | deviation: 1.2.x requires hub ≥0.22 |
| pandas | 2.0.3 | within the `<2.1` constraint; works with pandasql 0.7.3 |
| fastapi / pydantic | 0.128.x / 2.13.x | backend |

## Notes

- **Native only.** The app runs `py3.9 + native` exclusively (in-process on this
  venv). The former `py3.12 + semantic_profile` fallback was removed — on 3.12 the
  only installable pandas (2.2.x) is incompatible with `pandasql 0.7.3`, so the SQL
  filter tool failed and recommendations came back empty.
- The in-repo RecAI path (`recai/InteRecAgent`) is resolved automatically via
  `recbot/paths.py`; there's no `INTERECAGENT_ROOT` to set.
