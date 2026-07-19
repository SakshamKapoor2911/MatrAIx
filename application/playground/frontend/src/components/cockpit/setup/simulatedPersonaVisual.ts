/** Deterministic visual + copy helpers for batch cohort “simulated human” tiles. */

export interface SimulatedPersonaVisual {
  skin: string;
  hair: string;
  shirt: string;
  backdrop: string;
  hairStyle: 0 | 1 | 2 | 3;
  accessory: 0 | 1 | 2;
}

const SKIN_TONES = ["#f2c9a8", "#e8b796", "#c6865a", "#8d5524", "#5c3d2e"];
const HAIR_COLORS = ["#2c2416", "#4a3728", "#6b4c35", "#8b6914", "#1a1a1a", "#7a4a2e"];
const SHIRT_HUES = [205, 168, 142, 98, 262, 328, 24, 186];

const CHIP_PRIORITY = ["age_bracket", "region", "intent"] as const;

function hashSeed(seed: string): number {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

export function simulatedPersonaVisual(
  seed: string,
  dimensions: Record<string, string> = {},
): SimulatedPersonaVisual {
  // Face traits follow persona id only — never fold dimensions into the hash, or
  // chat (often missing dims) and the roster card render different people.
  const hash = hashSeed(seed);
  const domainHue = dimensions.domain
    ? hashSeed(dimensions.domain) % SHIRT_HUES.length
    : hash % SHIRT_HUES.length;
  const shirtHue = SHIRT_HUES[domainHue] ?? 205;
  return {
    skin: SKIN_TONES[hash % SKIN_TONES.length],
    hair: HAIR_COLORS[(hash >> 3) % HAIR_COLORS.length],
    shirt: `hsl(${shirtHue} 42% 46%)`,
    backdrop: `hsla(${shirtHue}, 48%, 52%, 0.12)`,
    hairStyle: ((hash >> 5) % 4) as 0 | 1 | 2 | 3,
    accessory: ((hash >> 7) % 3) as 0 | 1 | 2,
  };
}

export function personaRosterTitle(dimensions: Record<string, string>): string | null {
  const lines = personaRosterLines(dimensions);
  if (!lines) return null;
  return lines.secondary ? `${lines.primary} · ${lines.secondary}` : lines.primary;
}

export function personaRosterLines(
  dimensions: Record<string, string>,
): { primary: string; secondary: string | null } | null {
  const life = dimensions.life_stage?.trim();
  const domain = dimensions.domain?.trim();
  if (life && domain) return { primary: life, secondary: domain };
  if (life) return { primary: life, secondary: personaRosterChip(dimensions) };
  if (domain) return { primary: domain, secondary: personaRosterChip(dimensions) };
  const intent = dimensions.intent?.trim();
  if (intent) return { primary: intent, secondary: personaRosterChip(dimensions) };
  const chip = personaRosterChip(dimensions);
  return chip ? { primary: chip, secondary: null } : null;
}

export function personaRosterChip(dimensions: Record<string, string>): string | null {
  for (const key of CHIP_PRIORITY) {
    const value = dimensions[key]?.trim();
    if (value) return value;
  }
  return null;
}

export function personaCodenameSuffix(label: string): string {
  const id = label.replace(/^persona[-_]?/i, "").trim();
  return id.length > 4 ? id.slice(-4) : id || "????";
}

export function personaSeedFromCell(
  personaId: string | undefined,
  label: string,
): string {
  const fromId = personaId?.trim();
  if (fromId) return fromId;
  const fromLabel = label.replace(/^persona[-_]?/i, "").trim();
  return fromLabel || label;
}
