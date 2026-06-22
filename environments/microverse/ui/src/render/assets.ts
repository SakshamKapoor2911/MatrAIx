// Asset registry + loader for the MircoVerse world renderer.
//
// Source of truth (per the curated asset manifest): only `desert/*.png` (16px
// terrain + decor sheets, plus water.png as the Siphon hero) and
// `character/**/*.png` (512×512 paper-doll sheets) are used. Every `ts_*`,
// `tile_*`, `t2_*`, `t3_*`, `inspect_*`, `confirm_*`, `tileset*`, `preview_*`
// file is a discarded hand-crop and is intentionally NOT referenced here.
//
// Assets live under ui/public and are served from the site root ("/desert/…").
// Everything loads once at module init; the renderer polls `assetsReady()` and
// re-bakes terrain when ready.

export const TILE = 16 // native tile size in px (both terrain sheets and decor)

// ── Image cache ──────────────────────────────────────────────────────────────
const images = new Map<string, HTMLImageElement>()
let pending = 0
let allRequested = false

function load(src: string): HTMLImageElement {
  const existing = images.get(src)
  if (existing) return existing
  const img = new Image()
  pending++
  img.onload = () => { pending-- }
  img.onerror = () => { pending--; /* leave broken image out of draws */ }
  img.src = src
  images.set(src, img)
  return img
}

export function img(src: string): HTMLImageElement | null {
  const i = images.get(src)
  return i && i.complete && i.naturalWidth > 0 ? i : null
}

export function assetsReady(): boolean {
  return allRequested && pending === 0
}

// ── Terrain → 3×3 autotile blob sheet ─────────────────────────────────────────
// Each *_3x3.png is 144×48 = 9 cols × 3 rows of 16px subtiles. The cols 0–2 ×
// rows 0–2 block is a classic 9-slice (4 corners, 4 edges, centre fill at 1,1).
// Desert is the base layer (always centre fill); the other four terrains are
// "punched-in" patches that autotile their edges against the surrounding sand.
import type { Terrain } from '../types/simulation'

export const TERRAIN_SHEET: Record<Terrain, string> = {
  desert:     '/desert/sand_3x3.png',
  oasis:      '/desert/dry_dirt_3x3.png',
  mountain:   '/desert/slate_3x3.png',
  settlement: '/desert/cobbled_sandstone_3x3.png',
  ruins:      '/desert/sandstone_3x3.png',
}

export const SIPHON_SRC = '/desert/water.png' // hero structure, not a ground tile

// ── Decor catalogue (deterministic per-cell overlay, tied to world rules) ──────
// Each decor sprite signals a world fact: remains = death-cache, palm/iris =
// oasis water, cactus/bush = arid desert, stones = mountain rock mass.
export const DECOR = {
  remains: ['/desert/decor_remains1.png', '/desert/decor_remains2.png', '/desert/decor_remains3.png', '/desert/decor_remains4.png'],
  palm: ['/desert/tree_palm1.png', '/desert/tree_palm2.png', '/desert/tree_palm3.png', '/desert/tree_palm5.png'],
  iris: ['/desert/decor_iris1.png', '/desert/decor_iris3.png', '/desert/decor_iris5.png', '/desert/decor_iris7.png'],
  cactus: ['/desert/decor_cactus1.png', '/desert/decor_cactus2.png', '/desert/decor_cactus3.png', '/desert/decor_cactus_small1.png'],
  bush: ['/desert/decor_dead_bush1.png', '/desert/decor_dead_bush2.png', '/desert/decor_dead_bush3.png', '/desert/decor_dead_bush_small.png'],
  stoneLarge: ['/desert/decor_stone_large1.png', '/desert/decor_stone_large2.png'],
  stoneSmall: ['/desert/decor_stone_small1.png', '/desert/decor_stone_small2.png', '/desert/decor_stone_small3.png'],
} as const

// ── Character paper-doll layers (512×512 = 8×8 of 64px frames) ─────────────────
export const CHAR_FRAME = 64
export const CHAR_COLS = 8

// Two fully-animated body builds (char_a_pONE2 is only partially populated in
// the walk rows, so it is deliberately excluded). Appearance variety comes from
// body × outfit × hair combinations, not from partial sheets.
export const BODIES = [
  '/character/char_a_p1/char_a_p1_0bas_humn_v00.png',
  '/character/char_a_pONE3/char_a_pONE3_0bas_humn_v00.png',
]
export const OUTFITS = {
  robe:  '/character/char_a_p1/1out/char_a_p1_1out_fstr_v01.png',  // friendly cohort
  pants: '/character/char_a_p1/1out/char_a_p1_1out_pfpn_v01.png',  // neutral/aggressive cohort
}
export const HAIR = '/character/char_a_p1/4har/char_a_p1_4har_bob1_v00.png'

// ── Animation frame map (verified against the sheet + Mana Seed guide) ─────────
// Facing → row offset within a block; down/up/left/right = +0/+1/+2/+3.
export type Facing = 'down' | 'up' | 'left' | 'right'
export const FACING_ROW: Record<Facing, number> = { down: 0, up: 1, left: 2, right: 3 }

export interface Anim {
  baseRow: number      // top row of the 4-facing block
  cols: number[]       // column indices forming the loop
  fps: number          // 0 = hold first frame
}
// Rows 0–3 = stand/push/pull/jump (top block); rows 4–7 = walk/run (bottom block).
export const ANIMS = {
  stand: { baseRow: 0, cols: [0],             fps: 0 },
  push:  { baseRow: 0, cols: [2, 3],          fps: 4 },  // scavenge (dig)
  pull:  { baseRow: 0, cols: [4, 5],          fps: 4 },  // consume / trade
  jump:  { baseRow: 0, cols: [6, 7],          fps: 6 },  // attack (lunge)
  walk:  { baseRow: 4, cols: [0, 1, 2, 3, 4, 5], fps: 8 },
} as const satisfies Record<string, Anim>

// ── Kick off loading ───────────────────────────────────────────────────────
export function preloadAll(): void {
  if (allRequested) return
  for (const s of Object.values(TERRAIN_SHEET)) load(s)
  load(SIPHON_SRC)
  for (const group of Object.values(DECOR)) for (const s of group) load(s)
  for (const s of BODIES) load(s)
  for (const s of Object.values(OUTFITS)) load(s)
  load(HAIR)
  allRequested = true
}

// ── Deterministic per-cell hash (decor placement; no RNG, stable across frames)
export function cellHash(x: number, y: number, salt = 0): number {
  let h = (x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)
  h = (h ^ (h >>> 13)) >>> 0
  return (h % 100000) / 100000 // [0,1)
}
