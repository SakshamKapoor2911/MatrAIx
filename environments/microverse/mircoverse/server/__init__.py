"""The FastAPI server: the NORMATIVE §5 wire contract over a local engine (Protocol.md §1, §5).

The same six endpoints run locally now (FastAPI/uvicorn + Postgres) and would run unchanged on
API Gateway + Lambda later — the contract is engine-agnostic, so agents are AWS-portable.
"""

from mircoverse.server.app import (
    API_PREFIX,
    CONTRACT_ROUTES,
    app,
    create_app,
    run_tick_loop,
)

__all__ = ["app", "create_app", "run_tick_loop", "API_PREFIX", "CONTRACT_ROUTES"]
