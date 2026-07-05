import {
  hasMeaningfulTaskContext,
  normalizeOutputSchemaMarkdown,
  normalizeQuestionnaireMarkdown,
  normalizeTaskInstructionMarkdown,
} from "@/lib/taskContent";

export type TaskDocTabId = "instruction" | "context" | "questionnaire" | "output-schema";

export type TaskDocSection = {
  id: TaskDocTabId;
  label: string;
  icon: string;
  markdown: string;
};

export type TaskDocSource = {
  instructionMarkdown?: string | null;
  contextMarkdown?: string | null;
  questionnaireMarkdown?: string | null;
  outputSchemaMarkdown?: string | null;
};

/** Split task-owned docs into contract-aligned sections (instruction / context / questionnaire / output). */
export function buildTaskDocSections(source: TaskDocSource): TaskDocSection[] {
  const sections: TaskDocSection[] = [];

  const instruction = normalizeTaskInstructionMarkdown(source.instructionMarkdown);
  if (instruction) {
    sections.push({
      id: "instruction",
      label: "Instruction",
      icon: "description",
      markdown: instruction,
    });
  }

  const context = (source.contextMarkdown ?? "").trim();
  if (hasMeaningfulTaskContext(context)) {
    sections.push({
      id: "context",
      label: "Context",
      icon: "menu_book",
      markdown: context,
    });
  }

  const questionnaire = normalizeQuestionnaireMarkdown(source.questionnaireMarkdown);
  if (questionnaire) {
    sections.push({
      id: "questionnaire",
      label: "Questionnaire",
      icon: "list_alt",
      markdown: questionnaire,
    });
  }

  const outputSchema = normalizeOutputSchemaMarkdown(source.outputSchemaMarkdown);
  if (outputSchema) {
    sections.push({
      id: "output-schema",
      label: "Output schema",
      icon: "schema",
      markdown: outputSchema,
    });
  }

  return sections;
}
