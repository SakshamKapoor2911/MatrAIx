import { create } from 'zustand'
import type { SimEvent, WorldSnapshot, WorldUpdate } from '../types/simulation'

/** Position of an agent on the previous tick, for smooth interpolation. */
export interface PrevPos {
  x: number
  y: number
  alive: boolean
}

/** A transient speech/chat bubble over an agent, born when the agent communicates. */
export interface SpeechBubble {
  agentId: string
  text: string
  kind: 'whisper' | 'broadcast'
  /** Wall-clock ms when the utterance arrived; lifetime is measured from here. */
  bornAt: number
}

/** How long a bubble stays on screen (ms). Wall-clock, so it is decoupled from the
 *  tick rate — a bubble fades on its own schedule and never blocks the sim loop. */
export const BUBBLE_TTL_MS = 3400

/** Which event types carry agent SPEECH (vs third-person log notes). Only these spawn
 *  bubbles; the message text is what the agent "said" (Protocol §4.1 talk/signal). */
const SPEECH_EVENTS: Record<string, SpeechBubble['kind']> = {
  WHISPER_SENT: 'whisper',
  BROADCAST_SENT: 'broadcast',
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
  /** Live speech bubbles to overlay near agents, keyed by agent id (latest wins).
   *  Populated from speech events on each snapshot; pruned by wall-clock TTL. */
  bubbles: Record<string, SpeechBubble>
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
  bubbles: {},
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

      // ── Speech bubbles: cheap, snapshot-driven, wall-clock TTL ──────────────
      // Spawn a bubble from each speech event in this batch (latest per agent wins),
      // then drop any that have outlived their TTL. This is O(events + live bubbles)
      // per tick and writes plain data — the rAF render loop reads it without any
      // timers or extra React renders, so it never lags the simulation step.
      const now = Date.now()
      const bubbles: Record<string, SpeechBubble> = {}
      for (const [id, b] of Object.entries(state.bubbles)) {
        if (now - b.bornAt < BUBBLE_TTL_MS) bubbles[id] = b
      }
      for (const e of events ?? []) {
        const kind = e.event_type ? SPEECH_EVENTS[e.event_type] : undefined
        if (!kind || !e.agent_id || !e.message) continue
        bubbles[e.agent_id] = { agentId: e.agent_id, text: e.message, kind, bornAt: now }
      }

      return {
        snapshot: snap,
        prevAgents: prev,
        snapshotAt: now,
        bubbles,
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
      bubbles: {},
      selectedAgentId: null,
    }),
}))
