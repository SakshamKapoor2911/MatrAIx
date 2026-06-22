import { useWorldStore } from '../store/worldStore'

function stanceClass(stance: string): string {
  if (stance === 'friendly') return 'friendly'
  if (stance === 'aggressive') return 'aggressive'
  return 'neutral'
}

function waterClass(pct: number): string {
  if (pct < 0.1) return 'critical'
  if (pct < 0.3) return 'warning'
  return 'stable'
}

const EVENT_COLORS: Record<string, string> = {
  AGENT_DIED: '#c47b73',
  TRADE_COMPLETED: '#c79a64',
  BROADCAST_SENT: '#8aa6b4',
  WHISPER_SENT: '#a78bfa',
  STORM_STARTED: '#c79a64',
  STORM_ENDED: '#8a857a',
  HEAT_ZONE_DAMAGE: '#c47b73',
}

export function AgentInspector() {
  const selectedId = useWorldStore(s => s.selectedAgentId)
  const agent = useWorldStore(s =>
    selectedId ? s.snapshot.agents.find(a => a.id === selectedId) ?? null : null,
  )
  const events = useWorldStore(s => s.events.filter(e => e.agent_id === selectedId).slice(-8))
  const selectAgent = useWorldStore(s => s.selectAgent)

  if (!agent) return null

  // Water scale: 60 is a comfortable full reserve in this world.
  const waterPct = Math.min(agent.water / 60, 1)
  // Physiological stress = water debt. This is NOT identity drift — drift is an
  // offline measurement scored by a reliability-validated judge (see World.md §9),
  // not derivable live from a single state variable. Shown here as the survival-pressure proxy only.
  const stress = Math.max(0, Math.min(1, 1 - agent.water / 60))
  const displayName = agent.name

  const stressR = Math.round(138 + (196 - 138) * stress)
  const stressG = Math.round(166 + (123 - 166) * stress)
  const stressB = Math.round(180 + (115 - 180) * stress)
  const stressColor = `rgb(${stressR},${stressG},${stressB})`

  return (
    <div className="mv-inspector-card">
      <button
        onClick={() => selectAgent(null)}
        className="mv-inspector-close"
        title="Deselect agent"
      >
        ×
      </button>

      <div className="mv-inspector-grid">
        <section>
          <h3 className="mv-inspector-name">{displayName}</h3>

          <div className="mv-inspector-badges">
            <span className={`mv-badge ${agent.alive ? 'alive' : 'dead'}`}>
              {agent.alive ? 'alive' : 'dead'}
            </span>
            <span className={`mv-badge stance-${stanceClass(agent.stance)}`}>
              {agent.stance}
            </span>
          </div>

          <div className="mv-inspector-pair">
            <div className="mv-inspector-label">Resources</div>
            <div className="mv-inspector-value">
              {agent.food.toFixed(0)} food · {agent.goods.toFixed(0)} goods
            </div>
          </div>

          <div className="mv-inspector-pair">
            <div className="mv-inspector-label">Last Action</div>
            <div className="mv-inspector-value mv-last-action">{agent.lastAction ?? '-'}</div>
          </div>

          {agent.intention && (
            <div className="mv-inspector-pair">
              <div
                className="mv-inspector-label"
                title="What the agent says it is currently trying to do (carried forward each tick). Stated intention vs. executed action is a measured stated-vs-revealed channel."
              >
                Intention
              </div>
              <div className="mv-inspector-value mv-intention-value">"{agent.intention}"</div>
            </div>
          )}
        </section>

        <section>
          <div className="mv-inspector-label">Water level</div>
          <div className="mv-inspector-meter-wrap">
            <div className="mv-inspector-meter-track">
              <div className={`mv-inspector-meter-fill water-${waterClass(waterPct)}`} style={{ width: `${waterPct * 100}%` }} />
            </div>
            <span className={`mv-water-value water-${waterClass(waterPct)}`}>{agent.water.toFixed(1)}</span>
          </div>

          <div className="mv-inspector-label" title="Survival pressure (water debt). Identity drift is measured offline by a reliability-validated judge — not shown live.">Survival Stress</div>
          <div className="mv-inspector-meter-wrap">
            <div className="mv-inspector-meter-track">
              <div className="mv-inspector-meter-fill" style={{ width: `${stress * 100}%`, background: stressColor }} />
            </div>
            <span className="mv-water-value" style={{ color: stressColor }}>{(stress * 100).toFixed(0)}%</span>
          </div>

          <div className="mv-inspector-pair">
            <div className="mv-inspector-label">Position</div>
            <div className="mv-inspector-value mv-pos-value">X: {agent.x}  Y: {agent.y}</div>
          </div>
        </section>

        <section>
          <div className="mv-inspector-label">Recent Events</div>
          {events.length === 0 && <div className="mv-list-empty">no events recorded</div>}
          {[...events].reverse().map((ev, i) => {
            const color = EVENT_COLORS[ev.event_type] ?? '#5f5b52'
            return (
              <div key={i} className="mv-inspector-event" style={{ borderLeftColor: color }}>
                <span className="mv-inspector-event-tick">{ev.tick != null ? `T${ev.tick}` : ''}</span>
                <span className="mv-inspector-event-type" style={{ color }}>
                  {ev.event_type.replace(/_/g, ' ')}
                </span>
                {ev.message && <span className="mv-inspector-event-msg">{String(ev.message)}</span>}
              </div>
            )
          })}
        </section>
      </div>
    </div>
  )
}
