import { Sym } from "./cockpitShared";
import type { PersonaEvalPrompts } from "@/lib/types";

export interface PromptPanelProps {
  prompts: PersonaEvalPrompts | null | undefined;
}

export function PromptPanel({ prompts }: PromptPanelProps) {
  if (!prompts) {
    return (
      <div className="p-md">
        <div className="rounded-xl border border-dashed border-border-soft bg-surface-container-low px-4 py-10 text-center">
          <Sym name="terminal" size={28} className="text-outline" />
          <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">
            Run an eval to see the Harbor and task prompts.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 p-md">
      <PromptBlock label="Harbor prompt" sublabel="persona system prompt" value={prompts.harborPrompt} />
      <PromptBlock label="Task prompt" sublabel="application extra instruction" value={prompts.taskPrompt} />
    </div>
  );
}

function PromptBlock({ label, sublabel, value }: { label: string; sublabel: string; value: string }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
      <div className="flex items-center justify-between gap-3 border-b border-border-soft bg-surface-container-low px-3 py-2">
        <div className="min-w-0">
          <h3 className="text-headline-sm font-headline-sm text-on-surface">{label}</h3>
          <p className="truncate text-label-md font-label-md text-on-surface-variant">{sublabel}</p>
        </div>
        <Sym name="data_object" size={17} className="flex-shrink-0 text-outline" />
      </div>
      <pre className="custom-scrollbar max-h-72 overflow-auto whitespace-pre-wrap break-words p-3 font-mono-sm text-mono-sm leading-relaxed text-on-surface-variant">
        {value || "(empty)"}
      </pre>
    </section>
  );
}

export default PromptPanel;
