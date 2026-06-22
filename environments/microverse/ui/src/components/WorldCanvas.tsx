import { useEffect, useRef } from 'react'
import { useWorldStore } from '../store/worldStore'
import { createDemo, type Demo } from '../demo/driveDemo'
import { SCALE_25, SCALE_1000, type WorldScale } from '../demo/genWorld'
import type { Agent, WorldSnapshot } from '../types/simulation'
import { preloadAll, assetsReady, img, SIPHON_SRC, TILE } from '../render/assets'
import { bakeTerrain, type BakedTerrain } from '../render/terrain'
import {
  drawAgentSprite, drawAgentQuad, facingFromDelta, type Facing,
} from '../render/agents'

// Tick cadence for the standalone demo (ms). Interpolation fills the gap.
const DEMO_TICK_MS = 900

interface WorldCanvasProps {
  /** Which demo scale to drive when no live engine is connected. */
  scale: '25' | '1000'
}

function scaleOf(s: '25' | '1000'): WorldScale {
  return s === '1000' ? SCALE_1000 : SCALE_25
}

// ease-in-out cubic
const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

export function WorldCanvas({ scale }: WorldCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number>(0)

  const demoRef = useRef<Demo | null>(null)
  const sizeRef = useRef<{ w: number; h: number }>({ w: 800, h: 500 })
  const mouseRef = useRef<{ x: number; y: number } | null>(null)

  // Baked static terrain (rebuilt when the world/scale changes or assets arrive).
  const bakeRef = useRef<BakedTerrain | null>(null)
  const bakeKeyRef = useRef<string>('')
  // Per-agent facing, persisted across ticks (snapshots don't carry it).
  const facingRef = useRef<Record<string, Facing>>({})
  // Smoothed death-fade alpha per agent.
  const fadeRef = useRef<Record<string, number>>({})

  // Kick off asset loading once.
  useEffect(() => { preloadAll() }, [])

  // ── Demo lifecycle ────────────────────────────────────────────────────────
  useEffect(() => {
    const sc = scaleOf(scale)
    const demo = createDemo(sc)
    demoRef.current = demo
    fadeRef.current = {}
    facingRef.current = {}
    bakeRef.current = null
    bakeKeyRef.current = ''

    const store = useWorldStore.getState()
    store.applySnapshot(demo.snapshot, [])
    store.selectAgent(null)

    let stopped = false
    let timer: ReturnType<typeof setTimeout> | undefined
    function tickLoop() {
      if (stopped) return
      if (!useWorldStore.getState().connected) {
        const { snapshot, events } = demo.step()
        useWorldStore.getState().applySnapshot(snapshot, events)
      }
      timer = setTimeout(tickLoop, DEMO_TICK_MS)
    }
    timer = setTimeout(tickLoop, DEMO_TICK_MS)

    return () => {
      stopped = true
      if (timer) clearTimeout(timer)
    }
  }, [scale])

  // ── Renderer ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!

    let dpr = Math.min(window.devicePixelRatio || 1, 2)
    function applySize() {
      const parent = canvas!.parentElement!
      const rect = parent.getBoundingClientRect()
      const w = Math.max(1, Math.round(rect.width))
      const h = Math.max(1, Math.round(rect.height) || Math.round(w * 0.625))
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas!.width = Math.round(w * dpr)
      canvas!.height = Math.round(h * dpr)
      canvas!.style.width = w + 'px'
      canvas!.style.height = h + 'px'
      sizeRef.current = { w, h }
    }
    applySize()
    const ro = new ResizeObserver(applySize)
    ro.observe(canvas.parentElement!)

    function onMove(e: MouseEvent) {
      const r = canvas!.getBoundingClientRect()
      mouseRef.current = { x: e.clientX - r.left, y: e.clientY - r.top }
    }
    function onLeave() { mouseRef.current = null }
    function onClick() {
      const hit = lastHoverRef.current
      const store = useWorldStore.getState()
      store.selectAgent(hit && hit === store.selectedAgentId ? null : hit)
    }
    canvas.addEventListener('mousemove', onMove)
    canvas.addEventListener('mouseleave', onLeave)
    canvas.addEventListener('click', onClick)

    const lastHoverRef = { current: null as string | null }

    function layout(snap: WorldSnapshot) {
      const { w, h } = sizeRef.current
      const pad = 14
      const availW = w - pad * 2
      const availH = h - pad * 2
      const cell = Math.max(0.5, Math.min(availW / snap.gridW, availH / snap.gridH))
      const boardW = cell * snap.gridW
      const boardH = cell * snap.gridH
      const ox = (w - boardW) / 2
      const oy = (h - boardH) / 2
      return { cell, ox, oy, boardW, boardH }
    }

    // Rebake terrain if the world identity changed or assets just finished.
    function ensureBake(snap: WorldSnapshot) {
      const key = `${snap.gridW}x${snap.gridH}:${assetsReady()}`
      if (bakeKeyRef.current === key && bakeRef.current) return
      if (!assetsReady()) { bakeKeyRef.current = ''; return } // wait for art
      bakeRef.current = bakeTerrain(snap)
      bakeKeyRef.current = key
    }

    function draw(now: number) {
      const state = useWorldStore.getState()
      const snap = state.snapshot
      const { w: CW, h: CH } = sizeRef.current

      ctx.save()
      ctx.scale(dpr, dpr)
      ctx.imageSmoothingEnabled = false
      ctx.clearRect(0, 0, CW, CH)

      if (!snap.cells.length) {
        ctx.restore()
        rafRef.current = requestAnimationFrame(draw)
        return
      }

      const { cell, ox, oy, boardW, boardH } = layout(snap)
      const detailed = snap.gridW < 120
      const sinceMs = Date.now() - state.snapshotAt
      const interp = ease(Math.min(1, sinceMs / DEMO_TICK_MS))

      // board backing
      ctx.fillStyle = '#0d0c0a'
      ctx.fillRect(ox - 1, oy - 1, boardW + 2, boardH + 2)

      // ── Terrain (baked) ─────────────────────────────────────────────────
      ensureBake(snap)
      const bake = bakeRef.current
      if (bake) {
        ctx.imageSmoothingEnabled = false
        ctx.drawImage(
          bake.canvas, 0, 0, bake.gridW * TILE, bake.gridH * TILE,
          ox, oy, boardW, boardH,
        )
        // At the zoomed-out scale, a subtle dark wash lets the agent dots and
        // world conditions read against the otherwise-bright sand field.
        if (!detailed) {
          ctx.fillStyle = 'rgba(13,12,10,0.34)'
          ctx.fillRect(ox, oy, boardW, boardH)
        }
      } else {
        // assets not ready yet — flat neutral ground so layout still reads
        ctx.fillStyle = '#241f18'
        ctx.fillRect(ox, oy, boardW, boardH)
      }

      // ── Siphon hero structure at the centre cell ────────────────────────
      const sip = snap.cells.find((c) => c.siphon)
      if (sip) {
        const sIm = img(SIPHON_SRC)
        const cxp = ox + (sip.x + 0.5) * cell
        const cyp = oy + (sip.y + 0.5) * cell
        // slow pulse on the contested prize
        const pulse = (Math.sin(now / 1400) + 1) / 2
        if (sIm && detailed) {
          // scale the 229×218 structure so its footprint ≈ 3 cells wide
          const sw = cell * 3
          const sh = sw * (sIm.naturalHeight / sIm.naturalWidth)
          ctx.drawImage(sIm, cxp - sw / 2, cyp - sh * 0.82, sw, sh)
        }
        // amber marker ring (works at both scales)
        const r = Math.max(2, cell * 0.32)
        const g = ctx.createRadialGradient(cxp, cyp, 0, cxp, cyp, r * 3)
        g.addColorStop(0, `rgba(194,162,109,${(0.18 + pulse * 0.12).toFixed(3)})`)
        g.addColorStop(1, 'rgba(194,162,109,0)')
        ctx.fillStyle = g
        ctx.beginPath(); ctx.arc(cxp, cyp, r * 3, 0, Math.PI * 2); ctx.fill()
        if (detailed && cell >= 8) {
          ctx.fillStyle = 'rgba(215,185,136,0.8)'
          ctx.font = '9px "JetBrains Mono", monospace'
          ctx.textAlign = 'center'
          ctx.fillText('SIPHON', cxp, cyp - cell * 2.3)
          ctx.textAlign = 'left'
        }
      }

      // ── Heat zone — soft lethal ring ────────────────────────────────────
      if (snap.heatZoneCenter) {
        const [hx, hy] = snap.heatZoneCenter
        const cxp = ox + (hx + 0.5) * cell
        const cyp = oy + (hy + 0.5) * cell
        const hr = Math.min(snap.gridW, snap.gridH) * 0.12 * cell
        const g = ctx.createRadialGradient(cxp, cyp, hr * 0.3, cxp, cyp, hr)
        g.addColorStop(0, 'rgba(196,123,115,0.18)')
        g.addColorStop(1, 'rgba(196,123,115,0)')
        ctx.fillStyle = g
        ctx.beginPath(); ctx.arc(cxp, cyp, hr, 0, Math.PI * 2); ctx.fill()
        ctx.strokeStyle = 'rgba(196,123,115,0.30)'
        ctx.lineWidth = 1
        ctx.beginPath(); ctx.arc(cxp, cyp, hr, 0, Math.PI * 2); ctx.stroke()
      }

      // ── Agents ──────────────────────────────────────────────────────────
      const mouse = mouseRef.current
      let hover: string | null = null
      let hoverBest = Infinity
      const selectedId = state.selectedAgentId
      const fades = fadeRef.current
      const facings = facingRef.current

      // draw far-to-near (y order) so overlap reads correctly at the big scale
      const ordered = detailed
        ? [...snap.agents].sort((a, b) => a.y - b.y)
        : snap.agents

      for (const a of ordered) {
        const prev = state.prevAgents[a.id]
        const fromX = prev ? prev.x : a.x
        const fromY = prev ? prev.y : a.y
        const ix = fromX + (a.x - fromX) * interp
        const iy = fromY + (a.y - fromY) * interp

        // facing from the step delta (persist last non-zero facing)
        const ddx = a.x - fromX
        const ddy = a.y - fromY
        if (ddx !== 0 || ddy !== 0) {
          facings[a.id] = facingFromDelta(ddx, ddy, facings[a.id] ?? 'down')
        }
        const facing = facings[a.id] ?? 'down'

        // death fade
        const target = a.alive ? 1 : 0.2
        const cur = fades[a.id] ?? target
        fades[a.id] = cur + Math.sign(target - cur) * Math.min(0.06, Math.abs(target - cur))

        const cxp = ox + (ix + 0.5) * cell
        const cyp = oy + (iy + 0.5) * cell

        // Detailed (25-agent) board ALWAYS draws the paper-doll sprites — they stay
        // legible down to ~8px cells (verified), so we gate on `detailed` rather than an
        // absolute cell size (which fell back to dots on common <1200px viewports). The
        // zoomed-out 1000-agent board uses the LOD quad, where 1000 sprites would be noise.
        if (detailed) {
          ctx.globalAlpha = Math.max(fades[a.id], a.alive ? 1 : fades[a.id])
          drawAgentSprite(
            { ctx, cell, ox, oy, now, interp, selectedId },
            a, ix, iy, facing,
          )
          ctx.globalAlpha = 1
        } else {
          ctx.globalAlpha = a.alive ? 1 : 0.4
          drawAgentQuad(ctx, a, cxp, cyp, cell)
          ctx.globalAlpha = 1
        }

        // hover hit-test (both modes)
        if (mouse) {
          const d = Math.hypot(mouse.x - cxp, mouse.y - cyp)
          const hitR = detailed ? cell * 0.6 : Math.max(3, cell)
          if (d < hitR && d < hoverBest) { hoverBest = d; hover = a.id }
        }
      }
      lastHoverRef.current = hover

      // ── Sandstorm — translucent haze + drifting streaks ─────────────────
      if (snap.stormActive) {
        ctx.fillStyle = 'rgba(150,135,100,0.12)'
        ctx.fillRect(ox, oy, boardW, boardH)
        ctx.strokeStyle = 'rgba(180,160,120,0.10)'
        ctx.lineWidth = 1
        ctx.beginPath()
        for (let i = 0; i < 24; i++) {
          const sy = oy + ((i * 53.7 + now / 60) % boardH)
          ctx.moveTo(ox, sy)
          ctx.lineTo(ox + boardW, sy + 6)
        }
        ctx.stroke()
      }

      // ── Hover tooltip ───────────────────────────────────────────────────
      if (hover && mouse) {
        const a = snap.agents.find((x) => x.id === hover)
        if (a) drawTooltip(ctx, a, mouse.x, mouse.y, CW)
      }

      // ── Vignette ────────────────────────────────────────────────────────
      const vig = ctx.createRadialGradient(CW / 2, CH / 2, CH * 0.35, CW / 2, CH / 2, CW * 0.72)
      vig.addColorStop(0, 'rgba(0,0,0,0)')
      vig.addColorStop(1, 'rgba(0,0,0,0.28)')
      ctx.fillStyle = vig
      ctx.fillRect(0, 0, CW, CH)

      ctx.restore()
      rafRef.current = requestAnimationFrame(draw)
    }

    rafRef.current = requestAnimationFrame(draw)
    return () => {
      cancelAnimationFrame(rafRef.current)
      ro.disconnect()
      canvas.removeEventListener('mousemove', onMove)
      canvas.removeEventListener('mouseleave', onLeave)
      canvas.removeEventListener('click', onClick)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', width: '100%', height: '100%', borderRadius: 6, cursor: 'pointer' }}
    />
  )
}

function drawTooltip(
  ctx: CanvasRenderingContext2D, a: Agent, mx: number, my: number, CW: number,
): void {
  const label = `${a.name}  ·  ${a.stance}  ·  ${a.water.toFixed(0)}W  ·  ${a.goods.toFixed(0)}G  ·  ${a.alive ? a.lastAction ?? 'alive' : 'dead'}`
  // Stated intention (carried forward) as an italic second line — the
  // stated-vs-revealed pairing the inspector also shows. Clipped so it never
  // runs off the board.
  const rawIntent = a.alive && a.intention ? a.intention : ''
  const intent = rawIntent.length > 52 ? rawIntent.slice(0, 51) + '…' : rawIntent
  ctx.font = '10px "JetBrains Mono", monospace'
  const labelW = ctx.measureText(label).width
  ctx.font = 'italic 9px "JetBrains Mono", monospace'
  const intentW = intent ? ctx.measureText(`“${intent}”`).width : 0
  const pad = 7
  const bw = Math.max(labelW, intentW) + pad * 2
  const bh = intent ? 32 : 20
  const tx = Math.min(mx + 12, CW - bw - 4)
  const ty = (my - bh - 8 < 0 ? my + 14 : my - bh - 6)
  ctx.fillStyle = 'rgba(12,11,10,0.94)'
  ctx.fillRect(tx, ty, bw, bh)
  ctx.strokeStyle = 'rgba(194,162,109,0.4)'
  ctx.lineWidth = 1
  ctx.strokeRect(tx + 0.5, ty + 0.5, bw - 1, bh - 1)
  ctx.fillStyle = '#e8e5df'
  ctx.font = '10px "JetBrains Mono", monospace'
  ctx.fillText(label, tx + pad, ty + 14)
  if (intent) {
    ctx.fillStyle = 'rgba(200,180,150,0.85)'
    ctx.font = 'italic 9px "JetBrains Mono", monospace'
    ctx.fillText(`“${intent}”`, tx + pad, ty + 26)
  }
}
