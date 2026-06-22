import { useEffect, useRef } from 'react'
import { useWorldStore } from '../store/worldStore'
import type { SimEvent } from '../types/simulation'

const EVENT_META: Record<string, { color: string; label: string; icon: string }> = {
  AGENT_DIED:                    { color: '#ef4444', label: 'DIED',       icon: '†' },
  TRADE_COMPLETED:               { color: '#f59e0b', label: 'TRADE',      icon: '⇄' },
  ATTACK:                        { color: '#c47b73', label: 'ATTACK',     icon: '⚔' },
  CACHE_SCAVENGED:               { color: '#c79a64', label: 'SCAVENGE',   icon: '⛏' },
  BROADCAST_SENT:                { color: '#60a5fa', label: 'BROADCAST',  icon: '◉' },
  WHISPER_SENT:                  { color: '#a78bfa', label: 'WHISPER',    icon: '◎' },
  REFLECTION_WRITTEN:            { color: '#818cf8', label: 'REFLECTION', icon: '∫' },
  ACTION_REJECTED:               { color: '#e76325', label: 'REJECTED',   icon: '⚡' },
  STORM_STARTED:                 { color: '#fb923c', label: 'STORM',      icon: '◈' },
  STORM_ENDED:                   { color: '#4a6478', label: 'CALM',       icon: '◇' },
  HEAT_ZONE_DAMAGE:              { color: '#ef4444', label: 'HEAT DMG',   icon: '▲' },
  SIPHON_DISTRIBUTED:            { color: '#0db8b1', label: 'SIPHON',     icon: '⬡' },
}

function EventRow({ ev }: { ev: SimEvent }) {
  const meta  = EVENT_META[ev.event_type]
  const color = meta?.color ?? '#4a6478'
  const icon  = meta?.icon  ?? '·'
  const label = meta?.label ?? ev.event_type.replace(/_/g, ' ')
  const msg   = ev.message ? String(ev.message).slice(0, 50) : null

  return (
    <div className="mv-event-row" style={{ borderLeftColor: color }}>
      <div className="mv-event-top">
        <span className="mv-event-tick">
          {ev.tick != null ? `T${ev.tick}` : ''}
        </span>
        <span className="mv-event-icon" style={{ color }}>{icon}</span>
        <span className="mv-event-label" style={{ color }}>
          {label}
        </span>
        {ev.agent_id && (
          <span className="mv-event-agent">
            · {ev.agent_id}
          </span>
        )}
      </div>
      {msg && (
        <div className="mv-event-message">
          "{msg}"
        </div>
      )}
    </div>
  )
}

export function EventFeed() {
  const events    = useWorldStore(s => s.events.slice(-60))
  const scrollRef = useRef<HTMLDivElement>(null)

  // Keep the feed pinned to its newest entry by scrolling ONLY this container.
  // (Using scrollIntoView here would scroll the whole page down to the sim —
  // which is what caused the page to auto-jump to the prototype on load.)
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [events.length])

  return (
    <div className="mv-event-feed">
      <div className="mv-list-head mv-event-head">
        Event Log
      </div>
      <div className="mv-event-scroll" ref={scrollRef}>
        {events.length === 0 && (
          <div className="mv-list-empty">
            awaiting events...
          </div>
        )}
        {events.map((e, i) => <EventRow key={i} ev={e} />)}
      </div>
    </div>
  )
}
