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
  if (!hasPersona) return { status: "Select persona", tone: "idle" };
  if (phase === "error" || phase === "timeout") return { status: "Interrupted", tone: "error" };
  if (phase === "done") return { status: "Complete", tone: "done" };
  if (phase === "building") return { status: "Preparing", tone: "active" };
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
  if (phase === "error" || phase === "timeout") return { status: "Check run", tone: "error" };
  if (phase === "done") return { status: "Complete", tone: "done" };
  if (phase === "building") return { status: "Warming", tone: "active" };
  if (phase === "running") {
    const active =
      jobPhase.includes("recommend") ||
      jobPhase.includes("recai") ||
      jobPhase.includes("agent") ||
      jobPhase.includes("turn");
    if (active) return { status: "Serving chat", tone: "active" };
    return turnCount > 0 ? { status: "Conversation open", tone: "done" } : { status: "Waiting", tone: "idle" };
  }
  return { status: "Ready", tone: "idle" };
}

function scorerStatus(
  phase: PersonaEvalRunPhase,
  jobPhase: string,
  hasQuestionnaire: boolean,
): Pick<PipelineNode, "status" | "tone"> {
  if (phase === "error" || phase === "timeout") return { status: "Pending artifacts", tone: "error" };
  if (phase === "done") return hasQuestionnaire ? { status: "Complete", tone: "done" } : { status: "Awaiting score", tone: "idle" };
  if (phase === "running") {
    const active = jobPhase.includes("eval") || jobPhase.includes("scor") || jobPhase.includes("verifier");
    return active ? { status: "Scoring", tone: "active" } : { status: "Waiting", tone: "idle" };
  }
  return { status: "Waiting", tone: "idle" };
}

function toneClass(tone: PipelineNode["tone"]): string {
  if (tone === "active") return "border-primary/35 bg-primary-container/45 text-primary";
  if (tone === "done") return "border-success/30 bg-success-container/55 text-on-success-container";
  if (tone === "error") return "border-error/30 bg-error-container/55 text-on-error-container";
  return "border-border-soft bg-surface-container text-on-surface-variant";
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
      detail: "persona_self_report.json -> user_feedback.json",
      icon: "fact_check",
      ...scorer,
    },
  ];

  return (
    <section
      aria-label="Persona evaluation component pipeline"
      className="border-b border-border-soft bg-surface-container-lowest px-lg py-2.5"
    >
      <div className="grid grid-cols-1 gap-2 2xl:grid-cols-3">
        {nodes.map((node, index) => (
          <div key={node.key} className="flex min-w-0 items-center gap-2">
            <div className="flex min-w-0 flex-1 items-start gap-2 rounded-md border border-border-soft bg-surface-container-low px-3 py-2">
              <div className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded border ${toneClass(node.tone)}`}>
                <Sym name={node.icon} size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-label-md font-label-md uppercase tracking-wider text-on-surface">{node.label}</p>
                  <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[11px] font-medium ${toneClass(node.tone)}`}>
                    {node.status}
                  </span>
                </div>
                <p className="mt-0.5 truncate font-mono-sm text-mono-sm text-on-surface">{node.owner}</p>
                <p className="mt-1 line-clamp-2 text-body-sm leading-snug text-on-surface-variant">{node.detail}</p>
              </div>
            </div>
            {index < nodes.length - 1 && (
              <Sym name="arrow_forward" size={17} className="hidden flex-shrink-0 text-outline 2xl:inline-flex" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export default ComponentPipeline;
