# Release process

This document describes how to cut and publish an OHM release. For the 0.8.0 planning notes, see `notes/stable-release-0.8.0-plan.md` (local, gitignored).

## Current release

| Item | Value |
|------|-------|
| Application version | `0.8.0` (defined in `pyproject.toml`) |
| Git tag | `v0.8.0` |
| Docker image | `touchthesun/openhardwaremanager` |
| Image tags | `0.8.0`, `0.8`, `latest` |
| Platforms | `linux/amd64`, `linux/arm64` (multi-arch manifest via `docker buildx`) |

### Pull and run

```bash
docker pull touchthesun/openhardwaremanager:0.8.0
docker run -p 8001:8001 \
  -e STORAGE_PROVIDER=local \
  -e LLM_ENABLED=false \
  touchthesun/openhardwaremanager:0.8.0
curl -s http://localhost:8001/health
```

Federation is **off by default**. To enable it, set `OHM_FEDERATION_ENABLED=true` and see [federation infrastructure](development/federation-infra.md).

## Version mapping

| Context | Format | Example |
|---------|--------|---------|
| Python package | semver | `0.8.0` |
| Git tag | `v` + semver | `v0.8.0` |
| Docker image tag | semver (no `v`) | `0.8.0`, `0.8`, `latest` |
| Health API | semver | `"version": "0.8.0"` |

## Bump checklist (next release)

1. Update version in `pyproject.toml` (or run `uv run python scripts/bump_version.py X.Y.Z`).
2. Run `uv lock` and `uv sync --extra dev`.
3. Confirm `uv run ohm version` and local `/health` report the new version.
4. Update `CHANGELOG.md`.
5. Merge to `main` and wait for CI to pass (quality, test, contract-stability, security, docker-build-test).
6. Create git tag `vX.Y.Z` on the release commit.
7. Push the tag — the **Release** workflow validates the tag, runs tests, builds from `uv.lock`, and pushes a **multi-arch** manifest (`linux/amd64`, `linux/arm64`) to Docker Hub.
8. Push the git tag — the **Release** workflow creates the [GitHub Release](https://github.com/helpfulengineering/supply-graph-ai/releases) automatically after Docker publish (notes from `CHANGELOG.md` via `scripts/extract_changelog_section.py`).
9. Smoke-test the pulled image (see below).

## Git tags vs GitHub Releases

| Artifact | What it is | How you create it |
|----------|------------|-------------------|
| **Git tag** (`v0.8.0`) | A pointer to a commit in git | `git tag v0.8.0 && git push origin v0.8.0` |
| **GitHub Release** | A project page: title, notes, optional assets, zip/tarball source downloads | Created by the `github-release` job in `.github/workflows/release.yml`, or manually in the UI |

Pushing a tag **starts** the Release workflow and publishes Docker images, but GitHub does **not** list a release until the `github-release` job runs (or you create one manually). That is why Docker Hub can show `0.8.0` while **Releases** is empty.

`workflow_dispatch` with `dry_run: false` republishes Docker images only; it does **not** create a GitHub Release (no tag push).

### Retroactive release for an existing tag

If `v0.8.0` exists but no GitHub Release was created:

```bash
uv run python scripts/extract_changelog_section.py 0.8.0 -o /tmp/notes.md
gh release create v0.8.0 --title "Open Hardware Manager 0.8.0" --notes-file /tmp/notes.md
```

## GitHub Actions: Release workflow

Workflow file: `.github/workflows/release.yml`

| Trigger | Behavior |
|---------|----------|
| Push tag `v*.*.*` | Validate → test → docker-smoke (amd64) → **publish** multi-arch to Docker Hub |
| `workflow_dispatch` | Same pipeline; `dry_run: true` (default) skips push |

### Required secrets

| Secret | Purpose |
|--------|---------|
| `DOCKERHUB_USERNAME` | Docker Hub account (e.g. `touchthesun`) |
| `DOCKERHUB_TOKEN` | Access token with push permission for `openhardwaremanager` |

Configure under **Settings → Secrets and variables → Actions**.

The Release workflow only appears in the Actions UI after `.github/workflows/release.yml` exists on the **default branch** (`main`).

### Validate tag locally

```bash
uv run python scripts/validate_release_version.py --tag v0.8.0
```

## Pre-release test commands

```bash
uv sync --extra dev
uv run pytest tests -m "unit and not llm and not quarantine" --maxfail=1
uv run pytest tests -m "contract and not llm and not quarantine" --maxfail=1
uv run pip-audit
docker build --build-arg APP_VERSION=0.8.0 -t openhardwaremanager:0.8.0 .
```

## Post-publish smoke test

```bash
docker pull touchthesun/openhardwaremanager:0.8.0
docker run -d --name ohm-smoke -p 8001:8001 \
  -e STORAGE_PROVIDER=local -e LLM_ENABLED=false \
  touchthesun/openhardwaremanager:0.8.0
curl -sf http://localhost:8001/health
curl -sf http://localhost:8001/health/liveness
# Federation disabled by default:
curl -sf http://localhost:8001/v1/api/federation/identify | head -c 200
docker rm -f ohm-smoke
```

Expect `"version": "0.8.0"` on `/health` and federation routes to return 404 when federation is disabled.

## Multi-architecture images

Release publishes use **buildx** with `platforms: linux/amd64,linux/arm64` so images pull on Intel/AMD servers and Apple Silicon (ARM) Macs.

Smoke tests in CI still run a single **amd64** image loaded on the runner (`docker-smoke` job). The `publish` job uses QEMU + buildx to push one manifest list for all tags.

To verify locally after publish:

```bash
docker buildx imagetools inspect touchthesun/openhardwaremanager:0.8.0
docker pull touchthesun/openhardwaremanager:0.8.0   # uses host architecture
```

To rebuild an already-published tag (e.g. add arm64 to `0.8.0`), re-run **Release** with `workflow_dispatch` and `dry_run: false` on `main` at the release commit, or push a new patch tag (`v0.8.1`).

## Rollback

Pin a known-good image tag instead of `latest`:

```bash
docker pull touchthesun/openhardwaremanager:0.8.0
```

Redeploy using that tag. To republish an older version, check out the corresponding git tag and re-run the Release workflow only if intentional (overwrites moving tags like `latest`).

## Deferred (not part of every release)

- Deploy configs under `deploy/` still default to `ghcr.io/helpfulengineering/supply-graph-ai:latest` — migrate separately if cloud deploys should use Docker Hub.
- PyPI **Beta** classifier remains until a true `1.0.0` GA release.
- Optional GHCR mirror workflow.
