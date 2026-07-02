/**
 * Compact cockpit header — title + subtitle on the left, task-type switch on the right.
 * (No "Persona Cockpit" breadcrumb banner.)
 */
import { TaskTypeSwitch, type PersonaEvalTaskType } from "./TaskTypeSwitch";

export interface RunHeaderProps {
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
}

const SUBTITLES: Record<PersonaEvalTaskType, string> = {
  chatbot:
    "Pick personas and a chat application, then launch. Watch the simulated user converse bubble-by-bubble.",
  survey:
    "Pick a persona and a questionnaire, then launch. A simulated user fills out the form and we score the responses.",
  web: "Pick personas and a web task, then launch. The simulated user completes the site in a real browser trace.",
  cua: "Pick personas and a CUA task, then launch. The agent completes computer-use scenarios step by step.",
};

export function RunHeader({ taskType, onTaskTypeChange }: RunHeaderProps) {
  const subtitleClass =
    taskType === "survey"
      ? "mt-1 text-[12px] leading-relaxed text-text-variant sm:whitespace-nowrap sm:text-[13px]"
      : "mt-1 max-w-2xl text-[12px] leading-relaxed text-text-variant sm:text-[13px]";

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0 flex-1 pr-2 sm:pr-4">
        <h1 className="font-display text-[20px] font-bold leading-tight tracking-tight text-text-main sm:text-[22px]">
          Configure a simulation
        </h1>
        <p className={subtitleClass}>{SUBTITLES[taskType]}</p>
      </div>
      <TaskTypeSwitch value={taskType} onChange={onTaskTypeChange} className="shrink-0" />
    </div>
  );
}

export default RunHeader;
