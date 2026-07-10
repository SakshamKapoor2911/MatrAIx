/** Parse batch job folder names into human-readable list labels. */

const PREFIX_TOKENS = new Set(["pe", "example"]);

const TYPE_TOKENS_BY_APP: Record<string, readonly string[]> = {
  survey: ["survey"],
  chatbot: ["chat", "chatbot", "recommender", "agent"],
  web: ["web", "playwright", "cocoa", "browser"],
  "os-app": ["cua", "computer", "use", "appworld", "os", "app"],
};

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

function typeTokensForJob(parts: string[], applicationType?: string | null): Set<string> {
  const appKey = (applicationType ?? "").toLowerCase();
  if (appKey && TYPE_TOKENS_BY_APP[appKey]) {
    return new Set(TYPE_TOKENS_BY_APP[appKey]);
  }
  const inferred = new Set<string>();
  for (const tokens of Object.values(TYPE_TOKENS_BY_APP)) {
    if (tokens.some((token) => parts.includes(token))) {
      tokens.forEach((token) => inferred.add(token));
    }
  }
  return inferred;
}

/**
 * Turn `pe-example-survey-product-feedback-dd5cda65` into a title + short id.
 * Falls back to the full job name when the slug cannot be inferred.
 */
export function jobDisplayIdentity(
  jobName: string,
  applicationType?: string | null,
): JobDisplayIdentity {
  const shortId = jobShortId(jobName);
  let body = jobName;
  if (shortId) {
    body = body.slice(0, -(shortId.length + 1));
  }

  const parts = body.split("-").filter(Boolean);
  const typeTokens = typeTokensForJob(parts, applicationType);
  const titleParts = parts.filter(
    (part) => !PREFIX_TOKENS.has(part) && !typeTokens.has(part),
  );

  if (titleParts.length === 0) {
    return { title: shortId ?? jobName, shortId };
  }

  return {
    title: humanizeSlugParts(titleParts),
    shortId,
  };
}
