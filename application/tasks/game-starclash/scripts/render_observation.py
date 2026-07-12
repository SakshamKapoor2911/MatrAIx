"""HTML rendering for the Starclash task's browser-vision
brain.

`render_observation_html` turns a single persona's observation dict (see
`observations.build_observation`) into a self-contained, interactive HTML
page: a 2D room canvas, a hand-of-cards panel, chat/private-chat panels,
and context-dependent action controls. Every control is driven strictly by
`observation["action_menu"]["actions"]` (and the menu's accompanying
target/bounds lists) - nothing is rendered that isn't currently legal. On
activation, every control sets `window.__lastAction` to the exact same
action-dict shape the JSON brains (`brains.MockArenaBrain`/
`ClaudeArenaBrain`) already produce, plus `window.__actionReady = true` as a
simple ready flag, so a Playwright driver (`vision_brain.BrowserVisionBrain`)
can click through the page and read back a legal action.

`render_spectator_html` renders a full-game, read-only REPLAY page from a
complete `game_log.json`-shaped dict (see `run_arena.py`), for human
debugging/demo purposes - never shown to an agent.

No external assets/CDN/network calls anywhere in this module's output: both
functions must work loaded via `page.set_content` or a `data:`/`file://` URL
with zero network access.
"""

from __future__ import annotations

import base64
import functools
import math
import mimetypes
import os
from typing import Any, Dict, List, Optional
import json

# Optional baked-in art. If an image with this basename (any common
# extension) exists in `assets/` next to this script, it's inlined as a
# base64 data: URI at HTML-generation time and used in place of the
# procedural canvas/CSS rendering below - this keeps the zero-network/
# self-contained-HTML contract (no asset is ever fetched at *view* time)
# while still allowing generated art to replace the placeholder look.
# Nothing here is required: every call site falls back to the existing
# procedural drawing when the file is absent.
_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_ASSET_EXTS = (".png", ".jpg", ".jpeg", ".webp")


@functools.lru_cache(maxsize=None)
def _asset_data_uri(basename: str) -> Optional[str]:
    for ext in _ASSET_EXTS:
        path = os.path.join(_ASSET_DIR, basename + ext)
        if os.path.isfile(path):
            mime, _ = mimetypes.guess_type(path)
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime or 'image/png'};base64,{encoded}"
    return None


def _resolve_asset_uri(
    basename: str,
    *,
    inline_assets: bool = True,
    asset_rel_prefix: Optional[str] = None,
) -> Optional[str]:
    """Return a data: URI (inline, for agent/vision) or a relative path (for
    on-disk preview HTML opened via file:// next to a copied assets/ folder)."""
    if inline_assets:
        return _asset_data_uri(basename)
    if asset_rel_prefix:
        for ext in _ASSET_EXTS:
            if os.path.isfile(os.path.join(_ASSET_DIR, basename + ext)):
                return f"{asset_rel_prefix.rstrip('/')}/{basename}{ext}"
    return None


def _sync_preview_assets(target_dir: str) -> str:
    """Copy game art beside preview HTML; returns the rel prefix."""
    import shutil

    assets_out = os.path.join(target_dir, "assets")
    os.makedirs(assets_out, exist_ok=True)
    for basename in (
        "persona_sprite",
        "persona_battle",
        "nebula_backdrop",
        "room_floor",
        "battle_arena",
        "vs_badge",
        "rps_cards",
        "card_rock",
        "card_paper",
        "card_scissors",
    ):
        for ext in _ASSET_EXTS:
            src = os.path.join(_ASSET_DIR, basename + ext)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(assets_out, basename + ext))
                break
    return "assets"


def _esc(value: Any) -> str:
    """HTML-escape a value that will be interpolated into markup text (not
    JS). Numbers/None are stringified first."""
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _js(value: Any) -> str:
    """Safely embed a Python value into a <script> block as a JS literal."""
    return json.dumps(value)


def _js_attr(value: Any) -> str:
    """Safely embed a Python value as a JS literal inside an HTML
    attribute (e.g. onclick="fn({_js_attr(value)})"). `_js` alone is unsafe
    there because json.dumps uses double quotes, which would prematurely
    close a double-quoted HTML attribute; HTML-entity-escaping the JSON
    literal keeps the attribute well-formed while the browser decodes the
    entities back to the original characters before handing the string to
    the JS parser."""
    return _esc(json.dumps(value))


# Classic RPS hand-sign glyphs, shared across agent HUD, spectator replay,
# and the comms/event ticker - kept in one place so every surface reads
# the same card identity.
_CARD_GLYPHS = {"Rock": "\U0001f44a", "Paper": "\U0001f44b", "Scissors": "\u270c\ufe0f"}
_CARD_TYPES_ORDER = ("Rock", "Paper", "Scissors")


def _roster_card_header_html() -> str:
    return "".join(
        f'<th class="col-card-type" title="{_esc(card)}">{_CARD_GLYPHS[card]}</th>'
        for card in _CARD_TYPES_ORDER
    )


def _roster_card_cells_html(counts: Dict[str, int], *, pid: Optional[str] = None) -> str:
    cells = []
    for card in _CARD_TYPES_ORDER:
        id_attr = f' id="cards-{_esc(pid)}-{_esc(card)}"' if pid else ""
        cells.append(
            f'<td class="col-card-type"{id_attr}>'
            f'<span class="card-type-emoji">{_CARD_GLYPHS[card]}</span>'
            f'<span class="card-type-n">{_esc(int(counts.get(card, 0)))}</span>'
            f"</td>"
        )
    return "".join(cells)


def _arena_cards_strip_html(counts: Dict[str, int], *, dynamic: bool = False) -> str:
    """Public arena-wide Rock/Paper/Scissors totals (all players combined)."""
    stats = []
    for card in _CARD_TYPES_ORDER:
        id_attr = f' id="arena-count-{_esc(card)}"' if dynamic else ""
        stats.append(
            f'<div class="card-stat">'
            f'<div class="stat-emoji">{_CARD_GLYPHS[card]}</div>'
            f'<div class="stat-value"{id_attr}>{_esc(int(counts.get(card, 0)))}</div>'
            f"</div>"
        )
    return f"""
    <div class="hud" id="hud-arena-cards">
      <span class="hud-cards-title">Cards in play</span>
      {"".join(stats)}
    </div>
    """


_EVENT_GLYPHS = {
    "say": "\U0001f4ac",
    "wait": "\u23f3",
    "move": "\U0001f463",
    "challenge_issued": "\U0001f5e1\ufe0f",
    "challenge_accepted": "\U0001f91d",
    "challenge_declined": "\U0001f6ab",
    "challenge_auto_declined_no_cards": "\U0001f6ab",
    "battle_resolved": "",
    "private_message_sent": "\u2709\ufe0f",
    "system": "\U0001f6f0\ufe0f",
}
_PERSONA_COLORS = [
    "#ffb84d",
    "#a78bfa",
    "#2bb4c9",
    "#f4699a",
    "#b8e043",
    "#e8823a",
]


_AGENT_STYLE = """
  :root {
    color-scheme: dark;
    --void-deep: #050609;
    --void-mid: #0a0c14;
    --void-nebula: #140b22;
    --glass-bg: rgba(17, 20, 28, 0.72);
    --glass-border: rgba(77, 216, 232, 0.28);
    --amber: #ffa94d;
    --amber-bright: #ffc98a;
    --cyan: #4dd8e8;
    --violet: #a78bfa;
    --win: #5eff9d;
    --lose: #ff5468;
    --tie: #4dd8e8;
    --eliminated: #4a5170;
    --ink: #dfe6f5;
    --ink-dim: #8e97b8;
    --mono: "JetBrains Mono", "Fira Code", ui-monospace, monospace;
    --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
    /* Design resolution — entire UI scales to fit the real window. */
    --design-w: 1024;
    --design-h: 768;
    --ui-scale: 1;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    background: #020203;
    color: var(--ink);
    font-family: var(--sans);
    font-size: 14px;
    overflow: hidden;
  }
  /* Outer stage fills the browser; design frame is fixed-res and scaled. */
  .scale-stage {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background:
      radial-gradient(ellipse at 18% 8%, rgba(167, 139, 250, 0.10) 0%, transparent 45%),
      radial-gradient(ellipse at 84% 88%, rgba(77, 216, 232, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 50% 38%, var(--void-mid) 0%, var(--void-deep) 78%, #020203 100%);
  }
  .design-frame {
    position: relative;
    width: calc(var(--design-w) * 1px);
    height: calc(var(--design-h) * 1px);
    flex: 0 0 auto;
    transform: scale(var(--ui-scale));
    transform-origin: center center;
    overflow: hidden;
  }
  body::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background-image:
      radial-gradient(1px 1px at 12% 22%, rgba(223, 230, 245, 0.55) 0, transparent 60%),
      radial-gradient(1px 1px at 78% 14%, rgba(223, 230, 245, 0.4) 0, transparent 60%),
      radial-gradient(1.4px 1.4px at 34% 68%, rgba(223, 230, 245, 0.5) 0, transparent 60%),
      radial-gradient(1px 1px at 61% 82%, rgba(223, 230, 245, 0.35) 0, transparent 60%),
      radial-gradient(1.6px 1.6px at 91% 55%, rgba(223, 230, 245, 0.45) 0, transparent 60%),
      radial-gradient(1px 1px at 6% 78%, rgba(223, 230, 245, 0.3) 0, transparent 60%),
      radial-gradient(1px 1px at 47% 6%, rgba(223, 230, 245, 0.4) 0, transparent 60%),
      radial-gradient(1.3px 1.3px at 70% 40%, rgba(223, 230, 245, 0.4) 0, transparent 60%);
    background-repeat: no-repeat;
    opacity: 0.8;
  }
  body::after {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: repeating-linear-gradient(
      0deg,
      rgba(77, 216, 232, 0.018) 0px,
      rgba(77, 216, 232, 0.018) 1px,
      transparent 1px,
      transparent 3px
    );
    mix-blend-mode: overlay;
  }
  button { font-family: inherit; }
  .mono {
    font-family: var(--mono);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .glass {
    background:
      linear-gradient(160deg, rgba(77, 216, 232, 0.06), transparent 40%),
      var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 10px;
    backdrop-filter: blur(8px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(77, 216, 232, 0.05) inset;
  }

  /* -- Viewscreen fills the design frame (then whole UI auto-scales) --- */
  .viewscreen {
    position: absolute;
    inset: 0;
    z-index: 2;
    width: 100%;
    height: 100%;
    background: radial-gradient(ellipse at center, var(--void-mid) 0%, var(--void-deep) 72%, #020203 100%);
    overflow: hidden;
  }
  .viewscreen canvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    display: block;
  }
  .vignette {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0) 55%, rgba(0, 0, 0, 0.55) 100%);
    z-index: 2;
  }
  .porthole-frame {
    position: absolute;
    inset: 10px;
    pointer-events: none;
    border: 1px solid rgba(77, 216, 232, 0.22);
    border-radius: 14px;
    box-shadow: 0 0 40px rgba(77, 216, 232, 0.06) inset, 0 0 24px rgba(0, 0, 0, 0.6);
    z-index: 3;
  }
  .porthole-frame::before,
  .porthole-frame::after,
  .porthole-frame .bracket {
    position: absolute;
    width: 26px;
    height: 26px;
    border: 2px solid var(--amber);
    opacity: 0.75;
  }
  .porthole-frame::before {
    top: -1px; left: -1px;
    border-right: none; border-bottom: none;
    border-radius: 6px 0 0 0;
  }
  .porthole-frame::after {
    bottom: -1px; right: -1px;
    border-left: none; border-top: none;
    border-radius: 0 0 6px 0;
  }
  .porthole-frame .bracket.tr {
    top: -1px; right: -1px;
    border-left: none; border-bottom: none;
    border-radius: 0 6px 0 0;
  }
  .porthole-frame .bracket.bl {
    bottom: -1px; left: -1px;
    border-right: none; border-top: none;
    border-radius: 0 0 0 6px;
  }

  /* -- Generic HUD overlay chrome (shared with spectator) -------------- */
  .hud {
    position: absolute;
    z-index: 6;
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    backdrop-filter: blur(6px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    padding: 10px 12px;
  }
  .hud-title {
    font-family: var(--mono);
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--cyan);
    opacity: 0.85;
    margin: 0 0 6px 0;
  }

  /* -- Phase banner: top-docked, the single most prominent element --- */
  .phase-banner {
    position: absolute;
    top: 14px;
    left: 50%;
    transform: translateX(-50%);
    min-width: 380px;
    max-width: 700px;
    padding: 10px 24px;
    text-align: center;
    z-index: 20;
    overflow: hidden;
  }
  .phase-banner::before {
    content: "";
    position: absolute;
    top: 0;
    left: -60%;
    width: 40%;
    height: 100%;
    background: linear-gradient(100deg, transparent, rgba(255, 201, 138, 0.14), transparent);
    animation: banner-sheen 5s ease-in-out infinite;
  }
  @keyframes banner-sheen {
    0%, 30% { left: -60%; }
    70%, 100% { left: 140%; }
  }
  .phase-banner .phase-title {
    font-family: var(--mono);
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--amber-bright);
    text-shadow: 0 0 16px rgba(255, 169, 77, 0.35);
    white-space: normal;
    line-height: 1.25;
  }
  .phase-banner .phase-sub {
    margin-top: 4px;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink-dim);
    letter-spacing: 0.04em;
  }
  .phase-banner .phase-sub .hud-chip { color: var(--cyan); }

  /* -- Top-left: mission briefing header ----------------------------------- */
  #hud-briefing {
    top: 22px;
    left: 22px;
    max-width: 360px;
  }
  #hud-briefing .briefing-title {
    font-family: var(--mono);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--amber-bright);
    text-shadow: 0 0 14px rgba(255, 169, 77, 0.3);
    margin: 0;
  }
  #hud-briefing .briefing-meta {
    margin-top: 5px;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink-dim);
    letter-spacing: 0.02em;
  }

  /* -- Left edge: compact crew roster (map shows positions) ---------------- */
  #hud-roster {
    top: 88px;
    left: 16px;
    width: min(200px, 22vw);
    max-height: min(42vh, 320px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background:
      linear-gradient(165deg, rgba(77, 216, 232, 0.06), transparent 45%),
      rgba(8, 10, 18, 0.88);
    border-radius: 12px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(77, 216, 232, 0.12);
  }
  #hud-roster .roster-scroll {
    overflow-y: auto;
    flex: 1 1 auto;
  }
  .roster-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--sans);
    font-size: 11px;
  }
  .roster-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: rgba(10, 12, 20, 0.95);
    font-family: var(--mono);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ink-dim);
    padding: 6px 8px;
    text-align: left;
    border-bottom: 1px solid rgba(77, 216, 232, 0.18);
  }
  .roster-table td {
    padding: 6px 8px;
    border-bottom: 1px solid rgba(77, 216, 232, 0.06);
    color: var(--ink);
    white-space: nowrap;
  }
  .roster-table .col-stars {
    text-align: center;
    font-family: var(--mono);
    font-size: 10.5px;
    color: var(--amber-bright);
  }
  .roster-swatch {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
    margin-right: 6px;
    vertical-align: middle;
    box-shadow: 0 0 6px rgba(0,0,0,0.35);
  }
  .roster-table .col-card-type {
    text-align: center;
    font-family: var(--mono);
    font-size: 10px;
    padding: 4px 3px;
    min-width: 28px;
    color: var(--cyan);
  }
  .roster-table th.col-card-type {
    font-size: 14px;
    padding: 4px 3px;
    text-align: center;
  }
  .roster-table .card-type-emoji {
    display: block;
    font-size: 13px;
    line-height: 1;
  }
  .roster-table .card-type-n {
    display: block;
    font-size: 10px;
    margin-top: 2px;
    color: var(--cyan);
  }
  .roster-row.is-self .col-name { color: var(--amber-bright); font-weight: 600; }
  .roster-row.eliminated { opacity: 0.42; }
  .roster-row.eliminated td { text-decoration: line-through; color: var(--eliminated); }
  .roster-row.in-battle td { background: rgba(255, 169, 77, 0.12); }
  .roster-row.in-battle .col-name::after {
    content: "BATTLE";
    margin-left: 6px;
    font-family: var(--mono);
    font-size: 8px;
    letter-spacing: 0.06em;
    color: var(--amber-bright);
    padding: 1px 5px;
    border-radius: 4px;
    border: 1px solid rgba(255, 169, 77, 0.45);
    text-decoration: none;
    display: inline-block;
    vertical-align: middle;
  }

  /* -- Right edge: compact comms (mirrors roster) --------------------------- */
  #hud-comms {
    top: 88px;
    right: 16px;
    width: min(200px, 22vw);
    max-height: min(42vh, 320px);
    display: flex;
    flex-direction: column;
    background:
      linear-gradient(165deg, rgba(77, 216, 232, 0.08), transparent 45%),
      rgba(8, 10, 18, 0.9);
    border: 1px solid rgba(77, 216, 232, 0.28);
    border-radius: 12px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(77, 216, 232, 0.1);
  }
  #hud-comms .comms-scroll {
    list-style: none;
    margin: 0;
    padding: 6px;
    overflow-y: auto;
    flex: 1 1 auto;
  }
  #hud-comms .comms-scroll li {
    padding: 7px 10px;
    margin-bottom: 4px;
    border-radius: 8px;
    font-size: 11.5px;
    font-family: var(--sans);
    line-height: 1.4;
    background: rgba(17, 20, 28, 0.65);
    border: 1px solid rgba(77, 216, 232, 0.1);
  }
  #hud-comms .comms-scroll li.private {
    color: var(--cyan);
    border-color: rgba(77, 216, 232, 0.28);
    background: rgba(77, 216, 232, 0.06);
  }
  #hud-comms .comms-scroll li.comms-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 16px 10px;
    color: var(--ink-dim);
    background: transparent;
    border: 1px dashed rgba(77, 216, 232, 0.18);
    text-align: center;
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.04em;
  }
  #hud-comms .comms-scroll li.comms-empty .comms-empty-icon {
    font-size: 18px;
    opacity: 0.7;
  }
  #hud-comms .comms-scroll li .msg-glyph { margin-right: 5px; opacity: 0.9; }
  #hud-comms .comms-scroll li .msg-who {
    font-family: var(--mono);
    font-weight: 700;
    color: var(--amber-bright);
  }

  #hud-roster .roster-scroll::-webkit-scrollbar,
  #hud-comms .comms-scroll::-webkit-scrollbar { width: 6px; }
  #hud-roster .roster-scroll::-webkit-scrollbar-thumb,
  #hud-comms .comms-scroll::-webkit-scrollbar-thumb {
    background: rgba(77, 216, 232, 0.25);
    border-radius: 3px;
  }

  .bubble-layer { position: absolute; inset: 0; pointer-events: none; z-index: 10; }
  .stage-hint {
    position: absolute;
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
    padding: 5px 14px;
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--void-deep);
    background: var(--amber-bright);
    border-radius: 999px;
    box-shadow: 0 0 16px rgba(255, 169, 77, 0.5);
    display: none;
    z-index: 15;
    white-space: nowrap;
  }
  .stage-hint.challenge-hint { background: var(--win); box-shadow: 0 0 16px rgba(94, 255, 157, 0.5); }
  .stage-hint.showing { display: block; }
  .speech-bubble {
    position: absolute;
    transform: translate(-50%, -100%);
    max-width: 200px;
    padding: 5px 9px;
    border-radius: 9px;
    font-size: 11.5px;
    line-height: 1.3;
    color: var(--ink);
    background: rgba(10, 12, 20, 0.94);
    border: 1px solid var(--amber);
    box-shadow: 0 0 14px rgba(255, 169, 77, 0.35);
    white-space: normal;
  }
  .speech-bubble.private { border-color: var(--cyan); box-shadow: 0 0 14px rgba(77, 216, 232, 0.35); }
  .speech-bubble .bubble-who { font-family: var(--mono); font-size: 9.5px; color: var(--ink-dim); margin-bottom: 1px; }
  .speech-bubble.private .bubble-who { color: var(--cyan); }

  /* -- Top-right: arena card pool (aligned with briefing) ---------------- */
  #hud-arena-cards {
    top: 22px;
    right: 16px;
    width: min(200px, 22vw);
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: center;
    padding: 10px 12px;
    box-sizing: border-box;
    background:
      linear-gradient(155deg, rgba(255, 169, 77, 0.12), transparent 50%),
      rgba(12, 14, 22, 0.9);
    border: 1px solid rgba(255, 169, 77, 0.28);
    border-radius: 12px;
    box-shadow: 0 10px 26px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 201, 138, 0.12);
  }
  #hud-arena-cards .card-stat {
    text-align: center;
    min-width: 48px;
    padding: 4px 6px;
    border-radius: 10px;
    background: rgba(0, 0, 0, 0.22);
    border: 1px solid rgba(77, 216, 232, 0.12);
  }
  #hud-arena-cards .card-stat .stat-emoji { font-size: 22px; line-height: 1; }
  #hud-arena-cards .hud-cards-title {
    font-family: var(--mono);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--amber-bright);
    margin-right: 2px;
    align-self: center;
  }
  #hud-arena-cards .card-stat .stat-value {
    font-family: var(--mono);
    font-size: 18px;
    font-weight: 700;
    color: var(--cyan);
    margin-top: 2px;
  }
  /* Market / dense status is intentionally not shown on the agent HUD —
     it lives in the observation JSON / system prompt so CUA agents get a
     cleaner clickable surface. */
  .hud-status { display: none !important; }

  /* -- Hotbar: large, computer-use friendly action buttons ------------- */
  .hotbar {
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 10px;
    padding: 10px 14px;
    z-index: 20;
    border-radius: 16px;
    background:
      linear-gradient(180deg, rgba(30, 36, 52, 0.92), rgba(8, 10, 18, 0.94));
    border: 1px solid rgba(77, 216, 232, 0.35);
    box-shadow:
      0 14px 40px rgba(0, 0, 0, 0.65),
      0 0 0 1px rgba(255, 169, 77, 0.08) inset,
      0 1px 0 rgba(255, 255, 255, 0.06) inset;
  }
  .hotbar-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    min-width: 86px;
    min-height: 64px;
    padding: 10px 8px;
    background: linear-gradient(165deg, rgba(77, 216, 232, 0.16), rgba(77, 216, 232, 0.05));
    color: var(--ink);
    border: 1.5px solid rgba(77, 216, 232, 0.45);
    border-radius: 12px;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    user-select: none;
    transition: transform 0.12s ease, border-color 0.12s ease, background 0.12s ease;
  }
  .hotbar-btn .hb-label {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.12em;
    line-height: 1.1;
    color: var(--cyan);
  }
  .hotbar-btn .hb-hint {
    font-size: 9.5px;
    color: var(--ink-dim);
    letter-spacing: 0.03em;
    text-transform: none;
  }
  .hotbar-btn:hover {
    background: linear-gradient(165deg, rgba(77, 216, 232, 0.28), rgba(77, 216, 232, 0.1));
    border-color: var(--cyan);
    transform: translateY(-2px);
  }
  .hotbar-btn:active { transform: translateY(0); }
  .hotbar-btn.disabled,
  .hotbar-btn.disabled:hover {
    opacity: 0.42;
    cursor: not-allowed;
    transform: none;
    border-color: rgba(90, 98, 128, 0.35);
    background: rgba(16, 18, 28, 0.7);
    box-shadow: none;
    pointer-events: none;
  }
  .hotbar-btn.disabled .hb-label { color: var(--ink-dim); }
  .hotbar-btn.armed {
    background: linear-gradient(165deg, rgba(255, 169, 77, 0.32), rgba(255, 169, 77, 0.12));
    border-color: var(--amber);
    color: var(--amber-bright);
    box-shadow: 0 0 16px rgba(255, 169, 77, 0.45);
    animation: hotbar-pulse 1.4s ease-in-out infinite;
  }
  .hotbar-btn.armed .hb-label { color: var(--amber-bright); }
  @keyframes hotbar-pulse {
    0%, 100% { box-shadow: 0 0 10px rgba(255, 169, 77, 0.32); }
    50% { box-shadow: 0 0 22px rgba(255, 169, 77, 0.55); }
  }

  /* -- Composers: small popovers anchored above the hotbar ------------- */
  .composer {
    position: absolute;
    bottom: 92px;
    left: 50%;
    transform: translateX(-50%);
    width: 320px;
    padding: 10px 12px;
    z-index: 25;
    display: none;
  }
  .composer.open { display: block; }
  .composer .composer-title {
    font-family: var(--mono);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--cyan);
    margin-bottom: 6px;
  }
  .composer .chip-row { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 6px; }
  .composer .target-chip {
    font-family: var(--mono);
    font-size: 10.5px;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid rgba(77, 216, 232, 0.35);
    background: rgba(77, 216, 232, 0.08);
    color: var(--ink);
    cursor: pointer;
  }
  .composer .target-chip.selected {
    background: rgba(255, 169, 77, 0.22);
    border-color: var(--amber);
    color: var(--amber-bright);
  }
  .composer .composer-row { display: flex; gap: 6px; }
  .composer input[type="text"] {
    flex: 1 1 auto;
    font-family: var(--sans);
    font-size: 12.5px;
    background: rgba(5, 6, 9, 0.7);
    color: var(--ink);
    border: 1px solid rgba(77, 216, 232, 0.3);
    border-radius: 6px;
    padding: 6px 8px;
  }
  .composer button.send-btn {
    font-family: var(--mono);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: rgba(255, 169, 77, 0.18);
    color: var(--amber-bright);
    border: 1px solid rgba(255, 169, 77, 0.45);
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
  }
  .composer button.send-btn:hover { background: rgba(255, 169, 77, 0.3); }

  /* -- Hand dock: fanned battle-card hand (sub-step 1) ------------------ */
  .hand-dock {
    position: absolute;
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 20;
  }
  .opponent-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 999px;
    margin-bottom: 10px;
  }
  .opponent-chip .opp-silhouette {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #3a4160, #12141a 70%);
    border: 1px solid rgba(223, 230, 245, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--mono);
    font-size: 13px;
    color: var(--ink-dim);
    animation: opp-guess-pulse 1.8s ease-in-out infinite;
  }
  @keyframes opp-guess-pulse {
    0%, 100% { box-shadow: 0 0 0 rgba(223, 230, 245, 0); }
    50% { box-shadow: 0 0 10px rgba(223, 230, 245, 0.25); }
  }
  .opponent-chip .opp-name {
    font-family: var(--mono);
    font-size: 12px;
    letter-spacing: 0.04em;
    color: var(--ink-dim);
  }
  .hand-fan { display: flex; align-items: flex-end; justify-content: center; }
  .card-tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 108px;
    height: 152px;
    margin: 0 -14px;
    border-radius: 12px;
    text-align: center;
    font-weight: 700;
    font-size: 15px;
    font-family: var(--mono);
    letter-spacing: 0.04em;
    cursor: pointer;
    border: 2px solid rgba(223, 230, 245, 0.25);
    user-select: none;
    box-shadow: 0 10px 22px rgba(0, 0, 0, 0.5);
    transition: transform 0.12s ease, border-color 0.12s ease;
    position: relative;
  }
  .card-tile {
    transform: rotate(var(--fan-rot, 0deg)) translateY(var(--fan-lift, 0px));
  }
  .card-tile:hover {
    border-color: var(--amber-bright);
    transform: rotate(var(--fan-rot, 0deg)) translateY(calc(var(--fan-lift, 0px) - 16px)) scale(1.04);
  }
  .card-tile.disabled { opacity: 0.35; cursor: not-allowed; filter: grayscale(0.6); }
  .card-tile.disabled:hover {
    transform: rotate(var(--fan-rot, 0deg)) translateY(var(--fan-lift, 0px));
  }
  .card-tile .card-emoji {
    font-size: 40px;
    line-height: 1;
    margin-bottom: 6px;
    filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.45));
  }
  .card-tile .card-art {
    width: 72%;
    height: 58%;
    margin-bottom: 6px;
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.45));
  }
  .card-tile .card-qty {
    position: absolute;
    top: 6px;
    right: 8px;
    z-index: 2;
    min-width: 22px;
    height: 22px;
    padding: 0 6px;
    border-radius: 999px;
    background: linear-gradient(180deg, rgba(255, 201, 138, 0.95), rgba(255, 169, 77, 0.92));
    color: #1a1208;
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.02em;
    line-height: 22px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(255, 201, 138, 0.35);
  }
  .card-tile .card-name {
    font-size: 10px;
    letter-spacing: 0.14em;
    opacity: 0.85;
  }
  .card-tile .card-corner {
    position: absolute;
    font-size: 10px;
    opacity: 0.55;
  }
  .card-tile .card-corner.tl { top: 8px; left: 9px; }
  .card-tile .card-corner.br { bottom: 8px; right: 9px; transform: rotate(180deg); }
  .card-tile::after {
    content: "";
    position: absolute;
    inset: 5px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    pointer-events: none;
  }
  .card-Rock {
    background: linear-gradient(160deg, #5b5f80 0%, #3d4059 55%, #2c2e42 100%);
    color: #f2f0ff;
  }
  .card-Paper {
    background: linear-gradient(160deg, #2f7ba3 0%, #205e82 55%, #163f59 100%);
    color: #f0f8ff;
  }
  .card-Scissors {
    background: linear-gradient(160deg, #a13636 0%, #7c2323 55%, #551414 100%);
    color: #fff0ef;
  }
  .hand-note {
    margin-top: 10px;
    width: 340px;
  }

  /* -- Duel stage: clean face-off using original top-down sprites -------- */
  .battle-stage {
    position: absolute;
    inset: 0;
    z-index: 18;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    pointer-events: auto;
    background:
      radial-gradient(ellipse at 50% 35%, rgba(40, 28, 70, 0.55), transparent 55%),
      radial-gradient(ellipse at 50% 100%, rgba(5, 6, 9, 0.95), transparent 50%),
      linear-gradient(180deg, #0b0e18 0%, #05060c 100%);
  }
  .battle-stage .battle-bg {
    position: absolute;
    inset: 0;
    opacity: 0.35;
    background-size: cover;
    background-position: center;
    filter: blur(2px) saturate(0.85) brightness(0.55);
  }
  .battle-stage .battle-bg::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(5,6,9,0.2) 0%, rgba(5,6,9,0.75) 100%);
  }
  .battle-arena {
    position: relative;
    z-index: 2;
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 0;
    padding: 88px 28px 12px;
  }
  .battle-fighters {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    gap: clamp(28px, 8vw, 80px);
    width: min(920px, 100%);
  }
  .battle-pilot {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    min-width: 160px;
    position: relative;
  }
  .battle-pilot::before {
    content: "";
    position: absolute;
    bottom: 72px;
    left: 50%;
    transform: translateX(-50%);
    width: 88px;
    height: 18px;
    border-radius: 50%;
    background: radial-gradient(ellipse, rgba(77, 216, 232, 0.28), transparent 70%);
    filter: blur(1px);
    z-index: 0;
    pointer-events: none;
  }
  .battle-pilot.foe::before {
    background: radial-gradient(ellipse, rgba(255, 84, 104, 0.28), transparent 70%);
  }
  .battle-pilot.self::before {
    background: radial-gradient(ellipse, rgba(255, 169, 77, 0.32), transparent 70%);
  }
  .battle-pilot.foe .battle-sprite { filter: drop-shadow(0 0 18px rgba(255, 84, 104, 0.35)); }
  .battle-pilot.self .battle-sprite { filter: drop-shadow(0 0 18px rgba(255, 169, 77, 0.4)); }
  .battle-sprite {
    position: relative;
    z-index: 1;
    width: clamp(96px, 16vw, 140px);
    height: clamp(96px, 16vw, 140px);
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    background-color: transparent !important;
    border: none !important;
    image-rendering: pixelated;
    animation: battle-float 2.4s ease-in-out infinite;
  }
  .battle-sprite.foe { animation-delay: 0.3s; }
  @keyframes battle-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
  }
  .battle-plate {
    min-width: 168px;
    max-width: 220px;
    padding: 10px 14px;
    border-radius: 12px;
    background: rgba(8, 10, 18, 0.9);
    border: 1.5px solid rgba(77, 216, 232, 0.35);
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.45);
    text-align: center;
  }
  .battle-plate.foe { border-color: rgba(255, 84, 104, 0.5); }
  .battle-plate.self { border-color: rgba(255, 169, 77, 0.55); }
  .battle-plate .bp-role {
    font-family: var(--mono);
    font-size: 9px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-dim);
    margin-bottom: 4px;
  }
  .battle-plate .bp-name {
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--amber-bright);
  }
  .battle-plate.foe .bp-name { color: #ff9aab; }
  .battle-plate .bp-stars {
    margin-top: 6px;
    font-size: 15px;
    letter-spacing: 2px;
    color: var(--amber-bright);
  }
  .battle-vs-chip {
    align-self: center;
    font-family: var(--mono);
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.18em;
    color: var(--amber-bright);
    padding: 10px 14px;
    border-radius: 999px;
    border: 1.5px solid rgba(255, 169, 77, 0.55);
    background: rgba(8, 10, 18, 0.85);
    box-shadow: 0 0 20px rgba(255, 169, 77, 0.25);
    margin-bottom: 18px;
  }
  .battle-hand-dock {
    position: relative;
    z-index: 4;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 14px 16px 26px;
    background: linear-gradient(180deg, transparent, rgba(5, 6, 9, 0.88) 28%);
  }
  .battle-hand-dock .battle-prompt {
    font-family: var(--mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--cyan);
    text-shadow: 0 0 12px rgba(77, 216, 232, 0.45);
  }
  .battle-hand-dock .hand-fan {
    gap: 12px;
    justify-content: center;
  }
  .battle-hand-dock .card-tile {
    margin: 0;
    width: 112px;
    height: 152px;
    transform: none !important;
    border-radius: 14px;
  }
  .battle-hand-dock .card-tile:hover {
    transform: translateY(-12px) scale(1.06) !important;
    border-color: var(--amber-bright);
    box-shadow: 0 0 22px rgba(255, 169, 77, 0.45), 0 14px 28px rgba(0, 0, 0, 0.55);
  }
  .battle-hand-dock .card-tile .card-emoji { font-size: 44px; }
  .battle-hand-dock .card-tile .card-art {
    width: 78%;
    height: 62%;
  }
  .viewscreen.battle-mode #room-canvas,
  .viewscreen.battle-mode .vignette,
  .viewscreen.battle-mode .porthole-frame,
  .viewscreen.battle-mode .stage-hint,
  .viewscreen.battle-mode #bubble-layer,
  .viewscreen.battle-mode #hud-briefing,
  .viewscreen.battle-mode #hud-comms,
  .viewscreen.battle-mode #hud-arena-cards,
  .viewscreen.battle-mode #hud-roster {
    display: none !important;
  }
  .viewscreen.battle-mode .phase-banner {
    z-index: 22;
    background: rgba(8, 10, 18, 0.82);
  }
  .viewscreen.battle-mode .battle-stage {
    z-index: 19;
  }

  /* -- Challenge-response modal (sub-step 2) --------------------------- */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: radial-gradient(ellipse at 50% 45%, rgba(255, 169, 77, 0.08), rgba(2, 3, 6, 0.86) 65%);
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 50;
    animation: modal-fade-in 0.2s ease;
  }
  @keyframes modal-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  .modal-panel {
    width: 420px;
    padding: 24px 26px;
    text-align: center;
    animation: modal-pop-in 0.22s cubic-bezier(0.2, 0.9, 0.3, 1.2);
    box-shadow: 0 0 40px rgba(255, 169, 77, 0.12), 0 8px 24px rgba(0, 0, 0, 0.45);
  }
  @keyframes modal-pop-in {
    from { opacity: 0; transform: scale(0.92) translateY(8px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }
  .modal-panel .modal-eyebrow {
    font-family: var(--mono);
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--cyan);
    margin-bottom: 10px;
  }
  .modal-panel .modal-challenger {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-bottom: 18px;
  }
  .modal-panel .modal-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background-color: rgba(8, 10, 18, 0.9);
    background-size: 85%;
    background-repeat: no-repeat;
    background-position: center;
    border: 2px solid var(--amber-bright);
    box-shadow: 0 0 18px rgba(255, 169, 77, 0.5);
    animation: modal-avatar-glow 1.6s ease-in-out infinite;
    image-rendering: pixelated;
    flex: 0 0 auto;
  }
  @keyframes modal-avatar-glow {
    0%, 100% { box-shadow: 0 0 14px rgba(255, 169, 77, 0.4); }
    50% { box-shadow: 0 0 26px rgba(255, 169, 77, 0.7); }
  }
  .modal-panel .modal-name {
    font-family: var(--mono);
    font-size: 18px;
    font-weight: 700;
    color: var(--amber-bright);
  }
  .modal-buttons { display: flex; gap: 14px; justify-content: center; }
  .modal-buttons button {
    flex: 1 1 auto;
    font-family: var(--mono);
    font-size: 15px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 14px 10px;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.12s ease, transform 0.12s ease;
  }
  .modal-buttons .accept-btn {
    background: rgba(94, 255, 157, 0.16);
    border: 2px solid var(--win);
    color: var(--win);
  }
  .modal-buttons .accept-btn:hover { background: rgba(94, 255, 157, 0.3); transform: translateY(-1px); }
  .modal-buttons .decline-btn {
    background: rgba(255, 84, 104, 0.14);
    border: 2px solid var(--lose);
    color: var(--lose);
  }
  .modal-buttons .decline-btn:hover { background: rgba(255, 84, 104, 0.28); transform: translateY(-1px); }
  .modal-note { margin-top: 16px; }
  .modal-note .composer-title { text-align: left; font-size: 10px; color: var(--ink-dim); }
  .modal-note input {
    width: 100%;
    margin-top: 8px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid rgba(77, 216, 232, 0.28);
    background: rgba(5, 6, 9, 0.7);
    color: var(--ink);
    font-family: var(--sans);
    font-size: 13px;
  }
  .modal-note input:focus { outline: none; border-color: var(--cyan); }
"""


def _phase_label(observation: Dict[str, Any]) -> str:
    menu = observation.get("action_menu", {}) or {}
    actions: List[str] = list(menu.get("actions", []))
    if "play_card" in actions:
        opponent = observation.get("battle_opponent") or {}
        name = opponent.get("display_name") or opponent.get("id") or "Opponent"
        return f"Duel vs {name}"
    if "accept" in actions and "decline" in actions:
        challenger = observation.get("pending_challenge_from") or {}
        name = challenger.get("display_name") or challenger.get("id") or "someone"
        return f"Challenge from {name}"
    return "Choose your action"


# ---------------------------------------------------------------------------
# render_observation_html - the "Persona Cockpit" agent-facing HUD
# ---------------------------------------------------------------------------
#
# Structural layout (full-bleed `.viewscreen` root, aligned with the
# spectator replay HUD - instrument overlays on a porthole canvas):
#   - canvas + porthole chrome   full-viewport room viewscreen
#   - .phase-banner              top-center action prompt
#   - #hud-briefing              top-left room/helm readout
#   - .hud-status                top-right tick/market readout
#   - #hud-roster                left-edge pilot roster with star counts
#   - #hud-comms                 right-edge chat-room comms feed
#   - .hand-dock                 fanned battle-card hand, bottom (sub-step 1)
#   - .hotbar                    bottom action bar (sub-step 3)
#   - .composer                  say/private_message popover
#   - .modal-backdrop            accept/decline overlay (sub-step 2)
#
# Every control funnels through the same setAction()/mergePrivateNote() JS
# helpers as before, so window.__lastAction / window.__actionReady keep the
# exact contract vision_brain.py and brains.py already rely on.


def _hud_status_html(observation: Dict[str, Any]) -> str:
    """Market / dense status stays in observation JSON + system prompt only."""
    return ""


def _agent_briefing_html(observation: Dict[str, Any]) -> str:
    self_state = observation.get("self", {}) or {}
    room_name = observation.get("current_room", {}).get("name", "Main Chat Room")
    self_name = self_state.get("display_name", self_state.get("id", "You"))
    stars = int(self_state.get("stars", 0) or 0)
    hand_n = len(self_state.get("hand") or [])
    return f"""
    <div class="hud" id="hud-briefing">
      <div class="briefing-title">{_esc(room_name)}</div>
      <div class="briefing-meta">{_esc(self_name)} · \u2b50{stars} · {hand_n} cards</div>
    </div>
    """


def _star_pips_html(stars: int, max_pips: int, color: str) -> str:
    pips = []
    for idx in range(max_pips):
        filled = idx < stars
        bg = color if filled else "#232a44"
        opacity = "1" if filled else "0.45"
        pips.append(
            f'<span class="chip-pip" style="background:{_esc(bg)}; opacity:{opacity};"></span>'
        )
    return "".join(pips)


def _agent_roster_html(observation: Dict[str, Any]) -> str:
    """Compact crew scoreboard. Full positions are drawn on the room map."""
    roster: List[Dict[str, Any]] = observation.get("arena_roster", []) or []
    battle_opp = observation.get("battle_opponent") or {}
    battle_opp_id = battle_opp.get("id")
    rows = []
    for idx, row in enumerate(roster):
        pid = row.get("id")
        classes = ["roster-row"]
        if row.get("is_self"):
            classes.append("is-self")
        if row.get("eliminated"):
            classes.append("eliminated")
        if battle_opp_id and (pid == battle_opp_id or row.get("is_self")):
            classes.append("in-battle")
        name = row.get("short_name") or row.get("display_name") or pid
        if row.get("is_self"):
            name = f"{name}*"
        near_mark = " · near" if row.get("nearby") else ""
        color = (
            "#ffa94d"
            if row.get("is_self")
            else _PERSONA_COLORS[idx % len(_PERSONA_COLORS)]
        )
        swatch = (
            f'<span class="roster-swatch" style="background:{_esc(color)};"></span>'
        )
        rows.append(
            f'<tr class="{" ".join(classes)}" data-id="{_esc(pid)}">'
            f'<td class="col-name" title="{_esc(row.get("display_name", ""))}">'
            f"{swatch}{_esc(name)}{_esc(near_mark)}</td>"
            f'<td class="col-stars">\u2b50{_esc(row.get("stars", 0))}</td>'
            f"</tr>"
        )

    body = "".join(rows) or '<tr><td colspan="2" style="color:var(--ink-dim);">(no crew)</td></tr>'
    return f"""
    <div class="hud" id="hud-roster">
      <div class="hud-title">Crew</div>
      <div class="roster-scroll">
        <table class="roster-table">
          <thead><tr><th>Name</th><th>\u2b50</th></tr></thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    </div>
    """


def _phase_banner_html(observation: Dict[str, Any], phase: str) -> str:
    self_state = observation.get("self", {}) or {}
    self_name = self_state.get("display_name", self_state.get("id", "You"))
    return f"""
    <div class="phase-banner glass" id="phase-banner">
      <div class="phase-title">{_esc(phase.upper())}</div>
      <div class="phase-sub"><span class="hud-chip">{_esc(self_name)}</span> at the helm</div>
    </div>
    """


def _viewscreen_chrome_html(canvas_id: str = "room-canvas") -> str:
    return f"""
    <canvas id="{canvas_id}"></canvas>
    <div class="vignette"></div>
    <div class="porthole-frame"><span class="bracket tr"></span><span class="bracket bl"></span></div>
    <div class="stage-hint mono" id="move-hint">WASD OR CLICK TO WALK</div>
    <div class="stage-hint challenge-hint mono" id="challenge-hint">CLICK A GLOWING TARGET TO CHALLENGE</div>
    <div class="bubble-layer" id="bubble-layer"></div>
    """


def _agent_hand_strip_html(observation: Dict[str, Any]) -> str:
    """Show the ego pilot's remaining Rock/Paper/Scissors hand counts."""
    self_state = observation.get("self", {}) or {}
    hand: List[str] = list(self_state.get("hand", []))
    counts = {"Rock": 0, "Paper": 0, "Scissors": 0}
    for card in hand:
        if card in counts:
            counts[card] += 1
    return f"""
    <div class="hud" id="hud-cards">
      <span class="hud-cards-title">Hand</span>
      <div class="card-stat">
        <div class="stat-emoji">{_CARD_GLYPHS["Rock"]}</div>
        <div class="stat-value">{counts["Rock"]}</div>
        <div class="stat-label">Rock</div>
      </div>
      <div class="card-stat">
        <div class="stat-emoji">{_CARD_GLYPHS["Paper"]}</div>
        <div class="stat-value">{counts["Paper"]}</div>
        <div class="stat-label">Paper</div>
      </div>
      <div class="card-stat">
        <div class="stat-emoji">{_CARD_GLYPHS["Scissors"]}</div>
        <div class="stat-value">{counts["Scissors"]}</div>
        <div class="stat-label">Scissors</div>
      </div>
    </div>
    """


def _roster_name_lookup(observation: Dict[str, Any]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    self_state = observation.get("self", {}) or {}
    if self_state.get("id"):
        lookup[str(self_state["id"])] = self_state.get("display_name", self_state["id"])
    for row in observation.get("arena_roster", []) or []:
        pid = row.get("id")
        if pid:
            lookup[str(pid)] = row.get("short_name") or row.get("display_name") or str(pid)
    return lookup


def _agent_comms_html(observation: Dict[str, Any]) -> str:
    """Compact nearby-comms strip (last few lines only for CUA clarity)."""
    recent_chat: List[Dict[str, Any]] = observation.get("recent_chat", []) or []
    private_chat: List[Dict[str, Any]] = observation.get("private_chat_with_me", []) or []
    say_glyph = _EVENT_GLYPHS.get("say", "")
    pm_glyph = _EVENT_GLYPHS.get("private_message_sent", "")
    names = _roster_name_lookup(observation)

    items = []
    for msg in recent_chat[-6:]:
        pid = str(msg.get("persona_id", "?"))
        who = names.get(pid, pid)
        text = _clean_speech(msg.get("text", ""))
        if not text:
            continue
        if len(text) > 60:
            text = text[:57] + "…"
        items.append(
            f'<li><span class="msg-glyph">{say_glyph}</span>'
            f'<span class="msg-who">{_esc(who)}</span>: {_esc(text)}</li>'
        )
        if len(items) >= 3:
            break
    pm_items = []
    for msg in private_chat[-4:]:
        sender = names.get(str(msg.get("sender_id", "?")), msg.get("sender_id", "?"))
        text = _clean_speech(msg.get("text", ""))
        if not text:
            continue
        if len(text) > 50:
            text = text[:47] + "…"
        pm_items.append(
            f'<li class="private"><span class="msg-glyph">{pm_glyph}</span>'
            f"{_esc(sender)}: {_esc(text)}</li>"
        )
        if len(pm_items) >= 2:
            break
    items.extend(pm_items)

    feed = "".join(items) or (
        '<li class="comms-empty">'
        '<span class="comms-empty-icon">\U0001f4e1</span>'
        '<span>No recent chatter</span>'
        "</li>"
    )

    return f"""
    <div class="hud" id="hud-comms">
      <div class="hud-title">Comms</div>
      <ul class="comms-scroll">{feed}</ul>
    </div>
    """


def _hand_dock_html(
    observation: Dict[str, Any],
    *,
    sprite_uri: Optional[str] = None,
    battle_sprite_uri: Optional[str] = None,
    battle_arena_uri: Optional[str] = None,
    vs_badge_uri: Optional[str] = None,
) -> str:
    """Clean duel face-off for sub-step 1 (play_card).

    Uses the original top-down persona sprite (not the side-view battle art),
    two nameplates, a compact VS chip, and large clickable RPS cards.
    Opponent's card is never shown.
    """
    menu = observation.get("action_menu", {}) or {}
    actions: List[str] = list(menu.get("actions", []))
    self_state = observation.get("self", {}) or {}
    hand: List[str] = list(self_state.get("hand", []))
    can_play = "play_card" in actions
    available = set(menu.get("available_cards") or hand) if can_play else set()
    opponent = observation.get("battle_opponent") or {}
    opponent_name = opponent.get("display_name") or opponent.get("id") or "Opponent"
    opponent_id = opponent.get("id")
    self_name = self_state.get("display_name") or self_state.get("id") or "You"
    self_stars = int(self_state.get("stars", 0) or 0)

    opp_stars = self_stars
    for row in observation.get("arena_roster") or []:
        if row.get("id") == opponent_id:
            opp_stars = int(row.get("stars", 0) or 0)
            break

    # Prefer painted card art when present (indie game feel); emoji fallback.
    card_art = {
        "Rock": _asset_data_uri("card_rock"),
        "Paper": _asset_data_uri("card_paper"),
        "Scissors": _asset_data_uri("card_scissors"),
    }

    # Stack duplicate card types into one tile with a qty badge (cleaner
    # duel hand; play_card still submits by type, so stacking is safe).
    stacked: List[str] = []
    counts: Dict[str, int] = {}
    for card in hand:
        if card not in counts:
            stacked.append(card)
            counts[card] = 0
        counts[card] += 1

    tiles = []
    for card in stacked:
        playable = can_play and card in available
        classes = f"card-tile card-{_esc(card)}" + ("" if playable else " disabled")
        onclick_attr = f' onclick="submitPlayCard({_js_attr(card)})"' if playable else ""
        glyph = _CARD_GLYPHS.get(card, "")
        art = card_art.get(card)
        qty = counts.get(card, 1)
        qty_html = (
            f'<span class="card-qty" aria-label="{qty} in hand">×{qty}</span>'
            if qty > 1
            else ""
        )
        if art:
            face = (
                f'<div class="card-art" style="background-image:url(&quot;{_esc(art)}&quot;);"></div>'
            )
        else:
            face = f'<span class="card-emoji">{glyph}</span>'
        tiles.append(
            f'<div class="{classes}"{onclick_attr} data-card="{_esc(card)}">'
            f"{qty_html}"
            f"{face}"
            f'<span class="card-name">{_esc(card.upper())}</span>'
            f"</div>"
        )
    tiles_html = "".join(tiles) if tiles else (
        '<div class="mono" style="color:var(--ink-dim); padding:20px;">NO CARDS</div>'
    )

    # Prefer original room sprite for both pilots (user-facing consistency).
    sprite = sprite_uri or _asset_data_uri("persona_sprite") or battle_sprite_uri
    battle_arena_uri = battle_arena_uri or _asset_data_uri("nebula_backdrop")
    bg_style = (
        f' style="background-image:url(&quot;{_esc(battle_arena_uri)}&quot;);"'
        if battle_arena_uri
        else ""
    )
    sprite_style = (
        f' style="background-image:url(&quot;{_esc(sprite)}&quot;);"'
        if sprite
        else ""
    )

    self_star_pips = "\u2b50" * max(0, self_stars) + ("\u2606" * max(0, 3 - self_stars))
    opp_star_pips = "\u2b50" * max(0, opp_stars) + ("\u2606" * max(0, 3 - opp_stars))

    return f"""
    <div class="battle-stage" id="battle-stage">
      <div class="battle-bg"{bg_style}></div>
      <div class="battle-arena">
        <div class="battle-vs-chip">VS</div>
        <div class="battle-fighters">
          <div class="battle-pilot self">
            <div class="battle-sprite self"{sprite_style}></div>
            <div class="battle-plate self">
              <div class="bp-role">You</div>
              <div class="bp-name">{_esc(self_name)}</div>
              <div class="bp-stars">{self_star_pips}</div>
            </div>
          </div>
          <div class="battle-pilot foe">
            <div class="battle-sprite foe"{sprite_style}></div>
            <div class="battle-plate foe">
              <div class="bp-role">Opponent</div>
              <div class="bp-name">{_esc(opponent_name)}</div>
              <div class="bp-stars">{opp_star_pips}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="battle-hand-dock" id="hand-dock">
        <div class="battle-prompt">Pick your card</div>
        <div class="hand-fan">{tiles_html}</div>
      </div>
    </div>
    """


def _challenge_modal_html(observation: Dict[str, Any], sprite_uri: Optional[str] = None) -> str:
    """Focused accept/decline overlay for sub-step 2 - deliberately heavier
    visual weight than a routine hotbar icon, per the "binary high-stakes
    decision" design direction."""
    menu = observation.get("action_menu", {}) or {}
    actions: List[str] = list(menu.get("actions", []))
    if not ("accept" in actions and "decline" in actions):
        return ""
    challenger = observation.get("pending_challenge_from") or {}
    name = challenger.get("display_name") or challenger.get("id") or "someone"
    challenger_id = str(challenger.get("id") or "")

    # Resolve a friendly name for the optional private note target.
    name_by_id = {
        str(r.get("id")): (r.get("display_name") or r.get("short_name") or r.get("id"))
        for r in (observation.get("arena_roster") or [])
    }
    private_targets: List[str] = list(menu.get("private_message_targets") or [])
    note_html = ""
    if private_targets:
        target_id = private_targets[0]
        target_name = name_by_id.get(str(target_id), target_id)
        note_html = f"""
      <div class="modal-note">
        <div class="composer-title mono">Optional note to {_esc(target_name)}</div>
        <input type="text" id="modal-pm-text" placeholder="Say something private..." />
      </div>
        """

    # Always use the original top-down persona sprite for consistency.
    sprite_uri = _asset_data_uri("persona_sprite") or sprite_uri or _asset_data_uri(
        "persona_battle"
    )
    modal_avatar_style = (
        f' style="background-image:url(&quot;{_esc(sprite_uri)}&quot;);"'
        if sprite_uri
        else ""
    )

    return f"""
    <div class="modal-backdrop" id="challenge-modal">
      <div class="modal-panel glass">
        <div class="modal-eyebrow mono">Incoming Challenge</div>
        <div class="modal-challenger">
          <div class="modal-avatar"{modal_avatar_style}></div>
          <div class="modal-name">{_esc(name)}</div>
        </div>
        <div class="modal-buttons">
          <button class="accept-btn" onclick="submitSimple('accept')">Accept</button>
          <button class="decline-btn" onclick="submitSimple('decline')">Decline</button>
        </div>
        {note_html}
      </div>
    </div>
    """


def _hotbar_html(observation: Dict[str, Any]) -> str:
    """Bottom-docked action hotbar for free actions.

    Always shows the full cockpit strip (SAY / MOVE / DUEL / DM / WAIT) so
    the HUD reads as a complete game controller. Illegal actions render
    dimmed/disabled rather than vanishing — agents learn the control map
    even when no one is in proximity yet.
    """
    menu = observation.get("action_menu", {}) or {}
    actions: List[str] = list(menu.get("actions", []))
    if not actions:
        return ""

    def _btn(action_id: str, label: str, hint: str, onclick: str, el_id: str) -> str:
        legal = action_id in actions
        if legal:
            return (
                f'<div class="hotbar-btn glass" id="{el_id}" onclick="{onclick}">'
                f'<span class="hb-label">{label}</span>'
                f'<span class="hb-hint">{hint}</span></div>'
            )
        return (
            f'<div class="hotbar-btn glass disabled" id="{el_id}" title="Not available right now">'
            f'<span class="hb-label">{label}</span>'
            f'<span class="hb-hint">{hint}</span></div>'
        )

    buttons = [
        _btn("say", "SAY", "public chat", "toggleComposer('say')", "hotbar-say"),
        _btn("move", "MOVE", "wasd / click", "armMove()", "hotbar-move"),
        _btn("challenge", "DUEL", "click target", "armChallenge()", "hotbar-challenge"),
        _btn("private_message", "DM", "private msg", "toggleComposer('pm')", "hotbar-pm"),
        _btn("wait", "WAIT", "hold", "submitSimple('wait')", "hotbar-wait"),
    ]
    return f'<div class="hotbar" id="hotbar">{"".join(buttons)}</div>'


def _composers_html(observation: Dict[str, Any]) -> str:
    """Inline composer popovers for say/private_message, anchored above the
    hotbar rather than permanent side panels. Hidden (display:none) by
    default; JS toggles the `open` class. Only rendered at all when the
    corresponding action is actually legal, and the private_message target
    picker is built strictly from menu["private_message_targets"]."""
    menu = observation.get("action_menu", {}) or {}
    actions: List[str] = list(menu.get("actions", []))
    parts = []

    if "say" in actions:
        parts.append("""
      <div class="composer glass" id="composer-say">
        <div class="composer-title mono">Say something</div>
        <div class="composer-row">
          <input type="text" id="say-input" placeholder="Say something..." />
          <button class="send-btn" onclick="submitSay()">Send</button>
        </div>
      </div>
        """)

    if "private_message" in actions:
        pm_targets: List[str] = list(menu.get("private_message_targets") or [])
        chips = "".join(
            f'<div class="target-chip" data-target="{_esc(t)}" onclick="selectPmTarget({_js_attr(t)})">{_esc(t)}</div>'
            for t in pm_targets
        )
        parts.append(f"""
      <div class="composer glass" id="composer-pm">
        <div class="composer-title mono">Private message - pick a target</div>
        <div class="chip-row" id="pm-target-chips">{chips}</div>
        <div class="composer-row">
          <input type="text" id="pm-text" placeholder="Private message..." />
          <button class="send-btn" onclick="submitPrivateMessage()">Send</button>
        </div>
      </div>
        """)

    return "".join(parts)


def render_observation_html(
    observation: dict,
    *,
    inline_assets: bool = True,
    asset_rel_prefix: Optional[str] = None,
) -> str:
    """Render a single persona's observation dict as a self-contained HTML
    string (inline <style> and <script>, no external assets/CDN - must work
    with zero network access since it'll be loaded via a data: URL or local
    file, not served). Returns one complete <html>...</html> document.

    Every interactive control sets window.__lastAction (and
    window.__actionReady = true) to exactly the same action-dict shape the
    JSON brains (brains.MockArenaBrain / ClaudeArenaBrain) produce, driven
    strictly by observation["action_menu"]["actions"] and its accompanying
    target/bounds lists - nothing illegal is ever rendered as clickable.

    Visual language ("Persona Cockpit"): a first-person game HUD - a top
    phase banner stating plainly what's being asked, a centered room
    porthole with the self-avatar always visually distinct as "YOU", a
    bottom action hotbar or (for sub-steps 1/2) a dedicated focused view -
    matching render_spectator_html's void/glass/amber/cyan palette so the
    whole product reads as one system.
    """
    self_state = observation.get("self", {}) or {}
    room_bounds = observation.get("room_bounds", {}) or {}
    nearby: List[Dict[str, Any]] = observation.get("nearby_occupants", []) or []
    menu = observation.get("action_menu", {}) or {}
    actions: List[str] = list(menu.get("actions", []))

    self_name = self_state.get("display_name", self_state.get("id", "You"))
    phase = _phase_label(observation)

    is_battle_card = "play_card" in actions
    is_challenge_response = "accept" in actions and "decline" in actions

    nebula_uri = _resolve_asset_uri(
        "nebula_backdrop", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )
    floor_uri = _resolve_asset_uri(
        "room_floor", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )
    sprite_uri = _resolve_asset_uri(
        "persona_sprite", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )
    battle_sprite_uri = _resolve_asset_uri(
        "persona_battle", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )
    battle_arena_uri = _resolve_asset_uri(
        "battle_arena", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )
    vs_badge_uri = _resolve_asset_uri(
        "vs_badge", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )

    overlays = [
        _viewscreen_chrome_html(),
        _phase_banner_html(observation, phase),
        _agent_briefing_html(observation),
        _arena_cards_strip_html(observation.get("arena_card_counts") or {}),
        _agent_roster_html(observation),
    ]
    if not is_battle_card:
        overlays.append(_agent_comms_html(observation))
        overlays.append(_hotbar_html(observation))
        overlays.append(_composers_html(observation))
    else:
        overlays.append(
            _hand_dock_html(
                observation,
                sprite_uri=sprite_uri,
                battle_sprite_uri=battle_sprite_uri,
                battle_arena_uri=battle_arena_uri,
                vs_badge_uri=vs_badge_uri,
            )
        )
    if is_challenge_response:
        overlays.append(
            _challenge_modal_html(
                observation, sprite_uri=sprite_uri or battle_sprite_uri
            )
        )

    body_html = "\n".join(p for p in overlays if p)
    viewscreen_class = "viewscreen battle-mode" if is_battle_card else "viewscreen"

    # Data needed client-side to draw the canvas and validate clicks; kept
    # as plain JSON literals injected into <script>, never string-built.
    room_width = float(room_bounds.get("width", 20.0))
    room_height = float(room_bounds.get("height", 20.0))
    proximity_radius = room_bounds.get("proximity_radius")
    self_x = float(self_state.get("x", 0.0))
    self_y = float(self_state.get("y", 0.0))
    challengeable_targets = list(menu.get("challengeable_targets") or [])
    move_legal = "move" in actions
    challenge_legal = "challenge" in actions

    max_move_distance = float(room_bounds.get("max_move_distance", 2.0))

    # Draw EVERY non-eliminated crew member on the map (public positions from
    # arena_roster). Nearby ones are interactive; far ones are dimmed.
    nearby_ids = {occ.get("id") for occ in nearby}
    roster_rows = observation.get("arena_roster") or []
    occupants_payload = []
    if roster_rows:
        for row in roster_rows:
            if row.get("is_self") or row.get("eliminated"):
                continue
            pid = row.get("id")
            if row.get("x") is None or row.get("y") is None:
                continue
            is_near = bool(row.get("nearby")) or pid in nearby_ids
            occupants_payload.append(
                {
                    "id": pid,
                    "display_name": row.get("display_name", pid),
                    "short_name": row.get("short_name") or row.get("display_name", pid),
                    "x": row.get("x"),
                    "y": row.get("y"),
                    "stars": row.get("stars"),
                    "nearby": is_near,
                    "challengeable": pid in challengeable_targets,
                }
            )
    else:
        occupants_payload = [
            {
                "id": occ.get("id"),
                "display_name": occ.get("display_name", occ.get("id")),
                "short_name": occ.get("display_name", occ.get("id")),
                "x": occ.get("x"),
                "y": occ.get("y"),
                "stars": occ.get("stars"),
                "nearby": True,
                "challengeable": occ.get("id") in challengeable_targets,
            }
            for occ in nearby
        ]

    # Recent-chat/private-chat bubbles-over-avatars data: only the last 1-2
    # exchanges, and ONLY messages from personas actually present in
    # OCCUPANTS (or self) - this is a rendering enhancement layered on top
    # of data observations.py already scoped for leakage safety, never a
    # new data source of its own.
    recent_chat: List[Dict[str, Any]] = observation.get("recent_chat", []) or []
    private_chat: List[Dict[str, Any]] = observation.get("private_chat_with_me", []) or []
    bubble_payload = []
    for msg in recent_chat[-2:]:
        bubble_payload.append(
            {
                "persona_id": msg.get("persona_id"),
                "text": msg.get("text", ""),
                "private": False,
            }
        )
    for msg in private_chat[-2:]:
        sender = msg.get("sender_id")
        who = sender if sender != self_state.get("id") else msg.get("target_id")
        bubble_payload.append({"persona_id": who, "text": msg.get("text", ""), "private": True})

    script = f"""
<script>
  window.__lastAction = null;
  window.__actionReady = false;

  var ROOM_WIDTH = {_js(room_width)};
  var ROOM_HEIGHT = {_js(room_height)};
  var PROXIMITY_RADIUS = {_js(proximity_radius)};
  var SELF_X = {_js(self_x)};
  var SELF_Y = {_js(self_y)};
  var SELF_NAME = {_js(self_name)};
  var SELF_ID = {_js(self_state.get("id"))};
  var OCCUPANTS = {_js(occupants_payload)};
  var MOVE_LEGAL = {_js(move_legal)};
  var CHALLENGE_LEGAL = {_js(challenge_legal)};
  var MAX_MOVE_DISTANCE = {_js(max_move_distance)};
  var BUBBLES = {_js(bubble_payload)};
  var NEBULA_URI = {_js(nebula_uri)};
  var FLOOR_URI = {_js(floor_uri)};
  var SPRITE_URI = {_js(sprite_uri)};
  var ARENA_ROSTER = {_js({str(r.get("id")): (r.get("short_name") or r.get("display_name")) for r in (observation.get("arena_roster") or [])})};
  var BATTLE_OPPONENT_ID = {_js((observation.get("battle_opponent") or dict()).get("id"))};
  var SPRITE_FACE_OFFSET = Math.PI / 2;
  var PERSONA_COLORS = {_js(_PERSONA_COLORS)};
  var PERSONA_COLOR_BY_ID = {_js({
      str(r.get("id")): _PERSONA_COLORS[i % len(_PERSONA_COLORS)]
      for i, r in enumerate(observation.get("arena_roster") or [])
  })};

  var moveArmed = false;
  var challengeArmed = false;
  var pmSelectedTarget = null;
  var mouseRoomPt = null;

  function personaColor(pid) {{
    if (pid === SELF_ID) return '#ffa94d';
    return PERSONA_COLOR_BY_ID[pid] || PERSONA_COLORS[0] || '#a78bfa';
  }}

  function setAction(action) {{
    window.__lastAction = action;
    window.__actionReady = true;
  }}

  // The modal's optional private-note field (accept/decline, sub-step 2)
  // has exactly one legal target - the challenger - per
  // observation["action_menu"]["private_message_targets"], so it's baked
  // in server-side rather than needing a picker.
  var MODAL_PM_TARGET = {_js(list(menu.get("private_message_targets") or [None])[0] if menu.get("private_message_targets") else None)};

  function mergePrivateNote(action) {{
    var noteEl = document.getElementById('modal-pm-text');
    if (noteEl && noteEl.value && noteEl.value.trim().length > 0 && MODAL_PM_TARGET) {{
      action.private_message = {{target_id: MODAL_PM_TARGET, text: noteEl.value}};
    }}
    return action;
  }}

  function submitPlayCard(card) {{
    setAction({{action: 'play_card', card: card}});
  }}

  function submitSimple(name) {{
    setAction(mergePrivateNote({{action: name}}));
  }}

  function submitChallenge(targetId) {{
    setAction({{action: 'challenge', target_id: targetId}});
  }}

  function submitSay() {{
    var el = document.getElementById('say-input');
    var text = el ? el.value : '';
    if (!text || text.trim().length === 0) {{ text = '...'; }}
    setAction({{action: 'say', text: text}});
    closeComposers();
  }}

  function selectPmTarget(targetId) {{
    pmSelectedTarget = targetId;
    document.querySelectorAll('#pm-target-chips .target-chip').forEach(function(chip) {{
      chip.classList.toggle('selected', chip.getAttribute('data-target') === targetId);
    }});
  }}

  function submitPrivateMessage() {{
    var textEl = document.getElementById('pm-text');
    var text = textEl ? textEl.value : '';
    if (!text || text.trim().length === 0) {{ text = '...'; }}
    if (!pmSelectedTarget) {{
      var firstChip = document.querySelector('#pm-target-chips .target-chip');
      pmSelectedTarget = firstChip ? firstChip.getAttribute('data-target') : null;
    }}
    setAction({{action: 'private_message', private_message: {{target_id: pmSelectedTarget, text: text}}}});
    closeComposers();
  }}

  function closeComposers() {{
    document.querySelectorAll('.composer').forEach(function(el) {{ el.classList.remove('open'); }});
  }}

  function toggleComposer(name) {{
    var id = name === 'say' ? 'composer-say' : 'composer-pm';
    var el = document.getElementById(id);
    if (!el) return;
    var opening = !el.classList.contains('open');
    closeComposers();
    disarmModes();
    if (opening) {{ el.classList.add('open'); }}
  }}

  function disarmModes() {{
    moveArmed = false;
    challengeArmed = false;
    var moveBtn = document.getElementById('hotbar-move');
    var challengeBtn = document.getElementById('hotbar-challenge');
    if (moveBtn) moveBtn.classList.remove('armed');
    if (challengeBtn) challengeBtn.classList.remove('armed');
    var moveHint = document.getElementById('move-hint');
    var challengeHint = document.getElementById('challenge-hint');
    if (moveHint) moveHint.classList.remove('showing');
    if (challengeHint) challengeHint.classList.remove('showing');
  }}

  function armMove() {{
    if (!MOVE_LEGAL) return;
    closeComposers();
    var wasArmed = moveArmed;
    disarmModes();
    moveArmed = !wasArmed;
    var btn = document.getElementById('hotbar-move');
    var hint = document.getElementById('move-hint');
    if (moveArmed) {{
      if (btn) btn.classList.add('armed');
      if (hint) hint.classList.add('showing');
    }}
  }}

  function armChallenge() {{
    if (!CHALLENGE_LEGAL) return;
    closeComposers();
    var wasArmed = challengeArmed;
    disarmModes();
    challengeArmed = !wasArmed;
    var btn = document.getElementById('hotbar-challenge');
    var hint = document.getElementById('challenge-hint');
    if (challengeArmed) {{
      if (btn) btn.classList.add('armed');
      if (hint) hint.classList.add('showing');
    }}
  }}

  // Full ship art is shown (corridors + floor). Room (x,y) maps into the
  // checkerboard floor region *within* that art so pilots walk on tiles
  // while the whole room stays visible.
  var FLOOR_UV = {{ u0: 0.10, v0: 0.14, u1: 0.90, v1: 0.86 }};

  function roomArtRect(canvas) {{
    if (nebulaImgReady && nebulaImg.width > 0) {{
      var scale = Math.min(canvas.width / nebulaImg.width, canvas.height / nebulaImg.height);
      var dw = nebulaImg.width * scale;
      var dh = nebulaImg.height * scale;
      return {{
        x: (canvas.width - dw) / 2,
        y: (canvas.height - dh) / 2,
        w: dw,
        h: dh,
      }};
    }}
    var size = Math.min(canvas.width, canvas.height) * 0.88;
    return {{
      x: (canvas.width - size) / 2,
      y: (canvas.height - size) / 2,
      w: size,
      h: size,
    }};
  }}

  function playField(canvas) {{
    var art = roomArtRect(canvas);
    var fx = art.x + art.w * FLOOR_UV.u0;
    var fy = art.y + art.h * FLOOR_UV.v0;
    var fw = art.w * (FLOOR_UV.u1 - FLOOR_UV.u0);
    var fh = art.h * (FLOOR_UV.v1 - FLOOR_UV.v0);
    // Isotropic square inside the floor rectangle (keeps distances circular).
    var size = Math.min(fw, fh);
    return {{
      size: size,
      offsetX: fx + (fw - size) / 2,
      offsetY: fy + (fh - size) / 2,
    }};
  }}

  function roomToCanvas(x, y, canvas) {{
    var field = playField(canvas);
    var inset = Math.max(8, field.size * 0.03);
    var usable = field.size - inset * 2;
    return [
      field.offsetX + inset + (x / ROOM_WIDTH) * usable,
      field.offsetY + inset + (y / ROOM_HEIGHT) * usable,
    ];
  }}

  function canvasToRoom(px, py, canvas) {{
    var field = playField(canvas);
    var inset = Math.max(8, field.size * 0.03);
    var usable = field.size - inset * 2;
    return [
      ((px - field.offsetX - inset) / usable) * ROOM_WIDTH,
      ((py - field.offsetY - inset) / usable) * ROOM_HEIGHT,
    ];
  }}

  function submitMoveTo(targetX, targetY) {{
    if (!MOVE_LEGAL) return;
    var clamped = clampRoom(targetX, targetY);
    setAction({{action: 'move', target_x: clamped[0], target_y: clamped[1]}});
    disarmModes();
  }}

  function submitMoveDir(dx, dy) {{
    if (!MOVE_LEGAL) return;
    var dist = MAX_MOVE_DISTANCE || 2.0;
    var targetX = Math.min(ROOM_WIDTH, Math.max(0, SELF_X + dx * dist));
    var targetY = Math.min(ROOM_HEIGHT, Math.max(0, SELF_Y + dy * dist));
    submitMoveTo(targetX, targetY);
  }}

  function occupantAt(px, py, canvas) {{
    var hit = null;
    var hitDist = 18;
    OCCUPANTS.forEach(function(occ) {{
      var p = roomToCanvas(occ.x, occ.y, canvas);
      var d = Math.hypot(p[0] - px, p[1] - py);
      if (d <= hitDist) {{ hit = occ; hitDist = d; }}
    }});
    return hit;
  }}

  var starfieldCache = null;
  var nebulaImg = null;
  var nebulaImgReady = false;
  if (NEBULA_URI) {{
    nebulaImg = new Image();
    nebulaImg.onload = function() {{ nebulaImgReady = true; starfieldCache = null; }};
    nebulaImg.src = NEBULA_URI;
  }}

  var spriteImg = null;
  var spriteImgReady = false;
  if (SPRITE_URI) {{
    spriteImg = new Image();
    spriteImg.onload = function() {{ spriteImgReady = true; }};
    spriteImg.src = SPRITE_URI;
  }}

  function facingAngle(dirX, dirY) {{
    if (dirX === 0 && dirY === 0) return SPRITE_FACE_OFFSET;
    return Math.atan2(dirY, dirX) + SPRITE_FACE_OFFSET;
  }}

  function drawSprite(ctx, px, py, size, dirX, dirY) {{
    if (!spriteImgReady) return false;
    ctx.save();
    ctx.translate(px, py);
    ctx.rotate(facingAngle(dirX, dirY));
    ctx.drawImage(spriteImg, -size / 2, -size / 2, size, size);
    ctx.restore();
    return true;
  }}

  function facingToward(fromX, fromY, toX, toY) {{
    return {{x: toX - fromX, y: toY - fromY}};
  }}

  function occupantFacing(occ) {{
    if (BATTLE_OPPONENT_ID && occ.id === SELF_ID) {{
      var opp = OCCUPANTS.find(function(o) {{ return o.id === BATTLE_OPPONENT_ID; }});
      if (opp) return facingToward(SELF_X, SELF_Y, opp.x, opp.y);
    }}
    if (BATTLE_OPPONENT_ID && occ.id === BATTLE_OPPONENT_ID) {{
      return facingToward(occ.x, occ.y, SELF_X, SELF_Y);
    }}
    return {{x: 0, y: 0}};
  }}

  function selfFacing() {{
    if (BATTLE_OPPONENT_ID) {{
      var opp = OCCUPANTS.find(function(o) {{ return o.id === BATTLE_OPPONENT_ID; }});
      if (opp) return facingToward(SELF_X, SELF_Y, opp.x, opp.y);
    }}
    return {{x: 0, y: 0}};
  }}

  function clampRoom(x, y) {{
    return [
      Math.min(ROOM_WIDTH, Math.max(0, x)),
      Math.min(ROOM_HEIGHT, Math.max(0, y)),
    ];
  }}

  // Void + full ship room art (contain-fit, never cropped to floor-only).
  function buildStarfield(canvas) {{
    var g = document.createElement('canvas');
    g.width = canvas.width;
    g.height = canvas.height;
    var gctx = g.getContext('2d');
    var grad = gctx.createRadialGradient(
      g.width / 2, g.height / 2, 0,
      g.width / 2, g.height / 2, g.width * 0.75
    );
    grad.addColorStop(0, '#10131f');
    grad.addColorStop(0.55, '#0a0c14');
    grad.addColorStop(1, '#050609');
    gctx.fillStyle = grad;
    gctx.fillRect(0, 0, g.width, g.height);

    if (nebulaImgReady) {{
      var art = roomArtRect(canvas);
      gctx.drawImage(nebulaImg, art.x, art.y, art.w, art.h);
    }} else {{
      var neb = gctx.createRadialGradient(g.width * 0.28, g.height * 0.24, 0, g.width * 0.28, g.height * 0.24, g.width * 0.5);
      neb.addColorStop(0, 'rgba(167, 139, 250, 0.08)');
      neb.addColorStop(1, 'rgba(167, 139, 250, 0)');
      gctx.fillStyle = neb;
      gctx.fillRect(0, 0, g.width, g.height);
    }}

    var seedRand = 0.4217;
    function rand() {{
      seedRand = (seedRand * 9301 + 49297) % 233280;
      return seedRand / 233280;
    }}
    var starCount = Math.round((g.width * g.height) / 9000);
    for (var s = 0; s < starCount; s++) {{
      var sx = rand() * g.width;
      var sy = rand() * g.height;
      var sr = rand() * 1.1 + 0.25;
      gctx.beginPath();
      gctx.fillStyle = 'rgba(223, 230, 245, ' + (0.12 + rand() * 0.25) + ')';
      gctx.arc(sx, sy, sr, 0, Math.PI * 2);
      gctx.fill();
    }}
    return g;
  }}

  function drawRoom() {{
    var canvas = document.getElementById('room-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Full room backdrop (corridors + floor).
    if (!starfieldCache) {{ starfieldCache = buildStarfield(canvas); }}
    ctx.drawImage(starfieldCache, 0, 0);

    var selfPx = roomToCanvas(SELF_X, SELF_Y, canvas);

    // Dashed proximity ring around self, if known.
    if (PROXIMITY_RADIUS !== null && PROXIMITY_RADIUS !== undefined) {{
      var ringPx = (PROXIMITY_RADIUS / ROOM_WIDTH) * playField(canvas).size;
      ctx.beginPath();
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = 'rgba(255, 169, 77, 0.45)';
      ctx.lineWidth = 1.5;
      ctx.arc(selfPx[0], selfPx[1], ringPx, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
    }}

    // Battle link: pulsing amber tether between self and active opponent.
    var now = performance.now();
    var battlePulse = 0.5 + 0.5 * Math.sin(now / 220);
    var occSize = Math.max(18, Math.min(30, canvas.width * 0.06));
    var selfSize = Math.max(28, Math.min(46, canvas.width * 0.09));
    if (BATTLE_OPPONENT_ID) {{
      var battleOpp = OCCUPANTS.find(function(o) {{ return o.id === BATTLE_OPPONENT_ID; }});
      if (battleOpp) {{
        var oppPx = roomToCanvas(battleOpp.x, battleOpp.y, canvas);
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 169, 77, ' + (0.4 + battlePulse * 0.4) + ')';
        ctx.lineWidth = 2.5;
        ctx.setLineDash([5, 4]);
        ctx.moveTo(selfPx[0], selfPx[1]);
        ctx.lineTo(oppPx[0], oppPx[1]);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 169, 77, ' + battlePulse + ')';
        ctx.lineWidth = 2;
        ctx.arc(oppPx[0], oppPx[1], occSize * 0.5 + 6 + battlePulse * 4, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(selfPx[0], selfPx[1], selfSize * 0.5 + 6 + battlePulse * 4, 0, Math.PI * 2);
        ctx.stroke();
      }}
    }}

    // ALL other crew on the map (public positions). Nearby = full opacity +
    // challenge glow when legal; far = dimmed (walk closer to interact).
    var pulse = 0.55 + 0.45 * Math.sin(now / 260);
    ctx.font = '10.5px "JetBrains Mono", monospace';
    var occLabels = [];
    OCCUPANTS.forEach(function(occ) {{
      var p = roomToCanvas(occ.x, occ.y, canvas);
      var isNear = occ.nearby !== false;
      var showChallengeGlow = occ.challengeable && (challengeArmed || CHALLENGE_LEGAL);
      ctx.save();
      if (!isNear) {{ ctx.globalAlpha = 0.42; }}
      if (showChallengeGlow) {{
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(94, 255, 157, ' + pulse + ')';
        ctx.lineWidth = 2;
        ctx.arc(p[0], p[1], occSize * 0.5 + 5 + pulse * 3, 0, Math.PI * 2);
        ctx.stroke();
      }}
      var occFace = occupantFacing(occ);
      var drewSprite = drawSprite(ctx, p[0], p[1], occSize, occFace.x, occFace.y);
      var pColor = personaColor(occ.id);
      // Identity ring so each pilot is distinct even with shared sprite art.
      ctx.beginPath();
      ctx.strokeStyle = occ.challengeable
        ? 'rgba(94, 255, 157, 0.85)'
        : pColor;
      ctx.lineWidth = drewSprite ? 2.2 : 1.6;
      ctx.shadowBlur = isNear ? 8 : 0;
      ctx.shadowColor = pColor;
      ctx.arc(p[0], p[1], (drewSprite ? occSize * 0.5 : 7) + 2, 0, Math.PI * 2);
      ctx.stroke();
      ctx.shadowBlur = 0;
      if (!drewSprite) {{
        ctx.beginPath();
        ctx.fillStyle = pColor;
        ctx.arc(p[0], p[1], 7, 0, Math.PI * 2);
        ctx.fill();
      }}
      ctx.restore();
      var label = occ.short_name || occ.display_name || occ.id;
      if (!isNear) {{ label = label + ' (far)'; }}
      occLabels.push({{
        x: p[0] + (drewSprite ? occSize * 0.42 : 11),
        y: p[1] + (drewSprite ? occSize * 0.5 + 4 : 4),
        text: label,
        dim: !isNear,
        color: pColor,
        width: ctx.measureText(label).width || label.length * 6.2,
      }});
    }});
    var lineHeight = 15;
    for (var li = 0; li < occLabels.length; li++) {{
      for (var lj = 0; lj < li; lj++) {{
        var la = occLabels[li];
        var lb = occLabels[lj];
        var xOverlap = Math.abs(la.x - lb.x) < Math.max(la.width, lb.width) + 4;
        if (xOverlap && Math.abs(la.y - lb.y) < lineHeight) {{
          la.y = lb.y + lineHeight;
        }}
      }}
    }}
    occLabels.forEach(function(lbl) {{
      var padX = 5, pillH = 14;
      ctx.fillStyle = lbl.dim ? 'rgba(20, 24, 36, 0.72)' : 'rgba(8, 10, 18, 0.88)';
      ctx.strokeStyle = lbl.color || 'rgba(77, 216, 232, 0.35)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      if (ctx.roundRect) {{
        ctx.roundRect(lbl.x - padX, lbl.y - pillH + 3, lbl.width + padX * 2, pillH, 6);
      }} else {{
        ctx.rect(lbl.x - padX, lbl.y - pillH + 3, lbl.width + padX * 2, pillH);
      }}
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = lbl.dim ? 'rgba(142, 151, 184, 0.9)' : '#dfe6f5';
      ctx.fillText(lbl.text, lbl.x, lbl.y);
    }});

    // Self: always the visual center of the room - bigger, brighter, with
    // a reticle chevron beneath so "YOU" is unmistakable at a glance.
    ctx.save();
    ctx.shadowBlur = 20;
    ctx.shadowColor = '#ffa94d';
    var selfFace = selfFacing();
    var selfDrewSprite = drawSprite(ctx, selfPx[0], selfPx[1], selfSize, selfFace.x, selfFace.y);
    ctx.restore();
    if (!selfDrewSprite) {{
      ctx.beginPath();
      ctx.fillStyle = '#ffa94d';
      ctx.shadowBlur = 16;
      ctx.shadowColor = '#ffa94d';
      ctx.arc(selfPx[0], selfPx[1], 11, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = '#050609';
      ctx.lineWidth = 2;
      ctx.stroke();
    }}
    ctx.strokeStyle = 'rgba(255, 201, 138, 0.9)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(selfPx[0], selfPx[1], selfDrewSprite ? selfSize * 0.5 + 3 : 14, 0, Math.PI * 2);
    ctx.stroke();
    // Reticle chevron beneath self.
    var chevronY = selfPx[1] + (selfDrewSprite ? selfSize * 0.5 + 8 : 19);
    ctx.beginPath();
    ctx.strokeStyle = '#ffc98a';
    ctx.lineWidth = 1.5;
    ctx.moveTo(selfPx[0] - 6, chevronY);
    ctx.lineTo(selfPx[0], chevronY - 6);
    ctx.lineTo(selfPx[0] + 6, chevronY);
    ctx.stroke();
    ctx.fillStyle = '#ffc98a';
    ctx.font = 'bold 11px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('YOU', selfPx[0], selfPx[1] - (selfDrewSprite ? selfSize * 0.5 + 8 : 20));
    ctx.textAlign = 'left';

    // Faint targeting reticle following the mouse while move/challenge is
    // available, so hover state visually suggests "clickable target".
    if (mouseRoomPt && (challengeArmed || (MOVE_LEGAL && !challengeArmed))) {{
      var mp = roomToCanvas(mouseRoomPt[0], mouseRoomPt[1], canvas);
      ctx.beginPath();
      ctx.strokeStyle = challengeArmed
        ? 'rgba(94, 255, 157, 0.55)' : 'rgba(255, 201, 138, 0.55)';
      ctx.lineWidth = 1.2;
      ctx.moveTo(mp[0] - 9, mp[1]);
      ctx.lineTo(mp[0] + 9, mp[1]);
      ctx.moveTo(mp[0], mp[1] - 9);
      ctx.lineTo(mp[0], mp[1] + 9);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(mp[0], mp[1], 9, 0, Math.PI * 2);
      ctx.stroke();
    }}

    positionBubbles(canvas);
  }}

  function personaLabel(pid) {{
    if (pid === SELF_ID) return SELF_NAME;
    if (ARENA_ROSTER[pid]) return ARENA_ROSTER[pid];
    var occ = OCCUPANTS.find(function(o) {{ return o.id === pid; }});
    return occ ? occ.display_name : pid;
  }}

  function personaPoint(pid, canvas) {{
    if (pid === SELF_ID) return roomToCanvas(SELF_X, SELF_Y, canvas);
    var occ = OCCUPANTS.find(function(o) {{ return o.id === pid; }});
    if (!occ) return null;
    return roomToCanvas(occ.x, occ.y, canvas);
  }}

  function positionBubbles(canvas) {{
    var layer = document.getElementById('bubble-layer');
    if (!layer) return;
    layer.innerHTML = '';
    BUBBLES.forEach(function(msg, idx) {{
      var pt = personaPoint(msg.persona_id, canvas);
      if (!pt) return;
      var el = document.createElement('div');
      el.className = 'speech-bubble' + (msg.private ? ' private' : '');
      var who = document.createElement('div');
      who.className = 'bubble-who';
      who.textContent = (msg.private ? '\\u{{1F512}} ' : '') + personaLabel(msg.persona_id);
      var body = document.createElement('div');
      body.textContent = msg.text;
      el.appendChild(who);
      el.appendChild(body);
      el.style.left = pt[0] + 'px';
      el.style.top = (pt[1] - 18 - idx * 2) + 'px';
      layer.appendChild(el);
    }});
  }}

  function onStageMouseMove(evt) {{
    var canvas = document.getElementById('room-canvas');
    var rect = canvas.getBoundingClientRect();
    var px = (evt.clientX - rect.left) * (canvas.width / rect.width);
    var py = (evt.clientY - rect.top) * (canvas.height / rect.height);
    mouseRoomPt = canvasToRoom(px, py, canvas);
  }}

  function onCanvasClick(evt) {{
    var canvas = document.getElementById('room-canvas');
    var rect = canvas.getBoundingClientRect();
    var px = (evt.clientX - rect.left) * (canvas.width / rect.width);
    var py = (evt.clientY - rect.top) * (canvas.height / rect.height);

    if (challengeArmed && CHALLENGE_LEGAL) {{
      var occ = occupantAt(px, py, canvas);
      if (occ && occ.challengeable) {{
        submitChallenge(occ.id);
        disarmModes();
      }}
      return;
    }}

    if (MOVE_LEGAL && !challengeArmed) {{
      var room = canvasToRoom(px, py, canvas);
      submitMoveTo(room[0], room[1]);
      return;
    }}
  }}

  function onKeyDown(evt) {{
    if (!MOVE_LEGAL) return;
    var tag = (evt.target && evt.target.tagName) ? evt.target.tagName.toLowerCase() : '';
    if (tag === 'input' || tag === 'textarea') return;
    var key = evt.key.toLowerCase();
    if (key === 'w') {{ evt.preventDefault(); submitMoveDir(0, -1); }}
    else if (key === 's') {{ evt.preventDefault(); submitMoveDir(0, 1); }}
    else if (key === 'a') {{ evt.preventDefault(); submitMoveDir(-1, 0); }}
    else if (key === 'd') {{ evt.preventDefault(); submitMoveDir(1, 0); }}
  }}

  // Design resolution is fixed (1024x768). The whole design-frame is CSS
  // scaled to fit the real window so layout never reflows / clips badly.
  var DESIGN_W = 1024;
  var DESIGN_H = 768;

  function fitUiScale() {{
    var sw = window.innerWidth || DESIGN_W;
    var sh = window.innerHeight || DESIGN_H;
    var scale = Math.min(sw / DESIGN_W, sh / DESIGN_H);
    // Never go below a readable floor; letterbox instead of crushing UI.
    scale = Math.max(0.35, scale);
    document.documentElement.style.setProperty('--ui-scale', String(scale));
  }}

  function resizeStageCanvas() {{
    var canvas = document.getElementById('room-canvas');
    if (!canvas) return;
    if (canvas.width === DESIGN_W && canvas.height === DESIGN_H) return;
    canvas.width = DESIGN_W;
    canvas.height = DESIGN_H;
    starfieldCache = null;
  }}

  function renderLoop() {{
    drawRoom();
    requestAnimationFrame(renderLoop);
  }}

  document.addEventListener('DOMContentLoaded', function() {{
    var canvas = document.getElementById('room-canvas');
    if (canvas) {{
      canvas.addEventListener('click', onCanvasClick);
      canvas.addEventListener('mousemove', onStageMouseMove);
    }}
    fitUiScale();
    resizeStageCanvas();
    window.addEventListener('resize', function() {{
      fitUiScale();
      starfieldCache = null;
    }});
    document.addEventListener('keydown', onKeyDown);
    requestAnimationFrame(renderLoop);
  }});
</script>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
<title>Starclash - {_esc(self_name)}</title>
<style>{_AGENT_STYLE}</style>
</head>
<body>
<div class="scale-stage" id="scale-stage">
  <div class="design-frame" id="design-frame">
    <div class="{viewscreen_class}" id="viewscreen">
{body_html}
    </div>
  </div>
</div>
{script}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Spectator / human-viewing replay
# ---------------------------------------------------------------------------

_SPECTATOR_STYLE = """
  :root {
    color-scheme: dark;
    --void-deep: #050609;
    --void-mid: #0a0c14;
    --glass-bg: rgba(17, 20, 28, 0.72);
    --glass-border: rgba(77, 216, 232, 0.28);
    --amber: #ffa94d;
    --amber-bright: #ffc98a;
    --cyan: #4dd8e8;
    --win: #5eff9d;
    --lose: #ff5468;
    --tie: #4dd8e8;
    --eliminated: #4a5170;
    --ink: #dfe6f5;
    --ink-dim: #8e97b8;
    --mono: "JetBrains Mono", "Fira Code", ui-monospace, monospace;
    --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
    --design-w: 1280;
    --design-h: 720;
    --ui-scale: 1;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    background: #020203;
    color: var(--ink);
    font-family: var(--sans);
    font-size: 14px;
    overflow: hidden;
  }

  .scale-stage {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background: var(--void-deep);
  }
  .design-frame {
    position: relative;
    width: calc(var(--design-w) * 1px);
    height: calc(var(--design-h) * 1px);
    flex: 0 0 auto;
    transform: scale(var(--ui-scale));
    transform-origin: center center;
    overflow: hidden;
  }

  .hud-label {
    font-family: var(--mono);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 700;
  }

  /* -- Viewscreen fills the design frame; CSS scale fits the browser ------ */
  .viewscreen {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(ellipse at center, var(--void-mid) 0%, var(--void-deep) 72%, #020203 100%);
    overflow: hidden;
  }
  .viewscreen canvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    display: block;
  }
  /* Vignette layered above the canvas, below the HUD overlays. */
  .vignette {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0) 55%, rgba(0, 0, 0, 0.55) 100%);
    z-index: 2;
  }
  /* Glowing porthole border + corner brackets, drawn with pseudo-elements
     so no external image/SVG asset is needed. */
  .porthole-frame {
    position: absolute;
    inset: 10px;
    pointer-events: none;
    border: 1px solid rgba(77, 216, 232, 0.22);
    border-radius: 14px;
    box-shadow: 0 0 40px rgba(77, 216, 232, 0.06) inset, 0 0 24px rgba(0, 0, 0, 0.6);
    z-index: 3;
  }
  .porthole-frame::before,
  .porthole-frame::after,
  .porthole-frame .bracket {
    position: absolute;
    width: 26px;
    height: 26px;
    border: 2px solid var(--amber);
    opacity: 0.75;
  }
  .porthole-frame::before {
    top: -1px; left: -1px;
    border-right: none; border-bottom: none;
    border-radius: 6px 0 0 0;
  }
  .porthole-frame::after {
    bottom: -1px; right: -1px;
    border-left: none; border-top: none;
    border-radius: 0 0 6px 0;
  }
  .porthole-frame .bracket.tr {
    top: -1px; right: -1px;
    border-left: none; border-bottom: none;
    border-radius: 0 6px 0 0;
  }
  .porthole-frame .bracket.bl {
    bottom: -1px; left: -1px;
    border-right: none; border-top: none;
    border-radius: 0 0 0 6px;
  }

  /* -- Generic HUD overlay chrome ------------------------------------------ */
  .hud {
    position: absolute;
    z-index: 6;
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    backdrop-filter: blur(6px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    padding: 10px 12px;
  }
  .hud-title {
    font-family: var(--mono);
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--cyan);
    opacity: 0.85;
    margin: 0 0 6px 0;
  }

  /* -- Top-left: mission briefing header ----------------------------------- */
  #hud-briefing {
    top: 18px;
    left: 18px;
    width: min(280px, 24vw);
    min-height: 64px;
    padding: 12px 14px;
  }
  #hud-briefing .briefing-title {
    font-family: var(--mono);
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--amber-bright);
    text-shadow: 0 0 14px rgba(255, 169, 77, 0.3);
    margin: 0;
  }
  #hud-briefing .briefing-meta {
    margin-top: 6px;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink-dim);
    letter-spacing: 0.02em;
  }

  /* -- Left edge: crew roster table ---------------------------------------- */
  #hud-roster {
    top: 96px;
    left: 18px;
    width: min(280px, 24vw);
    bottom: 92px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 10px 10px 8px;
    background:
      linear-gradient(165deg, rgba(77, 216, 232, 0.08), transparent 45%),
      rgba(8, 10, 18, 0.9);
    border: 1px solid rgba(77, 216, 232, 0.28);
    border-radius: 14px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(77, 216, 232, 0.1);
  }
  #hud-roster .roster-scroll {
    overflow-y: auto;
    flex: 1 1 auto;
  }
  .roster-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--sans);
    font-size: 11px;
  }
  .roster-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: rgba(10, 12, 20, 0.95);
    font-family: var(--mono);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ink-dim);
    padding: 6px 8px;
    text-align: left;
    border-bottom: 1px solid rgba(77, 216, 232, 0.18);
  }
  .roster-table td {
    padding: 6px 8px;
    border-bottom: 1px solid rgba(77, 216, 232, 0.06);
    color: var(--ink);
    white-space: nowrap;
  }
  .roster-table .col-stars {
    text-align: center;
    font-family: var(--mono);
    font-size: 10.5px;
    color: var(--amber-bright);
  }
  .roster-swatch {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
    margin-right: 6px;
    vertical-align: middle;
    box-shadow: 0 0 6px rgba(0,0,0,0.35);
  }
  .roster-table .col-card-type {
    text-align: center;
    font-family: var(--mono);
    font-size: 10px;
    padding: 4px 3px;
    min-width: 28px;
    color: var(--cyan);
  }
  .roster-table th.col-card-type {
    font-size: 14px;
    padding: 4px 3px;
    text-align: center;
  }
  .roster-table .card-type-emoji {
    display: block;
    font-size: 13px;
    line-height: 1;
  }
  .roster-table .card-type-n {
    display: block;
    font-size: 10px;
    margin-top: 2px;
    color: var(--cyan);
  }
  .roster-row.eliminated { opacity: 0.42; }
  .roster-row.eliminated td { text-decoration: line-through; color: var(--eliminated); }
  .roster-row.in-battle td { background: rgba(255, 169, 77, 0.12); }
  .roster-row.in-battle .col-name::after {
    content: "BATTLE";
    margin-left: 6px;
    font-family: var(--mono);
    font-size: 8px;
    letter-spacing: 0.06em;
    color: var(--amber-bright);
    padding: 1px 5px;
    border-radius: 4px;
    border: 1px solid rgba(255, 169, 77, 0.45);
    text-decoration: none;
    display: inline-block;
    vertical-align: middle;
  }

  /* -- Right edge: comms feed (event log) — mirrors roster geometry -------- */
  #hud-comms {
    top: 96px;
    right: 18px;
    width: min(280px, 24vw);
    bottom: 92px;
    display: flex;
    flex-direction: column;
    padding: 10px 10px 8px;
    background:
      linear-gradient(165deg, rgba(77, 216, 232, 0.08), transparent 45%),
      rgba(8, 10, 18, 0.9);
    border: 1px solid rgba(77, 216, 232, 0.28);
    border-radius: 14px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(77, 216, 232, 0.1);
  }
  #hud-comms .comms-scroll {
    list-style: none;
    margin: 0;
    padding: 6px;
    overflow-y: auto;
    flex: 1 1 auto;
  }
  #hud-comms .comms-scroll li {
    padding: 7px 10px;
    margin-bottom: 4px;
    border-radius: 8px;
    font-size: 11.5px;
    font-family: var(--sans);
    line-height: 1.4;
    background: rgba(17, 20, 28, 0.65);
    border: 1px solid rgba(77, 216, 232, 0.1);
  }
  #hud-comms .comms-scroll li.future { opacity: 0.2; }
  #hud-comms .comms-scroll li.is-battle {
    background: rgba(255, 169, 77, 0.1);
    border-color: rgba(255, 169, 77, 0.28);
  }
  #hud-comms .comms-scroll li.current {
    border-left: 2px solid var(--amber);
    background: rgba(255, 169, 77, 0.16);
  }
  .tick-label {
    color: var(--amber-bright);
    font-family: var(--mono);
    font-weight: 700;
  }
  .persona-swatch {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
    margin-right: 5px;
    vertical-align: middle;
  }

  /* -- Bottom-center: playback control strip -------------------------------- */
  #hud-playback {
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: min(640px, calc(100vw - 380px));
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    border-radius: 999px;
  }
  #hud-playback button {
    font-family: var(--mono);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    background: rgba(255, 169, 77, 0.12);
    color: var(--amber-bright);
    border: 1px solid rgba(255, 169, 77, 0.4);
    border-radius: 999px;
    padding: 6px 16px;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
    flex: 0 0 auto;
  }
  #hud-playback button:hover { background: rgba(255, 169, 77, 0.22); border-color: var(--amber); }
  #hud-playback input[type="range"] {
    flex: 1 1 auto;
    accent-color: var(--amber);
  }
  #hud-playback .tick-display {
    flex: 0 0 auto;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink-dim);
    min-width: 78px;
    text-align: right;
  }

  .eliminated-text { color: var(--eliminated); text-decoration: line-through; }

  /* -- Top-right: arena-wide card pool (aligns with briefing height) -------- */
  #hud-arena-cards {
    top: 18px;
    right: 18px;
    width: min(280px, 24vw);
    min-height: 64px;
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: center;
    padding: 10px 14px;
    box-sizing: border-box;
    background:
      linear-gradient(155deg, rgba(255, 169, 77, 0.12), transparent 50%),
      rgba(12, 14, 22, 0.9);
    border: 1px solid rgba(255, 169, 77, 0.28);
    border-radius: 14px;
    box-shadow: 0 10px 26px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 201, 138, 0.12);
  }
  #hud-arena-cards .card-stat {
    text-align: center;
    min-width: 48px;
    padding: 4px 6px;
    border-radius: 10px;
    background: rgba(0, 0, 0, 0.22);
    border: 1px solid rgba(77, 216, 232, 0.12);
  }
  #hud-arena-cards .card-stat .stat-emoji { font-size: 22px; line-height: 1; }
  #hud-arena-cards .hud-cards-title {
    font-family: var(--mono);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--amber-bright);
    margin-right: 2px;
    align-self: center;
  }
  #hud-arena-cards .card-stat .stat-value {
    font-family: var(--mono);
    font-size: 18px;
    font-weight: 700;
    color: var(--cyan);
    margin-top: 2px;
  }

  /* -- Speech chat bubbles (say / private_message over avatars) -------------- */
  .bubble-layer { position: absolute; inset: 0; pointer-events: none; z-index: 10; }
  .speech-bubble {
    position: absolute;
    transform: translate(-50%, -100%);
    max-width: 200px;
    padding: 5px 9px;
    border-radius: 9px;
    font-size: 11.5px;
    line-height: 1.3;
    color: var(--ink);
    background: rgba(10, 12, 20, 0.94);
    border: 1px solid var(--amber);
    box-shadow: 0 0 14px rgba(255, 169, 77, 0.35);
    white-space: normal;
    z-index: 9;
  }
  .speech-bubble.private {
    border-color: var(--cyan);
    box-shadow: 0 0 14px rgba(77, 216, 232, 0.35);
  }
  .speech-bubble .bubble-who {
    font-family: var(--mono);
    font-size: 9.5px;
    color: var(--ink-dim);
    margin-bottom: 1px;
  }
  .speech-bubble.private .bubble-who { color: var(--cyan); }

  /* -- Duel chat bubble ------------------------------------------------------ */
  .duel-bubble {
    position: absolute;
    transform: translate(-50%, -100%) scale(0.4);
    background: rgba(10, 12, 20, 0.94);
    border: 1px solid var(--amber);
    border-radius: 10px;
    padding: 6px 10px;
    font-family: var(--sans);
    font-size: 12.5px;
    white-space: nowrap;
    color: var(--ink);
    box-shadow: 0 0 18px rgba(255, 169, 77, 0.4);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.25s ease, transform 0.25s ease;
    z-index: 8;
  }
  .duel-bubble.showing { opacity: 1; transform: translate(-50%, -100%) scale(1); }
  .duel-bubble::after {
    content: "";
    position: absolute;
    left: 50%;
    top: 100%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: var(--amber);
  }

  /* Name-label pill drawn on the canvas is handled in JS; nothing extra
     needed here, but keep a scrollbar treatment consistent with the HUD
     glass look for the roster/comms overlays. */
  #hud-roster .roster-scroll::-webkit-scrollbar,
  #hud-comms .comms-scroll::-webkit-scrollbar { width: 6px; }
  #hud-roster .roster-scroll::-webkit-scrollbar-thumb,
  #hud-comms .comms-scroll::-webkit-scrollbar-thumb {
    background: rgba(77, 216, 232, 0.25);
    border-radius: 3px;
  }
"""


def _is_empty_speech(text: Any) -> bool:
    """True for blank / placeholder mock speech (should not pollute comms)."""
    t = "" if text is None else str(text).strip()
    return (not t) or t in (".", "..", "...", "…", "....")


def _clean_speech(text: Any) -> str:
    t = "" if text is None else str(text).strip()
    if _is_empty_speech(t):
        return ""
    if len(t) > 80:
        return t[:77] + "…"
    return t


def _event_line(event: Dict[str, Any]) -> str:
    etype = event.get("type", "")
    glyph = _EVENT_GLYPHS.get(etype, "•")
    if etype == "say":
        speech = _clean_speech(event.get("text"))
        if not speech:
            return ""  # drop empty mock say lines from feeds
        return f"{glyph} {_esc(event.get('persona_id'))}: \"{_esc(speech)}\""
    if etype == "wait":
        return f"{glyph} {_esc(event.get('persona_id'))} waits."
    if etype == "move":
        return (
            f"{glyph} {_esc(event.get('persona_id'))} moves to "
            f"({_esc(round(float(event.get('to_x', 0)), 1))}, {_esc(round(float(event.get('to_y', 0)), 1))})"
        )
    if etype == "challenge_issued":
        return f"{glyph} {_esc(event.get('challenger_id'))} challenges {_esc(event.get('target_id'))}!"
    if etype == "challenge_accepted":
        return f"{glyph} {_esc(event.get('responder_id'))} accepts {_esc(event.get('challenger_id'))}'s challenge."
    if etype == "challenge_declined":
        return f"{glyph} {_esc(event.get('responder_id'))} declines {_esc(event.get('challenger_id'))}'s challenge."
    if etype == "challenge_auto_declined_no_cards":
        return f"{glyph} {_esc(event.get('challenger_id'))}'s challenge on {_esc(event.get('target_id'))} auto-declined (no cards)."
    if etype == "battle_resolved":
        winner = event.get("winner_id")
        outcome = f"{_esc(winner)} wins" if winner else "tie"
        card_a = event.get("card_a")
        card_b = event.get("card_b")
        glyph_a = _CARD_GLYPHS.get(card_a, "")
        glyph_b = _CARD_GLYPHS.get(card_b, "")
        return (
            f"{_esc(event.get('persona_a'))} ({glyph_a}) vs "
            f"{_esc(event.get('persona_b'))} ({glyph_b}) -&gt; {outcome}"
        )
    if etype == "private_message_sent":
        speech = _clean_speech(event.get("text"))
        if not speech:
            return ""
        return (
            f"{glyph} [private] {_esc(event.get('sender_id'))} &rarr; {_esc(event.get('target_id'))}: "
            f"\"{_esc(speech)}\""
        )
    if etype == "system":
        return f"{glyph} [system] {_esc(event.get('message'))} ({_esc({k: v for k, v in event.items() if k not in ('type', 'tick', 'message')})})"
    return f"[{_esc(etype)}] {_esc({k: v for k, v in event.items() if k not in ('type', 'tick')})}"


def _infer_initial_persona_card_counts(game_log: dict) -> Dict[str, Dict[str, int]]:
    """Per-persona Rock/Paper/Scissors counts at deal time (for replay HUD)."""
    stored = game_log.get("initial_persona_card_counts")
    if isinstance(stored, dict) and stored:
        result: Dict[str, Dict[str, int]] = {}
        for pid, counts in stored.items():
            if isinstance(counts, dict):
                result[str(pid)] = {
                    card: int(counts.get(card, 0)) for card in _CARD_TYPES_ORDER
                }
        if result:
            return result

    from engine import ArenaEngine, PersonaState

    hand_size = int(game_log.get("hand_size", 4))
    seed = int(game_log.get("seed", 42))
    personas = [
        PersonaState(
            id=p["id"],
            display_name=p.get("display_name", p["id"]),
            stars=3,
            hand=[],
        )
        for p in (game_log.get("personas") or [])
    ]
    if not personas:
        return {}

    engine = ArenaEngine(
        personas=personas,
        room_name=game_log.get("room_name", "Main Chat Room"),
        max_ticks=int(game_log.get("max_ticks", 10) or 10),
        seed=seed,
        hand_size=hand_size,
        observation_builder=lambda *_args: {},
    )
    return {
        pid: {card: engine.personas[pid].hand.count(card) for card in _CARD_TYPES_ORDER}
        for pid in engine.persona_order
    }


def _infer_spawn_positions(game_log: dict) -> Dict[str, Dict[str, float]]:
    """Per-persona spawn (x, y) at deal time - used as tick-0 replay positions."""
    stored = game_log.get("spawn_positions")
    if isinstance(stored, dict) and stored:
        result: Dict[str, Dict[str, float]] = {}
        for pid, pos in stored.items():
            if isinstance(pos, dict) and "x" in pos and "y" in pos:
                result[str(pid)] = {"x": float(pos["x"]), "y": float(pos["y"])}
        if result:
            return result

    inferred: Dict[str, Dict[str, float]] = {}
    for event in game_log.get("events") or []:
        if event.get("type") != "move":
            continue
        pid = event.get("persona_id")
        if pid and pid not in inferred:
            inferred[str(pid)] = {
                "x": float(event.get("from_x", 0.0)),
                "y": float(event.get("from_y", 0.0)),
            }

    room_w = float(game_log.get("room_width", 20.0))
    room_h = float(game_log.get("room_height", 20.0))
    personas = game_log.get("personas") or []
    for idx, persona in enumerate(personas):
        pid = str(persona.get("id"))
        if pid in inferred:
            continue
        # Grid fallback for personas that waited on tick 0 (no move event).
        cols = max(1, math.ceil(math.sqrt(len(personas))))
        row = idx // cols
        col = idx % cols
        inferred[pid] = {
            "x": room_w * (col + 1) / (cols + 1),
            "y": room_h * (row + 1) / (max(1, math.ceil(len(personas) / cols)) + 1),
        }
    return inferred


def _infer_initial_card_counts(game_log: dict) -> Dict[str, int]:
    """Return the arena-wide Rock/Paper/Scissors pool at deal time."""
    stored = game_log.get("initial_card_counts")
    if isinstance(stored, dict) and stored:
        return {card: int(stored.get(card, 0)) for card in ("Rock", "Paper", "Scissors")}

    personas = game_log.get("personas") or []
    hand_size = int(game_log.get("hand_size", 4))
    deck_size = len(personas) * hand_size
    base, remainder = divmod(deck_size, 3)
    counts = {"Rock": base, "Paper": base, "Scissors": base}
    for i in range(remainder):
        counts[("Rock", "Paper", "Scissors")[i]] += 1
    return counts


def render_spectator_html(
    game_log: dict,
    *,
    inline_assets: bool = True,
    asset_rel_prefix: Optional[str] = None,
) -> str:
    """Render a full-game REPLAY page (not interactive/clickable - just a
    scrubber + play button) from a complete game_log.json-shaped dict (see
    run_arena.py), styled as a "cockpit viewscreen": the room canvas fills
    the entire viewport as a full-bleed porthole, and every other piece of
    data (mission-briefing header, card-count strip, pilot roster, comms/
    event feed, playback scrubber) is a small glass HUD overlay docked to an
    edge/corner of that viewscreen rather than a boxed side-panel - the goal
    is a game screen with instrument overlays, not a dashboard with an inset
    canvas.

    Avatar movement between ticks is interpolated client-side (ease-out
    cubic over ~450ms) rather than snapped, with a separate small ambient
    idle bob layered on top so the scene feels alive between moves.
    battle_resolved events trigger a transient duel chat-bubble (staggered
    horizontally when multiple battles land on the same tick, so simultaneous
    duels fan out instead of stacking) plus a win/lose/tie visual effect on
    the canvas, and eliminated personas permanently switch to the muted
    "eliminated" identity color from that tick onward. All of this is driven
    by the same event-folding logic as before (computeStateAtTick) - only
    the rendering layer changed.
    """
    room_name = game_log.get("room_name", "Main Chat Room")
    seed = game_log.get("seed")
    max_ticks = game_log.get("max_ticks")
    termination_reason = game_log.get("termination_reason")
    personas: List[Dict[str, Any]] = game_log.get("personas", []) or []
    events: List[Dict[str, Any]] = game_log.get("events", []) or []
    final_state: Dict[str, Any] = game_log.get("final_state", {}) or {}

    persona_rows = []
    for idx, p in enumerate(personas):
        pid = p.get("id")
        fs = final_state.get(pid, {}) if isinstance(final_state, dict) else {}
        persona_rows.append(
            {
                "id": pid,
                "display_name": p.get("display_name", pid),
                "final_stars": fs.get("stars"),
                "eliminated": fs.get("eliminated", False),
                "final_x": fs.get("x"),
                "final_y": fs.get("y"),
                "color": _PERSONA_COLORS[idx % len(_PERSONA_COLORS)],
            }
        )

    total_events = len(events)

    initial_stars = 3
    initial_arena_card_counts = _infer_initial_card_counts(game_log)

    briefing_html = f"""
    <div class="hud" id="hud-briefing">
      <div class="briefing-title">{_esc(room_name)}</div>
      <div class="briefing-meta">
        REPLAY &middot; <span class="tick-label" id="briefing-event">0</span> / {total_events} moments
        &middot; seed {_esc(seed)} &middot; {_esc(termination_reason)}
      </div>
    </div>
    """

    arena_cards_html = _arena_cards_strip_html(initial_arena_card_counts, dynamic=True)

    roster_rows_html = "".join(
        f'<tr class="roster-row{" eliminated" if row["eliminated"] else ""}" '
        f'id="roster-{_esc(row["id"])}" data-id="{_esc(row["id"])}">'
        f'<td class="col-name" title="{_esc(row["display_name"])}">'
        f'<span class="persona-swatch" style="background:{_esc(row["color"])}"></span>'
        f'{_esc(row["display_name"] or row["id"])}</td>'
        f'<td class="col-stars" id="stars-{_esc(row["id"])}">\u2b50-</td>'
        f"</tr>"
        for row in persona_rows
    )

    roster_html = f"""
    <div class="hud" id="hud-roster">
      <div class="hud-title">Crew</div>
      <div class="roster-scroll">
        <table class="roster-table">
          <thead><tr><th>Name</th><th>Stars</th></tr></thead>
          <tbody>{roster_rows_html}</tbody>
        </table>
      </div>
    </div>
    """

    comms_html = """
    <div class="hud" id="hud-comms">
      <div class="hud-title">Comms Feed</div>
      <ul class="comms-scroll" id="event-ticker"></ul>
    </div>
    """

    playback_html = f"""
    <div class="hud" id="hud-playback">
      <button id="play-btn" onclick="togglePlay()">Play</button>
      <input type="range" id="event-slider" min="0" max="{total_events}" value="0"
             oninput="renderEventCount(parseInt(this.value, 10))" />
      <span id="event-display" class="tick-display">Moment 0 / {total_events}</span>
    </div>
    """

    viewscreen_chrome_html = """
    <canvas id="room-canvas"></canvas>
    <div class="vignette"></div>
    <div class="porthole-frame"><span class="bracket tr"></span><span class="bracket bl"></span></div>
    <div class="bubble-layer" id="bubble-layer"></div>
    """

    spawn_positions = _infer_spawn_positions(game_log)
    room_width_guess = float(game_log.get("room_width", 20.0))
    room_height_guess = float(game_log.get("room_height", room_width_guess))
    if room_width_guess <= 0 or room_height_guess <= 0:
        all_positions = [(row["final_x"], row["final_y"]) for row in persona_rows if row["final_x"] is not None]
        inferred_extent = max([max(abs(x), abs(y)) for x, y in all_positions], default=20.0)
        room_width_guess = max(20.0, inferred_extent * 1.2)
        room_height_guess = room_width_guess

    events_payload = events
    personas_payload = [
        {"id": row["id"], "display_name": row["display_name"], "color": row["color"]} for row in persona_rows
    ]
    starting_stars = {row["id"]: initial_stars for row in persona_rows}
    nebula_uri = _resolve_asset_uri(
        "nebula_backdrop", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )
    floor_uri = _resolve_asset_uri(
        "room_floor", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )
    sprite_uri = _resolve_asset_uri(
        "persona_sprite", inline_assets=inline_assets, asset_rel_prefix=asset_rel_prefix
    )

    script = f"""
<script>
  var EVENTS = {_js(events_payload)};
  var PERSONAS = {_js(personas_payload)};
  var STARTING_STARS = {_js(starting_stars)};
  var INITIAL_ARENA_CARD_COUNTS = {_js(initial_arena_card_counts)};
  var SPAWN_POSITIONS = {_js(spawn_positions)};
  var CARD_TYPES = {_js(list(_CARD_TYPES_ORDER))};
  var ROOM_WIDTH = {_js(room_width_guess)};
  var ROOM_HEIGHT = {_js(room_height_guess)};
  var TOTAL_EVENTS = {_js(total_events)};
  var CARD_GLYPHS = {_js(_CARD_GLYPHS)};
  var EVENT_GLYPHS = {_js(_EVENT_GLYPHS)};
  var NEBULA_URI = {_js(nebula_uri)};
  var FLOOR_URI = {_js(floor_uri)};
  var SPRITE_URI = {_js(sprite_uri)};
  var SPRITE_FACE_OFFSET = Math.PI / 2;
  var currentEventCount = 0;

  var ANIM_DURATION_MS = 450;
  var BUBBLE_HOLD_MS = 1200;
  var WIN_EFFECT_MS = 900;
  var LOSE_EFFECT_MS = 700;
  var TIE_EFFECT_MS = 700;
  var STAR_TRANSFER_MS = 900;
  var PLAY_INTERVAL_MS = 650;

  var playing = false;
  var playTimer = null;
  var currentLogicalState = null;
  var gridCanvas = null;

  // Visual (animated) avatar positions, kept separate from the logical
  // per-tick target positions computeStateAtTick() returns, so movement
  // between ticks eases smoothly rather than snapping.
  var visualPos = {{}};
  var animFromPos = {{}};
  var animToPos = {{}};
  var animStartTime = 0;

  // Small per-persona idle-bob phase offset, seeded once so avatars don't
  // all bob perfectly in sync (which would look mechanical rather than
  // alive) - purely a rendering flourish, layered on top of the tick-to-tick
  // walking interpolation above, never affecting logical/room-space state.
  var bobPhase = {{}};

  var activeEffects = [];   // {{kind, pid, startTime, duration}}
  var particles = [];       // {{x, y, vx, vy, startTime, duration, color}}
  var duelBubbleEls = [];   // {{el, timer}} - overlays for the current tick's battles
  var speechBubbleEls = []; // {{el, pid, stackIdx, private}} - say/private chat bubbles

  function personaIndex(pid) {{
    return PERSONAS.findIndex(function(p) {{ return p.id === pid; }});
  }}

  function personaColor(pid) {{
    var p = PERSONAS[personaIndex(pid)];
    return p ? p.color : '#8a93b8';
  }}

  function personaName(pid) {{
    var p = PERSONAS.find(function(p) {{ return p.id === pid; }});
    return p ? p.display_name : pid;
  }}

  function applyEvent(e, state) {{
    if (e.type === 'move') {{
      state.positions[e.persona_id] = {{x: e.to_x, y: e.to_y}};
      var mdx = e.to_x - e.from_x;
      var mdy = e.to_y - e.from_y;
      if (Math.hypot(mdx, mdy) > 0.01) {{
        state.facing[e.persona_id] = {{x: mdx, y: mdy}};
      }}
    }} else if (e.type === 'battle_resolved') {{
      state.stars[e.persona_a] = e.stars_after[e.persona_a];
      state.stars[e.persona_b] = e.stars_after[e.persona_b];
      if (state.stars[e.persona_a] <= 0) state.eliminated[e.persona_a] = true;
      if (state.stars[e.persona_b] <= 0) state.eliminated[e.persona_b] = true;
    }}
  }}

  function freshReplayState() {{
    var stars = {{}};
    var eliminated = {{}};
    var positions = {{}};
    var facing = {{}};
    PERSONAS.forEach(function(p) {{
      stars[p.id] = STARTING_STARS[p.id];
      eliminated[p.id] = false;
      var spawn = SPAWN_POSITIONS[p.id];
      positions[p.id] = spawn
        ? {{x: spawn.x, y: spawn.y}}
        : {{x: ROOM_WIDTH / 2, y: ROOM_HEIGHT / 2}};
      facing[p.id] = {{x: 1, y: 0}};
    }});
    return {{stars: stars, eliminated: eliminated, positions: positions, facing: facing}};
  }}

  // Replay folds the first `count` events in order (0 = spawn layout only).
  function computeStateAfterEvents(count) {{
    var state = freshReplayState();
    for (var i = 0; i < count && i < EVENTS.length; i++) {{
      applyEvent(EVENTS[i], state);
    }}
    return state;
  }}

  function arenaCardCountsAfterEvents(count) {{
    var counts = {{
      Rock: INITIAL_ARENA_CARD_COUNTS.Rock || 0,
      Paper: INITIAL_ARENA_CARD_COUNTS.Paper || 0,
      Scissors: INITIAL_ARENA_CARD_COUNTS.Scissors || 0,
    }};
    for (var i = 0; i < count && i < EVENTS.length; i++) {{
      var e = EVENTS[i];
      if (e.type !== 'battle_resolved') continue;
      if (counts.hasOwnProperty(e.card_a) && counts[e.card_a] > 0) counts[e.card_a] -= 1;
      if (counts.hasOwnProperty(e.card_b) && counts[e.card_b] > 0) counts[e.card_b] -= 1;
    }}
    return counts;
  }}

  function currentMomentEvent() {{
    if (currentEventCount <= 0 || currentEventCount > EVENTS.length) return null;
    return EVENTS[currentEventCount - 1];
  }}

  function battleParticipantsAtMoment() {{
    var e = currentMomentEvent();
    if (!e || e.type !== 'battle_resolved') return {{}};
    var participants = {{}};
    participants[e.persona_a] = true;
    participants[e.persona_b] = true;
    return participants;
  }}

  function clearSpeechBubbles() {{
    speechBubbleEls.forEach(function(entry) {{
      if (entry.el && entry.el.parentNode) entry.el.parentNode.removeChild(entry.el);
    }});
    speechBubbleEls = [];
  }}

  function showSpeechBubblesForMoment(state) {{
    clearSpeechBubbles();
    var e = currentMomentEvent();
    if (!e || (e.type !== 'say' && e.type !== 'private_message_sent')) return;
    var layer = document.getElementById('bubble-layer');
    if (!layer) return;

    var pid = e.type === 'say' ? e.persona_id : e.sender_id;
    var isPrivate = e.type === 'private_message_sent';
    var el = document.createElement('div');
    el.className = 'speech-bubble' + (isPrivate ? ' private' : '');
    var who = document.createElement('div');
    who.className = 'bubble-who';
    if (isPrivate) {{
      who.textContent = '\\uD83D\\uDD12 ' + personaName(e.sender_id) + ' \\u2192 ' + personaName(e.target_id);
    }} else {{
      who.textContent = personaName(pid);
    }}
    var body = document.createElement('div');
    body.textContent = e.text || '';
    el.appendChild(who);
    el.appendChild(body);
    layer.appendChild(el);
    speechBubbleEls.push({{el: el, pid: pid, stackIdx: 0, private: isPrivate}});
    var canvas = document.getElementById('room-canvas');
    if (canvas) positionSpeechBubbles(canvas);
  }}

  function positionSpeechBubbles(canvas) {{
    var layer = document.getElementById('bubble-layer');
    if (!layer || !canvas) return;
    var state = currentLogicalState;
    speechBubbleEls.forEach(function(entry) {{
      var pos = visualPos[entry.pid];
      if (!pos && state) pos = state.positions[entry.pid];
      if (!pos) return;
      var pt = roomToCanvas(pos.x, pos.y, canvas);
      entry.el.style.left = (canvas.offsetLeft + pt[0]) + 'px';
      entry.el.style.top = (canvas.offsetTop + pt[1] - 22 - entry.stackIdx * 6) + 'px';
    }});
  }}

  // Full room art visible; positions map to the floor UV inside that art.
  var FLOOR_UV = {{ u0: 0.10, v0: 0.14, u1: 0.90, v1: 0.86 }};

  function roomArtRect(canvas) {{
    if (nebulaImgReady && nebulaImg.width > 0) {{
      var scale = Math.min(canvas.width / nebulaImg.width, canvas.height / nebulaImg.height);
      var dw = nebulaImg.width * scale;
      var dh = nebulaImg.height * scale;
      return {{
        x: (canvas.width - dw) / 2,
        y: (canvas.height - dh) / 2,
        w: dw,
        h: dh,
      }};
    }}
    var size = Math.min(canvas.width, canvas.height) * 0.88;
    return {{
      x: (canvas.width - size) / 2,
      y: (canvas.height - size) / 2,
      w: size,
      h: size,
    }};
  }}

  function playField(canvas) {{
    var art = roomArtRect(canvas);
    var fx = art.x + art.w * FLOOR_UV.u0;
    var fy = art.y + art.h * FLOOR_UV.v0;
    var fw = art.w * (FLOOR_UV.u1 - FLOOR_UV.u0);
    var fh = art.h * (FLOOR_UV.v1 - FLOOR_UV.v0);
    var size = Math.min(fw, fh);
    return {{
      size: size,
      offsetX: fx + (fw - size) / 2,
      offsetY: fy + (fh - size) / 2,
    }};
  }}

  function roomToCanvas(x, y, canvas) {{
    var field = playField(canvas);
    var inset = Math.max(8, field.size * 0.03);
    var usable = field.size - inset * 2;
    return [
      field.offsetX + inset + (x / ROOM_WIDTH) * usable,
      field.offsetY + inset + (y / ROOM_HEIGHT) * usable,
    ];
  }}

  function easeOutCubic(t) {{
    return 1 - Math.pow(1 - t, 3);
  }}

  var nebulaImg = null;
  var nebulaImgReady = false;
  if (NEBULA_URI) {{
    nebulaImg = new Image();
    nebulaImg.onload = function() {{ nebulaImgReady = true; gridCanvas = null; }};
    nebulaImg.src = NEBULA_URI;
  }}

  var spriteImg = null;
  var spriteImgReady = false;
  if (SPRITE_URI) {{
    spriteImg = new Image();
    spriteImg.onload = function() {{ spriteImgReady = true; }};
    spriteImg.src = SPRITE_URI;
  }}

  function facingAngle(dirX, dirY) {{
    if (dirX === 0 && dirY === 0) return SPRITE_FACE_OFFSET;
    return Math.atan2(dirY, dirX) + SPRITE_FACE_OFFSET;
  }}

  function drawSprite(ctx, px, py, size, dirX, dirY) {{
    if (!spriteImgReady) return false;
    ctx.save();
    ctx.translate(px, py);
    ctx.rotate(facingAngle(dirX, dirY));
    ctx.drawImage(spriteImg, -size / 2, -size / 2, size, size);
    ctx.restore();
    return true;
  }}

  function battleOpponentAtMoment(pid) {{
    var e = currentMomentEvent();
    if (!e || e.type !== 'battle_resolved') return null;
    if (e.persona_a === pid) return e.persona_b;
    if (e.persona_b === pid) return e.persona_a;
    return null;
  }}

  function facingForPersona(pid, state, now) {{
    var oppId = battleOpponentAtMoment(pid);
    if (oppId) {{
      var myPos = visualPos[pid] || state.positions[pid];
      var oppPos = visualPos[oppId] || state.positions[oppId];
      if (myPos && oppPos) {{
        return {{x: oppPos.x - myPos.x, y: oppPos.y - myPos.y}};
      }}
    }}
    var from = animFromPos[pid];
    var to = animToPos[pid];
    if (from && to) {{
      var t = ANIM_DURATION_MS > 0 ? Math.min(1, (now - animStartTime) / ANIM_DURATION_MS) : 1;
      if (t < 1) {{
        var dx = to.x - from.x;
        var dy = to.y - from.y;
        if (Math.hypot(dx, dy) > 0.01) return {{x: dx, y: dy}};
      }}
    }}
    var stored = state.facing && state.facing[pid];
    return stored || {{x: 0, y: 0}};
  }}

  // Void + full ship room (contain-fit). Avatars map onto the floor UV.
  function buildGridCanvas(canvas) {{
    var g = document.createElement('canvas');
    g.width = canvas.width;
    g.height = canvas.height;
    var gctx = g.getContext('2d');
    var grad = gctx.createRadialGradient(
      g.width / 2, g.height / 2, 0,
      g.width / 2, g.height / 2, Math.max(g.width, g.height) * 0.75
    );
    grad.addColorStop(0, '#0a0c14');
    grad.addColorStop(1, '#050609');
    gctx.fillStyle = grad;
    gctx.fillRect(0, 0, g.width, g.height);

    if (nebulaImgReady) {{
      var art = roomArtRect(canvas);
      gctx.drawImage(nebulaImg, art.x, art.y, art.w, art.h);
    }} else {{
      var neb = gctx.createRadialGradient(g.width * 0.22, g.height * 0.2, 0, g.width * 0.22, g.height * 0.2, Math.max(g.width, g.height) * 0.55);
      neb.addColorStop(0, 'rgba(167, 139, 250, 0.07)');
      neb.addColorStop(1, 'rgba(167, 139, 250, 0)');
      gctx.fillStyle = neb;
      gctx.fillRect(0, 0, g.width, g.height);
    }}
    return g;
  }}

  // Design resolution is fixed; CSS scales the whole frame to the browser.
  var DESIGN_W = 1280;
  var DESIGN_H = 720;

  function fitUiScale() {{
    var sw = window.innerWidth || DESIGN_W;
    var sh = window.innerHeight || DESIGN_H;
    var scale = Math.min(sw / DESIGN_W, sh / DESIGN_H);
    scale = Math.max(0.35, scale);
    document.documentElement.style.setProperty('--ui-scale', String(scale));
  }}

  function resizeCanvas() {{
    var canvas = document.getElementById('room-canvas');
    if (!canvas) return;
    if (canvas.width === DESIGN_W && canvas.height === DESIGN_H && gridCanvas) return;
    canvas.width = DESIGN_W;
    canvas.height = DESIGN_H;
    gridCanvas = buildGridCanvas(canvas);
  }}

  function spawnStarTransfer(fromPos, toPos, canvas) {{
    var ptA = roomToCanvas(fromPos.x, fromPos.y, canvas);
    var ptB = roomToCanvas(toPos.x, toPos.y, canvas);
    activeEffects.push({{
      kind: 'star_transfer',
      fromX: ptA[0],
      fromY: ptA[1],
      toX: ptB[0],
      toY: ptB[1],
      startTime: performance.now(),
      duration: STAR_TRANSFER_MS,
    }});
  }}

  function drawStarTransfers(ctx, now) {{
    activeEffects.forEach(function(fx) {{
      if (fx.kind !== 'star_transfer') return;
      var t = Math.min(1, (now - fx.startTime) / fx.duration);
      if (t >= 1) return;
      var eased = easeOutCubic(t);
      var x = fx.fromX + (fx.toX - fx.fromX) * eased;
      var y = fx.fromY + (fx.toY - fx.fromY) * eased - Math.sin(t * Math.PI) * 22;
      ctx.save();
      ctx.font = 'bold 20px serif';
      ctx.shadowBlur = 14 * (1 - t * 0.4);
      ctx.shadowColor = '#ffc98a';
      ctx.fillStyle = '#ffc98a';
      ctx.fillText('\\u2B50', x - 10, y + 7);
      ctx.restore();
    }});
  }}

  function spawnParticles(pt, color) {{
    var count = 8;
    for (var i = 0; i < count; i++) {{
      var angle = (Math.PI * 2 * i) / count + Math.random() * 0.4;
      var speed = 1.0 + Math.random() * 1.1;
      particles.push({{
        x: pt[0],
        y: pt[1],
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        startTime: performance.now(),
        duration: 650,
        color: color,
      }});
    }}
  }}

  function drawParticles(ctx, now) {{
    particles = particles.filter(function(pa) {{ return (now - pa.startTime) < pa.duration; }});
    particles.forEach(function(pa) {{
      var t = (now - pa.startTime) / pa.duration;
      var x = pa.x + pa.vx * t * 22;
      var y = pa.y + pa.vy * t * 22;
      ctx.beginPath();
      ctx.globalAlpha = Math.max(0, 1 - t);
      ctx.fillStyle = pa.color;
      ctx.arc(x, y, 2.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }});
  }}

  // Tracks which personas currently have a visible duel bubble hovering
  // above them, so their name-label pill can be nudged aside instead of
  // ever sitting fully underneath the (deliberately opaque) bubble.
  var bubbleCoveredPids = {{}};

  function drawAvatars(ctx, canvas, now) {{
    var state = currentLogicalState;
    if (!state) return;

    var battlePulse = 0.5 + 0.5 * Math.sin(now / 220);
    var battle = currentMomentEvent();
    if (battle && battle.type === 'battle_resolved') {{
      var posA = visualPos[battle.persona_a] || state.positions[battle.persona_a];
      var posB = visualPos[battle.persona_b] || state.positions[battle.persona_b];
      if (posA && posB) {{
        var ptA = roomToCanvas(posA.x, posA.y, canvas);
        var ptB = roomToCanvas(posB.x, posB.y, canvas);
        ctx.save();
        ctx.strokeStyle = 'rgba(255, 169, 77, ' + (0.35 + battlePulse * 0.45) + ')';
        ctx.lineWidth = 2.5;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(ptA[0], ptA[1]);
        ctx.lineTo(ptB[0], ptB[1]);
        ctx.stroke();
        ctx.setLineDash([]);
        var linkR = Math.max(20, Math.min(34, canvas.width * 0.026)) * 0.5 + 6 + battlePulse * 4;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(ptA[0], ptA[1], linkR, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(ptB[0], ptB[1], linkR, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }}
    }}

    // Pass 1: pilot-chip tokens (ring + badge + glow + idle bob) and
    // elimination glyph, plus collect label geometry so overlapping labels
    // (personas standing close together, common near mid-room) can be
    // nudged apart before any text is drawn - drawing text per-persona
    // inline (as the previous renderer did) let labels stack illegibly on
    // top of each other whenever two avatars were within a few room-units.
    var labels = [];
    PERSONAS.forEach(function(p) {{
      var pos = visualPos[p.id] || state.positions[p.id];
      if (!pos) return;
      var pt = roomToCanvas(pos.x, pos.y, canvas);

      // Ambient idle motion: a gentle 2-3px vertical bob, distinct from
      // (and layered on top of) the tick-to-tick walking interpolation, so
      // the scene feels alive even while nobody is actively moving.
      var phase = bobPhase[p.id] || 0;
      var bob = Math.sin(now / 900 + phase) * 2.5;
      pt = [pt[0], pt[1] + bob];

      var eliminated = !!state.eliminated[p.id];
      var color = eliminated ? '#4a5170' : personaColor(p.id);
      var radius = 9;
      var spriteSize = Math.max(20, Math.min(34, canvas.width * 0.026));

      var effect = activeEffects.find(function(fx) {{
        return fx.pid === p.id && (now - fx.startTime) < fx.duration;
      }});

      ctx.save();
      if (effect) {{
        var progress = Math.min(1, (now - effect.startTime) / effect.duration);
        if (effect.kind === 'win') {{
          var ringR = (spriteImgReady ? spriteSize * 0.5 : 9) + progress * 18;
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(94, 255, 157, ' + (1 - progress) + ')';
          ctx.lineWidth = 2;
          ctx.arc(pt[0], pt[1], ringR, 0, Math.PI * 2);
          ctx.stroke();
          ctx.shadowBlur = 20 * (1 - progress);
          ctx.shadowColor = '#5eff9d';
        }} else if (effect.kind === 'lose') {{
          var shrink = 1 - 0.35 * Math.sin(progress * Math.PI);
          radius = 9 * shrink;
          spriteSize = spriteSize * shrink;
          color = '#ff5468';
          ctx.shadowBlur = 16 * (1 - progress);
          ctx.shadowColor = '#ff5468';
        }} else if (effect.kind === 'tie') {{
          var pulse = 1 + 0.25 * Math.sin(progress * Math.PI);
          radius = 9 * pulse;
          spriteSize = spriteSize * pulse;
          color = '#4dd8e8';
          ctx.shadowBlur = 12 * (1 - progress);
          ctx.shadowColor = '#4dd8e8';
        }}
      }} else {{
        // Baseline resting glow so every token reads as a lit instrument
        // marker rather than a flat dot, even with no active effect.
        ctx.shadowBlur = 7;
        ctx.shadowColor = color;
      }}

      var drewSprite = false;
      if (spriteImgReady) {{
        if (eliminated) ctx.globalAlpha = 0.4;
        var face = facingForPersona(p.id, state, now);
        drewSprite = drawSprite(ctx, pt[0], pt[1], spriteSize, face.x, face.y);
        ctx.globalAlpha = 1;
      }}
      if (!drewSprite) {{
        ctx.beginPath();
        ctx.fillStyle = color;
        ctx.arc(pt[0], pt[1], radius, 0, Math.PI * 2);
        ctx.fill();
      }}
      ctx.restore();

      // Identity-colored ring so each persona stays distinguishable by
      // color at a glance even though every token now shares the same
      // sprite art - the label pill (drawn in pass 2) reinforces this with
      // the same color, so color remains the "who is this" cue.
      var ringR = drewSprite ? spriteSize * 0.5 + 2 : radius + 1.6;
      ctx.beginPath();
      ctx.strokeStyle = eliminated ? 'rgba(74, 81, 112, 0.9)' : color;
      ctx.lineWidth = drewSprite ? 2 : 1.4;
      ctx.arc(pt[0], pt[1], ringR, 0, Math.PI * 2);
      ctx.stroke();

      if (eliminated) {{
        var xR = drewSprite ? spriteSize * 0.5 : radius;
        ctx.fillStyle = '#050609';
        ctx.beginPath();
        ctx.arc(pt[0], pt[1] + xR + 8, 8, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(5, 6, 9, 0.85)';
        ctx.fill();
        ctx.fillStyle = '#ff5468';
        ctx.font = 'bold 10px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('\\u00d7', pt[0], pt[1] + xR + 8.5);
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
      }}

      // Prefer short first names above the token so clusters fan cleaner.
      var short = (p.display_name || p.id || '').split(' ')[0];
      var text = short + ' \\u2605' + state.stars[p.id];
      var covered = !!bubbleCoveredPids[p.id];
      labels.push({{
        cx: pt[0],
        cy: pt[1],
        x: pt[0],
        y: pt[1] - (drewSprite ? spriteSize * 0.55 : 16),
        text: text,
        color: eliminated ? '#5b6488' : '#0a0c14',
        bg: eliminated ? 'rgba(74, 81, 112, 0.35)' : personaColor(p.id),
        width: ctx.measureText(text).width || text.length * 6.4,
        hidden: covered,
      }});
    }});

    // Cluster-aware label layout: names above sprites; fan pairs; side-stack
    // groups of 3+ so four-person piles stay readable.
    var lineHeight = 17;
    var assigned = {{}};
    for (var i = 0; i < labels.length; i++) {{
      if (labels[i].hidden || assigned[i]) continue;
      var members = [i];
      for (var j = i + 1; j < labels.length; j++) {{
        if (labels[j].hidden || assigned[j]) continue;
        if (Math.hypot(labels[j].cx - labels[i].cx, labels[j].cy - labels[i].cy) < 42) {{
          members.push(j);
        }}
      }}
      var n = members.length;
      // Centroid of the cluster (for stems / side stack).
      var cxSum = 0, cySum = 0;
      members.forEach(function(mi) {{ cxSum += labels[mi].cx; cySum += labels[mi].cy; }});
      var cCx = cxSum / n, cCy = cySum / n;
      members.forEach(function(mi, k) {{
        assigned[mi] = true;
        labels[mi].stem = false;
        if (n === 1) {{
          labels[mi].x = labels[mi].cx - labels[mi].width / 2;
          return;
        }}
        if (n === 2) {{
          var side = (k === 0) ? -1 : 1;
          labels[mi].x = labels[mi].cx + side * 18 - labels[mi].width / 2;
          labels[mi].y = labels[mi].cy - 22;
          labels[mi].stem = true;
          return;
        }}
        // 3+: vertical stack to the right of the pile with leader stems.
        var stackX = cCx + 36;
        // Prefer right; flip left if near right edge of canvas.
        if (stackX + labels[mi].width > canvas.width - 8) stackX = cCx - 36 - labels[mi].width;
        labels[mi].x = stackX;
        labels[mi].y = cCy - ((n - 1) * lineHeight) / 2 + k * lineHeight;
        labels[mi].stem = true;
      }});
    }}
    for (var pass = 0; pass < 6; pass++) {{
      for (var i2 = 0; i2 < labels.length; i2++) {{
        for (var j2 = 0; j2 < i2; j2++) {{
          var a = labels[i2];
          var b = labels[j2];
          if (a.hidden || b.hidden) continue;
          var xOverlap = Math.abs((a.x + a.width / 2) - (b.x + b.width / 2)) < (a.width + b.width) / 2 + 6;
          if (xOverlap && Math.abs(a.y - b.y) < lineHeight) {{
            a.y = b.y + lineHeight;
          }}
        }}
      }}
    }}

    ctx.font = 'bold 10.5px monospace';
    labels.forEach(function(lbl) {{
      if (lbl.hidden) return;
      var padX = 5;
      var pillH = 15;
      // Thin stem from token toward the label when fanned/stacked.
      if (lbl.stem) {{
        var lx = lbl.x + lbl.width / 2;
        var ly = lbl.y - pillH / 2 + 4;
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(223, 230, 245, 0.28)';
        ctx.lineWidth = 1;
        ctx.moveTo(lbl.cx, lbl.cy - 10);
        ctx.lineTo(lx, ly + pillH / 2);
        ctx.stroke();
      }}
      ctx.fillStyle = lbl.bg;
      ctx.beginPath();
      if (ctx.roundRect) {{
        ctx.roundRect(lbl.x - padX, lbl.y - pillH + 3, lbl.width + padX * 2, pillH, 7);
      }} else {{
        ctx.rect(lbl.x - padX, lbl.y - pillH + 3, lbl.width + padX * 2, pillH);
      }}
      ctx.fill();
      ctx.fillStyle = lbl.color;
      ctx.fillText(lbl.text, lbl.x, lbl.y);
    }});
  }}

  function stepAnimation(now) {{
    var t = ANIM_DURATION_MS > 0 ? Math.min(1, (now - animStartTime) / ANIM_DURATION_MS) : 1;
    var eased = easeOutCubic(t);
    PERSONAS.forEach(function(p) {{
      var from = animFromPos[p.id];
      var to = animToPos[p.id];
      if (from && to) {{
        visualPos[p.id] = {{
          x: from.x + (to.x - from.x) * eased,
          y: from.y + (to.y - from.y) * eased,
        }};
      }}
    }});
  }}

  function drawFrame(now) {{
    activeEffects = activeEffects.filter(function(fx) {{ return (now - fx.startTime) < fx.duration; }});
    resizeCanvas();
    stepAnimation(now);
    var canvas = document.getElementById('room-canvas');
    if (canvas) {{
      var ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (gridCanvas) ctx.drawImage(gridCanvas, 0, 0);
      drawAvatars(ctx, canvas, now);
      drawStarTransfers(ctx, now);
      drawParticles(ctx, now);
      positionSpeechBubbles(canvas);
    }}
    requestAnimationFrame(drawFrame);
  }}

  function renderArenaCards(count) {{
    var counts = arenaCardCountsAfterEvents(count);
    CARD_TYPES.forEach(function(cardType) {{
      var el = document.getElementById('arena-count-' + cardType);
      if (el) el.textContent = String(counts[cardType] || 0);
    }});
  }}

  function renderRoster(state) {{
    var inBattle = battleParticipantsAtMoment();
    PERSONAS.forEach(function(p) {{
      var row = document.getElementById('roster-' + p.id);
      var starsEl = document.getElementById('stars-' + p.id);
      var eliminated = !!state.eliminated[p.id];
      var stars = state.stars[p.id] || 0;
      if (row) {{
        row.classList.toggle('eliminated', eliminated);
        row.classList.toggle('in-battle', !!inBattle[p.id]);
      }}
      if (starsEl) starsEl.textContent = '\\u2b50' + stars;
    }});
  }}

  function isEmptySpeech(text) {{
    var t = (text === null || text === undefined) ? '' : String(text).trim();
    return !t || t === '.' || t === '..' || t === '...' || t === '....' || t === '\\u2026';
  }}

  function cleanSpeech(text) {{
    if (isEmptySpeech(text)) return '';
    var t = String(text).trim();
    if (t.length > 80) return t.slice(0, 77) + '…';
    return t;
  }}

  function describeEvent(e) {{
    var glyph = EVENT_GLYPHS[e.type] || '\\u2022';
    switch (e.type) {{
      case 'say': {{
        var speech = cleanSpeech(e.text);
        if (!speech) return null;  // hide empty mock chatter
        return glyph + ' ' + personaName(e.persona_id) + ': "' + speech + '"';
      }}
      case 'wait':
        return glyph + ' ' + personaName(e.persona_id) + ' waits.';
      case 'move':
        return glyph + ' ' + personaName(e.persona_id) + ' moves to (' + e.to_x.toFixed(1) + ', ' + e.to_y.toFixed(1) + ')';
      case 'challenge_issued':
        return glyph + ' ' + personaName(e.challenger_id) + ' challenges ' + personaName(e.target_id) + '!';
      case 'challenge_accepted':
        return glyph + ' ' + personaName(e.responder_id) + ' accepts ' + personaName(e.challenger_id) + '\\'s challenge.';
      case 'challenge_declined':
        return glyph + ' ' + personaName(e.responder_id) + ' declines ' + personaName(e.challenger_id) + '\\'s challenge.';
      case 'challenge_auto_declined_no_cards':
        return glyph + ' ' + personaName(e.challenger_id) + '\\'s challenge on ' + personaName(e.target_id) + ' auto-declined (no cards).';
      case 'battle_resolved':
        var outcome = e.winner_id ? (personaName(e.winner_id) + ' wins') : 'tie';
        var glyphA = CARD_GLYPHS[e.card_a] || '';
        var glyphB = CARD_GLYPHS[e.card_b] || '';
        return personaName(e.persona_a) + ' (' + glyphA + ') vs ' +
          personaName(e.persona_b) + ' (' + glyphB + ') -> ' + outcome;
      case 'private_message_sent': {{
        var pm = cleanSpeech(e.text);
        if (!pm) return null;
        return glyph + ' [private] ' + personaName(e.sender_id) + ' \\u2192 ' + personaName(e.target_id) + ': "' + pm + '"';
      }}
      case 'system':
        return glyph + ' [system] ' + e.message;
      default:
        return '[' + e.type + ']';
    }}
  }}

  function renderTicker(eventCount) {{
    var ticker = document.getElementById('event-ticker');
    if (!ticker) return;
    ticker.innerHTML = '';
    var firstCurrent = null;
    EVENTS.forEach(function(e, idx) {{
      var line = describeEvent(e);
      if (!line) return;  // skip empty speech clutter
      var li = document.createElement('li');
      var classes = [];
      if (idx >= eventCount) classes.push('future');
      if (e.type === 'battle_resolved') classes.push('is-battle');
      if (idx === eventCount - 1 && eventCount > 0) classes.push('current');
      li.className = classes.join(' ');
      var seq = (e.seq !== undefined && e.seq !== null) ? e.seq : idx;
      li.innerHTML = '<span class="tick-label">[#' + seq + ']</span> ' + line;
      ticker.appendChild(li);
      if (idx === eventCount - 1 && eventCount > 0 && !firstCurrent) firstCurrent = li;
    }});
    if (firstCurrent) {{
      firstCurrent.scrollIntoView({{block: 'center'}});
    }}
  }}

  function clearDuelBubbles() {{
    duelBubbleEls.forEach(function(entry) {{
      if (entry.timer) clearTimeout(entry.timer);
      if (entry.el && entry.el.parentNode) entry.el.parentNode.removeChild(entry.el);
    }});
    duelBubbleEls = [];
    bubbleCoveredPids = {{}};
  }}

  // Fixed horizontal offset applied to each subsequent simultaneous-tick
  // bubble so multiple battle_resolved events landing on the same tick fan
  // out left-to-right instead of stacking directly on top of one another
  // (the prior renderer only offset bubbles vertically by their midpoint,
  // which frequently still overlapped and covered persona name labels when
  // the battling pairs were near each other in room-space).
  var BUBBLE_STAGGER_X = 110;

  function showDuelBubbleForMoment(state) {{
    clearDuelBubbles();
    var e = currentMomentEvent();
    var container = document.querySelector('.viewscreen');
    var canvas = document.getElementById('room-canvas');
    if (!e || e.type !== 'battle_resolved' || !container || !canvas) return;

    bubbleCoveredPids[e.persona_a] = true;
    bubbleCoveredPids[e.persona_b] = true;

    var posA = state.positions[e.persona_a];
    var posB = state.positions[e.persona_b];
    if (!posA || !posB) return;
    var ptA = roomToCanvas(posA.x, posA.y, canvas);
    var ptB = roomToCanvas(posB.x, posB.y, canvas);
    var midX = (ptA[0] + ptB[0]) / 2;
    var midY = (ptA[1] + ptB[1]) / 2 - 34;

    var el = document.createElement('div');
    el.className = 'duel-bubble';
    var cardAGlyph = CARD_GLYPHS[e.card_a] || e.card_a;
    var cardBGlyph = CARD_GLYPHS[e.card_b] || e.card_b;
    el.innerHTML = cardAGlyph + ' vs ' + cardBGlyph;
    el.style.left = canvas.offsetLeft + midX + 'px';
    el.style.top = canvas.offsetTop + midY + 'px';
    container.appendChild(el);
    requestAnimationFrame(function() {{ el.classList.add('showing'); }});

    var timer = null;
    if (playing) {{
      timer = setTimeout(function() {{
        el.classList.remove('showing');
        setTimeout(function() {{
          if (el.parentNode) el.parentNode.removeChild(el);
        }}, 300);
      }}, BUBBLE_HOLD_MS);
    }}
    duelBubbleEls.push({{el: el, timer: timer}});

    var now = performance.now();
    var winner = e.winner_id;
    if (winner) {{
      var loserId = winner === e.persona_a ? e.persona_b : e.persona_a;
      activeEffects.push({{kind: 'win', pid: winner, startTime: now, duration: WIN_EFFECT_MS}});
      activeEffects.push({{kind: 'lose', pid: loserId, startTime: now, duration: LOSE_EFFECT_MS}});
      var winnerPos = state.positions[winner];
      var loserPos = state.positions[loserId];
      if (winnerPos) spawnParticles(roomToCanvas(winnerPos.x, winnerPos.y, canvas), '#5eff9d');
      if (loserPos && winnerPos) spawnStarTransfer(loserPos, winnerPos, canvas);
    }} else {{
      activeEffects.push({{kind: 'tie', pid: e.persona_a, startTime: now, duration: TIE_EFFECT_MS}});
      activeEffects.push({{kind: 'tie', pid: e.persona_b, startTime: now, duration: TIE_EFFECT_MS}});
    }}
  }}

  function renderEventCount(count) {{
    var slider = document.getElementById('event-slider');
    var display = document.getElementById('event-display');
    var briefingEvent = document.getElementById('briefing-event');
    if (slider) slider.value = count;
    if (display) display.textContent = 'Moment ' + count + ' / ' + TOTAL_EVENTS;
    if (briefingEvent) briefingEvent.textContent = String(count);

    currentEventCount = count;
    var state = computeStateAfterEvents(count);
    currentLogicalState = state;

    PERSONAS.forEach(function(p) {{
      var from = visualPos[p.id] || state.positions[p.id];
      animFromPos[p.id] = {{x: from.x, y: from.y}};
      animToPos[p.id] = {{x: state.positions[p.id].x, y: state.positions[p.id].y}};
    }});
    animStartTime = performance.now();

    renderRoster(state);
    renderArenaCards(count);
    renderTicker(count);
    showSpeechBubblesForMoment(state);
    showDuelBubbleForMoment(state);
  }}

  function togglePlay() {{
    var btn = document.getElementById('play-btn');
    if (playing) {{
      playing = false;
      if (playTimer) {{ clearInterval(playTimer); playTimer = null; }}
      if (btn) btn.textContent = 'Play';
      return;
    }}
    playing = true;
    if (btn) btn.textContent = 'Pause';
    playTimer = setInterval(function() {{
      var slider = document.getElementById('event-slider');
      var next = parseInt(slider.value, 10) + 1;
      if (next > TOTAL_EVENTS) {{
        togglePlay();
        return;
      }}
      renderEventCount(next);
    }}, PLAY_INTERVAL_MS);
  }}

  document.addEventListener('DOMContentLoaded', function() {{
    PERSONAS.forEach(function(p, idx) {{ bobPhase[p.id] = idx * 1.7; }});
    fitUiScale();
    resizeCanvas();
    window.addEventListener('resize', function() {{
      fitUiScale();
      gridCanvas = null;
      resizeCanvas();
    }});
    renderEventCount(0);
    requestAnimationFrame(drawFrame);
  }});
</script>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
<title>Starclash Replay - {_esc(room_name)}</title>
<style>{_SPECTATOR_STYLE}</style>
</head>
<body>
<div class="scale-stage" id="scale-stage">
  <div class="design-frame" id="design-frame">
    <div class="viewscreen">
{viewscreen_chrome_html}
{briefing_html}
{arena_cards_html}
{roster_html}
{comms_html}
{playback_html}
    </div>
  </div>
</div>
{script}
</body>
</html>
"""


def _environment_mirror_scripts_dir(script_dir: str) -> Optional[str]:
    """Map application/tasks/<task>/scripts to environment/.../application/<task>/scripts."""
    norm = os.path.normpath(script_dir)
    parts = norm.split(os.sep)
    try:
        tasks_idx = parts.index("tasks")
        app_idx = parts.index("application")
    except ValueError:
        return None
    if tasks_idx + 2 >= len(parts) or parts[tasks_idx + 2] != "scripts":
        return None
    task_name = parts[tasks_idx + 1]
    root = os.sep.join(parts[:app_idx])
    return os.path.join(root, "environment", "task-environments", "application", task_name, "scripts")


def _sync_sample_output_mirror(sample_dir: str) -> None:
    """Mirror generated previews into the task-environment copy (Live Server path)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_scripts = _environment_mirror_scripts_dir(script_dir)
    if not env_scripts or not os.path.isdir(env_scripts):
        return
    dst = os.path.join(env_scripts, "_sample_output")
    os.makedirs(dst, exist_ok=True)
    import shutil

    for name in os.listdir(sample_dir):
        src_path = os.path.join(sample_dir, name)
        dst_path = os.path.join(dst, name)
        if os.path.isdir(src_path):
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
    print(f"[OK] Mirrored previews to {dst}")


def _run_arena_sample(out_dir: str, seed: int, max_ticks: int) -> None:
    import subprocess
    import sys

    script_dir = os.path.dirname(os.path.abspath(__file__))
    map_path = os.path.join(script_dir, "..", "input", "ship_map.yaml")
    crew_path = os.path.join(script_dir, "..", "input", "crew_manifest.yaml")
    subprocess.run(
        [
            sys.executable,
            os.path.join(script_dir, "run_arena.py"),
            "--map",
            map_path,
            "--crew",
            crew_path,
            "--brain",
            "mock",
            "--seed",
            str(seed),
            "--max-ticks",
            str(max_ticks),
            "--out",
            out_dir,
        ],
        check=True,
    )


def _make_preview_engine(game_log: dict):
    """Shared engine scaffold for sample preview HTML (free / battle / challenge)."""
    import brains
    import observations
    from engine import ArenaEngine, PersonaState

    hand_size = int(game_log.get("hand_size", 4))
    persona_states = [
        PersonaState(
            id=p["id"],
            display_name=p.get("display_name", p["id"]),
            traits={"dimensions": p.get("traits_summary", {})},
            stars=3,
            hand=[],
        )
        for p in game_log["personas"]
    ]
    engine = ArenaEngine(
        personas=persona_states,
        room_name=game_log.get("room_name", "Main Chat Room"),
        max_ticks=game_log.get("max_ticks", 10),
        seed=game_log.get("seed", 42),
        hand_size=hand_size,
        observation_builder=observations.build_observation,
        room_width=float(game_log.get("room_width", 20.0)),
        room_height=float(game_log.get("room_height", 20.0)),
        proximity_radius=3.0,
        max_move_distance=2.0,
    )
    # Ensure everyone has a hand for battle previews.
    for p in engine.personas.values():
        if not p.hand:
            p.hand = (["Rock", "Paper", "Scissors", "Rock"])[:hand_size]
    mock_brain = brains.MockArenaBrain(seed=game_log.get("seed", 42))
    for _ in range(min(4, game_log.get("max_ticks", 10))):
        engine.run_tick(lambda persona, obs: mock_brain.decide(obs))
    return engine


def _build_preview_observation(game_log: dict) -> dict:
    """Rebuild a rich sub-step-3 (free action) observation for preview HTML."""
    import observations
    from engine import PersonaLifeState

    engine = _make_preview_engine(game_log)
    ego = engine.personas[engine.persona_order[0]]
    ego.state = PersonaLifeState.FREE
    return observations.build_observation(engine, ego, sub_step=3)


def _build_battle_preview_observation(game_log: dict) -> dict:
    """Force a sub-step-1 duel observation so battle UI previews stay current."""
    import observations
    from engine import PersonaLifeState

    engine = _make_preview_engine(game_log)
    order = engine.persona_order
    a = engine.personas[order[0]]
    b = engine.personas[order[1] if len(order) > 1 else order[0]]
    a.x, a.y = 10.0, 10.0
    b.x, b.y = 10.6, 10.3
    a.state = PersonaLifeState.BATTLE_CARD_PENDING
    b.state = PersonaLifeState.BATTLE_CARD_PENDING
    a.pending_partner_id = b.id
    b.pending_partner_id = a.id
    if not a.hand:
        a.hand = ["Rock", "Scissors", "Paper", "Paper"]
    return observations.build_observation(engine, a, sub_step=1)


def _build_challenge_preview_observation(game_log: dict) -> dict:
    """Force a sub-step-2 incoming-challenge observation for preview HTML."""
    import observations
    from engine import PersonaLifeState

    engine = _make_preview_engine(game_log)
    order = engine.persona_order
    a = engine.personas[order[0]]
    b = engine.personas[order[1] if len(order) > 1 else order[0]]
    a.x, a.y = 10.0, 10.0
    b.x, b.y = 10.5, 10.2
    a.state = PersonaLifeState.PENDING_CHALLENGE
    b.state = PersonaLifeState.AWAITING_RESPONSE
    a.pending_partner_id = b.id
    b.pending_partner_id = a.id
    return observations.build_observation(engine, a, sub_step=2)


def _write_preview_html(path: str, html: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Wrote {path} ({len(html)} bytes)")


if __name__ == "__main__":
    import sys

    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _SCRIPT_DIR)

    _SAMPLE_DIR = os.path.join(_SCRIPT_DIR, "_sample_output")
    _DEMO_DIR = os.path.join(_SCRIPT_DIR, "_sample_output", "demo")
    os.makedirs(_SAMPLE_DIR, exist_ok=True)
    os.makedirs(_DEMO_DIR, exist_ok=True)

    _GAME_LOG_PATH = os.path.join(_SAMPLE_DIR, "game_log.json")
    _quick = "--quick" in sys.argv
    if not _quick or not os.path.isfile(_GAME_LOG_PATH):
        print("[INFO] Generating short sample game (10 ticks) ...")
        _run_arena_sample(_SAMPLE_DIR, seed=42, max_ticks=10)
        if not _quick:
            print("[INFO] Generating long demo game (40 ticks) ...")
            _run_arena_sample(_DEMO_DIR, seed=77, max_ticks=40)

    with open(_GAME_LOG_PATH, "r", encoding="utf-8") as f:
        _game_log = json.load(f)

    _demo_log_path = os.path.join(_DEMO_DIR, "game_log.json")
    if os.path.isfile(_demo_log_path):
        with open(_demo_log_path, "r", encoding="utf-8") as f:
            _demo_log = json.load(f)
    else:
        _demo_log = _game_log

    # Inline assets so file:// previews never break on missing relative paths.
    _free_obs = _build_preview_observation(_game_log)
    _battle_obs = _build_battle_preview_observation(_game_log)
    _challenge_obs = _build_challenge_preview_observation(_game_log)

    _write_preview_html(
        os.path.join(_SAMPLE_DIR, "observation_preview.html"),
        render_observation_html(_free_obs, inline_assets=True),
    )
    _write_preview_html(
        os.path.join(_SAMPLE_DIR, "observation_battle_preview.html"),
        render_observation_html(_battle_obs, inline_assets=True),
    )
    _write_preview_html(
        os.path.join(_SAMPLE_DIR, "observation_challenge_preview.html"),
        render_observation_html(_challenge_obs, inline_assets=True),
    )

    _sample_assets = _sync_preview_assets(_SAMPLE_DIR)
    _spectator_html = render_spectator_html(
        _game_log, inline_assets=False, asset_rel_prefix=_sample_assets
    )
    _write_preview_html(
        os.path.join(_SAMPLE_DIR, "spectator_preview.html"), _spectator_html
    )

    _demo_assets = _sync_preview_assets(_DEMO_DIR)
    _demo_html = render_spectator_html(
        _demo_log, inline_assets=False, asset_rel_prefix=_demo_assets
    )
    _write_preview_html(
        os.path.join(_DEMO_DIR, "spectator_preview.html"), _demo_html
    )
    print(
        f"[OK] Demo spectator ready ({_demo_log.get('max_ticks')} ticks)"
    )

    _sync_sample_output_mirror(_SAMPLE_DIR)
