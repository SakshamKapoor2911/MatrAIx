// Real-run replay driver.
//
// Unlike driveDemo.ts (a synthetic stand-in that *dramatizes* the world rules),
// this plays back an ACTUAL finished run exported from the engine's action_log
// — the behavioral ground truth (Architecture: "action_log is replayable"). Every
// position, water level, death, and dialogue line is real; nothing is invented.
// The replay JSON is produced by `scripts/export_replay.py`.
//
// It exposes the SAME `Demo` interface as createDemo, so WorldCanvas consumes it
// unchanged: a `snapshot` for frame 0 and a `step()` that advances one real tick
// and surfaces that tick's real `talk` messages as speech-bubble events. When the
// run ends it holds on the final frame (the dead stay dead) so the demo can loop
// cleanly on a reload.

import type { Cell, SimEvent, WorldSnapshot } from '../types/simulation'
import type { Demo } from './driveDemo'
import type { WorldScale } from './genWorld'

interface ReplayAgent {
  id: string; name: string; x: number; y: number; water: number
  food: number; goods: number; alive: boolean; stance: string
  lastAction?: string | null; intention?: string | null
}
interface ReplayFrame { tick: number; agents: ReplayAgent[]; events: SimEvent[] }
interface ReplayFile {
  source: string; gridW: number; gridH: number; ticks: number
  cells: Cell[]; frames: ReplayFrame[]
}

function frameToSnapshot(f: ReplayFrame, cells: Cell[], gw: number, gh: number): WorldSnapshot {
  return {
    tick: f.tick,
    gridW: gw,
    gridH: gh,
    cells,
    agents: f.agents.map((a) => ({
      id: a.id, name: a.name, x: a.x, y: a.y,
      water: a.water, food: a.food, goods: a.goods,
      alive: a.alive,
      stance: (a.stance as WorldSnapshot['agents'][number]['stance']) ?? 'neutral',
      lastAction: a.lastAction ?? undefined,
      intention: a.intention ?? undefined,
    })),
    stormActive: false,
    siphonUnits: 0,
  }
}

/** Build a replay Demo from already-loaded replay JSON. */
export function createReplay(data: ReplayFile): Demo {
  const cells = data.cells
  const gw = data.gridW
  const gh = data.gridH
  const frames = data.frames
  let i = 0

  const scale: WorldScale = { gridW: gw, gridH: gh, agents: frames[0]?.agents.length ?? 0, seed: 0 }

  return {
    scale,
    snapshot: frameToSnapshot(frames[0], cells, gw, gh),
    step() {
      // Advance, then clamp to the last frame so the run ends gracefully (no loop
      // mid-story; a page reload restarts from frame 0).
      i = Math.min(i + 1, frames.length - 1)
      const f = frames[i]
      return { snapshot: frameToSnapshot(f, cells, gw, gh), events: f.events ?? [] }
    },
  }
}

/** Fetch + parse the exported replay file from /public. Returns null if absent. */
export async function loadReplay(url = '/replay.json'): Promise<ReplayFile | null> {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    return (await res.json()) as ReplayFile
  } catch {
    return null
  }
}
