/** Parse batch job folder names into human-readable list labels. */

const PREFIX_TOKENS = new Set(["pg", "pe", "example"]);

/** Leading type markers only (first content token), not product words mid-slug. */
const LEADING_TYPE_TOKENS = new Set(["survey", "chatbot", "web", "os"]);

/**
 * Trailing transport / harness suffixes — longest match first.
 * Never strip product words like `recommender` / `agent` from the middle.
 */
const TRAILING_TYPE_SUFFIXES: readonly (readonly string[])[] = [
  ["chat", "api"],
  ["chat", "mcp"],
  ["computer", "use"],
  ["os", "app"],
  ["chatbot"],
  ["survey"],
  ["playwright"],
  ["browser", "use"],
  ["cua"],
  ["cocoa"],
];

const HASH_SUFFIX = /-([a-f0-9]{6,8})$/i;

export interface JobDisplayIdentity {
  title: string;
  shortId: string | null;
}

/** Trailing launch hash when present, e.g. `dd5cda65`. */
export function jobShortId(jobName: string): string | null {
  const match = jobName.match(HASH_SUFFIX);
  return match ? match[1].toLowerCase() : null;
}

function humanizeSlugParts(parts: string[]): string {
  return parts
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function stripTrailingTypeSuffix(parts: string[]): string[] {
  const next = [...parts];
  for (const suffix of TRAILING_TYPE_SUFFIXES) {
    if (next.length < suffix.length) continue;
    const tail = next.slice(-suffix.length);
    if (tail.every((token, index) => token === suffix[index])) {
      return next.slice(0, -suffix.length);
    }
  }
  return next;
}

/**
 * Turn `pg-chat-recai-81497418` into a title + short id.
 * Falls back to the full job name when the slug cannot be inferred.
 */
export function jobDisplayIdentity(
  jobName: string,
  _applicationType?: string | null,
): JobDisplayIdentity {
  const shortId = jobShortId(jobName);
  let body = jobName;
  if (shortId) {
    body = body.slice(0, -(shortId.length + 1));
  }

  let parts = body
    .split(/[-_]+/)
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean)
    .filter((part) => !PREFIX_TOKENS.has(part));

  // Drop a single leading type marker (`survey-…`, `chatbot-…`).
  if (parts.length > 1 && LEADING_TYPE_TOKENS.has(parts[0])) {
    parts = parts.slice(1);
  }

  parts = stripTrailingTypeSuffix(parts);

  if (parts.length === 0) {
    return { title: shortId ?? jobName, shortId };
  }

  return {
    title: humanizeSlugParts(parts),
    shortId,
  };
}
