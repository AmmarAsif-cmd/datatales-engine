import Link from "next/link";

import { db, must } from "@/lib/db";
import { pageGate } from "@/lib/gate";
import { when } from "@/lib/format";

export const dynamic = "force-dynamic";

type Row = {
  id: string;
  slug: string;
  headline: string | null;
  status: string;
  verify_status: string;
  updated_at: string;
  finding_ids: string[];
  drafted_by: string | null;
};

const STATUS_BADGE: Record<string, string> = {
  draft: "plain",
  approved: "ok",
  rejected: "bad",
  published: "ok",
  failed: "bad",
};

export default async function StoriesPage() {
  const gate = await pageGate();
  if (gate) return gate;
  const stories = await must<Row[]>(
    db()
      .from("stories")
      .select("id, slug, headline, status, verify_status, updated_at, finding_ids, drafted_by")
      .order("updated_at", { ascending: false }),
  );
  return (
    <>
      <h1>Stories</h1>
      {!stories.length && (
        <p className="muted">
          No stories yet. Create one from the <Link href="/findings">findings shortlist</Link>.
        </p>
      )}
      {stories.length > 0 && (
        <div className="panel">
          <table className="stack">
            <thead>
              <tr>
                <th>Headline</th>
                <th>Status</th>
                <th>Verification</th>
                <th className="num">Findings</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {stories.map((s) => (
                <tr key={s.id}>
                  <td data-label="Headline">
                    <Link href={`/stories/${s.id}`}>{s.headline ?? "(untitled)"}</Link>
                    <div className="small muted">{s.slug}</div>
                  </td>
                  <td data-label="Status">
                    <span className={`badge ${STATUS_BADGE[s.status] ?? "plain"}`}>{s.status}</span>
                    {s.drafted_by === "claude" && <span className="badge claude">Claude</span>}
                  </td>
                  <td data-label="Verification">
                    <span
                      className={`badge ${s.verify_status === "passed" ? "ok" : s.verify_status === "failed" ? "bad" : "warn"}`}
                    >
                      {s.verify_status}
                    </span>
                  </td>
                  <td className="num" data-label="Findings">{s.finding_ids.length}</td>
                  <td className="small" data-label="Updated">{when(s.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
