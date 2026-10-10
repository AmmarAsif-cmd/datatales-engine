import RecipeApprove from "@/components/RecipeApprove";
import { db, must } from "@/lib/db";
import { when } from "@/lib/format";
import type { Json } from "@/lib/types";

export const dynamic = "force-dynamic";

type Recipe = {
  id: string;
  version: number;
  spec: { description?: string; steps?: { op: string }[]; checks?: Record<string, Json> };
  approved_at: string | null;
  approved_by: string | null;
  created_at: string;
  sources: { slug: string } | null;
};

export default async function RecipesPage() {
  const recipes = await must<Recipe[]>(
    db()
      .from("recipes")
      .select("id, version, spec, approved_at, approved_by, created_at, sources(slug)")
      .order("created_at", { ascending: false }),
  );
  return (
    <>
      <h1>Recipes</h1>
      <p className="small muted">
        Recipes are declarative cleaning steps. Only approved recipes run; approved versions are
        immutable. Approving writes <code>worker/recipes/&lt;source&gt;.v&lt;N&gt;.yaml</code>: commit
        it.
      </p>
      {recipes.map((r) => (
        <div className="panel" key={r.id}>
          <div className="row">
            <h2 style={{ margin: 0 }}>
              {r.sources?.slug} v{r.version}
            </h2>
            {r.approved_at ? (
              <span className="badge ok">
                approved by {r.approved_by}, {when(r.approved_at)}
              </span>
            ) : (
              <span className="badge warn">not approved</span>
            )}
          </div>
          {r.spec.description && <p>{r.spec.description}</p>}
          <p className="small">
            Steps: {(r.spec.steps ?? []).map((s) => s.op).join(" → ")}
          </p>
          {!r.approved_at && r.sources && <RecipeApprove source={r.sources.slug} version={r.version} />}
          <details>
            <summary className="small">Full spec</summary>
            <pre className="box small">{JSON.stringify(r.spec, null, 2)}</pre>
          </details>
        </div>
      ))}
    </>
  );
}
