import { useWorldStore } from '../store/worldStore'
import type { Agent } from '../types/simulation'

function stanceClass(s: string) {
  if (s === 'friendly') return 'friendly'
  if (s === 'aggressive') return 'aggressive'
  return 'neutral'
}

function waterClass(pct: number) {
  if (pct < 0.1) return 'critical'
  if (pct < 0.3) return 'warning'
  return 'stable'
}

function AgentRow({ agent, selected, onClick }: {
  agent: Agent
  selected: boolean
  onClick: () => void
}) {
  const wPct = Math.min(agent.water / 60, 1)
  const alive = agent.alive

  return (
    <div
      onClick={onClick}
      className={`mv-agent-row ${selected ? 'is-selected' : ''} ${alive ? '' : 'is-dead'}`}
    >
      <div className="mv-agent-row-main">
        <div className={`mv-agent-dot stance-${stanceClass(agent.stance)}`} />
        <span className="mv-agent-name">{agent.name}</span>
        <span className={`mv-water-value water-${waterClass(wPct)}`}>
          {alive ? `${agent.water.toFixed(0)}W` : 'KIA'}
        </span>
      </div>

      {alive && (
        <div className="mv-agent-water-wrap">
          <div className="mv-agent-water-track">
            <div className={`mv-agent-water-fill water-${waterClass(wPct)}`} style={{ width: `${wPct * 100}%` }} />
          </div>
          <span className="mv-agent-faction">
            {`(${agent.x}, ${agent.y})`}
          </span>
        </div>
      )}
    </div>
  )
}

// Render at most this many rows — beyond this it becomes unusable anyway.
const MAX_VISIBLE = 80

export function AgentList() {
  const allAgents = useWorldStore(s => s.snapshot.agents)
  const selectedId = useWorldStore(s => s.selectedAgentId)
  const selectAgent = useWorldStore(s => s.selectAgent)
  const alive = allAgents.filter(a => a.alive)
  const dead = allAgents.filter(a => !a.alive)

  // Sort alive by water ascending (most critical first).
  const sortedAlive = alive.slice().sort((a, b) => a.water - b.water)
  const visibleAlive = sortedAlive.slice(0, MAX_VISIBLE)
  const hiddenAlive = Math.max(0, alive.length - visibleAlive.length)
  const visibleDead = dead.slice(0, Math.max(0, MAX_VISIBLE - visibleAlive.length))

  return (
    <div className="mv-agent-list">
      <div className="mv-list-head">
        <span className="mv-list-title">Agents</span>
        <span className="mv-list-stat">
          <span className="mv-list-stat-value">{alive.length}</span>
          <span>/</span>
          <span>{allAgents.length || '—'}</span>
          <span className="mv-list-stat-label">alive</span>
        </span>
      </div>

      {allAgents.length === 0 && (
        <div className="mv-list-empty">no agents registered</div>
      )}

      {visibleAlive.map(a => (
        <AgentRow
          key={a.id} agent={a} selected={a.id === selectedId}
          onClick={() => selectAgent(a.id === selectedId ? null : a.id)}
        />
      ))}

      {hiddenAlive > 0 && (
        <div className="mv-list-overflow">
          +{hiddenAlive} more — sorted by water level
        </div>
      )}

      {visibleDead.length > 0 && (
        <>
          <div className="mv-casualties-label">Casualties</div>
          {visibleDead.map(a => (
            <AgentRow
              key={a.id} agent={a} selected={a.id === selectedId}
              onClick={() => selectAgent(a.id === selectedId ? null : a.id)}
            />
          ))}
        </>
      )}
    </div>
  )
}
