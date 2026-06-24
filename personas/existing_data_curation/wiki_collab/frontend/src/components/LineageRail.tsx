/**
 * The horizontal 5-stage curation stepper (Package → Run → Return → Audit →
 * Merge), derived client-side from `state.files`. Done stages are filled +
 * checked and link to their artifact; pending stages sit on a muted surface.
 * Connector tracks are coloured up to the last completed stage.
 */
import { Sym, FOCUS_RING } from "@/components/cockpit/cockpitShared";
import { deriveLineage } from "@/lib/lineage";
import type { LineageStage } from "@/lib/lineage";
import type { AppState } from "@/lib/types";

function StageNode({ stage, index }: { stage: LineageStage; index: number }) {
  const circle = (
    <span
      className={[
        "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border font-label-md tabular-nums transition-colors",
        stage.done
          ? "border-success bg-success text-on-primary"
          : "border-border-soft bg-surface-container text-on-surface-variant",
      ].join(" ")}
    >
      {stage.done ? <Sym name="check" size={16} fill={1} /> : index + 1}
    </span>
  );

  const text = (
    <span className="flex flex-col leading-tight">
      <span className={`font-body-md ${stage.done ? "text-on-surface" : "text-on-surface-variant"}`}>
        {stage.label}
      </span>
      <span className="font-body-sm text-on-surface-variant">{stage.sublabel}</span>
    </span>
  );

  const inner = (
    <span className="flex items-center gap-sm">
      {circle}
      {text}
    </span>
  );

  if (stage.done && stage.href) {
    return (
      <a
        href={stage.href}
        title={`Download ${stage.label} artifact`}
        className={`group rounded-lg px-1.5 py-1 transition-colors hover:bg-surface-container-low ${FOCUS_RING}`}
      >
        {inner}
      </a>
    );
  }
  return <div className="px-1.5 py-1">{inner}</div>;
}

export function LineageRail({ state }: { state: AppState }) {
  const stages = deriveLineage(state);

  return (
    <nav aria-label="Curation lineage" className="flex items-center gap-1 overflow-x-auto px-md py-sm">
      {stages.map((stage, i) => {
        const isLast = i === stages.length - 1;
        // Colour the connector if BOTH this stage and the next are done.
        const connectorDone = stage.done && stages[i + 1]?.done;
        return (
          <div key={stage.key} className="flex flex-1 items-center">
            <StageNode stage={stage} index={i} />
            {!isLast ? (
              <span
                aria-hidden
                className={`mx-1 h-0.5 flex-1 rounded-full ${connectorDone ? "bg-success" : "bg-surface-container-high"}`}
              />
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}
