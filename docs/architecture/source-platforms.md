# Source platforms for OKH ingestion

OHM is intended to support **multiple host sites** for ingesting open hardware projects and generating OKH manifests. This document summarizes which platforms are fully supported today and which are on the roadmap.

**Definitions**

- **Fully supported**: URL is recognized, and a platform-specific **extractor** exists and is used by the OKH generation pipeline (`OKHService.generate_from_url`). End-to-end ingestion works.
- **Recognized / roadmap**: Platform is defined in code (e.g. `PlatformType` enum) and URLs may be detected, but **no extractor is implemented** (or the pipeline does not route to it). Marked for future implementation.

---

## Fully supported (implemented)

| Platform | URL patterns | Extractor | Notes |
|----------|--------------|-----------|--------|
| **GitHub** | `github.com/{owner}/{repo}` | `GitHubExtractor` | Primary target for repo-based ingestion. |
| **GitLab** | `gitlab.com/...` (including subgroups); self-hosted `https://{host}/...` when `{host}` is listed in `GITLAB_SELF_HOSTED_HOSTS` | `GitLabExtractor` | API base is `{scheme}://{host}/api/v4`. See `notes/self-hosted-gitlab-plan.md`. |

These are the only two platforms for which `OKHService.generate_from_url` will run end-to-end; all others currently raise “Unsupported platform.”

---

## Recognized but not yet implemented (roadmap)

The following are **defined in the codebase** (e.g. `PlatformType` in `src/core/generation/models.py`) and **URL detection** exists in `URLRouter`, but **no project extractor is registered** and the generation pipeline does not use them:

| Platform | URL patterns | Status |
|----------|--------------|--------|
| **Codeberg** | `codeberg.org/{owner}/{repo}` | URL detected; no `CodebergExtractor`. Repo info extraction reuses GitHub-like pattern. |
| **Hackaday.io** | `hackaday.io/project/{id}` | URL detected; no `HackadayExtractor`. Repo info returns `hackaday`, `project-{id}`. |

Other hosts (e.g. **Thingiverse**, or other siloed/open-hardware sites) are **not** yet in the platform enum or URL router. OHM’s goal is to support multiple host sites over time; adding them is roadmap work once priorities and API/access are clear.

---

## Implementation details (reference)

- **Platform enum**: `src/core/generation/models.py` — `PlatformType`: `GITHUB`, `GITLAB`, `CODEBERG`, `HACKADAY`, `UNKNOWN`.
- **URL routing**: `src/core/generation/url_router.py` — `detect_platform()`, `validate_url()`, `route_to_extractor()`. Only GitHub and GitLab have extractors registered in `_initialize_extractors()`.
- **Extractors**: `src/core/generation/platforms/` — `github.py`, `gitlab.py` (and `local_git.py` for local Git clone; supports GitHub/GitLab URLs when cloning). No `codeberg.py` or `hackaday.py`.
- **Pipeline**: `src/core/services/okh_service.py` — `generate_from_url()` branches only on `PlatformType.GITHUB` and `PlatformType.GITLAB`; other platforms raise.

---

## For issue 1.3.1 (generation testing)

The current 1.3.1 plan assumes **GitHub and GitLab** as the test dataset sources, since those are the only platforms with working ingestion. Once Codeberg or other extractors are implemented, the same test framework (repositories.json, ground truth, harness) can be extended to include them.
