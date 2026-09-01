<!-- Generated from scripts/registry.toml by scripts/generate_scripts_index.py.
     Do not edit by hand — edit the registry and run `make scripts` (or scripts-check). -->

# Scripts

Developer and ops tooling for OHM. Source of truth is [`registry.toml`](registry.toml); this index is generated from it. Every script here is registered — `make scripts-check` fails otherwise.

A ✎ marks a script that **writes** files / storage / remote state; the rest are read-only (safe to run to inspect state).

## Release & versioning

| Script | What it does | Run |
| --- | --- | --- |
| `bump_version` ✎ | Bump the OHM version across pyproject.toml and the doc registry in lockstep; --check gates drift. | `uv run python scripts/bump_version.py <X.Y.Z> \| --check` |
| `extract_changelog_section` | Extract one version's section from CHANGELOG.md for GitHub Release notes. | `uv run python scripts/extract_changelog_section.py <X.Y.Z> [-o FILE]` |
| `validate_release_version` | Validate a git release tag matches pyproject.toml version; emits version/major_minor to GITHUB_OUTPUT. | `uv run python scripts/validate_release_version.py [--tag vX.Y.Z]` |

## Code / doc generation

| Script | What it does | Run |
| --- | --- | --- |
| `build_docs_site` ✎ | Stage docs-site/docs into docs-site/.build with status badges injected, for any static site generator to build. | `uv run python scripts/build_docs_site.py` |
| `dump_api_routes` | Print sorted 'METHOD path' lines for the v1 FastAPI app; --count-only for a route count; --openapi for the spec itself. | `uv run python scripts/dump_api_routes.py [--count-only\|--openapi]` |
| `generate_demo_world` ✎ | Emit frontend/src/lib/demo/world.ts from the seed dataset so the client Demo data toggle shows the same world make seed-demo produces; --check gates drift. | `uv run python scripts/generate_demo_world.py [--check]` |
| `generate_env_template` ✎ | Regenerate the schema-owned block of .env.example from the config schema; --check gates staleness. | `uv run python scripts/generate_env_template.py [--check]` |
| `generate_process_definitions` ✎ | Generate the PROCESS_DEFINITIONS fallback literal from processes.yaml; --check gates drift between the two. | `uv run python scripts/generate_process_definitions.py [--check]` |
| `generate_scripts_index` ✎ | Generate scripts/README.md from this registry; --check gates staleness and registry completeness. | `uv run python scripts/generate_scripts_index.py [--check]` |

## Verification & validation gates

| Script | What it does | Run |
| --- | --- | --- |
| `check_doc_links` | Fail when a documentation link cannot be followed: wrong host, an absolute link to a docs page that does not exist, or a repo-internal markdown link to a missing file. | `uv run python scripts/check_doc_links.py [--list]` |
| `local_async_generation_e2e` | Localhost Compose e2e for async generate-from-url jobs, progress, revoke, and LLM credential gates. | `uv run python scripts/local_async_generation_e2e.py` |
| `validate_docs` | Validate documentation claims against the code implementation. | `uv run python scripts/validate_docs.py` |
| `validate_okw_in_storage` | Read configured storage (local or remote) and report the OKW facilities found — quick config sanity check. | `uv run python scripts/validate_okw_in_storage.py` |
| `verify_dev_env` | Verify the local dev environment is fully provisioned (historically fragile deps load). | `uv run python scripts/verify_dev_env.py` |

## Synthetic data & seeding

| Script | What it does | Run |
| --- | --- | --- |
| `generate_synthetic_data` ✎ | Synthetic-data generator for OKH, OKW, and AssetRecord models — the primary fixture/demo dataset source. | `uv run python scripts/generate_synthetic_data.py [options]` |
| `import_okh_losh_batch` ✎ | Bulk-convert+validate+import a directory of OKH-LOSH v2.4 TOML manifests through OKHService.create(). | `uv run python scripts/import_okh_losh_batch.py --data-dir <DIR> [--dry-run] [--report FILE]` |
| `populate_ohm_storage_from_synthetic_data` ✎ | Upload OKH/OKW from synthetic_data/ into an Azure Blob container (seed a deployment). | `uv run python scripts/populate_ohm_storage_from_synthetic_data.py [options]` |
| `seed_demo_data` ✎ | Seed a deterministic demo world (10 designs, 7 facilities, every design buildable) so browse -> match -> supply tree completes with real data; --summary reports match coverage without writing. | `uv run python scripts/seed_demo_data.py [--clear] [--summary] [--storage-dir DIR]` |
| `seed_repair_scenario` ✎ | Seed a local OHM storage directory with a realistic repair-workflow scenario (asset + manifests). | `uv run python scripts/seed_repair_scenario.py [options]` |

## Storage operations

| Script | What it does | Run |
| --- | --- | --- |
| `clear_storage` ✎ | Delete OKH and OKW files from configured storage — dev reset. | `uv run python scripts/clear_storage.py [options]` |
| `copy_container_blobs` ✎ | Copy all blobs from one Azure container to another via OHM's storage provider (bypasses RBAC data-plane grant). | `uv run python scripts/copy_container_blobs.py <src-container> <dst-container>` |
| `setup_storage` ✎ | Bootstrap storage for a new environment: connect, verify with a real round trip, then create the top-level prefixes. | `uv run python scripts/setup_storage.py [options]` |

## Deployment pathways

| Script | What it does | Run |
| --- | --- | --- |
| `complete_deployment` ✎ | Finish a Cloud Run deployment after the image build completes. | `./scripts/complete_deployment.sh` |
| `deploy_cloud_run` ✎ | Build, push, and deploy the API to Google Cloud Run (non-Azure deployment pathway). | `./scripts/deploy_cloud_run.sh` |
| `extract_package_from_container` | Extract a built package artifact from a Docker container onto the host. | `./scripts/extract_package_from_container.sh` |
| `install` ✎ | Install and start a node on a host with Docker: mint secrets, resolve the latest release, start, wait for health, print the admin key. | `curl -fsSLO https://openhardwaremanager.org/install.sh && sha256sum -c install.sh.sha256 && sh install.sh` |

## Federation testing

| Script | What it does | Run |
| --- | --- | --- |
| `federation_e2e` | End-to-end federation smoke test: seed a manifest on peer A, sync to peer B, assert arrival. | `./scripts/federation_e2e.sh` |
| `federation_matrix` | Multi-feature federation validation matrix against two peers (Compose or Azure URLs). | `./scripts/federation_matrix.sh` |
| `federation_regression` | Pre-merge federation regression checks; runs federation_e2e.sh when a two-node stack is up. | `./scripts/federation_regression.sh` |
| `federation_seed_azure` ✎ | Seed divergent OKH catalogs on Peer A and Peer B after an Azure terraform bring-up. | `PEER_A_URL=… PEER_B_URL=… API_KEY_A=… API_KEY_B=… ./scripts/federation_seed_azure.sh` |

## LLM & matching evaluation

| Script | What it does | Run |
| --- | --- | --- |
| `matching_batch` | Batch matching eval: run 'ohm match requirements' against every generated OKH manifest. | `uv run python scripts/matching_batch.py [options]` |
| `okh_generation_azure_regen_batches` ✎ | Batch re-generate OKHs in the Azure production container from each manifest's repo URL, skipping existing work and appending a JSONL process log. | `uv run python scripts/okh_generation_azure_regen_batches.py [--dry-run] [--force] [--batch-size N]` |
| `okh_generation_azure_regen_lib` | Pure helpers (batching, key classification, JSONL log parsing) for okh_generation_azure_regen_batches; imported, not run directly. | `imported by scripts/okh_generation_azure_regen_batches.py` |
| `okh_generation_azure_regen_replace` ✎ | Re-generate every OKH in Azure blob from its repo URL and overwrite the same blob key. | `uv run python scripts/okh_generation_azure_regen_replace.py [--dry-run] [--force] [options]` |
| `okh_generation_baseline_report` ✎ | Produce the OKH-generation baseline report used as the eval comparison point. | `uv run python scripts/okh_generation_baseline_report.py [options]` |
| `okh_generation_batch` ✎ | Batch LLM OKH generation over the test repository set — core of the generation eval harness. | `uv run python scripts/okh_generation_batch.py [options]` |
| `okh_generation_chunked_evaluation` | Evaluate chunked-LLM canary quality gates against a baseline batch report. | `uv run python scripts/okh_generation_chunked_evaluation.py [options]` |
| `okh_generation_layer_compare` | Compare 3-layer vs 4-layer OKH manifests on disk with heuristic quality metrics. | `uv run python scripts/okh_generation_layer_compare.py [options]` |
| `okh_generation_materials_regen_compare` ✎ | Sequential from-URL regen with before/after Materials metrics tracker (no cloud writes). | `uv run python scripts/okh_generation_materials_regen_compare.py [--core-only] [options]` |
