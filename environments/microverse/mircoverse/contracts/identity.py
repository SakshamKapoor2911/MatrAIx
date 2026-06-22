"""Identity contract — registration & reflection (Protocol.md §5, §7.1).

That an agent registers an immutable original_soul at T=0 is NORMATIVE; the schema
here is the reference default (controlled arm uses a standardized one; open arm allows
participant-authored). current_identity starts as a copy of original_soul and is the
thing that may drift (World.md §0 operational definitions).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SoulFile(BaseModel):
    """The agent's identity document. Kept small and pure: it is the drift MEASUREMENT
    TARGET (World.md §9), so richer memory lives elsewhere and never bloats this."""
    core_values: list[str] = Field(default_factory=list)
    moral_boundaries: list[str] = Field(default_factory=list)
    personality: str = ""
    goals: list[str] = Field(default_factory=list)


class RegistrationRequest(BaseModel):
    name: str
    original_soul: SoulFile


class RegistrationResponse(BaseModel):
    agent_id: str
    api_key: str  # returned once, never persisted in plaintext (Architecture.md API auth)


class ReflectionRequest(BaseModel):
    """Agent-initiated identity revision. NEVER gated/forced/scheduled; POST /action is
    never blocked on it (Protocol.md §5.4). Writes a new current_identity + an
    identity_snapshots row with trigger=agent_revision."""
    tick: int
    current_identity: SoulFile
    reflection_note: str = ""  # appended to reflections.md; logged for research
