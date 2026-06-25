// Agent sprite renderer — Mana Seed paper-doll figures, directional animation,
// and per-action visual cues. Tied to the world rules: facing comes from the
// movement vector, the played animation comes from the resolved action, and the
// stance drives the outfit + a 1px outline tint (no garish recolouring).
//
// LOD: full 64px composited sprites when a cell renders large; a single
// stance-tinted quad + water-pressure dot when zoomed out (1000-agent view).

import type { Agent } from '../types/simulation'
import {
  CHAR_FRAME, BODIES, OUTFITS, HAIR,
  ANIMS, FACING_ROW, type Facing, type Anim, img,
} from './assets'

export type { Facing }

// Locked palette (mirrors index.css tokens) — the only stance colour signal.
const STANCE_TINT: Record<Agent['stance'], string> = {
  friendly:   '#7fae8a',
  neutral:    '#b6b1a7',
  aggressive: '#c47b73',
}
const GOLD = '#c2a26d'

// ── Per-agent stable appearance (body/outfit/hair) from a hash of the id ──────
function hashId(id: string): number {
  let h = 2166136261
  for (let i = 0; i < id.length; i++) { h ^= id.charCodeAt(i); h = Math.imul(h, 16777619) }
  return (h >>> 0)
}

interface Look { body: string; outfit: string; hair: string }
const lookCache = new Map<string, Look>()

function lookFor(a: Agent): Look {
  const cached = lookCache.get(a.id)
  if (cached) return cached
  const h = hashId(a.id)
  const body = BODIES[h % BODIES.length]
  // friendly wear the robe; others the pants outfit (manifest stance mapping)
  const outfit = a.stance === 'friendly' ? OUTFITS.robe : OUTFITS.pants
  const look = { body, outfit, hair: HAIR }
  lookCache.set(a.id, look)
  return look
}

// ── Facing from a movement delta (diagonal → dominant axis) ───────────────────
export function facingFromDelta(dx: number, dy: number, fallback: Facing = 'down'): Facing {
  if (dx === 0 && dy === 0) return fallback
  if (Math.abs(dx) >= Math.abs(dy)) return dx < 0 ? 'left' : 'right'
  return dy < 0 ? 'up' : 'down'
}

// ── Map a resolved action verb to an animation + cue kind ─────────────────────
type CueKind = 'none' | 'whisper' | 'broadcast' | 'consume' | 'trade' | 'attack' | 'scavenge'
interface ActionVisual { anim: Anim; cue: CueKind; moving: boolean }

function visualFor(action: string | undefined, moving: boolean): ActionVisual {
  switch (action) {
    case 'move':     return { anim: ANIMS.walk,  cue: 'none',      moving: true }
    case 'consume':  return { anim: ANIMS.pull,  cue: 'consume',   moving: false }
    case 'trade':    return { anim: ANIMS.pull,  cue: 'trade',     moving: false }
    case 'scavenge': return { anim: ANIMS.push,  cue: 'scavenge',  moving: false }
    case 'attack':   return { anim: ANIMS.jump,  cue: 'attack',    moving: false }
    case 'talk':     return { anim: ANIMS.stand, cue: 'whisper',   moving: false }
    case 'signal':   return { anim: ANIMS.stand, cue: 'broadcast', moving: false }
    case 'wait':
    default:         return { anim: moving ? ANIMS.walk : ANIMS.stand, cue: 'none', moving }
  }
}

function frameCol(anim: Anim, nowMs: number, phase: number): number {
  if (anim.fps <= 0 || anim.cols.length <= 1) return anim.cols[0]
  const i = Math.floor((nowMs / 1000) * anim.fps + phase) % anim.cols.length
  return anim.cols[i]
}

export interface DrawAgentCtx {
  ctx: CanvasRenderingContext2D
  cell: number          // px per cell on screen
  ox: number; oy: number
  now: number
  interp: number        // 0..1 across current tick
  selectedId: string | null
}

/**
 * Full composited sprite for the detailed (25-agent) view.
 * `ix,iy` are the interpolated cell coordinates; `facing` from movement delta.
 */
export function drawAgentSprite(
  d: DrawAgentCtx, a: Agent, ix: number, iy: number, facing: Facing,
): void {
  const { ctx, cell, ox, oy, now } = d
  const cxp = ox + (ix + 0.5) * cell
  const footY = oy + (iy + 1) * cell // feet anchor at the cell's bottom

  const moving = d.interp < 0.98 && a.alive // mid-step this tick
  const vis = visualFor(a.lastAction, moving)
  const phase = (hashId(a.id) % 6)

  // sprite is drawn at `spritePx`, scaled from the 64px frame; keep it a touch
  // larger than the cell so figures read clearly but still sit in their tile.
  const spritePx = cell * 1.9
  const sx = cxp - spritePx / 2
  // the 64px frame has ~20px of headroom and feet near y=44/64; align feet.
  const sy = footY - spritePx * (44 / 64) - cell * 0.05

  // shadow
  ctx.save()
  ctx.globalAlpha = a.alive ? 0.32 : 0.12
  ctx.fillStyle = '#000'
  ctx.beginPath()
  ctx.ellipse(cxp, footY - cell * 0.12, cell * 0.34, cell * 0.14, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()

  if (!a.alive) {
    drawDeadMark(ctx, cxp, footY - cell * 0.3, cell)
    return
  }

  const row = vis.anim.baseRow + FACING_ROW[facing]
  const col = frameCol(vis.anim, now, phase)
  const fsx = col * CHAR_FRAME
  const fsy = row * CHAR_FRAME

  const look = lookFor(a)
  // subtle idle bob when standing still
  const bob = vis.anim.fps === 0 ? Math.sin(now / 600 + phase) * (cell * 0.04) : 0

  for (const src of [look.body, look.outfit, look.hair]) {
    const im = img(src)
    if (!im) continue
    ctx.drawImage(im, fsx, fsy, CHAR_FRAME, CHAR_FRAME, sx, sy + bob, spritePx, spritePx)
  }

  // stance ring (1px tint) + selection highlight
  const isSel = a.id === d.selectedId
  if (isSel) {
    ctx.strokeStyle = GOLD
    ctx.lineWidth = 1.5
    ctx.beginPath(); ctx.ellipse(cxp, footY - cell * 0.1, cell * 0.42, cell * 0.18, 0, 0, Math.PI * 2); ctx.stroke()
  } else {
    ctx.strokeStyle = STANCE_TINT[a.stance]
    ctx.globalAlpha = 0.5
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.ellipse(cxp, footY - cell * 0.1, cell * 0.34, cell * 0.14, 0, 0, Math.PI * 2); ctx.stroke()
    ctx.globalAlpha = 1
  }

  // water-pressure bar beneath the figure
  drawWaterBar(ctx, a, cxp, footY + cell * 0.06, cell)

  // action cue overlay
  drawCue(ctx, vis.cue, cxp, sy + bob, spritePx, cell, now)
}

function drawWaterBar(ctx: CanvasRenderingContext2D, a: Agent, cx: number, y: number, cell: number): void {
  const w = cell * 0.6
  const h = Math.max(1.5, cell * 0.06)
  const x = cx - w / 2
  const pct = Math.max(0, Math.min(1, a.water / 60))
  ctx.fillStyle = 'rgba(0,0,0,0.45)'
  ctx.fillRect(x, y, w, h)
  ctx.fillStyle = pct < 0.18 ? '#c47b73' : pct < 0.4 ? '#c79a64' : '#8aa6b4'
  ctx.fillRect(x, y, w * pct, h)
}

function drawDeadMark(ctx: CanvasRenderingContext2D, cx: number, cy: number, cell: number): void {
  // small cairn / remains glyph — muted, no body
  ctx.save()
  ctx.globalAlpha = 0.55
  ctx.strokeStyle = '#5a4e3a'
  ctx.lineWidth = Math.max(1, cell * 0.06)
  const r = cell * 0.22
  ctx.beginPath()
  ctx.moveTo(cx - r, cy + r); ctx.lineTo(cx, cy - r * 0.4); ctx.lineTo(cx + r, cy + r)
  ctx.stroke()
  ctx.restore()
}

// ── Action cue overlays (procedural — bubbles/glyphs in the locked palette) ────
function drawCue(
  ctx: CanvasRenderingContext2D, cue: CueKind,
  cx: number, spriteTop: number, spritePx: number, cell: number, now: number,
): void {
  if (cue === 'none') return
  const topY = spriteTop + spritePx * 0.18

  if (cue === 'whisper' || cue === 'broadcast') {
    const broadcast = cue === 'broadcast'
    const bw = broadcast ? cell * 0.9 : cell * 0.6
    const bh = bw * 0.7
    const bx = broadcast ? cx - bw / 2 : cx + cell * 0.2
    const by = topY - bh - cell * 0.1
    if (broadcast) {
      // expanding ring = world-wide reach
      const t = (now % 1600) / 1600
      ctx.strokeStyle = `rgba(138,166,180,${(0.5 * (1 - t)).toFixed(3)})`
      ctx.lineWidth = 1
      ctx.beginPath(); ctx.arc(cx, by + bh / 2, cell * 0.4 + t * cell * 1.1, 0, Math.PI * 2); ctx.stroke()
    }
    roundedBubble(ctx, bx, by, bw, bh, broadcast ? '#8aa6b4' : '#b6b1a7')
    return
  }

  if (cue === 'attack') {
    const t = (now % 360) / 360
    ctx.strokeStyle = `rgba(196,123,115,${(0.8 * (1 - t)).toFixed(3)})`
    ctx.lineWidth = 2
    ctx.beginPath(); ctx.arc(cx, topY, cell * 0.2 + t * cell * 0.5, 0, Math.PI * 2); ctx.stroke()
    return
  }

  // consume / trade / scavenge → small resource glyph rising over the head
  const glyphColor = cue === 'scavenge' ? '#c79a64' : '#8aa6b4'
  const rise = ((now % 700) / 700) * cell * 0.3
  ctx.fillStyle = glyphColor
  ctx.globalAlpha = 0.85
  const gx = cx + cell * 0.18
  const gy = topY - rise
  // teardrop-ish dot
  ctx.beginPath(); ctx.arc(gx, gy, Math.max(1.4, cell * 0.09), 0, Math.PI * 2); ctx.fill()
  ctx.globalAlpha = 1
}

function roundedBubble(
  ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, stroke: string,
): void {
  const r = Math.min(w, h) * 0.32
  ctx.fillStyle = 'rgba(18,18,20,0.92)'
  ctx.strokeStyle = stroke
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
  ctx.fill(); ctx.stroke()
  // little tail
  ctx.beginPath()
  ctx.moveTo(x + w * 0.3, y + h)
  ctx.lineTo(x + w * 0.22, y + h + h * 0.35)
  ctx.lineTo(x + w * 0.45, y + h)
  ctx.closePath()
  ctx.fillStyle = 'rgba(18,18,20,0.92)'
  ctx.fill()
}

// ── Speech / chat bubbles (overlaid in a second pass, above all sprites) ───────
// A word-wrapped, faded chat bubble anchored above an agent's head. Whisper bubbles
// read as a directed aside (muted, with a downward tail); broadcast bubbles are
// brighter and wider (a call to the whole population). `age01` is 0→1 across the
// bubble's lifetime, driving a quick fade-in and a tail-end fade-out so bubbles
// never pop. Pure draw — all lifetime state lives in the store; this only paints.
const BUBBLE_FONT = '600 11px "JetBrains Mono", monospace'
const BUBBLE_FILL = 'rgba(16,15,18,0.93)'
const THOUGHT_FILL = 'rgba(18,20,30,0.88)'
const WHISPER_STROKE = '#b6b1a7'
const BROADCAST_STROKE = '#d7b988'
const THOUGHT_STROKE = '#7f93b8'
const BUBBLE_TEXT = '#ece9e2'
const THOUGHT_TEXT = '#c4cde0'

function wrapText(
  ctx: CanvasRenderingContext2D, text: string, maxWidth: number, maxLines: number,
): string[] {
  const words = text.split(/\s+/).filter(Boolean)
  const lines: string[] = []
  let line = ''
  for (const word of words) {
    const trial = line ? `${line} ${word}` : word
    if (ctx.measureText(trial).width > maxWidth && line) {
      lines.push(line)
      line = word
      if (lines.length === maxLines - 1) break
    } else {
      line = trial
    }
  }
  if (line && lines.length < maxLines) lines.push(line)
  // If we truncated, ellipsize the last surfaced line.
  const consumed = lines.join(' ').split(/\s+/).filter(Boolean).length
  if (consumed < words.length && lines.length) {
    let last = lines[lines.length - 1]
    while (last && ctx.measureText(last + '…').width > maxWidth) last = last.slice(0, -1)
    lines[lines.length - 1] = last + '…'
  }
  return lines
}

export interface SpeechBubbleArgs {
  text: string
  kind: 'whisper' | 'broadcast' | 'thought'
  /** 0→1 across the bubble's wall-clock lifetime (store TTL). */
  age01: number
  /** True for the currently-selected agent → bubble is emphasised. */
  selected: boolean
  /** Top clip boundary (px). The bubble is kept fully below this so it never
   *  hides behind the panel chrome / clips off the top of the canvas. */
  minTop?: number
  /** Left/right clip boundaries (px) so wide bubbles stay on the board. */
  minLeft?: number
  maxRight?: number
}

/**
 * Draw one speech bubble centred horizontally on `cx`, with its tail tip at
 * `anchorY` (just above the agent's head). Returns nothing; call in a pass after
 * all sprites so bubbles always layer on top.
 */
export function drawSpeechBubble(
  ctx: CanvasRenderingContext2D, cx: number, anchorY: number, cell: number, b: SpeechBubbleArgs,
): void {
  // Fade in over the first ~12% of life, hold, fade out over the last ~22%.
  const fadeIn = Math.min(1, b.age01 / 0.12)
  const fadeOut = b.age01 > 0.78 ? Math.max(0, (1 - b.age01) / 0.22) : 1
  const alpha = Math.max(0, Math.min(1, fadeIn * fadeOut))
  if (alpha <= 0.01) return

  // Sizing scales gently with cell so it reads at any zoom, clamped to sane px.
  const fontPx = Math.max(9, Math.min(13, cell * 0.5))
  const pad = Math.max(5, cell * 0.22)
  const maxW = Math.max(80, Math.min(180, cell * 7))
  const broadcast = b.kind === 'broadcast'
  const thought = b.kind === 'thought'

  ctx.save()
  ctx.globalAlpha = thought ? alpha * 0.92 : alpha
  ctx.font = `${broadcast ? '700' : thought ? 'italic 500' : '600'} ${fontPx.toFixed(0)}px "JetBrains Mono", monospace`
  void BUBBLE_FONT

  const lines = wrapText(ctx, b.text, maxW, 3)
  const lineH = fontPx + 3
  let textW = 0
  for (const ln of lines) textW = Math.max(textW, ctx.measureText(ln).width)

  const bw = textW + pad * 2
  const bh = lines.length * lineH + pad * 1.4
  // Rise slightly as it ages so it feels like it lifts off the agent.
  const lift = b.age01 * cell * 0.25
  let bx = cx - bw / 2
  let by = anchorY - bh - cell * 0.18 - lift

  // Keep the bubble on-board: clamp against the top (so it never hides behind the
  // panel chrome) and the left/right edges. The tail/dots are only drawn when the
  // bubble still sits above the agent after clamping.
  const minTop = b.minTop ?? 2
  const minLeft = b.minLeft ?? 2
  const maxRight = b.maxRight ?? Infinity
  if (by < minTop) by = minTop
  if (bx < minLeft) bx = minLeft
  if (bx + bw > maxRight) bx = maxRight - bw
  const tailX = Math.max(bx + bw * 0.2, Math.min(cx, bx + bw * 0.8)) // keep tail under the body
  const showTail = by + bh <= anchorY - cell * 0.08

  // Soft drop shadow for legibility over bright terrain.
  ctx.shadowColor = 'rgba(0,0,0,0.45)'
  ctx.shadowBlur = 6
  ctx.shadowOffsetY = 2

  const stroke = broadcast ? BROADCAST_STROKE : thought ? THOUGHT_STROKE : WHISPER_STROKE
  const fill = thought ? THOUGHT_FILL : BUBBLE_FILL
  const r = thought ? Math.min(bw, bh) * 0.42 : Math.min(bw, bh) * 0.22 // thoughts = puffy/round
  ctx.fillStyle = fill
  ctx.strokeStyle = stroke
  ctx.lineWidth = b.selected ? 1.8 : broadcast ? 1.3 : 1
  if (thought) ctx.setLineDash([3, 2]) // dashed cloud outline for an inner-voice feel
  ctx.beginPath()
  ctx.moveTo(bx + r, by)
  ctx.arcTo(bx + bw, by, bx + bw, by + bh, r)
  ctx.arcTo(bx + bw, by + bh, bx, by + bh, r)
  ctx.arcTo(bx, by + bh, bx, by, r)
  ctx.arcTo(bx, by, bx + bw, by, r)
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
  ctx.setLineDash([])

  ctx.shadowColor = 'transparent'
  if (thought && showTail) {
    // Thought bubbles trail two shrinking "thinking dots" toward the agent instead of
    // a pointed tail — the classic cartoon inner-monologue cue.
    ctx.fillStyle = fill
    ctx.strokeStyle = stroke
    ctx.lineWidth = 1
    const d1 = Math.max(2, cell * 0.12)
    ctx.beginPath(); ctx.arc(tailX - cell * 0.05, by + bh + cell * 0.12, d1, 0, Math.PI * 2); ctx.fill(); ctx.stroke()
    ctx.beginPath(); ctx.arc(tailX + cell * 0.08, by + bh + cell * 0.30, d1 * 0.6, 0, Math.PI * 2); ctx.fill(); ctx.stroke()
  } else if (!thought && showTail) {
    // Tail pointing down to the agent.
    const tw = Math.max(5, cell * 0.18)
    ctx.beginPath()
    ctx.moveTo(tailX - tw, by + bh)
    ctx.lineTo(tailX, by + bh + cell * 0.22)
    ctx.lineTo(tailX + tw, by + bh)
    ctx.closePath()
    ctx.fillStyle = fill
    ctx.fill()
    ctx.strokeStyle = stroke
    ctx.stroke()
  }

  // Broadcast badge dot so the kinds read apart at a glance.
  if (broadcast) {
    ctx.fillStyle = BROADCAST_STROKE
    ctx.beginPath(); ctx.arc(bx + pad * 0.6, by + bh / 2, Math.max(1.5, fontPx * 0.16), 0, Math.PI * 2); ctx.fill()
  }

  // Text — centred on the (possibly clamped) box, not the anchor.
  ctx.fillStyle = thought ? THOUGHT_TEXT : BUBBLE_TEXT
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  const x0 = bx + bw / 2
  let ty = by + pad * 0.7 + lineH / 2
  for (const ln of lines) {
    ctx.fillText(ln, x0, ty)
    ty += lineH
  }
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.restore()
}

// ── LOD quad for the zoomed-out (1000-agent) view ─────────────────────────────
export function drawAgentQuad(
  ctx: CanvasRenderingContext2D, a: Agent, cxp: number, cyp: number, cell: number,
): void {
  if (!a.alive) {
    ctx.globalAlpha = 0.28
    ctx.fillStyle = '#4a3e2e'
    ctx.fillRect(cxp - cell * 0.3, cyp - cell * 0.3, cell * 0.6, cell * 0.6)
    ctx.globalAlpha = 1
    return
  }
  const r = Math.max(1.6, cell * 0.5)
  // thin dark seat so the dot reads against bright sand at full zoom-out
  ctx.fillStyle = 'rgba(20,16,10,0.55)'
  ctx.beginPath(); ctx.arc(cxp, cyp, r + 0.8, 0, Math.PI * 2); ctx.fill()
  ctx.fillStyle = STANCE_TINT[a.stance]
  ctx.beginPath(); ctx.arc(cxp, cyp, r, 0, Math.PI * 2); ctx.fill()
  // water-pressure ring: red-edged near death
  const pct = Math.max(0, Math.min(1, a.water / 60))
  if (pct < 0.25) {
    ctx.strokeStyle = '#c47b73'
    ctx.lineWidth = Math.max(0.6, cell * 0.16)
    ctx.beginPath(); ctx.arc(cxp, cyp, r, 0, Math.PI * 2); ctx.stroke()
  }
}

export { STANCE_TINT }
