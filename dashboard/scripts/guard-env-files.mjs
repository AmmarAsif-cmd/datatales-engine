// Before a Cloudflare build: refuse if any .env* file (other than examples) exists here or
// at the repo root, because OpenNext would bundle its values into the Worker.
import { readdirSync } from "node:fs";

const offending = [".", ".."].flatMap((dir) =>
  readdirSync(dir)
    .filter((f) => f.startsWith(".env") && !f.endsWith(".example"))
    .map((f) => `${dir}/${f}`),
);
if (offending.length) {
  console.error(`Refusing to build: ${offending.join(", ")} would be bundled into the Worker.`);
  console.error("Move local secrets to dashboard/.dev.vars; production uses Worker secrets.");
  process.exit(1);
}
