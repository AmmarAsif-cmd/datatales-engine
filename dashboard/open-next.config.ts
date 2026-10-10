import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// Every page is rendered per request (force-dynamic) behind Cloudflare Access, so no
// incremental cache (and no R2 bucket) is needed.
export default defineCloudflareConfig({});
