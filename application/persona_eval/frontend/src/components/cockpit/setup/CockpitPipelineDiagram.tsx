import { useEffect, useState } from "react";

import type { PersonaEvalTaskType } from "../TaskTypeSwitch";
import { Sym } from "../cockpitShared";
import { DIMENSION_CHIP_TONES, ToneChip, transportChipTone } from "./ToneChip";

export interface CockpitPipelineDiagramProps {
  taskType: PersonaEvalTaskType;
  chatTransport?: "api" | "sidecar" | "mcp";
  /** Short label for the selected web persona agent (pipeline display). */
  webPersonaAgentLabel?: string;
  /** persona-computer-1 runtime label for CUA (Docker / use.computer). */
  cuaRuntimeLabel?: string;
  hasPersona: boolean;
  hasTask: boolean;
  className?: string;
}

interface NodeProps {
  label: string;
  icon: string;
  detail?: string;
  active?: boolean;
  visible?: boolean;
}

function PipelineNode({ label, icon, detail, active = false, visible = true }: NodeProps) {
  return (
    <div
      className={`rise-in flex w-[100px] shrink-0 flex-col items-center rounded-xl border px-2.5 py-3.5 text-center transition-all duration-500 sm:w-[108px] ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"
      } ${
        active
          ? "border-primary/50 bg-primary/12 shadow-[0_0_28px_-6px_rgb(var(--primary)/0.65)]"
          : "border-outline/40 bg-surface/35"
      }`}
    >
      <div
        className={`mb-2 grid h-10 w-10 place-items-center rounded-full border ${
          active ? "border-primary/50 bg-primary/15" : "border-outline/50 bg-surface-high/50"
        }`}
      >
        <Sym name={icon} size={20} className={active ? "text-primary" : "text-text-variant"} />
      </div>
      <p className="text-[12px] font-semibold text-text-main">{label}</p>
      {detail && (
        <p className="mt-1 font-mono text-[8px] uppercase tracking-wide text-text-dim">{detail}</p>
      )}
    </div>
  );
}

function Arrow({ visible = true }: { visible?: boolean }) {
  return (
    <Sym
      name="arrow_forward"
      size={18}
      className={`mx-1 hidden shrink-0 text-text-dim sm:block ${visible ? "opacity-70" : "opacity-0"}`}
    />
  );
}

interface TransportOption {
  id: string;
  label: string;
  icon: string;
}

function TransportFork({
  options,
  selected,
  visible,
}: {
  options: TransportOption[];
  selected: string;
  visible: boolean;
}) {
  return (
    <div
      className={`rise-in flex flex-col items-center transition-all duration-500 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"
      }`}
    >
      <p className="hud mb-2 text-[8px] text-text-dim">Adapter (pick one)</p>
      <div className="flex flex-wrap items-center justify-center gap-1.5 rounded-xl border border-outline/35 bg-gradient-to-br from-surface/40 via-surface/25 to-accent/5 px-2 py-2">
        {options.map((opt, index) => {
          const active = opt.id === selected;
          const tone =
            opt.id === "sidecar" || opt.id === "api" || opt.id === "mcp"
              ? transportChipTone(opt.id)
              : DIMENSION_CHIP_TONES[index % DIMENSION_CHIP_TONES.length];
          return (
            <ToneChip
              key={opt.id}
              tone={tone}
              solid={active}
              muted={!active}
              className="min-w-[72px] flex-col items-center rounded-lg px-2 py-2 text-center"
            >
              <Sym name={opt.icon} size={16} className={active ? "text-text-main" : "text-text-dim"} />
              <span className="mt-1 block text-[10px] font-medium">{opt.label}</span>
            </ToneChip>
          );
        })}
      </div>
    </div>
  );
}

const CHAT_TRANSPORTS: TransportOption[] = [
  { id: "sidecar", label: "Sidecar", icon: "dns" },
  { id: "api", label: "API", icon: "http" },
  { id: "mcp", label: "MCP", icon: "hub" },
];

export function CockpitPipelineDiagram({
  taskType,
  chatTransport = "sidecar",
  webPersonaAgentLabel,
  cuaRuntimeLabel,
  hasPersona,
  hasTask,
  className,
}: CockpitPipelineDiagramProps) {
  const [revealed, setRevealed] = useState(0);
  const stepCount = taskType === "survey" ? 3 : 4;

  useEffect(() => {
    setRevealed(0);
    const timers = Array.from({ length: stepCount }, (_, index) =>
      window.setTimeout(() => setRevealed(index + 1), 100 + index * 120),
    );
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [taskType, chatTransport, webPersonaAgentLabel, cuaRuntimeLabel, stepCount]);

  const ready = hasPersona && hasTask;
  const v = (step: number) => revealed >= step;

  const pipelineBody = (
    <>
      {taskType === "survey" && (
        <div className="flex w-full flex-wrap items-center justify-center gap-2 sm:gap-3">
          <PipelineNode label="Persona" icon="face" detail="bench-dev" active={hasPersona} visible={v(1)} />
          <Arrow visible={v(2)} />
          <PipelineNode label="Survey" icon="quiz" detail="instrument" active={hasTask} visible={v(2)} />
          <Arrow visible={v(3)} />
          <PipelineNode label="Scorer" icon="fact_check" active={ready} visible={v(3)} />
        </div>
      )}

      {taskType === "chatbot" && (
        <div className="flex w-full flex-wrap items-center justify-center gap-2 sm:gap-3">
          <PipelineNode label="Persona" icon="face" detail="user sim" active={hasPersona} visible={v(1)} />
          <Arrow visible={v(2)} />
          <TransportFork options={CHAT_TRANSPORTS} selected={chatTransport} visible={v(2)} />
          <Arrow visible={v(3)} />
          <PipelineNode label="Chatbot" icon="forum" detail="SUT" active={hasTask} visible={v(3)} />
          <Arrow visible={v(4)} />
          <PipelineNode label="Scorer" icon="fact_check" active={ready} visible={v(4)} />
        </div>
      )}

      {taskType === "web" && (
        <div className="flex w-full flex-wrap items-center justify-center gap-2 sm:gap-3">
          <PipelineNode label="Persona" icon="face" active={hasPersona} visible={v(1)} />
          <Arrow visible={v(2)} />
          <PipelineNode
            label="Persona agent"
            icon="smart_toy"
            detail={webPersonaAgentLabel ?? "per task"}
            active={hasTask}
            visible={v(2)}
          />
          <Arrow visible={v(3)} />
          <PipelineNode label="Website" icon="public" active={hasTask} visible={v(3)} />
          <Arrow visible={v(4)} />
          <PipelineNode label="Trace" icon="route" active={ready} visible={v(4)} />
        </div>
      )}

      {taskType === "cua" && (
        <div className="flex w-full flex-wrap items-center justify-center gap-2 sm:gap-3">
          <PipelineNode label="Persona" icon="face" active={hasPersona} visible={v(1)} />
          <Arrow visible={v(2)} />
          <PipelineNode
            label="persona-computer-1"
            icon="smart_toy"
            detail={cuaRuntimeLabel ?? "per task"}
            active={hasTask}
            visible={v(2)}
          />
          <Arrow visible={v(3)} />
          <PipelineNode label="Desktop" icon="desktop_windows" active={hasTask} visible={v(3)} />
          <Arrow visible={v(4)} />
          <PipelineNode label="Trace" icon="route" active={ready} visible={v(4)} />
        </div>
      )}
    </>
  );

  return (
    <div
      className={`glass-panel flex w-full flex-1 min-h-0 flex-col rounded-xl px-4 py-3 sm:px-6 sm:py-4 ${className ?? ""}`}
    >
      <div className="flex min-h-[2.5rem] flex-1 items-center justify-center px-2">
        <p className="font-display text-center text-[15px] font-semibold tracking-wide text-primary sm:text-[17px]">
          Simulation pipeline
        </p>
      </div>

      <div className="w-full shrink-0 py-1">{pipelineBody}</div>

      <div className="flex min-h-[2.5rem] flex-1 items-center justify-center px-2">
        <p className="text-center text-[13px] font-medium leading-snug sm:text-[14px]">
          {ready ? (
            <span className="font-semibold text-secondary">Ready to launch — pipeline locked.</span>
          ) : (
            <span className="text-text-variant">Select personas and a task, then run below.</span>
          )}
        </p>
      </div>
    </div>
  );
}
