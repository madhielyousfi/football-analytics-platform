import { readFileSync } from "fs";
import { join } from "path";

/** Read-only build-time access to the exported JSON snapshot (server only). */
export function snapshotFile(name: string): unknown {
  try {
    return JSON.parse(readFileSync(join(process.cwd(), "public", "data", name), "utf8"));
  } catch {
    return null;
  }
}
