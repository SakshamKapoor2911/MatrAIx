// Discrete-grid world model for MircoVerse (Protocol.md §2, §5.2).
// The world is a W×H grid of integer cells; agents occupy integer cell
// coordinates and move one cell per tick. There are no factions, tiers, or
// consortium primitives — those are emergent (Protocol.md §2.3, §10), not
// part of the world state the UI renders.

export type Terrain =
  | 'desert'
  | 'oasis'
  | 'mountain'
  | 'settlement'
  | 'ruins'

export type Stance = 'friendly' | 'neutral' | 'aggressive'

/** One grid cell. Resources are the three Protocol.md §2.2 resources. */
export interface Cell {
  x: number
  y: number
  terrain: Terrain
  water: number
  food: number
  goods: number
  /** True only for the single Settlement cell holding the Atmospheric Siphon. */
  siphon?: boolean
}

/** An agent at an integer cell position. */
export interface Agent {
  id: string
  name: string
  x: number
  y: number
  water: number
  food: number
  goods: number
  alive: boolean
  stance: Stance
  /** Optional last-resolved action verb, for the inspector. */
  lastAction?: string
  /** The agent's last-set intention (Protocol.md §4.2/§5.2) — what it says it is trying to
   *  do, carried forward each tick. Stated intention vs. revealed action is a research signal. */
  intention?: string
}

/** A full world snapshot for one tick — what the engine sends UI observers. */
export interface WorldSnapshot {
  tick: number
  gridW: number
  gridH: number
  /** Row-major cells, length === gridW * gridH; cell (x,y) at index y*gridW+x. */
  cells: Cell[]
  agents: Agent[]
  stormActive: boolean
  /** Centre of the lethal heat zone, if a heat cycle is currently active. */
  heatZoneCenter?: [number, number]
  /** Water units the Siphon produced this tick (Protocol.md §2.3). */
  siphonUnits: number
}

/** A research/event-feed entry (kept compatible with the existing EventFeed). */
export interface SimEvent {
  event_type: string
  agent_id?: string
  tick?: number
  message?: string
  target_id?: string
  [key: string]: unknown
}

/** Wire message shape — a read-only world broadcast (Protocol.md §5). */
export interface WorldUpdate {
  type: 'world_update'
  snapshot: WorldSnapshot
  recent_events?: SimEvent[]
}
