/**
 * RunConfigBar: the cockpit's "Run configuration" panel.
 *
 * Ports the mockup's Run-configuration card (`app-redesign-v3.html:170-184`): a
 * titled panel (`tune` icon + "Run configuration") over a 2-col grid of
 * field-style knobs: Application model (`engine`), Persona model, Domain
 * (RecAI-only), Conversation style (the accent knob), and a full-width Max-turns
 * slider.
 *
 * The application adapter itself is chosen by the card picker above (the
 * cockpit), and the read-only runtime facts live in their own right-rail panel,
 * so this panel is purely the editable run knobs. Knob options + their
 * descriptions come from the backend config metadata; the slider drives
 * `maxTurns`. Presentational: the parent owns the values + change callbacks.
 */
import { useId } from "react";

import { KnobSelect, type KnobOption } from "./KnobSelect";
import { FOCUS_RING, Sym } from "./cockpitShared";
import { fmtDomain } from "../runsShared";
import type { ApplicationId, ConfigKnob, Domain, GoalContext } from "@/lib/types";

/** Min/max for the max-turns slider (mirrors the backend's accepted range). */
const TURNS_MIN = 1;
const TURNS_MAX = 20;

export interface RunConfigBarProps {
  /** Config knob metadata from `/api/config/options` (engine, domain, …). */
  knobs: ConfigKnob[];
  /** Goal contexts (the "Conversation style" options). */
  goalContexts: GoalContext[];

  /** Selected chatbot application adapter (gates the RecAI-only Domain knob). */
  applicationId: ApplicationId;
  /** Selected model (engine) value. */
  engine: string;
  onEngine: (value: string) => void;
  /** Selected simulated-user model. */
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
  goalContexts,
  engine,
  onEngine,
  applicationId,
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
  const personaModelOptions = optionsFor(knobs, "personaModel");
  const domainOptions =
    applicationId === "recai" ? optionsFor(knobs, "domain").map((o) => ({ ...o, label: fmtDomain(o.label) })) : [];
  const styleOptions: KnobOption[] = goalContexts.map((g) => ({
    value: g.id,
    label: g.label,
    description: g.description,
  }));
  const styleValue = goalContextId ?? goalContexts[0]?.id ?? "";

  return (
    <div className="rounded-md border border-outline bg-surface p-5">
      <div className="mb-5 flex items-center gap-2 border-b border-outline pb-3.5">
        <Sym name="tune" size={16} className="text-primary" />
        <h3 className="hud text-[10px] text-primary">Run configuration</h3>
      </div>

      <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2">
        {engineOptions.length > 0 && (
          <KnobSelect
            block
            label="Application model"
            value={engine}
            options={engineOptions}
            onChange={onEngine}
            disabled={disabled}
          />
        )}
        {personaModelOptions.length > 0 && (
          <KnobSelect
            block
            label="Persona model"
            value={personaModel}
            options={personaModelOptions}
            onChange={onPersonaModel}
            disabled={disabled}
          />
        )}
        {domainOptions.length > 0 && (
          <KnobSelect
            block
            label="Domain"
            labelAccent="· RecAI"
            value={domain}
            options={domainOptions}
            onChange={(v) => onDomain(v as Domain)}
            disabled={disabled}
          />
        )}
        {styleOptions.length > 0 && (
          <div>
            <KnobSelect
              block
              accent
              label="Conversation style"
              value={styleValue}
              options={styleOptions}
              onChange={onGoalContext}
              disabled={disabled}
            />
            {styleOptions.length === 1 && (
              <p className="mt-1.5 text-[11px] leading-snug text-text-dim">
                One scenario for now. Targeted scenarios, like steering the persona toward a
                specific goal, are coming soon.
              </p>
            )}
          </div>
        )}

        {/* Max-turns slider: full width, label linked to the input. */}
        <label htmlFor={sliderId} className="block sm:col-span-2">
          <span className="hud mb-1.5 block text-[9px] text-text-dim">
            Max turns
            <span className="ml-1 font-mono normal-case tracking-normal text-text-variant">{maxTurns}</span>
          </span>
          <input
            id={sliderId}
            type="range"
            min={TURNS_MIN}
            max={TURNS_MAX}
            value={maxTurns}
            disabled={disabled}
            onChange={(e) => onMaxTurns(Number(e.target.value))}
            aria-valuetext={`${maxTurns} turns`}
            className={`w-full cursor-pointer accent-primary disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
          />
        </label>
      </div>
    </div>
  );
}

export default RunConfigBar;
