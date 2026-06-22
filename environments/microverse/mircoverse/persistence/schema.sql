-- MircoVerse — Postgres schema (Architecture.md "Database Schema").
--
-- This is the EXACT DDL from Architecture.md, made idempotent so migrate() can apply it
-- repeatedly without error (locally there is no pg_partman; Step 9's "ensure next partition"
-- check plus a DEFAULT partition cover partition lifecycle for the seed run).
--
-- The same SQL is intended to run on Aurora later — nothing here is engine-specific.

-- ── agents ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agents (
    agent_id          UUID PRIMARY KEY,
    display_name      VARCHAR(100),
    registered_at     TIMESTAMP,
    original_soul     JSONB,               -- immutable, enforced by DB trigger below
    current_identity  JSONB,               -- updated each reflection
    position_x        INT,
    position_y        INT,
    resources         JSONB,               -- {water, food, goods}
    status            VARCHAR(20),         -- active | dead | idle
    api_key_hash      VARCHAR(100),        -- SHA-256 of a high-entropy random token
    webhook_url       VARCHAR(500)         -- reserved; NOT used — server never calls the agent
);

-- Immutability enforced by a BEFORE UPDATE trigger (raises loudly), not a
-- DO INSTEAD NOTHING rule (which would silently drop the whole row's update).
CREATE OR REPLACE FUNCTION protect_original_soul()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.original_soul IS DISTINCT FROM NEW.original_soul THEN
        RAISE EXCEPTION 'original_soul is immutable (agent_id=%)', OLD.agent_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_protect_original_soul ON agents;
CREATE TRIGGER trg_protect_original_soul
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION protect_original_soul();

-- ── world_cells ─────────────────────────────────────────────────────────────────
-- One row per cell, updated in place — no full-grid JSONB blob.
CREATE TABLE IF NOT EXISTS world_cells (
    x             INT,
    y             INT,
    terrain       VARCHAR(20),
    water         INT,
    food          INT,
    goods         INT,                   -- non-survival status/wealth ("spice" in the loaded skin)
    passable      BOOLEAN,
    known_name    VARCHAR(100),
    PRIMARY KEY (x, y)
);

-- ── agent_known_locations ─────────────────────────────────────────────────────────
-- Separate table — not JSONB in agents row (avoids unbounded growth per agent).
CREATE TABLE IF NOT EXISTS agent_known_locations (
    agent_id          UUID REFERENCES agents(agent_id),
    x                 INT,
    y                 INT,
    location_type     VARCHAR(50),
    discovered_tick   INT,
    PRIMARY KEY (agent_id, x, y)
);

-- ── identity_snapshots ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS identity_snapshots (
    snapshot_id       UUID PRIMARY KEY,
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT,
    snapshot_at       TIMESTAMP,
    identity_json     JSONB,
    drift_score       FLOAT,               -- cosine distance from original_soul (online tripwire only)
    trigger           VARCHAR(20)          -- agent_revision | engine_measurement | forced_end
);

-- ── action_log (partitioned by tick range) ─────────────────────────────────────────
-- Partitioned for analytics performance. NOTE: a partitioned parent's PRIMARY KEY /
-- UNIQUE index must include every partition-key column, so the one-action-per-tick
-- uniqueness is (agent_id, tick_number) WHICH includes tick_number (the partition key),
-- and log_id uniqueness is enforced per-partition (it is a UUID, so collisions are nil).
CREATE TABLE IF NOT EXISTS action_log (
    log_id            UUID,
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT NOT NULL,
    action_type       VARCHAR(50),
    params            JSONB,
    result            JSONB,               -- filled by Step 7b
    intention         TEXT,                -- self-authored "what I'm trying to do" this tick (Protocol §4.2/§7.4); NULL = unchanged. No mechanical effect; logged for the intention-vs-action channel (World §9.5)
    submitted_at      TIMESTAMP,
    resolved_at       TIMESTAMP,
    status            VARCHAR(20)          -- accepted | rejected | timeout | defaulted
) PARTITION BY RANGE (tick_number);

-- Additive column for schemas created before `intention` existed (idempotent; Aurora-safe).
ALTER TABLE action_log ADD COLUMN IF NOT EXISTS intention TEXT;

-- DEFAULT partition is the safety net so an insert never errors on a missing range
-- (Architecture.md). Locally we lean on this + Step 9's ensure-next-partition; on Aurora
-- pg_partman pre-creates ranged partitions ahead of the tick clock.
CREATE TABLE IF NOT EXISTS action_log_default PARTITION OF action_log DEFAULT;

-- One action per (agent_id, tick_number). Backs the INSERT ... ON CONFLICT DO NOTHING
-- one-action-per-tick guarantee. tick_number (the partition key) is included as required.
CREATE UNIQUE INDEX IF NOT EXISTS one_action_per_tick
    ON action_log (agent_id, tick_number);

-- ── agent_tick_results (ephemeral serving cache) ───────────────────────────────────
-- Rows deleted after 2 ticks by Step 0. Replayable from action_log + world_cells.
CREATE TABLE IF NOT EXISTS agent_tick_results (
    agent_id          UUID,
    tick_number       INT,
    world_fov         JSONB,
    action_result     JSONB,
    events            JSONB,               -- messages received, things witnessed
    fetched_at        TIMESTAMP,           -- set when agent calls GET /world/observe
    PRIMARY KEY (agent_id, tick_number)
);

-- ── tick_scratch (inter-step scratch) ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tick_scratch (
    tick_number       INT,
    key               VARCHAR(100),        -- "positions", "damage_map", "dead_agents", etc.
    value             JSONB,
    PRIMARY KEY (tick_number, key)
);

-- ── tick_state ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tick_state (
    tick_number        INT PRIMARY KEY,
    window_open        BOOLEAN DEFAULT TRUE, -- conditional lock for double-trigger prevention
    active_agent_count INT,                  -- live agents as of window start; set by Step 9 from Step 2
    submitted_count    INT DEFAULT 0,        -- atomically incremented per accepted action (early-close)
    opened_at          TIMESTAMP,
    closed_at          TIMESTAMP,
    tick_ends_at       TIMESTAMP             -- updated on early close
);

-- ── tick_errors ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tick_errors (
    error_id          UUID PRIMARY KEY,
    tick_number       INT,
    step_name         VARCHAR(50),
    error_message     TEXT,
    occurred_at       TIMESTAMP
);

-- ── agent_memory (long-term subjective layer — typed markdown, one row per entry) ──
CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id         UUID PRIMARY KEY,
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT,
    memory_type       VARCHAR(16),         -- 'event' | 'relationship' | 'reflection'
    subject_agent_id  UUID,                -- for 'relationship' rows: who the belief is about (else NULL)
    content           TEXT,                -- the markdown entry, in the agent's own words
    importance        SMALLINT,            -- 1-10 salience; high for moral/high-pressure events
    created_at        TIMESTAMP
);

-- ── simulation_state (singleton) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS simulation_state (
    id                INT PRIMARY KEY DEFAULT 1,  -- singleton row
    status            VARCHAR(20),                -- registration | running | paused | ended
    current_tick      INT,
    started_at        TIMESTAMP,
    ended_at          TIMESTAMP
);

-- ── Evaluation artifacts (offline analysis pipeline; not written by the live engine) ──
CREATE TABLE IF NOT EXISTS boundary_state (
    agent_id          UUID REFERENCES agents(agent_id),
    boundary_text     TEXT,
    tick_number       INT,
    state             VARCHAR(12),         -- upheld | eroded | inverted | abandoned
    evidence_refs     JSONB,
    judged_by         VARCHAR(20),         -- llm_judge | human
    PRIMARY KEY (agent_id, boundary_text, tick_number, judged_by)
);

CREATE TABLE IF NOT EXISTS alignment_scores (
    agent_id          UUID REFERENCES agents(agent_id),
    tick_number       INT,
    alignment         FLOAT,
    violations        JSONB,
    PRIMARY KEY (agent_id, tick_number)
);

CREATE TABLE IF NOT EXISTS judge_validation (
    item_id           UUID PRIMARY KEY,
    sampled_from      VARCHAR(30),         -- boundary_state | alignment_scores
    item_ref          JSONB,
    llm_verdict       JSONB,
    human_verdicts    JSONB,
    agreement         FLOAT
);
