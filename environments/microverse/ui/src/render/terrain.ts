// Terrain baker — composes the static ground into one offscreen canvas.
//
// Why bake: terrain is static for a world (only the Siphon cell + agents move),
// so autotiling + decor placement run ONCE into a gridW*16 × gridH*16 buffer and
// the live renderer just blits that buffer scaled to the viewport each frame.
// This keeps the per-frame cost to one drawImage + the agents, even at 200×200.
//
// Everything here is deterministic: decor is chosen by a stable per-cell hash of
// (x,y), so the same world always bakes the same picture (Protocol.md §1).

import type { Cell, Terrain, WorldSnapshot } from '../types/simulation'
import {
  TILE, TERRAIN_SHEET, DECOR, img, cellHash,
} from './assets'
import { drawBuilding, drawRuin, buildingHash } from './buildings'

// Same-terrain 9-slice: pick the subtile column/row from cardinal neighbours.
// blob is 9 cols × 3 rows of 16px; the 3×3 at cols 0–2 is the classic 9-slice
// (centre fill at col 1,row 1). Desert is the base field and always uses centre.
function sliceCol(sameW: boolean, sameE: boolean): number {
  if (!sameW) return 0
  if (!sameE) return 2
  return 1
}
function sliceRow(sameN: boolean, sameS: boolean): number {
  if (!sameN) return 0
  if (!sameS) return 2
  return 1
}

interface Grid {
  at(x: number, y: number): Terrain | null
}

function makeGrid(snap: WorldSnapshot): Grid {
  const { gridW, gridH, cells } = snap
  // cells are row-major but be defensive: build an index by (x,y).
  const map = new Map<number, Terrain>()
  for (const c of cells) map.set(c.y * gridW + c.x, c.terrain)
  return {
    at(x, y) {
      if (x < 0 || x >= gridW || y < 0 || y >= gridH) return null
      return map.get(y * gridW + x) ?? null
    },
  }
}

// Draw a decor sprite bottom-anchored to a cell (its base sits on the cell, the
// sprite may overhang upward — e.g. palms). dx/dy nudge from the cell origin.
function blitDecor(
  ctx: CanvasRenderingContext2D, src: string | undefined,
  cx: number, cy: number, dx = 0, dy = 0,
): void {
  if (!src) return
  const im = img(src)
  if (!im) return
  const px = cx * TILE + dx
  // bottom-align: sprite's bottom edge rests at the cell's bottom
  const py = (cy + 1) * TILE - im.naturalHeight + dy
  ctx.drawImage(im, Math.round(px), Math.round(py))
}

function pick<T>(arr: readonly T[], r: number): T {
  return arr[Math.floor(r * arr.length) % arr.length]
}

// A small cache of goods sitting in the open desert — the periphery-wealth lure
// (World.md §2). Drawn programmatically in the locked restrained amber (no new
// asset, no neon): a little pile of stacked crates/bundles, bottom-anchored in the
// cell on a soft shadow so it reads as "tradeable wealth out here in the dangerous
// open" — distinct from the bleached skeletons that mark ruins death-caches, and
// never competing with the Siphon's saturated cyan (the board's only saturated accent).
function drawGoodsCache(ctx: CanvasRenderingContext2D, cx: number, cy: number, amount: number): void {
  const cxp = cx * TILE + TILE / 2
  const baseY = (cy + 1) * TILE - 2
  const n = Math.min(4, Math.max(1, amount))

  // ground shadow grounds the pile so it doesn't look like loose noise
  ctx.fillStyle = 'rgba(40,28,12,0.32)'
  ctx.beginPath()
  ctx.ellipse(cxp, baseY + 0.5, 4.2, 1.6, 0, 0, Math.PI * 2)
  ctx.fill()

  // stacked little blocks: warm amber faces with a darker right/under edge for form
  const place = [
    [-3, 0], [0, 0], [3, 0],   // bottom row (up to 3 wide)
    [-1.5, -3], [1.5, -3],     // second row
    [0, -6],                   // cap
  ]
  const blocks = Math.min(place.length, 1 + n)
  for (let i = 0; i < blocks; i++) {
    const [dx, dy] = place[i]
    const px = Math.round(cxp + dx - 1.5)
    const py = Math.round(baseY + dy - 3)
    ctx.fillStyle = 'rgba(176,116,34,0.95)'      // shaded side
    ctx.fillRect(px, py, 3, 3)
    ctx.fillStyle = 'rgba(206,150,58,0.97)'      // lit face
    ctx.fillRect(px, py, 2, 2)
  }
  // a single bright glint so the pile catches the eye at the detailed scale
  ctx.fillStyle = 'rgba(228,192,128,0.98)'
  ctx.fillRect(Math.round(cxp - 1), Math.round(baseY - 3 * Math.min(2, Math.floor(n / 2)) - 3), 1, 1)
}

export interface BakedTerrain {
  canvas: HTMLCanvasElement
  tilePx: number   // native px per cell in the buffer (== TILE)
  gridW: number
  gridH: number
  detailed: boolean
}

/**
 * Bake the static terrain for a snapshot into an offscreen canvas.
 * detailed=false (large grids) skips autotiling + decor for performance and
 * draws a flat centre-fill tile per cell.
 */
export function bakeTerrain(snap: WorldSnapshot): BakedTerrain {
  const { gridW, gridH } = snap
  const detailed = gridW < 120
  const canvas = document.createElement('canvas')
  canvas.width = gridW * TILE
  canvas.height = gridH * TILE
  const ctx = canvas.getContext('2d')!
  ctx.imageSmoothingEnabled = false

  const grid = makeGrid(snap)

  // Pass 1: ground tiles. Desert underlays the whole board first so every
  // punched-in patch has sand showing through its autotiled edges.
  const sandSheet = img(TERRAIN_SHEET.desert)
  for (const c of snap.cells) {
    const dx = c.x * TILE
    const dy = c.y * TILE
    // base sand everywhere
    if (sandSheet) ctx.drawImage(sandSheet, TILE, TILE, TILE, TILE, dx, dy, TILE, TILE)

    if (c.terrain === 'desert') continue
    const sheet = img(TERRAIN_SHEET[c.terrain])
    if (!sheet) continue

    if (!detailed) {
      ctx.drawImage(sheet, TILE, TILE, TILE, TILE, dx, dy, TILE, TILE)
      continue
    }
    // autotile this patch's edge against same-terrain cardinal neighbours
    const sameN = grid.at(c.x, c.y - 1) === c.terrain
    const sameS = grid.at(c.x, c.y + 1) === c.terrain
    const sameW = grid.at(c.x - 1, c.y) === c.terrain
    const sameE = grid.at(c.x + 1, c.y) === c.terrain
    const sc = sliceCol(sameW, sameE)
    const sr = sliceRow(sameN, sameS)
    ctx.drawImage(sheet, sc * TILE, sr * TILE, TILE, TILE, dx, dy, TILE, TILE)
  }

  if (!detailed) return { canvas, tilePx: TILE, gridW, gridH, detailed }

  // Pass 2: ground-level decor (no upward overhang) — deterministic per cell.
  for (const c of snap.cells) {
    placeGroundDecor(ctx, c)
  }

  // Pass 3: standing structures + tall decor, drawn TOP→BOTTOM so that a row's
  // overhang is correctly overlapped by the row below it (painter's order).
  const sip = snap.cells.find((c) => c.siphon)
  const cx = sip ? sip.x : Math.floor(gridW / 2)
  const cy = sip ? sip.y : Math.floor(gridH / 2)
  const rows = [...snap.cells].sort((a, b) => a.y - b.y || a.x - b.x)
  for (const c of rows) {
    placeStructures(ctx, c, cx, cy)
  }

  return { canvas, tilePx: TILE, gridW, gridH, detailed }
}

// Flat, ground-level decor that does not overhang upward (safe to draw before
// structures). Stones, iris clumps, bushes, scattered rubble, death-caches.
function placeGroundDecor(ctx: CanvasRenderingContext2D, c: Cell): void {
  const r = cellHash(c.x, c.y)
  switch (c.terrain) {
    case 'oasis': {
      if (r >= 0.18 && r < 0.72) blitDecor(ctx, pick(DECOR.iris, cellHash(c.x, c.y, 3)), c.x, c.y)
      break
    }
    case 'desert': {
      // Goods sitting in the open desert (periphery-wealth, World.md §2) — the lure
      // that draws agents away from the Siphon. Drawn over any arid decor below.
      if ((c.goods ?? 0) > 0) drawGoodsCache(ctx, c.x, c.y, c.goods)
      else if (r < 0.05) blitDecor(ctx, pick(DECOR.cactus, cellHash(c.x, c.y, 5)), c.x, c.y)
      else if (r < 0.09) blitDecor(ctx, pick(DECOR.bush, cellHash(c.x, c.y, 11)), c.x, c.y)
      break
    }
    case 'mountain': {
      if (r < 0.45) blitDecor(ctx, pick(DECOR.stoneLarge, cellHash(c.x, c.y, 13)), c.x, c.y)
      break
    }
    case 'ruins': {
      // death-cache marker where goods/food were dropped; otherwise rubble
      const hasCache = (c.goods ?? 0) > 0 || (c.food ?? 0) > 0
      if (hasCache) blitDecor(ctx, pick(DECOR.remains, cellHash(c.x, c.y, 17)), c.x, c.y)
      else if (r < 0.45) blitDecor(ctx, pick(DECOR.stoneSmall, cellHash(c.x, c.y, 19)), c.x, c.y)
      break
    }
    case 'settlement': {
      if (r > 0.9) blitDecor(ctx, pick(DECOR.iris, cellHash(c.x, c.y, 23)), c.x, c.y)
      break
    }
  }
}

// Tall, upward-overhanging elements: palms, town dwellings, and collapsed ruin
// walls. Must be drawn in top→bottom row order by the caller.
function placeStructures(
  ctx: CanvasRenderingContext2D, c: Cell, centerX: number, centerY: number,
): void {
  const r = cellHash(c.x, c.y)
  switch (c.terrain) {
    case 'oasis': {
      if (r < 0.18) blitDecor(ctx, pick(DECOR.palm, cellHash(c.x, c.y, 7)), c.x, c.y)
      break
    }
    case 'settlement': {
      if (c.siphon) break // the Siphon hero is drawn live by the canvas
      const d = Math.abs(c.x - centerX) + Math.abs(c.y - centerY)
      // Keep a clear plaza around the ~3-cell-wide Siphon hero so dwellings
      // never crowd the prize at the town's heart.
      if (d <= 2) break
      // Dense dwellings near the centre, thinning toward the edge → a real
      // town. Skip a few cells as courtyards/streets for an organic skyline.
      const skip = cellHash(c.x, c.y, 31)
      if (skip < 0.22) break
      const size = Math.max(0.2, 1 - d / 14)
      drawBuilding(ctx, c.x, c.y, buildingHash(c.x, c.y), size)
      break
    }
    case 'ruins': {
      // collapsed dwellings interspersed with the rubble (not on cache cells)
      const hasCache = (c.goods ?? 0) > 0 || (c.food ?? 0) > 0
      if (!hasCache && r >= 0.45 && r < 0.78) drawRuin(ctx, c.x, c.y, buildingHash(c.x, c.y))
      break
    }
  }
}
