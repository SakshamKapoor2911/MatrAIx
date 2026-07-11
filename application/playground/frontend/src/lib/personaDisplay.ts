/** Shared helpers for bench persona identity in the UI. */

const REGION_NAME_POOLS: Record<string, Array<[string, string]>> = {
  "East Asia": [
    ["Mei Lin", "Tan"],
    ["Yuki", "Sato"],
    ["Wei", "Zhang"],
    ["Hana", "Kim"],
    ["Jun", "Park"],
    ["Li Wei", "Chen"],
    ["Aiko", "Nakamura"],
    ["Min", "Ho"],
  ],
  "Southeast Asia": [
    ["Anh", "Nguyen"],
    ["Rizal", "Putra"],
    ["Siti", "Rahman"],
    ["Kai", "Lim"],
    ["Mai", "Tran"],
    ["Arif", "Hassan"],
  ],
  "South Asia": [
    ["Arjun", "Mehta"],
    ["Priya", "Sharma"],
    ["Rohan", "Kapoor"],
    ["Anika", "Das"],
    ["Vikram", "Singh"],
    ["Nisha", "Iyer"],
  ],
  "Western Europe": [
    ["Sofia", "Andersson"],
    ["Luka", "Petrov"],
    ["Emma", "Dubois"],
    ["Marco", "Rossi"],
    ["Clara", "Müller"],
    ["Noah", "Bakker"],
  ],
  "Eastern Europe": [
    ["Mila", "Novak"],
    ["Ivan", "Kowalski"],
    ["Elena", "Popescu"],
    ["Tomas", "Horvat"],
    ["Anya", "Volkova"],
    ["Petra", "Jansen"],
  ],
  "North America": [
    ["Jordan", "Lee"],
    ["Maya", "Patel"],
    ["Ethan", "Brooks"],
    ["Sienna", "Carter"],
    ["Noah", "Williams"],
    ["Ava", "Martinez"],
  ],
  LATAM: [
    ["Camila", "Rojas"],
    ["Diego", "Fernandez"],
    ["Lucia", "Santos"],
    ["Mateo", "Garcia"],
    ["Valentina", "Lopez"],
    ["Andres", "Mendoza"],
  ],
  MENA: [
    ["Layla", "Haddad"],
    ["Omar", "Khalil"],
    ["Yasmin", "Farouk"],
    ["Karim", "Nasser"],
    ["Nadia", "Rahman"],
    ["Samir", "Aziz"],
  ],
  "Sub-Saharan Africa": [
    ["Amara", "Okafor"],
    ["Kwame", "Mensah"],
    ["Zola", "Ndlovu"],
    ["Amina", "Diallo"],
    ["Tendai", "Moyo"],
    ["Kofi", "Adeyemi"],
  ],
  Oceania: [
    ["Harper", "Ngata"],
    ["Liam", "Murphy"],
    ["Isla", "Campbell"],
    ["Jack", "Mitchell"],
    ["Ruby", "Taylor"],
    ["Finn", "Walsh"],
  ],
};

const DEFAULT_NAME_POOL: Array<[string, string]> = [
  ["Jordan", "Lee"],
  ["Maya", "Patel"],
  ["Alex", "Rivera"],
  ["Sam", "Okafor"],
  ["Riley", "Chen"],
  ["Casey", "Brooks"],
  ["Quinn", "Santos"],
  ["Avery", "Kim"],
];

function hashIndex(seed: string, modulo: number): number {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) | 0;
  }
  return Math.abs(hash) % Math.max(modulo, 1);
}

export function isMachinePersonaName(name: string | null | undefined): boolean {
  const trimmed = (name ?? "").trim();
  if (!trimmed) return true;
  return /^persona[-_]/i.test(trimmed);
}

/** Mirror of personabench.persona_display_name.synthetic_display_name */
export function syntheticDisplayName(
  personaId: string,
  dimensions: Record<string, string> = {},
): string {
  const pid = personaId.trim();
  const region = (dimensions.region ?? "").trim();
  const pool = REGION_NAME_POOLS[region] ?? DEFAULT_NAME_POOL;
  const idx = hashIndex(`${pid}:${region}`, pool.length);
  const [first, last] = pool[idx] ?? DEFAULT_NAME_POOL[0];
  return `${first} ${last}`;
}

export function personaDisplayId(personaId: string | null | undefined): string {
  const raw = (personaId ?? "").trim();
  if (!raw) return "persona-????";
  return raw.startsWith("persona-") ? raw : `persona-${raw}`;
}

export function personaPrimaryName(
  name: string | null | undefined,
  personaId: string | null | undefined,
  dimensions: Record<string, string> = {},
): string {
  const trimmed = (name ?? "").trim();
  if (trimmed && !isMachinePersonaName(trimmed)) return trimmed;
  if (personaId?.trim()) return syntheticDisplayName(personaId, dimensions);
  return trimmed || "Unknown persona";
}

export function normalizePersonaPoolName<
  T extends { personaId: string; name?: string | null; dimensions?: Record<string, string> },
>(persona: T): T {
  return {
    ...persona,
    name: personaPrimaryName(persona.name, persona.personaId, persona.dimensions ?? {}),
  };
}
