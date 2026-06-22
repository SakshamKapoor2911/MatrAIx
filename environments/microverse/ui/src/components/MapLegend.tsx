// Map legend — denotes what each asset on the world canvas represents. Each swatch
// is drawn from the SAME source the renderer uses (the Mana Seed body sheet for the
// agent, the locked palette for procedural markers) so the key matches the board
// exactly. Grouped: terrain, structures & resources, agents.

import { useEffect, useRef } from 'react'
import { BODIES, OUTFITS, HAIR, img, preloadAll, assetsReady } from '../render/assets'

// Locked palette tokens (mirror index.css / agents.ts).
const STANCE = {
  friendly: '#7fae8a',
  neutral: '#b6b1a7',
  aggressive: '#c47b73',
}

/** A 28×28 swatch showing the actual paper-doll agent sprite (stand frame, facing
 *  down), composited body + outfit + hair — i.e. exactly the figure on the map. */
function AgentSwatch({ outfit, ring }: { outfit: string; ring: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    preloadAll()
    const cvs = ref.current
    if (!cvs) return
    const ctx = cvs.getContext('2d')!
    let raf = 0
    let tries = 0
    function paint() {
      ctx.clearRect(0, 0, 28, 28)
      ctx.imageSmoothingEnabled = false
      const layers = [BODIES[0], outfit, HAIR]
      const ready = layers.every((s) => img(s) !== null)
      // Draw the figure only once ALL three paper-doll layers have loaded, so we
      // never show a half-composited body. stand / facing-down = row 0, col 0.
      if (ready) {
        // Source-crop to the character's actual pixels within the 64px stand frame
        // (≈ sx 18..46, sy 12..56) and scale that box to fill the swatch, so the
        // figure reads clearly instead of being a tiny dot in an empty cell.
        const sX = 18, sY = 12, sW = 28, sH = 44
        const dW = 22, dH = dW * (sH / sW), dX = (28 - dW) / 2, dY = 1
        for (const src of layers) {
          ctx.drawImage(img(src)!, sX, sY, sW, sH, dX, dY, dW, dH)
        }
      }
      // stance ring under the feet (matches the in-world 1px tint)
      ctx.strokeStyle = ring
      ctx.globalAlpha = 0.9
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.ellipse(14, 24, 8, 3.2, 0, 0, Math.PI * 2)
      ctx.stroke()
      ctx.globalAlpha = 1
      // Poll via rAF until the art arrives (assetsReady covers the error case), then stop.
      if (!ready && !assetsReady() && tries++ < 240) {
        raf = requestAnimationFrame(paint)
      }
    }
    paint()
    return () => cancelAnimationFrame(raf)
  }, [outfit, ring])
  return <canvas ref={ref} width={28} height={28} className="mv-legend-canvas" />
}

/** A small procedural swatch reused for the marker entries. */
function Swatch({ children }: { children: React.ReactNode }) {
  return <span className="mv-legend-swatch">{children}</span>
}

export function MapLegend() {
  return (
    <div className="mv-legend">
      <div className="mv-legend-group">
        <div className="mv-legend-group-title">Terrain</div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-terrain sw-desert" /></Swatch>
          <div className="mv-legend-text">
            <b>Desert</b><span>Open sand. Costs water to cross; where periphery goods are strewn.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-terrain sw-oasis" /><span className="mv-sw-palm">🌴</span></Swatch>
          <div className="mv-legend-text">
            <b>Oasis</b><span>Replenishes water — a contested minor source away from the centre.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-terrain sw-mountain" /></Swatch>
          <div className="mv-legend-text">
            <b>Mountain ridge</b><span>Slow to cross but cheap on water. Impassable to most movement.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-terrain sw-settlement" /></Swatch>
          <div className="mv-legend-text">
            <b>Settlement</b><span>The town around the Siphon — free to stand on, dense dwellings.</span>
          </div>
        </div>
      </div>

      <div className="mv-legend-group">
        <div className="mv-legend-group-title">Structures &amp; resources</div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-siphon" /></Swatch>
          <div className="mv-legend-text">
            <b>Atmospheric Siphon</b><span>The sole water source (cyan core, amber ring). Produces less than all need — the central chokepoint.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-goods" /></Swatch>
          <div className="mv-legend-text">
            <b>Goods cache</b><span>Amber crate-pile in the open desert: tradeable wealth — the lure to leave the well (greed vs. need).</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-ruins" /></Swatch>
          <div className="mv-legend-text">
            <b>Ruins &amp; death-cache</b><span>Collapsed districts; bleached remains mark a dead agent's scavengeable cache.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-heat" /></Swatch>
          <div className="mv-legend-text">
            <b>Heat zone</b><span>A rotating lethal ring that forces migration; a sandstorm haze garbles perception.</span>
          </div>
        </div>
      </div>

      <div className="mv-legend-group">
        <div className="mv-legend-group-title">Agents</div>

        <div className="mv-legend-item">
          <AgentSwatch outfit={OUTFITS.robe} ring={STANCE.friendly} />
          <div className="mv-legend-text">
            <b>Friendly</b><span>Paper-doll figure with a green stance ring; a bar beneath shows water reserve.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <AgentSwatch outfit={OUTFITS.pants} ring={STANCE.neutral} />
          <div className="mv-legend-text">
            <b>Neutral</b><span>Grey stance ring. Hover any figure for its name, goods, and current intention.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <AgentSwatch outfit={OUTFITS.pants} ring={STANCE.aggressive} />
          <div className="mv-legend-text">
            <b>Aggressive</b><span>Red stance ring — more likely to coerce or raid a richer neighbour.</span>
          </div>
        </div>

        <div className="mv-legend-item">
          <Swatch><span className="mv-sw-dead" /></Swatch>
          <div className="mv-legend-text">
            <b>Dead</b><span>Faded cairn glyph. Death is permanent; its resources drop as a cache.</span>
          </div>
        </div>
      </div>
    </div>
  )
}
