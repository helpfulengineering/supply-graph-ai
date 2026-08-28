#!/usr/bin/env node
/**
 * Generate typed API client definitions from the backend's OpenAPI spec.
 *
 * Generic harness core: reads openapiSpecCommand / openapiUrl + apiTypesOutput
 * from harness.config.json so this script is project-agnostic. Backend contract
 * drift becomes a TypeScript compile error in the frontend.
 *
 * Two sources, in preference order:
 *
 *   openapiSpecCommand — a command that writes the spec to the path it is
 *     given, substituted for {out}. No server needed, so regenerating is a
 *     thing anyone can do at any time. That matters more than it sounds: while
 *     this script could only read a URL, regenerating required a running API,
 *     and the committed schema drifted from the app it claims to describe.
 *   openapiUrl — a live server. The fallback, for projects with no in-process
 *     way to render their own spec.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const cfg = JSON.parse(
  readFileSync(new URL("../harness.config.json", import.meta.url), "utf-8"),
);

const out = fileURLToPath(new URL(`../${cfg.apiTypesOutput}`, import.meta.url));
const repoRoot = fileURLToPath(new URL("../..", import.meta.url));

/** Where openapi-typescript reads the spec from, and what to say when it fails. */
function resolveSource() {
  if (!cfg.openapiSpecCommand) {
    return {
      input: cfg.openapiUrl,
      describe: cfg.openapiUrl,
      hint:
        `Is the API reachable at ${cfg.openapiUrl}?\n` +
        `Start it (e.g. 'docker compose up -d ohm-api') and retry.`,
      cleanup: () => {},
    };
  }
  const dir = mkdtempSync(join(tmpdir(), "openapi-"));
  const file = join(dir, "openapi.json");
  execFileSync(cfg.openapiSpecCommand.replaceAll("{out}", file), {
    cwd: repoRoot,
    shell: true,
    stdio: "inherit",
  });
  return {
    input: file,
    describe: cfg.openapiSpecCommand,
    hint: `The spec command failed. Run it directly to see why:\n  ${cfg.openapiSpecCommand}`,
    cleanup: () => rmSync(dir, { recursive: true, force: true }),
  };
}

let source;
try {
  source = resolveSource();
} catch (err) {
  console.error(`\nFailed to read the OpenAPI spec.\n${err.message ?? err}`);
  process.exit(1);
}

console.log(`Generating API types from ${source.describe} -> ${cfg.apiTypesOutput}`);
try {
  execFileSync("npx", ["--yes", "openapi-typescript", source.input, "-o", out], {
    stdio: "inherit",
  });
} catch {
  console.error(`\nFailed to generate API types. ${source.hint}`);
  process.exit(1);
} finally {
  source.cleanup();
}
