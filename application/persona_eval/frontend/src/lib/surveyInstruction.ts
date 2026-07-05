import type { SurveyInstrument } from "./types";

/** Markdown brief for cockpit review (matches backend build_survey_instruction_markdown). */
export function buildSurveyInstructionMarkdown(instrument: SurveyInstrument): string {
  const lines = [
    `# ${instrument.title}`,
    "",
    instrument.description?.trim() || "Answer each question as the assigned persona.",
    "",
    "## Questions",
    "",
  ];
  instrument.questions.forEach((question, index) => {
    lines.push(`### ${index + 1}. ${question.prompt}`);
    if (question.construct) {
      lines.push(`*Construct: ${question.construct}*`);
    }
    if (question.type === "likert") {
      lines.push(`**Type:** Likert scale (${question.minValue ?? 1}–${question.maxValue ?? 5})`);
    } else if (question.type === "single_choice") {
      lines.push("**Type:** Choose one");
      question.options.forEach((option) => lines.push(`- ${option}`));
    } else if (question.type === "multi_choice") {
      lines.push("**Type:** Choose all that apply");
      question.options.forEach((option) => lines.push(`- ${option}`));
    } else if (question.type === "free_text") {
      lines.push("**Type:** Free text");
    }
    lines.push("");
  });
  return lines.join("\n");
}
