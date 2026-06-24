/**
 * RunConfigBar — the cockpit's editable knobs + read-only environment facts.
 *
 * Ports the mockup's config bar: RecBot model · Persona model · Domain ·
 * Conversation style knobs (the `KnobSelect` dropdowns), a Max-turns slider,
 * and the right-aligned
 * `EnvironmentPopover` of fixed-stack facts. The knob choices + their
 * descriptions come from the backend config metadata (`engine`/`domain` knobs)
 * and the goal-contexts (the "Conversation style"); the slider drives the run's
 * `maxTurns`.
 *
 * The Conversation-style knob is the highlighted (primary-bordered) one, as in
 * the mockup. The slider is explicitly linked to its label (`htmlFor`/`id`) so
 * a screen reader announces "Max turns" when it lands on the control, and its
 * live value is shown beside the label.
 *
 * Presentational w.r.t. the run: the parent owns the selected values and the
 * change callbacks; while a run is in flight the knobs are disabled.
 */
import { useId } from "react";

import { EnvironmentPopover } from "./EnvironmentPopover";
import { KnobSelect, type KnobOption } from "./KnobSelect";
import { FOCUS_RING } from "./cockpitShared";
import type { ApplicationId, ConfigEnvironment, ConfigKnob, Domain, GoalContext } from "@/lib/types";

/** Min/max for the max-turns slider (mirrors the backend's accepted range). */
const TURNS_MIN = 1;
const TURNS_MAX = 20;

export interface RunConfigBarProps {
  /** Config knob metadata from `/api/config/options` (engine, domain, …). */
  knobs: ConfigKnob[];
  /** Read-only fixed-stack facts. */
  environment: ConfigEnvironment | null;
  /** Goal contexts (the "Conversation style" options). */
  goalContexts: GoalContext[];

  /** Selected chatbot application adapter. */
  applicationId: ApplicationId;
  onApplicationId: (value: ApplicationId) => void;
  /** Selected model (engine) value. */
  engine: string;
  onEngine: (value: string) => void;
  /** Selected Harbor persona-agent model. */
  personaModel: string;
  onPersonaModel: (value: string) => void;
  /** Selected domain. */
  domain: Domain;
  onDomain: (value: Domain) => void;
  /** Selected goal-context id (the conversation style), or null for the first. */
  goalContextId: string | null;
  onGoalContext: (value: string) => void;
  /** Max turns. */
  maxTurns: number;
  onMaxTurns: (value: number) => void;

  /** Disable the knobs (a run is in flight). */
  disabled?: boolean;
}

/** Pull a knob's options (as `KnobOption[]`) by key, or an empty list. */
function optionsFor(knobs: ConfigKnob[], key: string): KnobOption[] {
  const knob = knobs.find((k) => k.key === key);
  return knob ? knob.options.map((o) => ({ value: o.value, label: o.label, description: o.description })) : [];
}

export function RunConfigBar({
  knobs,
  environment,
  goalContexts,
  engine,
  onEngine,
  applicationId,
  onApplicationId,
  personaModel,
  onPersonaModel,
  domain,
  onDomain,
  goalContextId,
  onGoalContext,
  maxTurns,
  onMaxTurns,
  disabled,
}: RunConfigBarProps) {
  const sliderId = useId();

  const engineOptions = optionsFor(knobs, "engine");
  const applicationOptions = optionsFor(knobs, "applicationId");
  const personaModelOptions = optionsFor(knobs, "personaModel");
  const domainOptions = applicationId === "recai" ? optionsFor(knobs, "domain") : [];
  const styleOptions: KnobOption[] = goalContexts.map((g) => ({
    value: g.id,
    label: g.label,
    description: g.description,
  }));
  const styleValue = goalContextId ?? goalContexts[0]?.id ?? "";

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-2 border-b border-border-soft bg-surface-container-lowest px-lg py-2.5 shadow-sm">
      {applicationOptions.length > 0 && (
        <KnobSelect
          label="Application"
          value={applicationId}
          options={applicationOptions}
          onChange={(v) => onApplicationId(v as ApplicationId)}
          disabled={disabled}
        />
      )}
      {engineOptions.length > 0 && (
        <KnobSelect
          label="Application model"
          value={engine}
          options={engineOptions}
          onChange={onEngine}
          disabled={disabled}
        />
      )}
      {personaModelOptions.length > 0 && (
        <KnobSelect
          label="Persona model"
          value={personaModel}
          options={personaModelOptions}
          onChange={onPersonaModel}
          disabled={disabled}
        />
      )}
      {domainOptions.length > 0 && (
        <KnobSelect
          label="Domain"
          value={domain}
          options={domainOptions}
          onChange={(v) => onDomain(v as Domain)}
          disabled={disabled}
        />
      )}
      {styleOptions.length > 0 && (
        <KnobSelect
          label="Conversation style"
          value={styleValue}
          options={styleOptions}
          onChange={onGoalContext}
          accent
          disabled={disabled}
        />
      )}

      {/* Max-turns slider — label linked to the input via htmlFor/id. */}
      <div className="flex flex-shrink-0 items-center gap-3">
        <label
          htmlFor={sliderId}
          className="flex items-center gap-1 text-label-md font-label-md uppercase tracking-wider text-on-surface-variant"
        >
          Max turns:{" "}
          <span className="rounded bg-surface-container px-1.5 font-mono-sm text-mono-sm text-on-surface">
            {maxTurns}
          </span>
        </label>
        <input
          id={sliderId}
          type="range"
          min={TURNS_MIN}
          max={TURNS_MAX}
          value={maxTurns}
          disabled={disabled}
          onChange={(e) => onMaxTurns(Number(e.target.value))}
          aria-valuetext={`${maxTurns} turns`}
          className={`h-1 w-24 cursor-pointer appearance-none rounded-lg bg-outline-variant accent-primary disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
        />
      </div>

      <EnvironmentPopover environment={environment} />
    </div>
  );
}

export default RunConfigBar;
