import { Sym } from "./cockpitShared";
import type { PlaygroundPrompts } from "@/lib/types";

export interface PromptPanelProps {
  prompts: PlaygroundPrompts | null | undefined;
}

export function PromptPanel({ prompts }: PromptPanelProps) {
  if (!prompts) {
    return (
      <div className="p-md">
        <div className="rise-in rounded-md border border-dashed border-outline-dim bg-surface-low px-4 py-10 text-center">
          <Sym name="terminal" size={28} className="text-text-dim" />
          <p className="mt-2 text-[13px] leading-relaxed text-text-variant">
            Run a simulation to see the exact prompts used.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 p-md">
      <PromptBlock
        label="Persona prompt"
        sublabel="simulated-user system prompt"
        value={prompts.personaPrompt ?? prompts.harborPrompt ?? ""}
        index={0}
      />
      <PromptBlock label="Task prompt" sublabel="application instruction" value={prompts.taskPrompt ?? ""} index={1} />
    </div>
  );
}

function PromptBlock({
  label,
  sublabel,
  value,
  index = 0,
}: {
  label: string;
  sublabel: string;
  value: string;
  index?: number;
}) {
  return (
    <section
      className="rise-in overflow-hidden rounded-md border border-outline bg-surface-lowest"
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms` }}
    >
      <div className="flex items-center justify-between gap-3 border-b border-outline bg-surface-low px-3 py-2">
        <div className="min-w-0">
          <h3 className="font-semibold text-sm text-text-main">{label}</h3>
          <p className="hud break-words text-[9px] text-text-dim">{sublabel}</p>
        </div>
        <Sym name="data_object" size={16} className="flex-shrink-0 text-text-dim" />
      </div>
      <pre className="custom-scrollbar max-h-72 overflow-auto whitespace-pre-wrap break-words bg-field p-3 font-mono text-[11px] leading-relaxed text-text-variant">
        {value || "(empty)"}
      </pre>
    </section>
  );
}

export default PromptPanel;
