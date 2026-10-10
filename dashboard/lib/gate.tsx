import "server-only";

import { type AccessUser, AccessDenied, requireUser } from "./access";

/** For pages: the signed-in user, or null (render <Denied />). Never leaks the reason. */
export async function pageUser(): Promise<AccessUser | null> {
  try {
    return await requireUser();
  } catch (e) {
    if (e instanceof AccessDenied) return null;
    throw e;
  }
}

export function Denied() {
  return (
    <div className="panel">
      <h1>Not signed in</h1>
      <p>This dashboard is only available through Cloudflare Access at admin.datatales.co.uk.</p>
    </div>
  );
}
