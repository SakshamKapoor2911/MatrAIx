import { create } from 'zustand'
import type { SimEvent, WorldSnapshot, WorldUpdate } from '../types/simulation'

/** Position of an agent on the previous tick, for smooth interpolation. */
export interface PrevPos {
  x: number
  y: number
  alive: boolean
}

const EMPTY_SNAPSHOT: WorldSnapshot = {
  tick: 0,
  gridW: 50,
  gridH: 50,
  cells: [],
  agents: [],
  stormActive: false,
  siphonUnits: 0,
}

interface WorldStore {
  snapshot: WorldSnapshot
  /** Per-agent position on the previous tick, keyed by agent id. */
  prevAgents: Record<string, PrevPos>
  /** Wall-clock ms at which the current snapshot was applied (interp anchor). */
  snapshotAt: number
  events: SimEvent[]
  connected: boolean

  selectedAgentId: string | null
  selectAgent: (id: string | null) => void

  /** Replace the live world with a new tick snapshot. */
  applySnapshot: (snap: WorldSnapshot, events?: SimEvent[]) => void
  /** Wire entry point for the read-only socket broadcast. */
  applyUpdate: (update: WorldUpdate) => void
  setConnected: (v: boolean) => void
  reset: () => void
}

export const useWorldStore = create<WorldStore>((set) => ({
  snapshot: EMPTY_SNAPSHOT,
  prevAgents: {},
  snapshotAt: Date.now(),
  events: [],
  connected: false,

  selectedAgentId: null,
  selectAgent: (id) => set({ selectedAgentId: id }),

  applySnapshot: (snap, events) =>
    set((state) => {
      // Capture where every agent was, so the renderer can ease between cells.
      const prev: Record<string, PrevPos> = {}
      for (const a of state.snapshot.agents) {
        prev[a.id] = { x: a.x, y: a.y, alive: a.alive }
      }
      return {
        snapshot: snap,
        prevAgents: prev,
        snapshotAt: Date.now(),
        events: events && events.length
          ? [...state.events, ...events].slice(-500)
          : state.events,
      }
    }),

  applyUpdate: (update) => {
    useWorldStore.getState().applySnapshot(update.snapshot, update.recent_events)
  },

  setConnected: (v) => set({ connected: v }),

  reset: () =>
    set({
      snapshot: EMPTY_SNAPSHOT,
      prevAgents: {},
      snapshotAt: Date.now(),
      events: [],
      selectedAgentId: null,
    }),
}))
