import Link from "next/link";
import { notFound } from "next/navigation";

import ChartPreview from "@/components/ChartPreview";
import CopyButton from "@/components/CopyButton";
import CoverGraphics from "@/components/CoverGraphics";
import type { ChartFacts, Cover, Row, Spec } from "@/lib/graphics/alt.ts";
import ClaudeUsage from "@/components/ClaudeUsage";
import { ClaudeDraftForm, EditForm, PasteForm, StatusButtons } from "@/components/StoryForms";
import VerifyReport from "@/components/VerifyReport";
import { db } from "@/lib/db";
import { when } from "@/lib/format";
import type { Story } from "@/lib/types";
import { pageGate } from "@/lib/gate";
import { buildPrompt } from "@/lib/logic/narrate.ts";

export const dynamic = "force-dynamic";

const NOUNS: Record<string, string> = {
  country: "UK nations",
  region: "regions",
  local_authority: "local authorities",
};

/** The main chart plus any `more_charts` stored with it. */
function specsOf(spec: Record<string, unknown>): Spec[] {
  const { more_charts: more, ...main } = spec as Spec & { more_charts?: Spec[] };
  return [main, ...(more ?? [])];
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function StoryPage({ params }: { params: Promise<{ id: string }> }) {
  const gate = await pageGate();
  if (gate) return gate;
  const { id } = await params;
  if (!UUID.test(id)) notFound();
  const { data: story, error } = await db().from("stories").select("*").eq("id", id).maybeSingle<Story>();
  if (error) throw new Error(error.message);
  if (!story) notFound();

  const prompt = buildPrompt(story.numbers ?? {}, story.chart_data ?? [], story.chart_spec ?? {});
  const locked = story.status === "approved" || story.status === "published";
  const claims = (story.verify_report?.claims ?? []).map((c) => ({
    sentence: c.sentence,
    keys: c.keys,
    checks: (c.checks ?? []).map((ch) => ({
      kind: ch.kind,
      ...(ch.group ? { group: ch.group } : {}),
      ...(ch.period ? { period: ch.period } : {}),
      ...(ch.start ? { start: ch.start } : {}),
      ...(ch.end ? { end: ch.end } : {}),
    })),
  }));
  const passed = story.verify_status === "passed";

  return (
    <>
      <p className="small">
        <Link href="/stories">← Stories</Link>
      </p>
      <h1>{story.headline}</h1>
      <p className="row">
        <span className="badge plain">{story.status}</span>
        <span className={`badge ${passed ? "ok" : story.verify_status === "failed" ? "bad" : "warn"}`}>
          verification {story.verify_status}
        </span>
        {story.drafted_by === "claude" && <span className="badge claude">Drafted by Claude</span>}
        <span className="small muted">
          slug <code>{story.slug}</code> · {story.finding_ids.length} findings · updated{" "}
          {when(story.updated_at)}
        </span>
      </p>

      {story.draft_note && (
        <p className={`msg ${story.status === "failed" ? "bad" : "warn"}`} role="status">
          {story.draft_note}
        </p>
      )}
      <ClaudeUsage compact />

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Draft with Claude</h2>
        <ClaudeDraftForm storyId={story.id} locked={locked} />
        <p className="small muted">Or use the copy-paste flow below as a backup.</p>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Review decision</h2>
        <StatusButtons story={story} />
      </div>

      <div className="grid2">
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>1. Copy the prompt</h2>
          <p className="small muted">
            {prompt.length.toLocaleString("en-GB")} characters. Paste it into Claude chat, then
            paste the JSON reply in step 2.
          </p>
          <CopyButton text={prompt} />
          <details style={{ marginTop: "0.6rem" }}>
            <summary className="small">Show prompt</summary>
            <pre className="box small">{prompt}</pre>
          </details>
        </div>
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>2. Paste the reply</h2>
          <PasteForm storyId={story.id} locked={locked} />
        </div>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Verification report</h2>
        <VerifyReport report={story.verify_report} />
      </div>

      {story.chart_data && story.chart_spec && story.headline && (
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Graphics</h2>
          <CoverGraphics
            slug={story.slug}
            headline={story.headline}
            cover={((story.numbers ?? {}) as { cover?: Cover }).cover ?? {}}
            specs={specsOf(story.chart_spec)}
            data={story.chart_data as Row[]}
            source={((story.numbers ?? {}) as { source?: { publisher?: string } }).source?.publisher}
            groupNoun={NOUNS[String((story.numbers ?? {}).geo_level ?? "")]}
            facts={((story.numbers ?? {}) as { chart_facts?: ChartFacts }).chart_facts}
          />
        </div>
      )}

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Chart preview</h2>
        {story.chart_data && story.chart_spec ? (
          <ChartPreview data={story.chart_data} spec={story.chart_spec as Record<string, never>} />
        ) : (
          <p className="muted">No chart data.</p>
        )}
        <details>
          <summary className="small">Chart data ({story.chart_data?.length ?? 0} rows) and spec</summary>
          <pre className="box small">{JSON.stringify(story.chart_spec, null, 1)}</pre>
          <pre className="box small">{JSON.stringify(story.chart_data, null, 1)}</pre>
        </details>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>3. Edit and re-verify</h2>
        <EditForm story={story} claimsJson={JSON.stringify(claims, null, 2)} />
      </div>

      <div className="panel">
        <details>
          <summary>Numbers behind this story</summary>
          <pre className="box small">{JSON.stringify(story.numbers, null, 1)}</pre>
        </details>
      </div>
    </>
  );
}
