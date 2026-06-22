// Deterministic demo-world generator.
//
// Produces a fully-specified WorldSnapshot for either scale the renderer must
// handle: the 50×50 / 25-agent controlled seed run (Protocol.md §2.1) and a
// 200×200 / 1000-agent load-test world. A single seeded RNG drives every
// stochastic choice so the world is reproducible (Protocol.md §1, §9). This is
// a standalone stand-in for the engine — no network required.

import type { Agent, Cell, WorldSnapshot } from '../types/simulation'

/** xorshift32 — small, fast, reproducible. */
export function makeRng(seed: number): () => number {
  let x = seed >>> 0 || 0x9e3779b9
  return () => {
    x ^= x << 13
    x ^= x >>> 17
    x ^= x << 5
    return (x >>> 0) / 0xffffffff
  }
}

export interface WorldScale {
  gridW: number
  gridH: number
  agents: number
  seed: number
}

export const SCALE_25: WorldScale = { gridW: 50, gridH: 50, agents: 25, seed: 0x5eed25 }
export const SCALE_1000: WorldScale = { gridW: 200, gridH: 200, agents: 1000, seed: 0x5eed1000 }

const NAMES = [
  'Kael', 'Vex', 'Sable', 'Drey', 'Linh', 'Mott', 'Asha', 'Crix', 'Zuri', 'Tor',
  'Nyx', 'Brak', 'Sera', 'Vane', 'Dusk', 'Oryn', 'Fela', 'Gorm', 'Ilse', 'Jaxx',
  'Kira', 'Lorn', 'Mira', 'Nox', 'Olev', 'Pyre', 'Qua', 'Rael', 'Skye', 'Thorn',
]

const STANCES = ['friendly', 'neutral', 'neutral', 'aggressive'] as const

const idx = (x: number, y: number, w: number) => y * w + x

/**
 * Lay down terrain. The Siphon sits at the grid centre on a Settlement cell;
 * a few oases, a mountain ridge, and scattered ruins fill the rest of the
 * desert. Deterministic given the seed.
 */
function genCells(w: number, h: number, rng: () => number): Cell[] {
  const cells: Cell[] = new Array(w * h)
  const cx = Math.floor(w / 2)
  const cy = Math.floor(h / 2)

  // Base desert fill.
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      cells[idx(x, y, w)] = {
        x, y,
        terrain: 'desert',
        water: 0,
        food: rng() < 0.06 ? 1 + Math.floor(rng() * 3) : 0,
        goods: 0,
      }
    }
  }

  // A diagonal mountain ridge through the lower-left quadrant.
  const ridgeLen = Math.floor(Math.min(w, h) * 0.7)
  for (let i = 0; i < ridgeLen; i++) {
    const mx = Math.floor(w * 0.18 + i * 0.55)
    const my = Math.floor(h * 0.82 - i * 0.45)
    for (let t = -1; t <= 1; t++) {
      const xx = mx + t
      if (xx < 0 || xx >= w || my < 0 || my >= h) continue
      if (rng() < 0.8) cells[idx(xx, my, w)].terrain = 'mountain'
    }
  }

  // Oases — contested water sources scattered away from centre.
  const oasisCount = Math.max(5, Math.round((w * h) / 600))
  for (let i = 0; i < oasisCount; i++) {
    const ox = 3 + Math.floor(rng() * (w - 6))
    const oy = 3 + Math.floor(rng() * (h - 6))
    if (Math.abs(ox - cx) < 4 && Math.abs(oy - cy) < 4) continue
    const r = rng() < 0.4 ? 1 : 0
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        const xx = ox + dx, yy = oy + dy
        if (xx < 0 || xx >= w || yy < 0 || yy >= h) continue
        const c = cells[idx(xx, yy, w)]
        c.terrain = 'oasis'
        c.water = 12 + Math.floor(rng() * 20)
      }
    }
  }

  // Ruins DISTRICTS — clustered collapsed settlements (not lone scattered cells),
  // where death-caches sit (Protocol.md §2.4). A few blobs read as fallen towns.
  const ruinClusters = w > 120 ? 7 : 3
  for (let i = 0; i < ruinClusters; i++) {
    const rx = 5 + Math.floor(rng() * (w - 10))
    const ry = 5 + Math.floor(rng() * (h - 10))
    if (Math.abs(rx - cx) < 7 && Math.abs(ry - cy) < 7) continue // keep clear of town
    const rr = 1 + Math.floor(rng() * 2)
    for (let dy = -rr; dy <= rr; dy++) {
      for (let dx = -rr; dx <= rr; dx++) {
        const xx = rx + dx, yy = ry + dy
        if (xx < 0 || xx >= w || yy < 0 || yy >= h) continue
        if (Math.abs(dx) + Math.abs(dy) > rr) continue
        const c = cells[idx(xx, yy, w)]
        if (c.terrain !== 'desert') continue
        c.terrain = 'ruins'
        // a couple of cells per cluster hold a scavengeable cache
        if (rng() < 0.35) { c.goods = 1 + Math.floor(rng() * 3); c.food = Math.floor(rng() * 3) }
      }
    }
  }

  // The SETTLEMENT — a sizable town clustered around the centre, holding the
  // Siphon. Larger than before so the world reads as inhabited, with an
  // irregular edge (not a clean diamond) so the skyline looks organic.
  const settleR = w > 120 ? 9 : 6
  for (let dy = -settleR; dy <= settleR; dy++) {
    for (let dx = -settleR; dx <= settleR; dx++) {
      const xx = cx + dx, yy = cy + dy
      if (xx < 0 || xx >= w || yy < 0 || yy >= h) continue
      const dist = Math.hypot(dx, dy) + (rng() - 0.5) * 1.6 // jittered radius
      if (dist > settleR) continue
      const c = cells[idx(xx, yy, w)]
      c.terrain = 'settlement'
      c.water = 0
    }
  }
  // GOODS — the periphery-wealth layer (World.md §2). Non-survival, tradeable
  // wealth seeded ONLY out in the dangerous open desert, weighted toward cells
  // far from the Siphon: this is the "reason to leave the well", the lure that
  // separates greed from need. (Ruins also hold goods, set above, as the
  // death-cache loot.) Appended last so the verified town/ridge/oasis layout is
  // RNG-stable; only the goods scatter consumes the tail of the stream.
  const maxD = Math.hypot(cx, cy)
  for (const c of cells) {
    if (c.terrain !== 'desert' || c.goods > 0) continue
    const dist = Math.hypot(c.x - cx, c.y - cy)
    // none near the centre, ramping to a sparse scatter at the dangerous edge
    const edge = Math.min(1, dist / maxD)
    if (edge > 0.35 && rng() < 0.018 * edge) {
      c.goods = 1 + Math.floor(rng() * 4)
    }
  }

  // The single Siphon cell at the exact centre.
  const sip = cells[idx(cx, cy, w)]
  sip.terrain = 'settlement'
  sip.siphon = true
  sip.water = 0 // filled per-tick by genWorld/driver

  return cells
}

/** Spawn agents on non-mountain cells, with deliberately unequal water. */
function genAgents(
  count: number, w: number, h: number, cells: Cell[], rng: () => number,
): Agent[] {
  const agents: Agent[] = []
  const occupied = new Set<number>()
  for (let i = 0; i < count; i++) {
    let x = 0, y = 0, tries = 0
    do {
      x = Math.floor(rng() * w)
      y = Math.floor(rng() * h)
      tries++
    } while (
      tries < 40 &&
      (cells[idx(x, y, w)].terrain === 'mountain' || occupied.has(idx(x, y, w)))
    )
    occupied.add(idx(x, y, w))

    // Most agents start 40–60 water; ~8% start critically low (Protocol.md §2.2).
    const low = rng() < 0.08
    const water = low ? 6 + Math.floor(rng() * 8) : 40 + Math.floor(rng() * 21)

    agents.push({
      id: `agent_${String(i).padStart(count > 99 ? 4 : 2, '0')}`,
      name: NAMES[i % NAMES.length] + (i >= NAMES.length ? `·${Math.floor(i / NAMES.length) + 1}` : ''),
      x, y,
      water,
      food: 8 + Math.floor(rng() * 14),
      goods: Math.floor(rng() * 6),
      alive: true,
      stance: STANCES[Math.floor(rng() * STANCES.length)],
      lastAction: 'wait',
    })
  }
  return agents
}

/** Build a complete, deterministic snapshot for a given scale. */
export function genWorld(scale: WorldScale): WorldSnapshot {
  const rng = makeRng(scale.seed)
  const { gridW, gridH } = scale
  const cells = genCells(gridW, gridH, rng)
  const agents = genAgents(scale.agents, gridW, gridH, cells, rng)
  const siphonUnits = Math.round(1.5 * scale.agents)

  // Seed the Siphon cell with this tick's output.
  const cx = Math.floor(gridW / 2)
  const cy = Math.floor(gridH / 2)
  cells[idx(cx, cy, gridW)].water = siphonUnits

  return {
    tick: 0,
    gridW,
    gridH,
    cells,
    agents,
    stormActive: false,
    heatZoneCenter: [Math.floor(gridW * 0.75), Math.floor(gridH * 0.2)],
    siphonUnits,
  }
}
