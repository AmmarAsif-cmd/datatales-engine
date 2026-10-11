import BacklogActions from "@/components/BacklogActions";
import { RunDiscoveryButton } from "@/components/Buttons";
import { db, must } from "@/lib/db";
import { when } from "@/lib/format";
import { pageGate } from "@/lib/gate";

export const dynamic = "force-dynamic";

type Item = {
  id: string;
  title: string;
  publisher: string;
  source_url: string;
  catalogue: "data_gov_uk" | "ons" | "seed";
  licence: string;
  formats: string[];
  update_frequency: string | null;
  geography_levels: string[];
  has_time_series: boolean | null;
  score: number | null;
  pitch: string | null;
  status: "suggested" | "accepted" | "rejected" | "ingested";
  reject_reason: string | null;
  error: string | null;
  source_slug: string | null;
  created_at: string;
};

const CATALOGUE: Record<Item["catalogue"], string> = {
  data_gov_uk: "data.gov.uk",
  ons: "ONS",
  seed: "curated list",
};
const LEVEL: Record<string, string> = {
  local_authority: "local authorities",
  region: "regions",
  country: "nations",
};

function Card({ item }: { item: Item }) {
  const levels = item.geography_levels.map((l) => LEVEL[l] ?? l).join(", ");
  return (
    <div className="panel">
      <div className="row">
        {item.score !== null && <span className="badge plain score">{item.score}</span>}
        <h3 style={{ margin: 0 }}>
          <a href={item.source_url} target="_blank" rel="noreferrer">
            {item.title}
          </a>
        </h3>
      </div>
      {item.pitch && <p>{item.pitch}</p>}
      <p className="small muted">
        {item.publisher} · {item.licence}
        {item.update_frequency && <> · updated {item.update_frequency.toLowerCase()}</>}
        {item.formats.length > 0 && <> · {item.formats.join(", ")}</>}
        {levels && <> · by {levels}</>}
        {item.has_time_series && <> · time series</>} · found via {CATALOGUE[item.catalogue]}, {when(item.created_at)}
      </p>
      {item.reject_reason && <p className="small">Rejected: {item.reject_reason}</p>}
      {item.error && <p className="msg bad">Could not add it: {item.error}</p>}
      {item.status === "ingested" ? (
        <p className="small">
          <span className="badge ok">in the pipeline</span> as <code>{item.source_slug}</code>
        </p>
      ) : (
        <BacklogActions itemId={item.id} status={item.status} failed={!!item.error} />
      )}
    </div>
  );
}

export default async function SuggestedPage() {
  const gate = await pageGate();
  if (gate) return gate;
  const items = await must<Item[]>(
    db()
      .from("dataset_backlog")
      .select("*")
      .order("score", { ascending: false, nullsFirst: false })
      .order("created_at", { ascending: false }),
  );
  const groups: [string, Item[], string][] = [
    ["Suggested", items.filter((i) => i.status === "suggested"), "Accept the ones worth a story; reject the rest (they are never suggested again)."],
    ["Accepted", items.filter((i) => i.status === "accepted"), "Each Monday the highest-scored accepted dataset is added to the pipeline."],
    ["In the pipeline", items.filter((i) => i.status === "ingested"), ""],
    ["Rejected", items.filter((i) => i.status === "rejected"), ""],
  ]; // prettier-ignore
  return (
    <>
      <h1>Suggested datasets</h1>
      <p className="small muted">
        Found weekly on data.gov.uk and the ONS (Open Government Licence, machine-readable, with a time series or a
        breakdown by place; nothing personal). Claude scored them 0–100 from catalogue metadata only.
      </p>
      <RunDiscoveryButton />
      {groups.map(([title, list, help]) =>
        list.length ? (
          <section key={title}>
            <h2>
              {title} <span className="small muted">({list.length})</span>
            </h2>
            {help && <p className="small muted">{help}</p>}
            {title === "Rejected" ? (
              <details>
                <summary className="small">Show rejected</summary>
                {list.map((i) => (
                  <Card key={i.id} item={i} />
                ))}
              </details>
            ) : (
              list.map((i) => <Card key={i.id} item={i} />)
            )}
          </section>
        ) : null,
      )}
      {!items.length && <p>No suggestions yet. Run discovery, or seed the backlog (python -m datatales backlog-seed).</p>}
    </>
  );
}
