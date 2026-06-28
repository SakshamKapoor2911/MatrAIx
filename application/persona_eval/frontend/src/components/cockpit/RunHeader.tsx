/**
 * RunHeader: the cockpit setup-form header (mockup `app-redesign-v3.html:99-113`).
 *
 * The eyebrow ("PersonaEval · Cockpit"), the "Configure a simulation" title and
 * its friendly subtitle on the left; the application-type segmented switch
 * (`TaskTypeSwitch`) on the right. Presentational. The parent owns the task
 * type + run lifecycle; the switch is disabled while a run is in flight.
 */
import { TaskTypeSwitch, type PersonaEvalTaskType } from "./TaskTypeSwitch";

export interface RunHeaderProps {
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
  /** A run is in flight (disables switching task type). */
  running: boolean;
}

export function RunHeader({ taskType, onTaskTypeChange, running }: RunHeaderProps) {
  return (
    <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
      <div>
        <div className="hud mb-2 text-[10px] text-primary">PersonaEval · Cockpit</div>
        <h1 className="font-display text-[26px] font-bold tracking-tight text-text-main">Configure a simulation</h1>
        <p className="mt-1 text-[13px] leading-relaxed text-text-variant">
          Pick a persona and an app, choose your run options, then launch. PersonaEval role-plays the user and scores
          how the app responds.
        </p>
      </div>
      <div className="shrink-0">
        <TaskTypeSwitch value={taskType} onChange={onTaskTypeChange} disabled={running} />
      </div>
    </div>
  );
}

export default RunHeader;
