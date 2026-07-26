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
