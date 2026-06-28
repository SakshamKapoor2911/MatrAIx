/**
 * ChatConfigBar: the Chat workbench's config row (below the top nav).
 *
 * Mirrors the cockpit's RunConfigBar register: the editable config knobs on the
 * left (driven by the `/api/config/options` metadata, via `ConfigBar`) and the
 * read-only "Environment" facts popover on the right. Keeping the knobs in their
 * own bar (not the top nav) keeps the two-surface nav clean at every width.
 *
 * Rendered only in Chat (the cockpit owns its own config bar).
 */
import { ConfigBar } from "./ConfigBar";
import { EnvironmentPopover } from "./cockpit/EnvironmentPopover";
import type { ConfigEnvironment, ConfigKnob, SessionConfig } from "@/lib/types";
import type { ConfigOptionsMap } from "./ConfigBar";

export interface ChatConfigBarProps {
  config: SessionConfig | null;
  options: ConfigKnob[] | ConfigOptionsMap | null;
  environment: ConfigEnvironment | null;
  disabled?: boolean;
  onChange: (patch: Partial<SessionConfig>) => void;
}

export function ChatConfigBar({ config, options, environment, disabled, onChange }: ChatConfigBarProps) {
  return (
    <div className="flex flex-shrink-0 flex-wrap items-center gap-x-5 gap-y-2 border-b border-outline bg-surface-lowest px-5 py-2.5">
      <ConfigBar config={config} options={options} disabled={disabled} onChange={onChange} />
      <EnvironmentPopover environment={environment} />
    </div>
  );
}

export default ChatConfigBar;
