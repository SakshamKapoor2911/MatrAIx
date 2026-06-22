"""MircoVerse — behavioral instrument for LLM identity drift under moral pressure.

Greenfield engine implementing the frozen contracts in World.md (rules/why),
Architecture.md (production infra), and Protocol.md (agent-facing wire contract).

Package layout:
    contracts/   Pydantic models for the NORMATIVE wire contract (Protocol.md §4-5)
    world/       Pure, deterministic world core (grid, resources, 8 actions, seeded tick)
    persistence/ Postgres schema + data-access layer (Architecture.md schema)
    resolution/  Tick resolver — the Steps 1-9 pipeline run as one local function
    server/      FastAPI implementing the HTTP contract (Protocol.md §5)
    agents/      Reference LLM agent + mock load-test agent (Protocol.md §6-7)
    measurement/ Engine snapshots + cosine tripwire (World.md §9.3)
    manifest/    Experiment manifest load/validate + seeded RNG (Protocol.md §9)
"""

__version__ = "0.1.0"
