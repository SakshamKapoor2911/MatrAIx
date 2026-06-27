# PersonaEval Application

`application/persona_eval/` contains application-owned evaluation helpers for
persona studies. It is separate from:

- `persona/`, which owns persona schemas, datasets, and curation pipelines.
- `environment/` and `src/harbor/`, which own runtime execution.

Current scope:

- `backend/service/survey_types.py`: lightweight survey dataclasses and
  validation helpers.
- `backend/service/survey_instruments.py`: built-in survey instruments migrated
  from MatrAIx PersonaEval work.
- `backend/service/recommender_eval.py`: recommender chat artifact mapping,
  PersonaEval result dataclasses, and Harbor prompt/persona helpers.

Deferred scope:

- API endpoints
- Harbor survey runners
- UI/frontend code
- historical experiment outputs

Generated survey results, traces, and caches should stay outside git unless
they are tiny fixtures used by tests.
