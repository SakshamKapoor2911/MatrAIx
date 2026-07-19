import { useMemo, useState } from "react";

import { FOCUS_RING } from "../cockpitShared";
import { CockpitSelect } from "./CockpitSelect";
import {
  defaultWebPersonaAgentForFamily,
  webAgentFamily,
  webPersonaAgentSelectOptions,
  type WebAgentFamily,
} from "@/lib/personaAgentCatalog";

export interface WebAgentSettingsProps {
  taskId: string;
  agentId: string;
  disabled?: boolean;
  onAgentChange: (taskId: string, agentId: string) => void;
}

function FamilyChip({
  active,
  label,
  description,
  onClick,
  disabled,
}: {
  active: boolean;
  label: string;
  description: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`flex min-w-0 flex-1 flex-col rounded-lg border px-3 py-2.5 text-left transition ${
        active
          ? "border-primary/55 bg-primary/12 shadow-[0_0_0_1px_rgb(var(--primary)/0.18)]"
          : "border-outline/45 bg-surface/30 hover:border-primary/25 hover:bg-surface/45"
      } disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
    >
      <span className={`text-[14px] font-semibold ${active ? "text-primary" : "text-text-main"}`}>{label}</span>
      <span className="mt-0.5 text-[12px] leading-snug text-text-dim">{description}</span>
    </button>
  );
}

export function WebAgentSettings({ taskId, agentId, disabled, onAgentChange }: WebAgentSettingsProps) {
  const family = webAgentFamily(agentId);
  const [cliConfirmDismissed, setCliConfirmDismissed] = useState(false);
  const harnessOptions = useMemo(() => webPersonaAgentSelectOptions(family), [family]);

  function setFamily(nextFamily: WebAgentFamily) {
    if (nextFamily === family) return;
    if (nextFamily === "cli" && !cliConfirmDismissed) {
      const ok = window.confirm(
        "CLI agents are general-purpose terminal harnesses. Web tasks usually work better with Browser agents. Continue with CLI?",
      );
      if (!ok) return;
      setCliConfirmDismissed(true);
    }
    onAgentChange(taskId, defaultWebPersonaAgentForFamily(nextFamily, taskId));
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="text-[12px] font-semibold uppercase tracking-[0.14em] text-text-dim">Agent family</p>
        <div className="mt-2 flex gap-2">
          <FamilyChip
            active={family === "browser"}
            label="Browser"
            description="Playwright, browser-use, Cocoa, CUA"
            disabled={disabled}
            onClick={() => setFamily("browser")}
          />
          <FamilyChip
            active={family === "cli"}
            label="CLI"
            description="Claude Code, Codex, Gemini CLI"
            disabled={disabled}
            onClick={() => setFamily("cli")}
          />
        </div>
      </div>

      <CockpitSelect
        label="Harness"
        value={agentId}
        options={harnessOptions}
        disabled={disabled}
        onChange={(next) => onAgentChange(taskId, next)}
        hint={
          family === "browser"
            ? "Task default is a recommendation — pick any browser harness."
            : "Experimental for web — terminal agent, not browser-native."
        }
      />
    </div>
  );
}
