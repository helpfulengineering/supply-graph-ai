/**
 * Repository URL validation (pure, unit-tested).
 *
 * Validated client-side so an obviously-wrong URL fails instantly rather than
 * after a minute of extraction. This is a courtesy check, not a security
 * boundary — the server decides what it will actually fetch.
 *
 * v1 supports public GitHub and GitLab repositories only. Private repositories
 * need per-user credentials, which needs user auth, which does not exist yet.
 */

export type UrlProblem =
  | "empty"
  | "not_a_url"
  | "not_http"
  | "unsupported_host"
  | "missing_repo_path";

export interface UrlCheck {
  valid: boolean;
  problem?: UrlProblem;
  message?: string;
  /** Normalised URL to send, when valid. */
  normalized?: string;
}

const SUPPORTED_HOSTS = ["github.com", "gitlab.com"];

const MESSAGES: Record<UrlProblem, string> = {
  empty: "Enter the URL of a public GitHub or GitLab repository.",
  not_a_url: "That doesn't look like a URL.",
  not_http: "The URL needs to start with https://",
  unsupported_host: "Only public GitHub and GitLab repositories are supported for now.",
  missing_repo_path: "That's a host, not a repository — include the owner and repo name.",
};

function fail(problem: UrlProblem): UrlCheck {
  return { valid: false, problem, message: MESSAGES[problem] };
}

export function checkRepoUrl(raw: string): UrlCheck {
  const trimmed = raw.trim();
  if (!trimmed) return fail("empty");

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return fail("not_a_url");
  }

  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    return fail("not_http");
  }

  const host = parsed.hostname.replace(/^www\./, "").toLowerCase();
  if (!SUPPORTED_HOSTS.includes(host)) return fail("unsupported_host");

  // Need at least owner/repo.
  const segments = parsed.pathname.split("/").filter(Boolean);
  if (segments.length < 2) return fail("missing_repo_path");

  // Drop trailing .git and any query/fragment noise; keep owner/repo path.
  const owner = segments[0];
  const repo = segments[1].replace(/\.git$/, "");
  return {
    valid: true,
    normalized: `https://${host}/${owner}/${repo}`,
  };
}

export interface UrlListEntry {
  raw: string;
  check: UrlCheck;
}

export interface UrlListResult {
  /** Deduplicated normalised URLs in input order (valid only). */
  urls: string[];
  entries: UrlListEntry[];
  /** True when every non-empty token is valid and at least one URL remains. */
  valid: boolean;
  /** First human-readable problem, if any. */
  message?: string;
}

/**
 * Parse a comma-separated list of repository URLs.
 * Empty tokens are ignored; duplicates (by normalised URL) are dropped.
 */
export function parseRepoUrlList(raw: string): UrlListResult {
  const tokens = raw
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  if (tokens.length === 0) {
    const empty = fail("empty");
    return { urls: [], entries: [], valid: false, message: empty.message };
  }

  const entries: UrlListEntry[] = [];
  const urls: string[] = [];
  const seen = new Set<string>();

  for (const token of tokens) {
    const check = checkRepoUrl(token);
    entries.push({ raw: token, check });
    if (!check.valid || !check.normalized) continue;
    if (seen.has(check.normalized)) continue;
    seen.add(check.normalized);
    urls.push(check.normalized);
  }

  const firstBad = entries.find((e) => !e.check.valid);
  if (firstBad) {
    return {
      urls,
      entries,
      valid: false,
      message: firstBad.check.message,
    };
  }
  return { urls, entries, valid: urls.length > 0 };
}
