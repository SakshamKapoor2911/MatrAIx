// Procedural desert structures — the tileset ships no building sprites, so the
// settlement and ruins are drawn here as small sandstone dwellings (and their
// collapsed counterparts) in the locked warm palette. Everything is pixel-crisp
// (no smoothing) and deterministic per cell, so a world always bakes the same
// skyline. Buildings are bottom-anchored and overhang upward like the palms, so
// they read as 3-D massing rather than flat tiles.

import { TILE, cellHash } from './assets'

// Warm sandstone palette (sits inside the index.css lock — no neon, no fantasy)
const WALL_LIT   = '#b79468'
const WALL_SHADE = '#8a6b44'
const ROOF        = '#cdb083'
const ROOF_SHADE  = '#b2925f'
const TRIM         = '#6f5436'
const DOOR          = '#2a2018'
const WINDOW         = '#3a2c1e'
const SHADOW          = 'rgba(0,0,0,0.30)'

function px(n: number): number { return Math.round(n) }

/**
 * A single adobe/sandstone dwelling occupying one cell, drawn bottom-anchored
 * so its base sits on the cell and the structure rises into the cell(s) above.
 * `size` 0..1 scales the massing (town centre = bigger). Deterministic via hash.
 */
export function drawBuilding(
  ctx: CanvasRenderingContext2D, cx: number, cy: number, hash: number, size = 1,
): void {
  const T = TILE
  const baseX = cx * T
  const baseY = (cy + 1) * T // bottom edge of the cell

  // footprint a touch narrower than a full cell so neighbours don't merge
  const w = px(T * (0.82 + size * 0.12))
  const h = px(T * (1.05 + size * 0.7)) // taller than one cell → overhangs up
  const x = px(baseX + (T - w) / 2)
  const y = px(baseY - h)

  // ground shadow cast to the SE
  ctx.fillStyle = SHADOW
  ctx.fillRect(x + 2, baseY - 2, w, 3)
  ctx.fillRect(x + w - 1, y + 4, 3, h - 4)

  const roofH = px(h * 0.30)
  const wallY = y + roofH

  // wall block (lit front + shaded right edge)
  ctx.fillStyle = WALL_LIT
  ctx.fillRect(x, wallY, w, baseY - wallY)
  ctx.fillStyle = WALL_SHADE
  ctx.fillRect(x + w - px(w * 0.28), wallY, px(w * 0.28), baseY - wallY)

  // flat roof slab, slightly wider than walls (parapet)
  ctx.fillStyle = ROOF
  ctx.fillRect(x - 1, y, w + 2, roofH)
  ctx.fillStyle = ROOF_SHADE
  ctx.fillRect(x - 1, y + roofH - 2, w + 2, 2)
  ctx.fillStyle = TRIM
  ctx.fillRect(x - 1, y, w + 2, 1)

  // doorway (centered, lower) + a small window when the hut is tall enough
  const doorW = Math.max(2, px(w * 0.26))
  const doorH = Math.max(3, px((baseY - wallY) * 0.55))
  ctx.fillStyle = DOOR
  ctx.fillRect(px(x + w / 2 - doorW / 2), baseY - doorH, doorW, doorH)
  if (h > T * 1.3 && (hash * 100) % 10 > 4) {
    const winW = Math.max(1, px(w * 0.18))
    ctx.fillStyle = WINDOW
    ctx.fillRect(px(x + w * 0.2), wallY + 2, winW, winW)
  }
}

/**
 * A collapsed dwelling for ruins cells — broken low walls, a gap, scattered
 * rubble. No roof. Reads as the same architecture, fallen.
 */
export function drawRuin(
  ctx: CanvasRenderingContext2D, cx: number, cy: number, hash: number,
): void {
  const T = TILE
  const baseX = cx * T
  const baseY = (cy + 1) * T
  const w = px(T * 0.8)
  const x = px(baseX + (T - w) / 2)
  const wallH = px(T * (0.4 + (hash % 0.3)))
  const y = baseY - wallH

  // ground shadow
  ctx.fillStyle = SHADOW
  ctx.fillRect(x + 1, baseY - 2, w, 2)

  // a broken wall: left stub tall, right stub short, gap between
  const stubW = px(w * 0.32)
  ctx.fillStyle = WALL_SHADE
  ctx.fillRect(x, y, stubW, wallH)
  ctx.fillStyle = WALL_LIT
  ctx.fillRect(x, y, stubW, 1)
  // jagged top
  ctx.fillStyle = WALL_SHADE
  const rStubH = px(wallH * 0.55)
  ctx.fillRect(x + w - stubW, baseY - rStubH, stubW, rStubH)
  ctx.fillStyle = WALL_LIT
  ctx.fillRect(x + w - stubW, baseY - rStubH, stubW, 1)

  // rubble dots in the gap
  ctx.fillStyle = TRIM
  const r1 = (hash * 13) % 1
  const r2 = (hash * 29) % 1
  ctx.fillRect(px(x + w * (0.4 + r1 * 0.2)), baseY - 2, 2, 2)
  ctx.fillRect(px(x + w * (0.5 + r2 * 0.2)), baseY - 1, 1, 1)
}

// Helper to vary structures stably per cell.
export function buildingHash(x: number, y: number): number {
  return cellHash(x, y, 41)
}
