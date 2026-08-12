/**
 * Capability matching rules — the instance configuration behind every match.
 *
 * Mounted under /api/match/rules, but a different concern from a match: these
 * change how matching behaves for every caller, which is why their surface is
 * Settings rather than the match page.
 *
 * Every response is a `create_success_response` envelope whose `data` the
 * generated schema types as an open record, so the shapes are declared here and
 * this module is the one place that narrows them.
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";

export interface CapabilityRule {
  id: string;
  type: string;
  capability: string;
  satisfies_requirements: string[];
  direction: string;
  confidence: number;
  domain: string;
  description: string | null;
  source: string | null;
  tags: string[];
}

export interface RuleList {
  rules: CapabilityRule[];
  total: number;
  domains: string[];
}

export interface RuleValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/** Rule ids, per domain, that an import would add / change / remove. */
export interface RuleChanges {
  added: string[];
  updated: string[];
  deleted: string[];
}

export interface RuleComparison {
  /** Keyed by domain. A single-domain file compares under its own domain. */
  domains: Record<string, { changes: RuleChanges }>;
}

export interface RuleImportResult {
  imported: number;
  domains: string[];
}

export type RuleFileFormat = "yaml" | "json";

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
    requestIdFromError(error, response),
  );
}

function payload<T>(data: unknown): T {
  return ((data as { data?: unknown } | undefined)?.data ?? {}) as T;
}

export async function listRules(domain?: string): Promise<RuleList> {
  const { data, error, response } = await apiClient.GET("/api/match/rules/", {
    params: { query: { domain } },
  });
  if (error || !response.ok) fail(error, response, "Failed to load rules");
  const body = payload<Partial<RuleList>>(data);
  return {
    rules: body.rules ?? [],
    total: body.total ?? 0,
    domains: body.domains ?? [],
  };
}

/** Check a rules file without writing anything. */
export async function validateRules(
  fileContent: string,
  fileFormat: RuleFileFormat,
): Promise<RuleValidation> {
  const { data, error, response } = await apiClient.POST(
    "/api/match/rules/validate",
    {
      body: {
        file_content: fileContent,
        file_format: fileFormat,
        // Inherited from the shared request base and meaningless for a rules
        // file. Required by the schema, so they are sent as null rather than
        // omitted.
        quality_level: null,
        strict_mode: null,
      },
    },
  );
  if (error || !response.ok) fail(error, response, "Validation failed");
  const body = payload<Partial<RuleValidation>>(data);
  return {
    valid: body.valid ?? false,
    errors: body.errors ?? [],
    warnings: body.warnings ?? [],
  };
}

/** What importing this file would change. The step that makes import safe. */
export async function compareRules(
  fileContent: string,
  fileFormat: RuleFileFormat,
): Promise<RuleComparison> {
  const { data, error, response } = await apiClient.POST(
    "/api/match/rules/compare",
    {
      body: {
        file_content: fileContent,
        file_format: fileFormat,
        // Inherited from the shared request base and meaningless for a rules
        // file. Required by the schema, so they are sent as null rather than
        // omitted.
        quality_level: null,
        strict_mode: null,
      },
    },
  );
  if (error || !response.ok) fail(error, response, "Comparison failed");
  const body = payload<Record<string, unknown>>(data);
  // A multi-domain file answers {domains: {...}}; a single-domain file answers
  // the comparison directly. Normalised here so the panel renders one shape.
  if (body.domains && typeof body.domains === "object") {
    return { domains: body.domains as RuleComparison["domains"] };
  }
  return { domains: { "this file": body as { changes: RuleChanges } } };
}

/**
 * Import rules FROM A FILE.
 *
 * Split from `reloadRules` deliberately: POST /import does two different things
 * depending on whether `file_content` is present, and a single wrapper taking
 * an optional string is a call site that can silently mean the other one.
 */
export async function importRules(
  fileContent: string,
  fileFormat: RuleFileFormat,
): Promise<RuleImportResult> {
  const { data, error, response } = await apiClient.POST(
    "/api/match/rules/import",
    {
      body: {
        file_content: fileContent,
        file_format: fileFormat,
        partial_update: false,
        dry_run: false,
        // Inherited from the shared request base and meaningless for a rules
        // file. Required by the schema, so they are sent as null rather than
        // omitted.
        quality_level: null,
        strict_mode: null,
      },
    },
  );
  if (error || !response.ok) fail(error, response, "Import failed");
  const body = payload<Partial<RuleImportResult>>(data);
  return { imported: body.imported ?? 0, domains: body.domains ?? [] };
}

/** Reload rules from the server's own filesystem — the same endpoint, no body. */
export async function reloadRules(): Promise<RuleImportResult> {
  const { data, error, response } = await apiClient.POST(
    "/api/match/rules/import",
    {
      // No file_content: that absence is what makes this a reload from the
      // server's own filesystem rather than an import.
      body: {
        partial_update: false,
        dry_run: false,
        // Inherited from the shared request base and meaningless for a rules
        // file. Required by the schema, so they are sent as null rather than
        // omitted.
        quality_level: null,
        strict_mode: null,
      },
    },
  );
  if (error || !response.ok) fail(error, response, "Reload failed");
  const body = payload<Partial<RuleImportResult>>(data);
  return { imported: body.imported ?? 0, domains: body.domains ?? [] };
}

/** Export the current rule set as a file the next node can import. */
export async function exportRules(
  fileFormat: RuleFileFormat,
  domain?: string,
): Promise<string> {
  const { data, error, response } = await apiClient.POST(
    "/api/match/rules/export",
    {
      params: { query: { format: fileFormat, domain } },
    },
  );
  if (error || !response.ok) fail(error, response, "Export failed");
  const body = payload<{ file_content?: string }>(data);
  return body.file_content ?? "";
}

/** Discard every loaded rule and return to the built-in set. */
export async function resetRules(): Promise<void> {
  const { error, response } = await apiClient.POST("/api/match/rules/reset", {
    // The server refuses without it; there is no UI state where the caller
    // reached this and did not mean it — the confirmation is in the panel.
    params: { query: { confirm: true } },
  });
  if (error || !response.ok) fail(error, response, "Reset failed");
}

// Deliberately no fetchRule: GET /api/match/rules/{domain}/{rule_id} returns
// what the list already carries, so a client function for it would be one with
// no caller — which is exactly the drift the coverage gate exists to catch.
