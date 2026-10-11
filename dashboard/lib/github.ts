import "server-only";

/**
 * Trigger GitHub Actions workflows from the dashboard.
 *
 * Uses workflow_dispatch, which a fine-grained token can do with ONLY
 * "Actions: Read and write" on this one repository. (repository_dispatch would need
 * "Contents: write", i.e. a token that could also push code.) The workflows themselves
 * hold the write access they need.
 */

const API = "https://api.github.com";

export const WORKFLOWS = {
  publish: "publish.yml",
  storyNew: "story-new.yml",
  recipeApprove: "recipe-approve.yml",
  recipeDraft: "recipe-draft.yml",
  pipeline: "pipeline.yml",
  discovery: "discovery.yml",
} as const;

function settings(): { repo: string; token: string } {
  const repo = process.env.GITHUB_REPO?.trim();
  const token = process.env.GITHUB_DISPATCH_TOKEN?.trim();
  if (!repo || !token) {
    throw new Error("GITHUB_REPO and GITHUB_DISPATCH_TOKEN must be set to trigger workflows.");
  }
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) throw new Error("GITHUB_REPO must look like owner/name");
  return { repo, token };
}

function ghHeaders(token: string): HeadersInit {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${token}`,
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "datatales-dashboard",
  };
}

export async function dispatch(workflow: string, inputs: Record<string, string> = {}): Promise<void> {
  const { repo, token } = settings();
  const res = await fetch(`${API}/repos/${repo}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: { ...ghHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main", inputs }),
  });
  if (res.status !== 204 && res.status !== 200) {
    const detail = (await res.text()).slice(0, 300);
    throw new Error(`GitHub refused to start ${workflow} (${res.status}): ${detail}`);
  }
}

export type WorkflowRun = {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  html_url: string;
  created_at: string;
  event: string;
};

export async function recentRuns(limit = 8): Promise<WorkflowRun[]> {
  const { repo, token } = settings();
  const res = await fetch(`${API}/repos/${repo}/actions/runs?per_page=${limit}&event=workflow_dispatch`, {
    headers: ghHeaders(token),
  });
  if (!res.ok) throw new Error(`could not list workflow runs (${res.status})`);
  const body = (await res.json()) as { workflow_runs: WorkflowRun[] };
  return body.workflow_runs;
}
