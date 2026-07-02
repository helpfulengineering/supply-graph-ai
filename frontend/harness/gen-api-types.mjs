#!/usr/bin/env node
/**
 * Generate typed API client definitions from the backend's OpenAPI spec.
 *
 * Generic harness core: reads openapiUrl + apiTypesOutput from harness.config.json
 * so this script is project-agnostic. Backend contract drift becomes a
 * TypeScript compile error in the frontend.
 *
 * Requires the API to be reachable at openapiUrl (dev server or container).
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const cfg = JSON.parse(
  readFileSync(new URL("../harness.config.json", import.meta.url), "utf-8"),
);

const out = fileURLToPath(new URL(`../${cfg.apiTypesOutput}`, import.meta.url));

console.log(`Generating API types from ${cfg.openapiUrl} -> ${cfg.apiTypesOutput}`);
try {
  execFileSync(
    "npx",
    ["--yes", "openapi-typescript", cfg.openapiUrl, "-o", out],
    { stdio: "inherit" },
  );
} catch {
  console.error(
    `\nFailed to generate API types. Is the API reachable at ${cfg.openapiUrl}?\n` +
      `Start it (e.g. 'docker compose up -d ohm-api') and retry.`,
  );
  process.exit(1);
}
