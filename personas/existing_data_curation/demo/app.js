"use strict";

const MATRAIX_SCHEMA_URL = "https://matraix.ai/dimensions.js?v=3";

const CLAIMS = {
  instance_of: "P31",
  sex_or_gender: "P21",
  occupation: "P106",
  country_of_citizenship: "P27",
  date_of_birth: "P569",
  date_of_death: "P570",
  birth_place: "P19",
  languages: "P1412",
  field_of_work: "P101",
  notable_work: "P800",
  creator: "P170",
  present_in_work: "P1441",
  fictional_universe: "P1080",
  position_held: "P39",
  education: "P69",
  awards: "P166",
  political_party: "P102"
};

const EXTRA_FIELD_DEFS = [
  {
    id: "source_entity_type",
    label: "Source entity type",
    category: "Demo metadata",
    description: "Whether the source entity is a real person or fictional character.",
    values: ["real_person", "fictional_character"]
  },
  {
    id: "identity_name",
    label: "Identity name",
    category: "Demo metadata",
    description: "Resolved Wikidata/Wikipedia display name.",
    values: []
  },
  {
    id: "known_for_or_source_work",
    label: "Known for/source work",
    category: "Demo metadata",
    description: "Representative work, fictional universe, or source work when available.",
    values: []
  },
  {
    id: "creator",
    label: "Creator",
    category: "Demo metadata",
    description: "Creator of a fictional character when available.",
    values: []
  },
  {
    id: "birth_date",
    label: "Raw birth date",
    category: "Demo metadata",
    description: "Raw Wikidata birth date when available.",
    values: []
  },
  {
    id: "death_date",
    label: "Raw death date",
    category: "Demo metadata",
    description: "Raw Wikidata death date when available.",
    values: []
  }
];

const FALLBACK_SCHEMA = {
  schemaVersion: "fallback",
  dimensions: [
    { id: "domain", label: "Domain", category: "Expertise: Domains", values: [] },
    { id: "role_function", label: "Role function", category: "Professional: Industry", values: [] },
    { id: "subject_specialty", label: "Subject specialty", category: "Expertise: Domains", values: [] },
    { id: "primary_language", label: "Primary language", category: "Linguistic: Language", values: [] },
    { id: "gender_identity", label: "Gender identity", category: "Demographic: Core", values: [] },
    { id: "region", label: "Region", category: "Demographic: Core", values: [] },
    { id: "wiki_birth_date", label: "Birth Date", category: "Demographic: Life Events", values: [] },
    { id: "wiki_nationality", label: "Nationality", category: "Demographic: Core", values: [] },
    { id: "wiki_occupation", label: "Occupation", category: "Professional: Industry", values: [] },
    { id: "wiki_field_of_work", label: "Field of Work", category: "Learning: Academic", values: [] }
  ]
};

const COUNTRY_TO_REGION = {
  "United States of America": "North America",
  "United States": "North America",
  "Canada": "North America",
  "Mexico": "Latin America",
  "Brazil": "Latin America",
  "Argentina": "Latin America",
  "Chile": "Latin America",
  "Colombia": "Latin America",
  "United Kingdom": "Western Europe",
  "United Kingdom of Great Britain and Ireland": "Western Europe",
  "England": "Western Europe",
  "France": "Western Europe",
  "Germany": "Western Europe",
  "German Empire": "Western Europe",
  "Switzerland": "Western Europe",
  "Italy": "Western Europe",
  "Kingdom of Italy": "Western Europe",
  "Spain": "Western Europe",
  "Netherlands": "Western Europe",
  "Poland": "Eastern Europe",
  "Russia": "Eastern Europe",
  "Soviet Union": "Eastern Europe",
  "Ukraine": "Eastern Europe",
  "South Africa": "Sub-Saharan Africa",
  "Egypt": "MENA",
  "Iran": "MENA",
  "Saudi Arabia": "MENA",
  "India": "South Asia",
  "Pakistan": "South Asia",
  "Bangladesh": "South Asia",
  "People's Republic of China": "East Asia",
  "China": "East Asia",
  "Japan": "East Asia",
  "South Korea": "East Asia",
  "Indonesia": "Southeast Asia",
  "Philippines": "Southeast Asia",
  "Vietnam": "Southeast Asia",
  "Australia": "Oceania",
  "New Zealand": "Oceania"
};

const COUNTRY_TO_NATIONALITY = {
  "United States of America": "American",
  "United States": "American",
  "United Kingdom": "British",
  "United Kingdom of Great Britain and Ireland": "British",
  "England": "British",
  "France": "French",
  "Germany": "German",
  "German Empire": "German",
  "Japan": "Japanese",
  "People's Republic of China": "Chinese",
  "China": "Chinese",
  "India": "Indian",
  "Canada": "Canadian",
  "Australia": "Australian"
};

const schemaState = {
  data: FALLBACK_SCHEMA,
  dimensions: FALLBACK_SCHEMA.dimensions,
  byId: new Map(FALLBACK_SCHEMA.dimensions.map((dimension) => [dimension.id, dimension])),
  loaded: false,
  source: "fallback"
};

const state = {
  currentRecord: null,
  currentEvidence: null,
  lastPrompt: "",
  assignmentMode: "mapped",
  assignmentQuery: ""
};

const el = {
  input: document.getElementById("entityInput"),
  type: document.getElementById("entityType"),
  run: document.getElementById("runButton"),
  status: document.getElementById("status"),
  resultName: document.getElementById("resultName"),
  resultDescription: document.getElementById("resultDescription"),
  badges: document.getElementById("badges"),
  empty: document.getElementById("emptyState"),
  content: document.getElementById("resultContent"),
  image: document.getElementById("wikiImage"),
  summary: document.getElementById("summaryText"),
  fieldGrid: document.getElementById("fieldGrid"),
  assignments: document.getElementById("assignmentList"),
  seedJson: document.getElementById("seedJson"),
  evidenceJson: document.getElementById("evidenceJson"),
  promptText: document.getElementById("promptText"),
  copy: document.getElementById("copyButton"),
  download: document.getElementById("downloadButton"),
  toast: document.getElementById("toast")
};

injectRuntimeStyles();
installAssignmentToolbar();

function injectRuntimeStyles() {
  const style = document.createElement("style");
  style.textContent = `
    .schema-note {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f7faf7;
      color: #3f5b36;
      padding: 9px 10px;
      font-size: 13px;
      margin: 12px 0 0;
    }

    .field-tools {
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr);
      gap: 8px;
      margin: 12px 0;
    }

    .assignment-meta {
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 13px;
    }

    .assignments {
      max-height: 520px;
      overflow: auto;
      padding-right: 4px;
    }

    .assignment.unsupported {
      background: #f7f8fa;
      color: var(--muted);
    }

    .assignment.unsupported .confidence {
      color: var(--muted);
    }

    .assignment-category {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }

    .assignment-desc {
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 12px;
    }

    @media (max-width: 640px) {
      .field-tools {
        grid-template-columns: 1fr;
      }
    }
  `;
  document.head.appendChild(style);
}

function installAssignmentToolbar() {
  const container = document.createElement("div");
  container.innerHTML = `
    <div class="field-tools">
      <select id="fieldMode" aria-label="Field view mode">
        <option value="mapped">Mapped values</option>
        <option value="all">All persona keys</option>
      </select>
      <input id="fieldSearch" type="search" placeholder="filter persona keys..." aria-label="Filter persona keys">
    </div>
    <p id="assignmentMeta" class="assignment-meta">Schema loading...</p>
  `;
  el.assignments.parentElement.insertBefore(container, el.assignments);
  el.fieldMode = document.getElementById("fieldMode");
  el.fieldSearch = document.getElementById("fieldSearch");
  el.assignmentMeta = document.getElementById("assignmentMeta");
  el.fieldMode.addEventListener("change", () => {
    state.assignmentMode = el.fieldMode.value;
    renderAssignments();
  });
  el.fieldSearch.addEventListener("input", () => {
    state.assignmentQuery = el.fieldSearch.value;
    renderAssignments();
  });
}

function showStatus(message, isError = false) {
  el.status.textContent = message;
  el.status.classList.toggle("error", isError);
  el.status.classList.add("active");
}

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("active");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    el.toast.classList.remove("active");
  }, 2200);
}

async function loadPersonaSchema() {
  if (schemaState.loaded) {
    return schemaState;
  }
  if (window.MATRAIX_DIMENSIONS?.dimensions?.length) {
    setSchema(window.MATRAIX_DIMENSIONS, "matraix.ai");
    return schemaState;
  }
  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = MATRAIX_SCHEMA_URL;
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("Could not load matrAIx persona schema."));
    document.head.appendChild(script);
  });
  if (!window.MATRAIX_DIMENSIONS?.dimensions?.length) {
    throw new Error("matrAIx persona schema did not expose dimensions.");
  }
  setSchema(window.MATRAIX_DIMENSIONS, "matraix.ai");
  return schemaState;
}

function setSchema(data, source) {
  schemaState.data = data;
  schemaState.dimensions = data.dimensions || [];
  schemaState.byId = new Map(schemaState.dimensions.map((dimension) => [dimension.id, dimension]));
  schemaState.loaded = true;
  schemaState.source = source;
}

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: { "Accept": "application/json" }
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function wikidataApi(params) {
  const url = new URL("https://www.wikidata.org/w/api.php");
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
  url.searchParams.set("format", "json");
  url.searchParams.set("origin", "*");
  return url.toString();
}

async function searchWikidata(name, expectedType) {
  const data = await fetchJson(wikidataApi({
    action: "wbsearchentities",
    search: name,
    language: "en",
    limit: "8"
  }));
  const candidates = data.search || [];
  if (!candidates.length) {
    throw new Error(`No Wikidata result for "${name}".`);
  }

  for (const candidate of candidates) {
    const entity = await getEntity(candidate.id);
    const inferred = inferEntityType(entity);
    if (!expectedType || inferred === expectedType) {
      return entity;
    }
  }
  return getEntity(candidates[0].id);
}

async function getEntity(qid) {
  const data = await fetchJson(wikidataApi({
    action: "wbgetentities",
    ids: qid,
    props: "labels|descriptions|claims|sitelinks",
    languages: "en"
  }));
  const entity = data.entities && data.entities[qid];
  if (!entity || entity.missing === "") {
    throw new Error(`Wikidata entity ${qid} was not found.`);
  }
  return entity;
}

function getEntityLabel(entity) {
  return entity.labels?.en?.value || entity.id;
}

function getEntityDescription(entity) {
  return entity.descriptions?.en?.value || "";
}

function claimValues(entity, propertyId) {
  return (entity.claims?.[propertyId] || [])
    .map((claim) => claim.mainsnak?.datavalue?.value)
    .filter(Boolean);
}

function claimQids(entity, propertyId) {
  return claimValues(entity, propertyId)
    .filter((value) => value && value["entity-type"] === "item")
    .map((value) => `Q${value["numeric-id"]}`);
}

function timeClaims(entity, propertyId) {
  return claimValues(entity, propertyId)
    .filter((value) => typeof value.time === "string")
    .map((value) => value.time.replace(/^\+/, "").replace(/T.*$/, ""));
}

async function getLabels(qids) {
  const unique = [...new Set(qids)].filter(Boolean);
  const labels = {};
  for (let index = 0; index < unique.length; index += 50) {
    const batch = unique.slice(index, index + 50);
    const data = await fetchJson(wikidataApi({
      action: "wbgetentities",
      ids: batch.join("|"),
      props: "labels|descriptions",
      languages: "en"
    }));
    Object.entries(data.entities || {}).forEach(([qid, entity]) => {
      labels[qid] = entity.labels?.en?.value || qid;
    });
  }
  return labels;
}

function inferEntityType(entity) {
  const description = getEntityDescription(entity).toLowerCase();
  const directInstances = claimQids(entity, CLAIMS.instance_of);
  if (directInstances.includes("Q5")) {
    return "real_person";
  }
  if (directInstances.includes("Q95074")) {
    return "fictional_character";
  }
  if (description.includes("fictional") || description.includes("character")) {
    return "fictional_character";
  }
  return "real_person";
}

async function getWikipediaSummary(entity) {
  const title = entity.sitelinks?.enwiki?.title || getEntityLabel(entity);
  const url = new URL("https://en.wikipedia.org/w/api.php");
  url.searchParams.set("action", "query");
  url.searchParams.set("format", "json");
  url.searchParams.set("origin", "*");
  url.searchParams.set("redirects", "1");
  url.searchParams.set("prop", "extracts|pageimages|info");
  url.searchParams.set("exintro", "1");
  url.searchParams.set("explaintext", "1");
  url.searchParams.set("piprop", "thumbnail");
  url.searchParams.set("pithumbsize", "900");
  url.searchParams.set("inprop", "url");
  url.searchParams.set("titles", title);

  const data = await fetchJson(url.toString());
  const pages = Object.values(data.query?.pages || {});
  const page = pages[0] || {};
  return {
    title: page.title || title,
    extract: page.extract || "",
    url: page.fullurl || `https://en.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`,
    thumbnail: page.thumbnail?.source || null
  };
}

function mapLabels(qids, labels, limit = 8) {
  return qids.slice(0, limit).map((qid) => labels[qid] || qid);
}

function first(values) {
  return values.find((value) => value !== null && value !== undefined && value !== "") || null;
}

function normalized(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function textIncludesAny(text, needles) {
  const haystack = normalized(Array.isArray(text) ? text.join(" ") : text);
  return needles.some((needle) => haystack.includes(normalized(needle)));
}

function allowedValue(field, candidates) {
  const dimension = schemaState.byId.get(field);
  const values = dimension?.values || [];
  if (!values.length) {
    return first(candidates);
  }
  const byNorm = new Map(values.map((value) => [normalized(value), value]));
  for (const candidate of candidates.flat().filter(Boolean)) {
    const exact = byNorm.get(normalized(candidate));
    if (exact) {
      return exact;
    }
  }
  return null;
}

function birthDateBucket(dateValue) {
  const year = Number(String(dateValue || "").slice(0, 4));
  if (!Number.isFinite(year)) {
    return null;
  }
  if (year < 1900) {
    return "1800s";
  }
  if (year < 1920) {
    return "1900-1920";
  }
  if (year < 1940) {
    return "1920-1940";
  }
  if (year < 1960) {
    return "1940-1960";
  }
  if (year < 1980) {
    return "1960-1980";
  }
  if (year < 2000) {
    return "1980-2000";
  }
  return "2000+";
}

function mapDomain(claimSets, summary) {
  const text = [claimSets.field_of_work, claimSets.occupation, summary].flat().join(" ");
  if (textIncludesAny(text, ["software", "computer science", "artificial intelligence", "machine learning", "data science"])) return "Software & AI";
  if (textIncludesAny(text, ["medicine", "physician", "clinical", "health", "nursing", "surgery", "cardiology"])) return "Healthcare & Medicine";
  if (textIncludesAny(text, ["law", "judge", "attorney", "legal", "constitution"])) return "Law & Policy";
  if (textIncludesAny(text, ["finance", "economics", "bank", "trading", "accounting"])) return "Finance & Economics";
  if (textIncludesAny(text, ["teacher", "professor", "education", "curriculum", "pedagogy"])) return "Education";
  if (textIncludesAny(text, ["engineer", "engineering", "robotics", "mechanical", "electrical"])) return "Engineering";
  if (textIncludesAny(text, ["physics", "chemist", "biology", "scientist", "astronomy", "mathematics"])) return "Natural Sciences";
  if (textIncludesAny(text, ["sociology", "psychology", "anthropology", "political science"])) return "Social Sciences";
  if (textIncludesAny(text, ["writer", "literature", "artist", "music", "film", "philosopher", "fictional character", "novel"])) return "Arts & Humanities";
  if (textIncludesAny(text, ["business", "manager", "entrepreneur", "operations"])) return "Business & Management";
  if (textIncludesAny(text, ["politician", "minister", "president", "government", "public sector"])) return "Public Sector";
  return null;
}

function mapRole(claimSets, summary) {
  const text = [claimSets.occupation, claimSets.position_held, summary].flat().join(" ");
  if (textIncludesAny(text, ["engineer", "engineering"])) return "Engineering";
  if (textIncludesAny(text, ["researcher", "scientist", "physicist", "chemist", "biologist", "mathematician"])) return "Research";
  if (textIncludesAny(text, ["designer", "architect"])) return "Design";
  if (textIncludesAny(text, ["sales", "go-to-market", "marketing"])) return "Sales / GTM";
  if (textIncludesAny(text, ["operations", "administrator"])) return "Operations";
  if (textIncludesAny(text, ["finance", "economist", "accountant"])) return "Finance";
  if (textIncludesAny(text, ["lawyer", "judge", "legal"])) return "Legal";
  if (textIncludesAny(text, ["doctor", "physician", "surgeon", "nurse", "clinical"])) return "Clinical";
  if (textIncludesAny(text, ["teacher", "professor", "educator"])) return "Teaching";
  if (textIncludesAny(text, ["president", "ceo", "founder", "executive", "minister", "governor"])) return "Executive";
  return null;
}

function mapSubjectSpecialty(claimSets, summary) {
  const text = [claimSets.field_of_work, claimSets.occupation, summary].flat().join(" ");
  const mappings = [
    ["Machine learning", ["machine learning", "artificial intelligence", "deep learning"]],
    ["Cardiology", ["cardiology", "cardiologist"]],
    ["Constitutional law", ["constitutional law"]],
    ["Quant trading", ["quantitative trading", "quant trading"]],
    ["Curriculum design", ["curriculum design"]],
    ["Structural engineering", ["structural engineering"]],
    ["Molecular biology", ["molecular biology"]],
    ["Behavioral economics", ["behavioral economics"]],
    ["Comparative literature", ["comparative literature"]],
    ["Operations", ["operations"]],
    ["Agronomy", ["agronomy"]],
    ["Robotics", ["robotics"]],
    ["Investigative reporting", ["investigative reporting"]],
    ["Urban planning", ["urban planning"]],
    ["Culinary arts", ["culinary arts"]],
    ["Electrical work", ["electrical work", "electrician"]]
  ];
  return first(mappings.filter(([, needles]) => textIncludesAny(text, needles)).map(([value]) => value));
}

function mapAcademicField(claimSets, summary) {
  const text = [claimSets.field_of_work, claimSets.occupation, claimSets.education, summary].flat().join(" ");
  if (textIncludesAny(text, ["science", "physics", "engineering", "mathematics", "computer", "biology", "chemistry"])) return "STEM";
  if (textIncludesAny(text, ["medicine", "physician", "clinical", "health"])) return "Medicine";
  if (textIncludesAny(text, ["law", "legal", "judge"])) return "Law";
  if (textIncludesAny(text, ["business", "management", "finance", "economics"])) return "Business";
  if (textIncludesAny(text, ["literature", "history", "philosophy", "humanities"])) return "Humanities";
  if (textIncludesAny(text, ["sociology", "psychology", "political science", "anthropology"])) return "Social science";
  if (textIncludesAny(text, ["art", "music", "film", "theater", "architecture"])) return "Arts";
  return null;
}

function mapHighestEducation(summary, education) {
  const text = [summary, education].flat().join(" ");
  if (textIncludesAny(text, ["postdoctoral", "postdoc"])) return "Postdoc";
  if (textIncludesAny(text, ["doctorate", "doctoral", "phd", "ph.d"])) return "Doctorate";
  if (textIncludesAny(text, ["master", "msc", "m.sc", "ma ", "m.a."])) return "Master's";
  if (textIncludesAny(text, ["bachelor", "undergraduate", "bsc", "b.sc", "ba ", "b.a."])) return "Bachelor's";
  if (textIncludesAny(text, ["vocational", "certificate"])) return "Vocational / cert";
  if (textIncludesAny(text, ["secondary", "high school"])) return "Secondary";
  if (textIncludesAny(text, ["primary school"])) return "Primary";
  return null;
}

function mapWikiEducation(summary, education) {
  const highest = mapHighestEducation(summary, education);
  const map = {
    "No formal": "No formal education",
    "Primary": "Primary",
    "Secondary": "Secondary",
    "Bachelor's": "Bachelor's degree",
    "Master's": "Master's degree",
    "Doctorate": "Doctorate",
    "Postdoc": "Postdoctoral"
  };
  return map[highest] || null;
}

function mapWikiOccupation(claimSets, summary) {
  const text = [claimSets.occupation, summary].flat().join(" ");
  if (textIncludesAny(text, ["scientist", "physicist", "chemist", "biologist", "mathematician"])) return "Scientist";
  if (textIncludesAny(text, ["politician", "minister", "president", "governor", "mayor"])) return "Politician";
  if (textIncludesAny(text, ["artist", "writer", "poet", "novelist", "composer", "painter", "sculptor"])) return "Artist";
  if (textIncludesAny(text, ["athlete", "player", "footballer", "olympic"])) return "Athlete";
  if (textIncludesAny(text, ["entrepreneur", "founder", "businessperson"])) return "Entrepreneur";
  if (textIncludesAny(text, ["actor", "actress", "singer", "performer", "entertainer"])) return "Entertainer";
  if (textIncludesAny(text, ["academic", "professor", "scholar"])) return "Academic";
  if (textIncludesAny(text, ["military", "general", "admiral", "soldier"])) return "Military";
  if (textIncludesAny(text, ["religious", "bishop", "archbishop", "priest", "rabbi", "imam"])) return "Religious";
  return claimSets.occupation.length ? "Other" : null;
}

function mapWikiField(claimSets, summary) {
  const text = [claimSets.field_of_work, claimSets.occupation, summary].flat().join(" ");
  if (textIncludesAny(text, ["physics", "physicist"])) return "Physics";
  if (textIncludesAny(text, ["medicine", "medical", "physician", "clinical"])) return "Medicine";
  if (textIncludesAny(text, ["literature", "writer", "novelist", "poet"])) return "Literature";
  if (textIncludesAny(text, ["politics", "political", "government", "minister", "president"])) return "Politics";
  if (textIncludesAny(text, ["law", "legal", "judge"])) return "Law";
  if (textIncludesAny(text, ["engineering", "engineer"])) return "Engineering";
  if (textIncludesAny(text, ["business", "entrepreneur", "management"])) return "Business";
  if (textIncludesAny(text, ["art", "music", "film", "theater", "architecture"])) return "Arts";
  if (textIncludesAny(text, ["sport", "athlete", "football", "basketball", "olympic"])) return "Sports";
  if (textIncludesAny(text, ["religion", "religious", "theology"])) return "Religion";
  return null;
}

function mapPosition(positionLabels) {
  const text = positionLabels.join(" ");
  if (textIncludesAny(text, ["chief executive officer", "ceo"])) return "CEO";
  if (textIncludesAny(text, ["president"])) return "President";
  if (textIncludesAny(text, ["minister"])) return "Minister";
  if (textIncludesAny(text, ["governor"])) return "Governor";
  if (textIncludesAny(text, ["mayor"])) return "Mayor";
  if (textIncludesAny(text, ["archbishop"])) return "Archbishop";
  if (textIncludesAny(text, ["chancellor"])) return "Chancellor";
  if (textIncludesAny(text, ["general"])) return "General";
  if (textIncludesAny(text, ["ambassador"])) return "Ambassador";
  return positionLabels.length ? "None" : null;
}

function mapAward(awardLabels) {
  const text = awardLabels.join(" ");
  if (textIncludesAny(text, ["nobel"])) return "Nobel Prize";
  if (textIncludesAny(text, ["academy award", "oscar"])) return "Academy Award";
  if (textIncludesAny(text, ["pulitzer"])) return "Pulitzer Prize";
  if (textIncludesAny(text, ["emmy"])) return "Emmy Award";
  if (textIncludesAny(text, ["olympic"])) return "Olympic Medal";
  if (textIncludesAny(text, ["grammy"])) return "Grammy Award";
  return awardLabels.length ? "Other major award" : null;
}

function mapPolitical(partyLabels) {
  const text = partyLabels.join(" ");
  if (textIncludesAny(text, ["democratic"])) return "Democratic";
  if (textIncludesAny(text, ["republican"])) return "Republican";
  if (textIncludesAny(text, ["conservative"])) return "Conservative";
  if (textIncludesAny(text, ["labour", "labor"])) return "Labour";
  if (textIncludesAny(text, ["green"])) return "Green";
  if (textIncludesAny(text, ["independent"])) return "Independent";
  if (textIncludesAny(text, ["progressive"])) return "Progressive";
  if (textIncludesAny(text, ["socialist"])) return "Socialist";
  if (textIncludesAny(text, ["liberal"])) return "Liberal";
  return partyLabels.length ? "Other" : null;
}

function evidenceQuote(summary, value) {
  if (!summary || !value) {
    return null;
  }
  const sentences = summary.match(/[^.!?]+[.!?]+/g) || [summary];
  const lowerValue = String(value).toLowerCase();
  return first(sentences.filter((sentence) => sentence.toLowerCase().includes(lowerValue))) ||
    sentences[0]?.trim() ||
    null;
}

function initDimensions() {
  const dimensions = {};
  EXTRA_FIELD_DEFS.forEach((field) => {
    dimensions[field.id] = null;
  });
  schemaState.dimensions.forEach((dimension) => {
    dimensions[dimension.id] = null;
  });
  return dimensions;
}

function labelForField(field) {
  return schemaState.byId.get(field)?.label ||
    EXTRA_FIELD_DEFS.find((item) => item.id === field)?.label ||
    field;
}

function definitionForField(field) {
  return schemaState.byId.get(field) ||
    EXTRA_FIELD_DEFS.find((item) => item.id === field) ||
    { id: field, label: field, category: "Unknown", description: "", values: [] };
}

function targetFieldDefs() {
  const seen = new Set();
  return [...EXTRA_FIELD_DEFS, ...schemaState.dimensions].filter((definition) => {
    if (seen.has(definition.id)) {
      return false;
    }
    seen.add(definition.id);
    return true;
  });
}

function buildAssignments(dimensions, assignmentMeta, summary) {
  return targetFieldDefs().map((definition) => {
    const value = dimensions[definition.id] || null;
    const meta = assignmentMeta[definition.id] || {};
    const quote = meta.evidence || evidenceQuote(summary, Array.isArray(value) ? value[0] : value);
    return {
      field: definition.id,
      label: definition.label,
      category: definition.category || "Uncategorized",
      value,
      evidence_quotes: value ? [quote || `Derived from Wikidata/Wikipedia evidence: ${value}`] : [],
      confidence: value ? (meta.confidence || 0.82) : 0.0,
      assignment_type: value ? (meta.assignment_type || "structured_claim_or_summary_hint") : "unsupported"
    };
  });
}

function buildPrompt(record, evidence) {
  const targetFields = targetFieldDefs()
    .map((definition) => `- ${definition.id}: ${definition.label} (${definition.category || "Uncategorized"})`)
    .join("\n");
  return [
    "You are assigning matrAIx persona fields from Wikipedia/Wikidata evidence.",
    "Use only the evidence below. Return null when unsupported.",
    "",
    `Schema source: ${MATRAIX_SCHEMA_URL}`,
    `Target fields (${targetFieldDefs().length}):`,
    targetFields,
    "",
    "Wikipedia summary:",
    evidence.wikipedia_summary || "",
    "",
    "Wikidata claims:",
    JSON.stringify(evidence.wikidata_claims, null, 2),
    "",
    "Current seed dimensions:",
    JSON.stringify(record.persona.dimensions, null, 2)
  ].join("\n");
}

function buildRecord(entity, summary, labels, expectedType) {
  const entityType = expectedType || inferEntityType(entity);
  const label = getEntityLabel(entity);

  const claimSets = {
    instance_of: mapLabels(claimQids(entity, CLAIMS.instance_of), labels),
    occupation: mapLabels(claimQids(entity, CLAIMS.occupation), labels),
    country_of_citizenship: mapLabels(claimQids(entity, CLAIMS.country_of_citizenship), labels),
    sex_or_gender: mapLabels(claimQids(entity, CLAIMS.sex_or_gender), labels, 2),
    languages: mapLabels(claimQids(entity, CLAIMS.languages), labels),
    field_of_work: mapLabels(claimQids(entity, CLAIMS.field_of_work), labels),
    notable_work: mapLabels(claimQids(entity, CLAIMS.notable_work), labels),
    creator: mapLabels(claimQids(entity, CLAIMS.creator), labels),
    present_in_work: mapLabels(claimQids(entity, CLAIMS.present_in_work), labels),
    fictional_universe: mapLabels(claimQids(entity, CLAIMS.fictional_universe), labels),
    birth_place: mapLabels(claimQids(entity, CLAIMS.birth_place), labels),
    position_held: mapLabels(claimQids(entity, CLAIMS.position_held), labels),
    education: mapLabels(claimQids(entity, CLAIMS.education), labels),
    awards: mapLabels(claimQids(entity, CLAIMS.awards), labels),
    political_party: mapLabels(claimQids(entity, CLAIMS.political_party), labels)
  };

  const dimensions = initDimensions();
  const assignmentMeta = {};
  const birthDate = first(timeClaims(entity, CLAIMS.date_of_birth));
  const deathDate = first(timeClaims(entity, CLAIMS.date_of_death));
  const country = first(claimSets.country_of_citizenship);
  const knownFor = first(claimSets.notable_work) ||
    first(claimSets.present_in_work) ||
    first(claimSets.fictional_universe);

  function setField(field, value, meta = {}) {
    if (value === null || value === undefined || value === "") {
      return;
    }
    dimensions[field] = value;
    assignmentMeta[field] = meta;
  }

  function setAllowedField(field, candidates, meta = {}) {
    const value = allowedValue(field, candidates);
    if (value) {
      setField(field, value, meta);
    }
  }

  setField("source_entity_type", entityType, { assignment_type: "direct", confidence: 0.99 });
  setField("identity_name", label, { assignment_type: "direct", confidence: 0.99 });
  setField("known_for_or_source_work", knownFor, { assignment_type: "structured_claim", confidence: 0.86 });
  setField("creator", first(claimSets.creator), { assignment_type: "structured_claim", confidence: 0.9 });
  setField("birth_date", birthDate, { assignment_type: "structured_claim", confidence: 0.95 });
  setField("death_date", deathDate, { assignment_type: "structured_claim", confidence: 0.95 });

  setAllowedField("gender_identity", [first(claimSets.sex_or_gender) === "male" ? "Man" : null, first(claimSets.sex_or_gender) === "female" ? "Woman" : null], {
    assignment_type: "structured_claim",
    confidence: 0.9
  });
  setAllowedField("primary_language", [first(claimSets.languages)], {
    assignment_type: "structured_claim",
    confidence: 0.82
  });
  setAllowedField("region", [COUNTRY_TO_REGION[country]], {
    assignment_type: "structured_claim",
    confidence: 0.82
  });
  setAllowedField("wiki_birth_date", [birthDateBucket(birthDate)], {
    assignment_type: "structured_claim",
    confidence: 0.92
  });
  setAllowedField("wiki_nationality", country ? [COUNTRY_TO_NATIONALITY[country], "Other"] : [], {
    assignment_type: "structured_claim",
    confidence: COUNTRY_TO_NATIONALITY[country] ? 0.88 : 0.55
  });
  setAllowedField("domain", [mapDomain(claimSets, summary.extract)], {
    assignment_type: "summary_inference",
    confidence: 0.7
  });
  setAllowedField("role_function", [mapRole(claimSets, summary.extract)], {
    assignment_type: "summary_inference",
    confidence: 0.7
  });
  setAllowedField("subject_specialty", [mapSubjectSpecialty(claimSets, summary.extract)], {
    assignment_type: "summary_inference",
    confidence: 0.66
  });
  setAllowedField("academic_field", [mapAcademicField(claimSets, summary.extract)], {
    assignment_type: "summary_inference",
    confidence: 0.68
  });
  setAllowedField("highest_education", [mapHighestEducation(summary.extract, claimSets.education)], {
    assignment_type: "summary_inference",
    confidence: 0.64
  });
  setAllowedField("wiki_occupation", [mapWikiOccupation(claimSets, summary.extract)], {
    assignment_type: "summary_inference",
    confidence: 0.72
  });
  setAllowedField("wiki_field_of_work", [mapWikiField(claimSets, summary.extract)], {
    assignment_type: "summary_inference",
    confidence: 0.72
  });
  setAllowedField("wiki_position_held", [mapPosition(claimSets.position_held)], {
    assignment_type: "structured_claim",
    confidence: 0.78
  });
  setAllowedField("wiki_education_level", [mapWikiEducation(summary.extract, claimSets.education)], {
    assignment_type: "summary_inference",
    confidence: 0.62
  });
  setAllowedField("wiki_awards_recognition", [mapAward(claimSets.awards)], {
    assignment_type: "structured_claim",
    confidence: 0.82
  });
  setAllowedField("wiki_political_affiliation", [mapPolitical(claimSets.political_party)], {
    assignment_type: "structured_claim",
    confidence: 0.78
  });

  const evidence = {
    wikidata_qid: entity.id,
    wikipedia_title: summary.title,
    wikipedia_url: summary.url,
    wikipedia_summary: summary.extract,
    wikidata_claims: claimSets
  };

  const assignments = buildAssignments(dimensions, assignmentMeta, summary.extract);
  const mappedCount = assignments.filter((assignment) => assignment.value).length;
  const record = {
    metadata: {
      source: "wikidata_wikipedia_browser_demo",
      qid: entity.id,
      entity_type: entityType,
      wikipedia_language: "en",
      wikipedia_title: summary.title,
      schema_source: MATRAIX_SCHEMA_URL,
      schema_version: schemaState.data.schemaVersion || null,
      schema_dimension_count: schemaState.dimensions.length,
      mapped_dimension_count: mappedCount,
      generated_at: new Date().toISOString()
    },
    persona: {
      name: label,
      summary: summary.extract,
      dimensions,
      llm_field_assignments: assignments
    },
    source_evidence: evidence,
    validation: {
      mode: "browser_demo_rule_based",
      notes: [
        "This online demo loads the matrAIx persona schema from matraix.ai/persona.html's dimensions.js.",
        "Fields without direct or conservative rule-based support are preserved as null.",
        "The PR script can run Claude Code over the same seed record for production curation."
      ]
    }
  };
  return { record, evidence };
}

function renderRecord(record, evidence, thumbnail) {
  state.currentRecord = record;
  state.currentEvidence = evidence;
  state.lastPrompt = buildPrompt(record, evidence);

  el.empty.hidden = true;
  el.content.hidden = false;
  el.resultName.textContent = record.persona.name;
  el.resultDescription.textContent = record.metadata.wikipedia_title;
  el.summary.textContent = record.persona.summary || "No English Wikipedia summary found.";

  if (thumbnail) {
    el.image.src = thumbnail;
    el.image.alt = `${record.persona.name} image from Wikipedia`;
    el.image.style.display = "block";
  } else {
    el.image.removeAttribute("src");
    el.image.alt = "";
    el.image.style.display = "none";
  }

  el.badges.innerHTML = "";
  [
    record.metadata.entity_type.replace("_", " "),
    record.metadata.qid,
    `${record.metadata.schema_dimension_count} persona keys`,
    `${record.metadata.mapped_dimension_count} mapped`
  ].forEach((text, index) => {
    const badge = document.createElement("span");
    badge.className = `badge ${index === 0 ? "green" : index === 2 ? "gold" : ""}`;
    badge.textContent = text;
    el.badges.appendChild(badge);
  });

  renderFieldSummary(record);
  renderAssignments();
  el.seedJson.textContent = JSON.stringify(record, null, 2);
  el.evidenceJson.textContent = JSON.stringify(evidence, null, 2);
  el.promptText.textContent = state.lastPrompt;
}

function renderFieldSummary(record) {
  const priorityFields = [
    "source_entity_type",
    "identity_name",
    "domain",
    "role_function",
    "subject_specialty",
    "academic_field",
    "wiki_occupation",
    "wiki_field_of_work",
    "wiki_birth_date",
    "wiki_nationality",
    "wiki_awards_recognition",
    "known_for_or_source_work"
  ];
  const mappedFields = priorityFields
    .filter((field) => record.persona.dimensions[field])
    .slice(0, 10);

  el.fieldGrid.innerHTML = "";
  mappedFields.forEach((field) => {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = labelForField(field);
    const value = record.persona.dimensions[field];
    dd.textContent = Array.isArray(value) ? value.join(", ") : value || "null";
    wrapper.append(dt, dd);
    el.fieldGrid.appendChild(wrapper);
  });

  const note = document.createElement("p");
  note.className = "schema-note";
  note.textContent = `Loaded ${record.metadata.schema_dimension_count} persona keys from matraix.ai; ${record.metadata.mapped_dimension_count} have conservative demo values and the rest are null.`;
  el.fieldGrid.appendChild(note);
}

function renderAssignments() {
  if (!state.currentRecord) {
    return;
  }
  const query = normalized(state.assignmentQuery);
  const assignments = state.currentRecord.persona.llm_field_assignments
    .filter((assignment) => state.assignmentMode === "all" || assignment.value)
    .filter((assignment) => {
      if (!query) {
        return true;
      }
      const definition = definitionForField(assignment.field);
      return normalized(`${assignment.field} ${assignment.label} ${assignment.category} ${definition.description || ""} ${assignment.value || ""}`).includes(query);
    })
    .sort((left, right) => {
      if (Boolean(left.value) !== Boolean(right.value)) {
        return left.value ? -1 : 1;
      }
      return left.field.localeCompare(right.field);
    });

  el.assignmentMeta.textContent =
    `${assignments.length} shown | ${state.currentRecord.metadata.mapped_dimension_count} mapped | ${state.currentRecord.metadata.schema_dimension_count} matrAIx schema dimensions`;
  el.assignments.innerHTML = "";
  assignments.forEach((assignment) => {
    const definition = definitionForField(assignment.field);
    const item = document.createElement("article");
    item.className = `assignment ${assignment.value ? "" : "unsupported"}`;

    const head = document.createElement("div");
    head.className = "assignment-head";
    const name = document.createElement("div");
    name.className = "assignment-name";
    name.textContent = `${assignment.label || labelForField(assignment.field)} (${assignment.field})`;

    const category = document.createElement("span");
    category.className = "assignment-category";
    category.textContent = assignment.category || definition.category || "Uncategorized";
    name.appendChild(category);

    const confidence = document.createElement("div");
    confidence.className = "confidence";
    confidence.textContent = `${Math.round(assignment.confidence * 100)}%`;
    head.append(name, confidence);

    const value = document.createElement("p");
    value.className = "assignment-value";
    value.textContent = assignment.value || "null";

    const evidenceLine = document.createElement("p");
    evidenceLine.className = "assignment-evidence";
    evidenceLine.textContent = assignment.evidence_quotes[0] || assignment.assignment_type;

    const desc = document.createElement("p");
    desc.className = "assignment-desc";
    const values = definition.values?.length ? `Allowed values: ${definition.values.slice(0, 8).join(", ")}${definition.values.length > 8 ? "..." : ""}` : "Open or metadata field";
    desc.textContent = `${definition.description || "No description."} ${values}`;

    item.append(head, value, evidenceLine, desc);
    el.assignments.appendChild(item);
  });
}

async function runLookup() {
  const raw = el.input.value.trim();
  if (!raw) {
    showStatus("Enter a name or Wikidata QID.", true);
    return;
  }
  const expectedType = el.type.value || null;
  const started = performance.now();
  showStatus("Loading matrAIx persona schema...");
  el.run.disabled = true;
  try {
    await loadPersonaSchema();
    showStatus("Resolving Wikidata entity and Wikipedia summary...");
    const entity = /^Q\d+$/i.test(raw)
      ? await getEntity(raw.toUpperCase())
      : await searchWikidata(raw, expectedType);

    const allQids = Object.values(CLAIMS).flatMap((propertyId) => claimQids(entity, propertyId));
    showStatus("Loading linked claim labels...");
    const [labels, summary] = await Promise.all([
      getLabels(allQids),
      getWikipediaSummary(entity)
    ]);

    const { record, evidence } = buildRecord(entity, summary, labels, expectedType);
    renderRecord(record, evidence, summary.thumbnail);
    const elapsed = Math.round(performance.now() - started);
    showStatus(`Loaded ${record.persona.name}: ${record.metadata.mapped_dimension_count}/${record.metadata.schema_dimension_count} schema keys mapped in ${elapsed} ms.`);
  } catch (error) {
    console.error(error);
    showStatus(error.message || "Lookup failed.", true);
  } finally {
    el.run.disabled = false;
  }
}

function setTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.tab === name));
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${name}`);
  });
}

async function copyJson() {
  if (!state.currentRecord) {
    showToast("No record to copy yet.");
    return;
  }
  await navigator.clipboard.writeText(JSON.stringify(state.currentRecord, null, 2));
  showToast("Persona seed JSON copied.");
}

function downloadJson() {
  if (!state.currentRecord) {
    showToast("No record to download yet.");
    return;
  }
  const slug = state.currentRecord.persona.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const blob = new Blob([JSON.stringify(state.currentRecord, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${slug || "persona-seed"}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

el.run.addEventListener("click", runLookup);
el.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    runLookup();
  }
});
document.querySelectorAll(".examples button").forEach((button) => {
  button.addEventListener("click", () => {
    el.input.value = button.dataset.qid;
    el.type.value = button.dataset.type;
    runLookup();
  });
});
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => setTab(tab.dataset.tab));
});
el.copy.addEventListener("click", copyJson);
el.download.addEventListener("click", downloadJson);

runLookup();
