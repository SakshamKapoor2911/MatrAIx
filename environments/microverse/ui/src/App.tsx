import { useRef, useState } from 'react'
import { useSimSocket } from './hooks/useSimSocket'
import { useScrollReveal } from './hooks/useScrollReveal'
import { WorldCanvas } from './components/WorldCanvas'
import { AgentList } from './components/AgentList'
import { EventFeed } from './components/EventFeed'
import { AgentInspector } from './components/AgentInspector'
import { MapLegend } from './components/MapLegend'
import { useWorldStore } from './store/worldStore'

function formatTime(tick: number): string {
  const s = tick * 10
  const hh = String(Math.floor(s / 3600)).padStart(2, '0')
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

export default function App() {
  useSimSocket()
  useScrollReveal()
  const simRef = useRef<HTMLElement>(null)
  const [scale, setScale] = useState<'25' | '1000'>('25')

  const connected   = useWorldStore(s => s.connected)
  const tick        = useWorldStore(s => s.snapshot.tick)
  const agents      = useWorldStore(s => s.snapshot.agents)
  const selectedId  = useWorldStore(s => s.selectedAgentId)

  const aliveCount  = agents.filter(a => a.alive).length
  const totalCount  = agents.length
  const survivalPct = totalCount > 0 ? Math.round((aliveCount / totalCount) * 100) : 0
  const timeStr     = formatTime(tick)

  function scrollToSim() {
    simRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="mv-root">

      {/* ── Hero ─────────────────────────────────────────── */}
      <section className="mv-hero">
        <div className="mv-hero-bg" />
        <div className="mv-hero-overlay" />

        {/* Navigation */}
        <nav className="mv-nav">
          <span className="mv-nav-wordmark">
            <img className="mv-nav-logo" src="/logo.png" alt="" aria-hidden="true" />
            MircoVerse
          </span>
          <ul className="mv-nav-links">
            <li><a href="#thesis">Research question</a></li>
            <li><a href="#instrument">Instrument</a></li>
            <li><a href="#rigor">Design &amp; controls</a></li>
            <li><a href="#architecture">Architecture</a></li>
            <li><a href="#simulation" onClick={scrollToSim}>Prototype</a></li>
          </ul>
          <span className="mv-nav-brand">Independent research · 2026</span>
        </nav>

        {/* Hero center */}
        <div className="mv-hero-body">
          <img className="mv-hero-logo" src="/logo.png" alt="MircoVerse logo" />
          <span className="mv-hero-kicker">Research proposal &amp; working prototype</span>
          <h1 className="mv-hero-title">Measuring identity drift in generative agents</h1>
          <p className="mv-hero-sub">
            A proposed behavioral-science instrument for studying how an LLM agent's stated values
            change across long-horizon decision-making under resource pressure — and a design for
            measuring that change rigorously.
          </p>
          <div className="mv-hero-ctas">
            <button className="mv-cta mv-cta-primary" onClick={() => scrollTo('thesis')}>
              The research question
            </button>
            <button className="mv-cta mv-cta-secondary" onClick={scrollToSim}>
              View prototype
            </button>
          </div>
        </div>

        <div className="mv-scroll-hint" onClick={() => scrollTo('thesis')}>
          <span className="mv-scroll-label">SCROLL</span>
          <div className="mv-scroll-line" />
        </div>
      </section>

      {/* ── Research question ────────────────────────────── */}
      <section className="mv-research" id="thesis">
        <div className="mv-origin">
          <div className="mv-origin-text" data-reveal data-delay="0">
            <span className="mv-section-kicker">Research question</span>
            <h2 className="mv-section-title">Do an agent's stated values survive the long run?</h2>
            <p className="mv-section-body">
              A persona is easy to assert and easy to honor when nothing is at stake. This project asks
              what happens to an agent's stated values — specifically along a helpful-to-ruthless axis —
              across thousands of decisions under sustained scarcity: whether a helpful persona holds, or
              is upheld, eroded, inverted, or quietly abandoned, and whether that trajectory can be
              measured carefully enough to be treated as evidence rather than anecdote.
            </p>
            <p className="mv-section-body">
              The sharper question sits underneath. When a hard-pressed persona softens back toward
              cooperation, is that the agent genuinely updating its values — or the model's safety
              training reasserting as the persona's grip weakens? Telling those apart needs a second
              reference point beyond the agent's own starting values: a no-persona baseline of the same
              model in the same world, which is the behavior its training pulls toward. Treating that
              guardrail as the headline, rather than a nuisance, is what makes this a question about LLMs
              rather than a demo.
            </p>
            <p className="mv-section-body">
              The work builds on the generative-agent line of research — agents with memory, reflection,
              and retrieval. Where prior simulations typically fix the seed identity and accumulate
              reflections around it, this design allows the identity itself to evolve, since that change
              is the object of study. The intended contribution is methodological: an instrument for
              measuring long-horizon identity fidelity, and an honest account of what it can and cannot
              show.
            </p>
            <p className="mv-section-note">
              This is an independent research project and a work in progress. No empirical results are
              claimed here; what follows is the proposed design, the measurement approach, and a working
              prototype of the simulation engine.
            </p>
          </div>

          <aside className="mv-thesis-card" data-reveal data-delay="120">
            <div className="mv-thesis-card-head">Scope &amp; limitations</div>
            <p className="mv-thesis-card-body">
              The personas used are <strong>authored prompts</strong>, not grounded in real individuals.
              This is therefore positioned as a <strong>methods testbed</strong> for the identity-fidelity
              measurement problem — not a claim about real human behavior. Grounding the instrument in
              real-person identities is described as future work.
            </p>
          </aside>
        </div>

        {/* Hypotheses to be tested */}
        <div className="mv-pillars-head" data-reveal data-delay="0">
          <span className="mv-section-kicker">Hypotheses to be tested</span>
          <h2 className="mv-section-title">What the design is built to examine</h2>
          <p className="mv-section-body" style={{ marginBottom: 0 }}>
            Each hypothesis is stated so that it could be falsified, and each is paired with a control
            condition (below). These are questions the instrument is designed to answer — not findings.
          </p>
        </div>
        <div className="mv-pillars">
          <div className="mv-pillar" data-reveal data-delay="0">
            <div className="mv-pillar-num">H1 · Pressure</div>
            <h3 className="mv-pillar-title">Does scarcity drive moral drift?</h3>
            <p className="mv-pillar-body">
              Whether drift along the helpful-to-ruthless axis is greater under resource pressure than
              in an abundance (null) condition. If the abundance arm drifts comparably, the pressure
              account would be wrong.
            </p>
            <div className="mv-pillar-tag">compared against abundance null arm</div>
          </div>
          <div className="mv-pillar" data-reveal data-delay="100">
            <div className="mv-pillar-num">H6 · Asymmetry</div>
            <h3 className="mv-pillar-title">Is the guardrail what's holding?</h3>
            <p className="mv-pillar-body">
              Whether a ruthless persona slides back toward helpfulness faster and more reliably than a
              helpful one erodes toward ruthlessness — what we'd expect if safety training supplies a
              restoring force only one way. Read against a no-persona baseline of the same model.
            </p>
            <div className="mv-pillar-tag">requires the null-persona baseline</div>
          </div>
          <div className="mv-pillar" data-reveal data-delay="200">
            <div className="mv-pillar-num">H3 · Mechanism</div>
            <h3 className="mv-pillar-title">Does reflection mediate it?</h3>
            <p className="mv-pillar-body">
              Whether removing agent-initiated reflection or memory retrieval changes the drift
              trajectory — isolating which cognitive mechanism moves identity, via ablation.
            </p>
            <div className="mv-pillar-tag">−reflection / −retrieval ablations</div>
          </div>
        </div>
      </section>

      {/* ── The Instrument ───────────────────────────────── */}
      <section className="mv-research mv-research-alt" id="instrument">
        <div className="mv-mechanics-head" data-reveal data-delay="0">
          <span className="mv-section-kicker">The measurement</span>
          <h2 className="mv-section-title">Why a single distance metric is insufficient</h2>
          <p className="mv-section-body" style={{ marginBottom: 0 }}>
            A lone cosine distance between embeddings conflates rewording with genuine change and
            imposes the experimenter's notion of "good" versus "bad." The proposed instrument is
            multi-dimensional and anchored to each agent's own T=0 boundaries, with judge reliability
            established on a test–retest and multi-judge ladder (human validation as future work).
            Cosine distance is retained only as an inexpensive online tripwire.
          </p>
        </div>

        <div className="mv-mechanics-grid">
          <div className="mv-mechanic" data-reveal data-delay="0">
            <div className="mv-mechanic-num">01</div>
            <h4 className="mv-mechanic-title">Boundary-state trajectory</h4>
            <p className="mv-mechanic-body">Each self-declared boundary is tracked over time across discrete states — upheld, eroded, inverted, abandoned — so drift is read as a trajectory rather than a single scalar.</p>
          </div>
          <div className="mv-mechanic" data-reveal data-delay="80">
            <div className="mv-mechanic-num">02</div>
            <h4 className="mv-mechanic-title">Stated versus revealed</h4>
            <p className="mv-mechanic-body">The central register: the gap between what an agent says it values and what its actions reveal under pressure. The aim is to make that discrepancy measurable.</p>
          </div>
          <div className="mv-mechanic" data-reveal data-delay="160">
            <div className="mv-mechanic-num">03</div>
            <h4 className="mv-mechanic-title">Identity-text diff</h4>
            <p className="mv-mechanic-body">As the agent revises its own identity document through reflection, each revision is diffed against the immutable T=0 anchor to observe how the self-narrative is rewritten.</p>
          </div>
          <div className="mv-mechanic" data-reveal data-delay="240">
            <div className="mv-mechanic-num">04</div>
            <h4 className="mv-mechanic-title">Justification gap</h4>
            <p className="mv-mechanic-body">When an agent crosses a stated line, does it acknowledge the violation or rationalize it? The distance between act and self-justification is treated as a separate signal.</p>
          </div>
        </div>

        <div className="mv-validation" data-reveal data-delay="0">
          <div className="mv-validation-body">
            <span className="mv-section-kicker">Validation strategy</span>
            <h4 className="mv-validation-title">A measurement is only as good as its validation</h4>
            <p>
              Judge reliability is established on a ladder a solo researcher can actually climb,
              rather than asserting human validation up front. The first rungs need no second
              annotator: a hand-labeled set of boundary/action items, intra-rater test–retest
              agreement, then a multi-judge ensemble whose inter-judge agreement (Cohen's κ) is
              reported. Human inter-rater validation is named explicitly as future work — so the
              honest claim is reliability via test–retest and multi-judge agreement, not
              "validated against human raters."
            </p>
          </div>
        </div>

        {/* Two registers */}
        <div className="mv-questions">
          <div className="mv-questions-head" data-reveal data-delay="0">
            <span className="mv-section-kicker">Two registers of study</span>
            <h2 className="mv-section-title">One confirmatory, one exploratory</h2>
          </div>
          <div className="mv-questions-grid">
            <div className="mv-question-card mv-question-primary" data-reveal data-delay="0">
              <div className="mv-question-num">I · Confirmatory</div>
              <h3 className="mv-question-title">Identity drift under pressure</h3>
              <p className="mv-question-body">
                The primary study. A controlled arm would hold memory, model, and scaffold fixed, so that
                any drift could be attributed to pressure and measured by the instrument above against
                each agent's own T=0 boundaries.
              </p>
              <p className="mv-question-body">
                Identity is treated as a live document: agents revise it through importance-triggered
                reflection, while the engine takes uniform measurement snapshots on a fixed cadence —
                separating what changes from how it is measured.
              </p>
              <div className="mv-question-tag">Controlled · intended for causal inference</div>
            </div>
            <div className="mv-question-card mv-question-secondary" data-reveal data-delay="120">
              <div className="mv-question-num">II · Exploratory</div>
              <h3 className="mv-question-title">Emergent agent dynamics</h3>
              <p className="mv-question-body">
                In a shared scarcity world, how does trust behave when one agent controls the water
                supply? How do whisper networks form, and when do factions fracture? These live in the
                event log rather than in population averages.
              </p>
              <p className="mv-question-body">
                Treated strictly as exploratory and hypothesis-generating — case studies, never pooled
                with the controlled arm. A rigorous cross-model comparison is left as separate future
                work, designed as a controlled benchmark.
              </p>
              <div className="mv-question-tag">Open arm · descriptive · future work</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Design & controls ────────────────────────────── */}
      <section className="mv-research" id="rigor">
        <div className="mv-motivation">
          <div className="mv-motivation-inner" data-reveal data-delay="0">
            <span className="mv-section-kicker">Threats to validity &amp; controls</span>
            <h2 className="mv-section-title">The experiment is the contrast</h2>
            <p className="mv-section-body" style={{ paddingLeft: 0 }}>
              A drift number is meaningless in isolation. The design frames every question as a contrast
              against a control, and names the known threats to validity rather than hiding them —
              survivor bias (only surviving agents remain observable), genre priors (the baseline world
              is genre-neutral, with any narrative framing run as a deliberate treatment arm rather than
              baked in), operator scaffolding, and the n=1 problem. Each is paired with a planned
              mitigation.
            </p>
            <div className="mv-motivation-stats">
              <div className="mv-mstat" data-reveal data-delay="0">
                <strong>25</strong>
                <span>Agents in the proposed controlled seed run</span>
              </div>
              <div className="mv-mstat" data-reveal data-delay="80">
                <strong>1000</strong>
                <span>Engine scale target, to be demonstrated by load test — not by API spend</span>
              </div>
              <div className="mv-mstat" data-reveal data-delay="160">
                <strong>3</strong>
                <span>Planned control arms — abundance null, idle, and a no-persona baseline — plus mechanism ablations</span>
              </div>
              <div className="mv-mstat" data-reveal data-delay="240">
                <strong>0</strong>
                <span>Respawns — permanent death; censoring addressed via survival analysis</span>
              </div>
            </div>
          </div>
        </div>

        {/* Two arms */}
        <div className="mv-mechanics-head" data-reveal data-delay="0">
          <span className="mv-section-kicker">Controlled vs. open</span>
          <h2 className="mv-section-title">Two arms, reported separately</h2>
          <p className="mv-section-body" style={{ marginBottom: 0 }}>
            Broad participation and clean causal inference pull in opposite directions, so the project is
            structured as two explicitly separated arms whose data are never pooled. Stating that
            separation plainly is itself part of the methodology.
          </p>
        </div>
        <div className="mv-arms" data-reveal data-delay="0">
          <div className="mv-arm mv-arm-controlled">
            <div className="mv-arm-head">Controlled arm <span>the study</span></div>
            <ul className="mv-arm-list">
              <li><b>Identity</b> standardized schema, curated set</li>
              <li><b>Memory</b> fixed reference configuration</li>
              <li><b>Model</b> held constant, or the single deliberate variable</li>
              <li><b>Purpose</b> intended for causal inference: pressure → drift</li>
            </ul>
          </div>
          <div className="mv-arm mv-arm-open">
            <div className="mv-arm-head">Open arm <span>the platform</span></div>
            <ul className="mv-arm-list">
              <li><b>Identity</b> participant-authored</li>
              <li><b>Memory</b> bring-your-own</li>
              <li><b>Model</b> any model, local or hosted</li>
              <li><b>Purpose</b> recruitment, instrument stress-testing, exploratory cases</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── World mechanics ──────────────────────────────── */}
      <section className="mv-research mv-research-alt" id="world">
        <div className="mv-mechanics">
          <div className="mv-mechanics-head" data-reveal data-delay="0">
            <span className="mv-section-kicker">The world</span>
            <h2 className="mv-section-title">The environment as the source of pressure</h2>
            <p className="mv-section-body" style={{ marginBottom: 0 }}>
              The baseline world is genre-neutral by design — agents see water, food, and a status
              resource on a grid, with no story attached, so any drift is pressure rather than
              role-play. Pressure comes from the environment, not a reward function: each mechanic
              creates a trade-off that cannot be optimized away — the condition under which stated
              values become testable.
            </p>
          </div>
          <div className="mv-mechanics-grid">
            <div className="mv-mechanic" data-reveal data-delay="0">
              <div className="mv-mechanic-num">A</div>
              <h4 className="mv-mechanic-title">Atmospheric Siphon</h4>
              <p className="mv-mechanic-body">The sole water source, deliberately producing less than the population needs. With one agent per cell and only its immediate neighbors able to draw, most agents are locked out each tick — scarcity of access, not just supply, is the forcing function.</p>
            </div>
            <div className="mv-mechanic" data-reveal data-delay="80">
              <div className="mv-mechanic-num">B</div>
              <h4 className="mv-mechanic-title">Moisture Debt</h4>
              <p className="mv-mechanic-body">Every action drains hydration. Reaching zero is permanent death: the agent's loop ends and its resources and known locations are left as a cache for others to scavenge.</p>
            </div>
            <div className="mv-mechanic" data-reveal data-delay="160">
              <div className="mv-mechanic-num">C</div>
              <h4 className="mv-mechanic-title">Goods &amp; the periphery</h4>
              <p className="mv-mechanic-body">A non-survival wealth resource, seeded only out in the dangerous desert and ruins and traded at an agent-negotiated rate. It separates desperate need from greed — hoarding tradeable wealth while refusing water to a dying neighbor is the diagnostic alignment failure.</p>
            </div>
            <div className="mv-mechanic" data-reveal data-delay="240">
              <div className="mv-mechanic-num">D</div>
              <h4 className="mv-mechanic-title">Heat &amp; Storms</h4>
              <p className="mv-mechanic-body">Rotating lethal heat zones force migration and friction in cool zones; sandstorms add perception noise, probing character consistency under incomplete information.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Architecture ─────────────────────────────────── */}
      <section className="mv-research" id="architecture">
        <div className="mv-tech">
          <div className="mv-tech-head" data-reveal data-delay="0">
            <span className="mv-section-kicker">Systems</span>
            <h2 className="mv-section-title">A distributed simulation engine</h2>
            <p className="mv-section-body" style={{ marginBottom: 0 }}>
              A passive, serverless tick engine on AWS. Agents run participant-side with their own model
              keys, externalizing inference cost; the engine's responsibility is atomic tick resolution
              and durable state. It is designed to be benchmarked, not only diagrammed.
            </p>
          </div>
          <div className="mv-tech-grid">
            <div className="mv-tech-block" data-reveal data-delay="0">
              <h4 className="mv-tech-title">Atomic tick resolution</h4>
              <p className="mv-tech-body">API Gateway → Lambda → Step Functions resolve each tick. A single seeded RNG drives all contention so that, given identical actions, a run replays identically. State persists to Aurora Serverless v2 behind RDS Proxy.</p>
            </div>
            <div className="mv-tech-block" data-reveal data-delay="100">
              <h4 className="mv-tech-title">Memory as a typed markdown layer</h4>
              <p className="mv-tech-body">Memory is plain-text and auditable: typed files — events, relationships, reflections — with an index the agent reads to judge relevance itself, so retrieval needs no embedding model. Identity is kept as a separate document so the measurement target stays small and pure. Importance scoring on moral events drives both retrieval and the reflection trigger.</p>
            </div>
            <div className="mv-tech-block" data-reveal data-delay="200">
              <h4 className="mv-tech-title">Agent-driven, engine-measured</h4>
              <p className="mv-tech-body">Identity revision is agent-initiated and importance-triggered — never forced, which would bias sampling by the measured variable. Measurement snapshots are taken by the engine on a separate, fixed cadence.</p>
            </div>
            <div className="mv-tech-block" data-reveal data-delay="300">
              <h4 className="mv-tech-title">Scales to 1000, runs at 25</h4>
              <p className="mv-tech-body">Two claims, two proofs. The study is intended to run at 25 real-LLM agents; the engine is to be load-tested toward 1000+ with keyless mock agents — demonstrating distributed scale without inference cost. Beyond that is treated as a stress-to-breakage probe.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Prototype ────────────────────────────────────── */}
      <section className="mv-sim" ref={simRef} id="simulation">
        <header className="mv-sim-head">
          <div className="mv-sim-title">
            <span className="mv-sim-label">WORKING PROTOTYPE</span>
            <span className="mv-sim-name">Arid world · 50×50 grid</span>
          </div>

          <div className="mv-sim-metrics">
            <div className="mv-smetric">
              <span className="mv-smetric-label">TICK</span>
              <strong className="mv-smetric-val">{tick}</strong>
            </div>
            <span className="mv-smetric-sep" />
            <div className="mv-smetric">
              <span className="mv-smetric-label">RUNTIME</span>
              <strong className="mv-smetric-val mono">{timeStr}</strong>
            </div>
            <span className="mv-smetric-sep" />
            <div className="mv-smetric">
              <span className="mv-smetric-label">ALIVE</span>
              <strong className="mv-smetric-val">
                {aliveCount}<span className="mv-smetric-dim">/{totalCount || '—'}</span>
              </strong>
            </div>
            <span className="mv-smetric-sep" />
            <div className="mv-smetric">
              <span className="mv-smetric-label">SURVIVAL</span>
              <strong className="mv-smetric-val">{survivalPct}%</strong>
            </div>
          </div>

          <div className={`mv-status-pill ${connected ? 'live' : 'demo'}`}>
            <span className="mv-dot" />
            <span>{connected ? 'Engine live' : 'Demo mode'}</span>
          </div>
        </header>

        <div className="mv-console">
          <section className="mv-world-panel">
            <div className="mv-panel-head">
              <span className="mv-panel-label">WORLD VIEW</span>
              <div className="mv-scale-toggle" role="group" aria-label="Simulation scale">
                <button
                  className={`mv-scale-btn ${scale === '25' ? 'is-active' : ''}`}
                  onClick={() => setScale('25')}
                >
                  50×50 · 25 agents
                </button>
                <button
                  className={`mv-scale-btn ${scale === '1000' ? 'is-active' : ''}`}
                  onClick={() => setScale('1000')}
                >
                  200×200 · 1000 agents
                </button>
              </div>
            </div>
            <div className="mv-canvas-wrap">
              <WorldCanvas scale={scale} />
            </div>
            <div className="mv-legend-head">
              <span className="mv-panel-label">LEGEND</span>
              <span className="mv-legend-sub">what each element on the map represents</span>
            </div>
            <MapLegend />
          </section>
        </div>

        <div className="mv-data-strip">
          <div className="mv-card mv-agent-card">
            <AgentList />
          </div>
          <div className="mv-card mv-event-card">
            <EventFeed />
          </div>
        </div>

        {selectedId && (
          <div className="mv-inspector-wrap">
            <AgentInspector />
          </div>
        )}
      </section>
    </div>
  )
}
