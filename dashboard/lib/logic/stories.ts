/**
 * TypeScript ports of worker/datatales/candidates.py (shortlist) and stories.slugify.
 * Must match Python (checked against worker/tests/golden/cases.json).
 */

export type FindingRow = {
  id: string;
  detector: string;
  title_hint: string;
  score: number;
  numbers: Record<string, unknown>;
};

export type Candidate = {
  geography: string;
  geo_level: string | null;
  good_news: boolean;
  findings: FindingRow[];
  measures: string[];
  finding_ids: string[];
  score: number;
  title: string;
};

export const SHORTLIST_SIZE = 5;
export const MAX_PER_GEOGRAPHY = 2;
const CORROBORATION_BONUS = 0.15;

const round4 = (x: number) => Math.round(x * 1e4) / 1e4;

function cmp<T>(a: T, b: T): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function groupFindings(findings: FindingRow[]): Candidate[] {
  const groups = new Map<string, Candidate>();
  for (const f of findings) {
    const n = f.numbers;
    const geography = String(n.group ?? "None");
    const level = (n.geo_level as string | null | undefined) ?? null;
    const good = Boolean(n.good_news);
    const key = JSON.stringify([geography, level, good]);
    if (!groups.has(key)) {
      groups.set(key, {
        geography, geo_level: level, good_news: good, findings: [], measures: [], finding_ids: [], score: 0, title: "",
      }); // prettier-ignore
    }
    groups.get(key)!.findings.push(f);
  }
  for (const c of groups.values()) {
    c.findings.sort((a, b) => b.score - a.score || cmp(a.detector, b.detector) || cmp(a.id, b.id));
    c.measures = [...new Set(c.findings.map((f) => String(f.numbers.measure ?? "None")))].sort();
    c.finding_ids = c.findings.map((f) => f.id);
    const bonus = 1 + CORROBORATION_BONUS * (c.measures.length - 1);
    c.score = round4(Math.min(1, c.findings[0].score * bonus));
    c.title = `${c.geography} (${c.geo_level ?? "None"}): ${c.good_news ? "good news" : "bad news"} on ${c.measures.join(", ")}`;
  }
  return [...groups.values()].sort(
    (a, b) => b.score - a.score || cmp(a.geography, b.geography) || Number(!a.good_news) - Number(!b.good_news),
  );
}

export function shortlist(findings: FindingRow[], size = SHORTLIST_SIZE, perGeo = MAX_PER_GEOGRAPHY): Candidate[] {
  const picked: Candidate[] = [];
  const count = new Map<string, number>();
  for (const c of groupFindings(findings)) {
    if ((count.get(c.geography) ?? 0) >= perGeo) continue;
    picked.push(c);
    count.set(c.geography, (count.get(c.geography) ?? 0) + 1);
    if (picked.length === size) break;
  }
  return picked;
}

export function slugify(text: string, maxLen = 80): string {
  const spaced = text.replace(/[‐-―−/]/g, " ");
  const ascii = spaced.normalize("NFKD").replace(/[^\x00-\x7F]/g, "");
  const slug = ascii.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return slug.slice(0, maxLen).replace(/-+$/, "") || "story";
}
