import { Sym } from "./cockpitShared";
import type { ConfigEnvironment } from "@/lib/types";
import type { PersonaEvalRunPhase } from "@/lib/usePersonaEval";

interface ComponentPipelineProps {
  environment: ConfigEnvironment | null;
  engine: string;
  personaModel: string;
  phase: PersonaEvalRunPhase;
  jobPhase: string | null | undefined;
  hasPersona: boolean;
  turnCount: number;
  hasQuestionnaire: boolean;
}

interface PipelineNode {
  key: string;
  label: string;
  owner: string;
  detail: string;
  icon: string;
  status: string;
  tone: "idle" | "active" | "done" | "error";
}

function normalizedPhase(value: string | null | undefined): string {
  return (value ?? "").toLowerCase();
}

function personaStatus(phase: PersonaEvalRunPhase, jobPhase: string, hasPersona: boolean): Pick<PipelineNode, "status" | "tone"> {
  if (!hasPersona) return { status: "Choose a persona", tone: "idle" };
  if (phase === "error" || phase === "timeout") return { status: "Stopped early", tone: "error" };
  if (phase === "done") return { status: "Complete", tone: "done" };
  if (phase === "building") return { status: "Getting ready", tone: "active" };
  if (phase === "running") {
    const active = jobPhase.includes("persona") || jobPhase.includes("user") || jobPhase.includes("simulat");
    return { status: active ? "Active" : "Connected", tone: active ? "active" : "done" };
  }
  return { status: "Ready", tone: "idle" };
}

function chatbotStatus(
  phase: PersonaEvalRunPhase,
  jobPhase: string,
  turnCount: number,
): Pick<PipelineNode, "status" | "tone"> {
  if (phase === "error" || phase === "timeout") return { status: "Needs a look", tone: "error" };
  if (phase === "done") return { status: "Complete", tone: "done" };
  if (phase === "building") return { status: "Warming up", tone: "active" };
  if (phase === "running") {
    const active =
      jobPhase.includes("recommend") ||
      jobPhase.includes("recai") ||
      jobPhase.includes("agent") ||
      jobPhase.includes("turn");
    if (active) return { status: "Replying", tone: "active" };
    return turnCount > 0 ? { status: "Chatting", tone: "done" } : { status: "Waiting its turn", tone: "idle" };
  }
  return { status: "Ready", tone: "idle" };
}

function scorerStatus(
  phase: PersonaEvalRunPhase,
  jobPhase: string,
  hasQuestionnaire: boolean,
): Pick<PipelineNode, "status" | "tone"> {
  if (phase === "error" || phase === "timeout") return { status: "Nothing to score", tone: "error" };
  if (phase === "done") return hasQuestionnaire ? { status: "Complete", tone: "done" } : { status: "Not scored yet", tone: "idle" };
  if (phase === "running") {
    const active = jobPhase.includes("eval") || jobPhase.includes("scor") || jobPhase.includes("verifier");
    return active ? { status: "Scoring", tone: "active" } : { status: "Waiting its turn", tone: "idle" };
  }
  return { status: "Waiting its turn", tone: "idle" };
}

function toneClass(tone: PipelineNode["tone"]): string {
  if (tone === "active") return "border-primary/40 bg-primary/10 text-primary";
  if (tone === "done") return "border-secondary/40 bg-secondary/10 text-secondary";
  if (tone === "error") return "border-danger/40 bg-danger/10 text-danger";
  return "border-outline-dim bg-surface-low text-text-dim";
}

export function ComponentPipeline({
  environment,
  engine,
  personaModel,
  phase,
  jobPhase,
  hasPersona,
  turnCount,
  hasQuestionnaire,
}: ComponentPipelineProps) {
  const rawPhase = normalizedPhase(jobPhase);
  const persona = personaStatus(phase, rawPhase, hasPersona);
  const chatbot = chatbotStatus(phase, rawPhase, turnCount);
  const scorer = scorerStatus(phase, rawPhase, hasQuestionnaire);
  const personaPromptOwner = environment?.promptOwnership.personaSystemPrompt ?? "Persona prompt from task runtime";

  const nodes: PipelineNode[] = [
    {
      key: "persona",
      label: "Persona",
      owner: environment?.personaAgent ?? "PersonaEval task controller",
      detail: `${personaModel || environment?.personaModel || "anthropic/claude-haiku-4-5"} · ${personaPromptOwner}`,
      icon: "badge",
      ...persona,
    },
    {
      key: "chatbot",
      label: "Chatbot",
      owner: environment?.applicationApi ?? "chatbot-api sidecar",
      detail: `${engine || "gpt-4o-mini"} · ${environment?.agent ?? "chatbot application adapter"}`,
      icon: "forum",
      ...chatbot,
    },
    {
      key: "scorer",
      label: "Scorer",
      owner: environment?.scorer ?? "PersonaEval self-report scorer",
      detail: "Turns the user's self-report into the final scores.",
      icon: "fact_check",
      ...scorer,
    },
  ];

  return (
    <section
      aria-label="Persona evaluation component pipeline"
      className="border-b border-outline-dim bg-surface-lowest px-5 py-2.5"
    >
      <p className="mb-2 hud text-[10px] text-text-dim">Pipeline</p>
      {phase === "idle" && (
        <p className="mb-2 text-[11px] leading-relaxed text-text-dim">
          Your run flows left to right: the <strong className="font-semibold text-text-variant">Persona</strong> plays
          the user, the <strong className="font-semibold text-text-variant">Chatbot</strong> is the app you&apos;re
          testing, and the <strong className="font-semibold text-text-variant">Scorer</strong> rates the result.
        </p>
      )}
      <div className="grid grid-cols-1 gap-2 2xl:grid-cols-3">
        {nodes.map((node, index) => (
          <div key={node.key} className="flex min-w-0 items-center gap-2">
            <div className="flex min-w-0 flex-1 items-start gap-2 rounded-md border border-outline bg-surface-low px-3 py-2">
              <div className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded border ${toneClass(node.tone)}`}>
                <Sym name={node.icon} size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate hud text-[10px] text-text-main">{node.label}</p>
                  <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[11px] font-medium ${toneClass(node.tone)}`}>
                    {node.status}
                  </span>
                </div>
                <p className="mt-0.5 truncate font-mono text-[11px] text-text-variant">{node.owner}</p>
                <p className="mt-1 line-clamp-2 text-[12px] leading-snug text-text-dim">{node.detail}</p>
              </div>
            </div>
            {index < nodes.length - 1 && (
              <Sym name="arrow_forward" size={17} className="hidden flex-shrink-0 text-text-dim 2xl:inline-flex" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export default ComponentPipeline;
