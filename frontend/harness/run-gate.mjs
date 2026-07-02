#!/usr/bin/env node
/**
 * The `frontend-ready` gate — the single success signal for the autonomous
 * build loop. Runs each stage in order, stops at the first failure, and exits
 * nonzero so callers (make, CI, the agent loop) can read a boolean result.
 *
 * Generic harness core: stages are project-agnostic and delegate to npm
 * scripts. Project specifics live in harness.config.json.
 */
import { spawnSync } from "node:child_process";

const stages = [
  ["typecheck", "npm", ["run", "typecheck"]],
  ["lint", "npm", ["run", "lint"]],
  ["unit", "npm", ["run", "test:unit"]],
  ["build", "npm", ["run", "build"]],
  ["e2e (mocked) + a11y + screenshots", "npm", ["run", "e2e"]],
];

const t0 = Date.now();
for (const [name, cmd, args] of stages) {
  process.stdout.write(`\n→ frontend-ready: ${name}\n`);
  const res = spawnSync(cmd, args, { stdio: "inherit", shell: process.platform === "win32" });
  if (res.status !== 0) {
    process.stderr.write(`\n✗ frontend-ready FAILED at: ${name}\n`);
    process.exit(res.status ?? 1);
  }
}
const secs = ((Date.now() - t0) / 1000).toFixed(1);
process.stdout.write(`\n✓ frontend-ready: all stages passed (${secs}s)\n`);
