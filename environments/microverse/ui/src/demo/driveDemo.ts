// Standalone demo driver.
//
// Steps a generated world tick-by-tick so the map dramatizes the world RULES
// (Protocol.md §2–4) without the real engine. Agents are not random wanderers:
// they SEEK water, CONTEND at the deliberately-insufficient Siphon, run to
// oases, FLEE the rotating heat zone, and — when they meet — fire the full
// social action space (trade / talk / signal / attack) and SCAVENGE the dead.
// A dead agent leaves a death-cache that the living may loot (§2.4).
//
// Everything runs off a single seeded RNG so a demo session replays
// identically. This is a UI stand-in only — it is NOT the Protocol.md tick
// resolver and makes no scientific claim. Its job is to make the existing
// world legible: every visible behaviour maps to a real rule.

import type { Agent, SimEvent, WorldSnapshot } from '../types/simulation'
import { genWorld, makeRng, type WorldScale } from './genWorld'

const DIRS: ReadonlyArray<[number, number]> = [
  [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1],
]

const STANCES = ['friendly', 'neutral', 'aggressive'] as const

// Below this water an agent prioritises getting to water over everything else
// (Protocol.md §2.2 — water is the hard survival constraint).
const THIRST = 25
// What a "comfortable" agent tops out at; the Siphon never fully sates a crowd.
const SATED = 45

const WHISPERS = [
  'There is water at the old ruins.',
  'The Siphon ran dry before I drank.',
  'Trade you a location for goods.',
  'Stay clear of the eastern heat.',
  "Don't trust the one who came from the dunes.",
  'I saw a cache near the fallen town.',
]
const BROADCASTS = [
  'The Siphon cannot feed us all.',
  'Form a line — or take it by force.',
  'Heat is moving. Migrate now.',
]

export interface Demo {
  scale: WorldScale
  snapshot: WorldSnapshot
  /** Advance one tick; returns the new snapshot and any events generated. */
  step: () => { snapshot: WorldSnapshot; events: SimEvent[] }
}

export function createDemo(scale: WorldScale): Demo {
  const rng = makeRng(scale.seed ^ 0xa5a5)
  const base = genWorld(scale)

  // Mutable working copy of agents (cells are stable except the Siphon cell).
  let agents: Agent[] = base.agents.map((a) => ({ ...a }))
  const cells = base.cells // terrain is static; we only re-stamp the siphon
  const W = base.gridW
  const H = base.gridH
  let tick = base.tick
  let stormActive = false
  let stormTicksLeft = 0
  let heat: [number, number] = base.heatZoneCenter ?? [Math.floor(W * 0.75), Math.floor(H * 0.2)]
  let heatAngle = 0
  const heatRadius = Math.min(W, H) * 0.32
  const cx = Math.floor(W / 2)
  const cy = Math.floor(H / 2)

  const at = (x: number, y: number) => cells[y * W + x]
  const inBounds = (x: number, y: number) => x >= 0 && x < W && y >= 0 && y < H
  const isMountain = (x: number, y: number) => inBounds(x, y) && at(x, y).terrain === 'mountain'

  // Precompute the water sources every agent is drawn toward: the central
  // Siphon plus each oasis cell (Protocol.md §2.3 single insufficient Siphon +
  // §2.2 contested oases). These are the gravity wells of the whole map.
  const oases: Array<[number, number]> = []
  for (const c of cells) if (c.terrain === 'oasis') oases.push([c.x, c.y])

  /** Nearest known water source to (x,y): the Siphon or an oasis. */
  function nearestWater(x: number, y: number): [number, number] {
    let best: [number, number] = [cx, cy]
    let bestD = Math.abs(x - cx) + Math.abs(y - cy)
    for (const [ox, oy] of oases) {
      const d = Math.abs(x - ox) + Math.abs(y - oy)
      if (d < bestD) { bestD = d; best = [ox, oy] }
    }
    return best
  }

  /** One Moore step from (x,y) toward (tx,ty), avoiding mountains. */
  function stepToward(x: number, y: number, tx: number, ty: number): [number, number] {
    const sx = Math.sign(tx - x)
    const sy = Math.sign(ty - y)
    const cands: Array<[number, number]> = [
      [x + sx, y + sy], [x + sx, y], [x, y + sy],
    ]
    for (const [nx, ny] of cands) {
      if (!inBounds(nx, ny)) continue
      if (isMountain(nx, ny) && rng() < 0.85) continue
      return [nx, ny]
    }
    return [x, y]
  }

  /** One Moore step from (x,y) directly away from (ax,ay) — fleeing. */
  function stepAway(x: number, y: number, ax: number, ay: number): [number, number] {
    const sx = Math.sign(x - ax) || (rng() < 0.5 ? 1 : -1)
    const sy = Math.sign(y - ay) || (rng() < 0.5 ? 1 : -1)
    const nx = x + sx, ny = y + sy
    if (inBounds(nx, ny) && !isMountain(nx, ny)) return [nx, ny]
    const [dx, dy] = DIRS[Math.floor(rng() * DIRS.length)]
    return inBounds(x + dx, y + dy) ? [x + dx, y + dy] : [x, y]
  }

  const cheb = (ax: number, ay: number, bx: number, by: number) =>
    Math.max(Math.abs(ax - bx), Math.abs(ay - by))

  function step(): { snapshot: WorldSnapshot; events: SimEvent[] } {
    tick += 1
    const events: SimEvent[] = []

    // ── World conditions (Protocol.md §2.5) ─────────────────────────────────
    if (stormActive) {
      stormTicksLeft -= 1
      if (stormTicksLeft <= 0) {
        stormActive = false
        events.push({ event_type: 'STORM_ENDED', tick })
      }
    } else if (rng() < 0.06) {
      stormActive = true
      stormTicksLeft = 14 + Math.floor(rng() * 12)
      events.push({ event_type: 'STORM_STARTED', tick })
    }

    // Heat zone rotates on a fixed orbit → forces periodic migration (§2.5).
    heatAngle += 0.035
    heat = [
      Math.round(cx + Math.cos(heatAngle) * heatRadius),
      Math.round(cy + Math.sin(heatAngle) * heatRadius),
    ]
    const heatRad = Math.min(W, H) * 0.12
    const heatR2 = heatRad * heatRad
    const inHeat = (x: number, y: number) =>
      (x - heat[0]) ** 2 + (y - heat[1]) ** 2 < heatR2

    // Fast lookups for adjacency / corpse-looting this tick.
    const alive = agents.filter((a) => a.alive)
    const occ = new Map<number, Agent>()
    for (const a of alive) occ.set(a.y * W + a.x, a)
    // Corpses still holding a lootable cache (their leftover resources, §2.4).
    const corpses = agents.filter(
      (a) => !a.alive && (a.water > 0 || a.food > 0 || a.goods > 0),
    )

    const neighborsOf = (a: Agent): Agent[] => {
      const out: Agent[] = []
      for (const [dx, dy] of DIRS) {
        const n = occ.get((a.y + dy) * W + (a.x + dx))
        if (n && n.id !== a.id) out.push(n)
      }
      return out
    }
    const corpseNear = (a: Agent): Agent | null => {
      for (const c of corpses) if (cheb(a.x, a.y, c.x, c.y) <= 1) return c
      return null
    }

    // Agents that will draw from the Siphon this tick (resolved by contention).
    const siphonClaims: Agent[] = []

    // ── Per-agent decision: exactly ONE action (Protocol.md §4) ─────────────
    agents = agents.map((src) => {
      if (!src.alive) return src
      const a: Agent = { ...src }

      // Base survival drain (terrain + hazards). Water is the hard constraint.
      const terrain = at(a.x, a.y).terrain
      let drain = 1
      if (terrain === 'desert') drain += 1
      if (terrain === 'mountain') drain += 0.5
      if (stormActive) drain += 0.5
      if (inHeat(a.x, a.y)) {
        drain += 3
        if (rng() < 0.5) events.push({ event_type: 'HEAT_ZONE_DAMAGE', agent_id: a.id, tick })
      }

      const thirsty = a.water < THIRST
      const onSiphon = cheb(a.x, a.y, cx, cy) <= 1
      const onOasis = terrain === 'oasis'
      const corpse = corpseNear(a)
      const neighbors = neighborsOf(a)

      // A self-authored "what I'm trying to do" line, carried forward (Protocol §4.2/§7.4).
      // UI stand-in only: derived from the agent's dominant drive so the inspector can show
      // the stated-intention-vs-executed-action pairing the real engine logs.
      if (inHeat(a.x, a.y)) a.intention = 'Get clear of the heat zone before it kills me.'
      else if (thirsty && (onSiphon || onOasis)) a.intention = 'Drink here and rebuild my water reserve.'
      else if (thirsty && corpse) a.intention = 'Take what the dead left — I need the water more than they do.'
      else if (thirsty) a.intention = 'Reach water before I run dry.'
      else if (a.stance === 'aggressive' && neighbors.length > 0) a.intention = 'Hold my ground; take what I must to stay ahead.'
      else if (neighbors.length > 0) a.intention = 'Keep my footing with the others — trade or talk, not fight.'
      else if (a.goods > 0) a.intention = 'Carry my goods somewhere they buy water.'

      // 1) FLEE the heat zone — survival overrides everything (§2.5).
      if (inHeat(a.x, a.y)) {
        ;[a.x, a.y] = stepAway(a.x, a.y, heat[0], heat[1])
        a.lastAction = 'move'
      }
      // 2) DRINK: at the Siphon → queue for contention; at an oasis → consume.
      else if (thirsty && onSiphon) {
        siphonClaims.push(a) // served (or denied) in the contention pass below
        a.lastAction = 'consume'
      }
      else if (thirsty && onOasis) {
        a.lastAction = 'consume' // oasis replenish applied after drain
      }
      // 3) SCAVENGE a nearby death-cache when it would help (§2.4, P4 probe).
      else if (corpse && (thirsty || rng() < 0.25)) {
        a.water += corpse.water
        a.food += corpse.food
        a.goods += corpse.goods
        corpse.water = 0; corpse.food = 0; corpse.goods = 0
        a.lastAction = 'scavenge'
        events.push({
          event_type: 'CACHE_SCAVENGED', agent_id: a.id, tick,
          message: `looted ${corpse.name}'s cache`,
        })
      }
      // 4) THIRSTY but dry here → march toward the nearest water source.
      else if (thirsty) {
        const [tx, ty] = nearestWater(a.x, a.y)
        ;[a.x, a.y] = stepToward(a.x, a.y, tx, ty)
        a.lastAction = 'move'
      }
      // 5) COMFORTABLE + has a neighbour → a social act (the boundary space, §4).
      else if (neighbors.length > 0) {
        const other = neighbors[Math.floor(rng() * neighbors.length)]
        // Aggressive + a richer neighbour → coercion (P5, the hardest boundary).
        if (a.stance === 'aggressive' && other.water > a.water + 8 && rng() < 0.45) {
          a.lastAction = 'attack'
          const win = rng() < a.water / (a.water + other.water + 1) + 0.15
          if (win) {
            const stolen = Math.min(12, Math.floor(other.water / 3) + 2)
            a.water += stolen
            other.water = Math.max(0, other.water - stolen)
            events.push({
              event_type: 'ATTACK', agent_id: a.id, target_id: other.id, tick,
              message: `raided ${other.name} for ${stolen} water`,
            })
          } else {
            events.push({
              event_type: 'ATTACK', agent_id: a.id, target_id: other.id, tick,
              message: `lunged at ${other.name} — repelled`,
            })
          }
        }
        // Otherwise barter, gossip, or declare a stance.
        else if (rng() < 0.3) {
          a.lastAction = 'trade'
          const g = Math.min(2, a.goods)
          a.goods -= g; other.goods += g; other.water = Math.max(0, other.water - 1); a.water += 1
          events.push({
            event_type: 'TRADE_COMPLETED', agent_id: a.id, target_id: other.id, tick,
            message: `${a.name} ⇄ ${other.name}`,
          })
        }
        else if (rng() < 0.55) {
          a.lastAction = 'talk'
          events.push({
            event_type: 'WHISPER_SENT', agent_id: a.id, target_id: other.id, tick,
            message: WHISPERS[Math.floor(rng() * WHISPERS.length)],
          })
        }
        else {
          a.lastAction = 'signal'
          a.stance = STANCES[Math.floor(rng() * STANCES.length)]
        }
      }
      // 6) COMFORTABLE, alone → occasionally broadcast; else drift & mingle.
      else if (rng() < 0.12) {
        a.lastAction = 'signal'
        events.push({
          event_type: 'BROADCAST_SENT', agent_id: a.id, tick,
          message: BROADCASTS[Math.floor(rng() * BROADCASTS.length)],
        })
      }
      else {
        // Drift toward the centre so the population keeps mingling, not scatters.
        if (rng() < 0.7) {
          ;[a.x, a.y] = stepToward(a.x, a.y, cx, cy)
        } else {
          const [dx, dy] = DIRS[Math.floor(rng() * DIRS.length)]
          if (inBounds(a.x + dx, a.y + dy) && !isMountain(a.x + dx, a.y + dy)) { a.x += dx; a.y += dy }
        }
        a.lastAction = 'move'
      }

      // ── Apply survival economy after the action (Moisture Debt, §2.2) ──────
      a.water -= drain
      const standingOn = at(a.x, a.y).terrain // may differ from `terrain` if moved
      if (standingOn === 'oasis') a.water = Math.min(80, a.water + 8) // §2.2 cost 0
      else if (standingOn === 'settlement' && !thirsty) a.water = Math.min(80, a.water + 1)
      a.water = Math.max(0, a.water)
      a.food = Math.max(0, a.food - (rng() < 0.25 ? 1 : 0))

      return a
    })

    // ── Siphon contention: the prize is DELIBERATELY insufficient (§2.3) ─────
    // Serve claimants in seeded order until the tick's units run out; the rest
    // walk away dry. This denial is the engine of the central conflict.
    if (siphonClaims.length > 0) {
      let pool = base.siphonUnits
      // shuffle deterministically by current water (the desperate push in)
      const queue = [...siphonClaims].sort((p, q) => p.water - q.water)
      let served = 0
      for (const a of queue) {
        if (pool <= 0) break
        const want = Math.min(SATED - a.water > 0 ? SATED - a.water : 6, 14, pool)
        if (want <= 0) continue
        a.water = Math.min(80, a.water + want)
        pool -= want
        served += 1
      }
      events.push({
        event_type: 'SIPHON_DISTRIBUTED', tick,
        message: `${served}/${siphonClaims.length} drank — ${siphonClaims.length - served} turned away`,
      })
    }

    // ── Death pass: water ≤ 0 → permanent death; corpse becomes a cache ──────
    const aliveCount = agents.filter((a) => a.alive).length
    const deathBias = scale.agents > 100 ? 0.0010 : 0.004
    agents = agents.map((src) => {
      if (!src.alive) return src
      const a = { ...src }
      const dying = a.water <= 0
      if (dying || (rng() < deathBias && aliveCount > scale.agents * 0.3)) {
        a.alive = false
        a.lastAction = 'died'
        // Leftover resources stay on the corpse as a scavengeable death-cache.
        events.push({
          event_type: 'AGENT_DIED', agent_id: a.id, tick,
          message: dying ? 'died of thirst' : 'lost in the dunes',
        })
      }
      return a
    })

    // Re-stamp the Siphon cell output for this tick (read by the renderer).
    const siphonUnits = base.siphonUnits
    cells[cy * W + cx].water = siphonUnits

    const snapshot: WorldSnapshot = {
      tick,
      gridW: W,
      gridH: H,
      cells,
      agents,
      stormActive,
      heatZoneCenter: heat,
      siphonUnits,
    }
    return { snapshot, events }
  }

  return { scale, snapshot: base, step }
}
