import type { CuaEvalTask, SurveyHarborTask, SurveyInstrument, WebEvalTask } from "@/lib/types";
import { suggestedWebPersonaAgent, webPersonaAgentLabel, cuaRuntimeLabel, suggestedCuaBackend } from "@/lib/personaAgentCatalog";
import type { TaskCardModel } from "./TaskSelectionRail";

export function surveyInstrumentCards(instruments: SurveyInstrument[]): TaskCardModel[] {
  return instruments.map((item) => ({
    id: item.id,
    title: item.title,
    subtitle: item.description,
    taskType: "survey",
    taskPath: "",
    surveyKind: "instrument",
    surveyInstrumentId: item.id,
    available: true,
    statusLabel: "Questionnaire",
  }));
}

export function surveyHarborTaskCards(tasks: SurveyHarborTask[]): TaskCardModel[] {
  return tasks.map((item) => ({
    id: item.id,
    title: item.title,
    subtitle: item.description,
    taskType: "survey",
    taskPath: item.taskPath,
    surveyKind: "harbor",
    surveyInstrumentId: item.instrumentId,
    available: true,
    statusLabel: item.surveyKind === "example" ? "Example" : "Survey task",
    profileMarkdown: item.profileMarkdown,
  }));
}

export function webEvalTaskCards(tasks: WebEvalTask[]): TaskCardModel[] {
  return tasks.map((item) => ({
    id: item.id,
    title: item.title,
    subtitle: item.description ?? item.siteName,
    taskType: "web",
    taskPath: item.taskPath ?? "",
    available: true,
    statusLabel: webPersonaAgentLabel(suggestedWebPersonaAgent(item.id)),
    profileMarkdown: item.profileMarkdown,
  }));
}

export function cuaTaskCards(tasks: CuaEvalTask[]): TaskCardModel[] {
  return tasks.map((item) => ({
    id: item.id,
    title: item.title,
    subtitle: item.description ?? item.environmentLabel,
    taskType: "cua",
    taskPath: item.taskPath,
    platform: item.platform,
    available: true,
    statusLabel:
      item.platform === "macos" || item.platform === "ios"
        ? `${item.platform} · ${cuaRuntimeLabel(suggestedCuaBackend(item.platform))}`
        : item.platform,
    profileMarkdown: item.profileMarkdown,
  }));
}
