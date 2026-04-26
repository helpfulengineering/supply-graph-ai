#!/usr/bin/env python3
"""
For each OKH manifest under ``tmp/oshwa/okh-manifests`` (or ``--manifests-dir``):

1. Build a package via ``PackageService.build_package_from_dict``
2. Validate on disk with ``PackageService.verify_package_metadata`` (inventory + checksums)
3. Push with ``PackageRemoteStorage.push_package`` (same path as ``ohm package push`` fallback)
4. List blobs under ``packages/{org}/{project}/{version}/`` (see ``OHM_PACKAGE_STORAGE_PREFIX``) and assert expected keys exist

Environment / container
-------------------------
Loads repo-root ``.env`` via ``src.config.storage_config`` (same as other scripts).

Typical Azure variables: ``AZURE_STORAGE_ACCOUNT``, ``AZURE_STORAGE_KEY``,
``AZURE_STORAGE_CONTAINER``. Override default container with ``--container`` or
``AZURE_OKH_PACKAGE_CONTAINER`` (checked before ``AZURE_STORAGE_CONTAINER``).

Examples
--------
    conda activate supply-graph-ai
    python scripts/batch_build_push_okh_packages.py --dry-run
    python scripts/batch_build_push_okh_packages.py --limit 2 --no-push
    python scripts/batch_build_push_okh_packages.py --limit 1 --no-push -v
    python scripts/batch_build_push_okh_packages.py --limit 1 --no-push -vv
    python scripts/batch_build_push_okh_packages.py --limit 5 --report out.json --trace-report
    python scripts/batch_build_push_okh_packages.py --create-container

    # Single manifest already in remote OKH storage (same Azure config as the API)
    python scripts/batch_build_push_okh_packages.py \\
        --okh-id 00000000-0000-0000-0000-000000000000 --no-push -v

    # All OKH manifests in remote storage (SmartFileDiscovery under okh/)
    python scripts/batch_build_push_okh_packages.py --from-remote-okh --no-push -v
    python scripts/batch_build_push_okh_packages.py --from-remote-okh --limit 3 --report /tmp/report.json
    python scripts/batch_build_push_okh_packages.py --from-remote-okh --no-push --no-log-file
    python scripts/batch_build_push_okh_packages.py --from-remote-okh --no-push --fetch-retries 3
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.packaging.builder import PackageAssetDownloadError  # noqa: E402

_MANIFEST_LABEL: contextvars.ContextVar[str] = contextvars.ContextVar(
    "batch_manifest_label", default=""
)
_FETCH_TRACE_LINES: contextvars.ContextVar[Optional[List[str]]] = (
    contextvars.ContextVar("batch_fetch_trace", default=None)
)


class _ManifestLabelFilter(logging.Filter):
    """Prefix log lines with the current manifest filename (batch context)."""

    def filter(self, record: logging.LogRecord) -> bool:
        label = _MANIFEST_LABEL.get()
        record.manifest_label = f"[{label}] " if label else ""
        return True


class _FetchTraceHandler(logging.Handler):
    """Collect WARNING+ from packaging / package_service into the current trace list."""

    _PREFIXES = ("src.core.packaging", "src.core.services.package_service")

    def emit(self, record: logging.LogRecord) -> None:
        buf = _FETCH_TRACE_LINES.get()
        if buf is None or record.levelno < logging.WARNING:
            return
        if not any(record.name.startswith(p) for p in self._PREFIXES):
            return
        label = _MANIFEST_LABEL.get() or "-"
        buf.append(
            f"{label} | {record.levelname} | {record.name} | {record.getMessage()}"
        )


_BATCH_LOG_HANDLERS: List[logging.Handler] = []


def _configure_batch_logging(
    verbose: int,
    collect_trace: bool,
    log_file: Optional[Path] = None,
) -> None:
    """Attach stderr logging (``-v`` / ``-vv``), optional trace collection, and/or file log."""
    global _BATCH_LOG_HANDLERS
    for h in _BATCH_LOG_HANDLERS:
        for name in ("src.core.packaging", "src.core.services.package_service"):
            logging.getLogger(name).removeHandler(h)
    _BATCH_LOG_HANDLERS.clear()

    label_filter = _ManifestLabelFilter()
    fmt = "%(manifest_label)s%(levelname)s %(name)s: %(message)s"
    handlers: List[logging.Handler] = []

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_h = logging.FileHandler(log_file, encoding="utf-8")
        file_h.setLevel(logging.DEBUG)
        file_h.addFilter(label_filter)
        file_h.setFormatter(
            logging.Formatter(
                "%(asctime)s %(manifest_label)s%(levelname)s %(name)s: %(message)s"
            )
        )
        handlers.append(file_h)

    if verbose >= 1:
        level = logging.DEBUG if verbose >= 2 else logging.INFO
        stream_h = logging.StreamHandler(sys.stderr)
        stream_h.setLevel(level)
        stream_h.addFilter(label_filter)
        stream_h.setFormatter(logging.Formatter(fmt))
        handlers.append(stream_h)
    if collect_trace:
        trace_h = _FetchTraceHandler()
        trace_h.setLevel(logging.WARNING)
        handlers.append(trace_h)

    if not handlers:
        return

    for name in ("src.core.packaging", "src.core.services.package_service"):
        lg = logging.getLogger(name)
        if log_file is not None or verbose >= 2:
            lg.setLevel(logging.DEBUG)
        elif verbose >= 1 or collect_trace:
            lg.setLevel(logging.INFO if verbose >= 1 else logging.WARNING)
        else:
            lg.setLevel(logging.DEBUG)
        for h in handlers:
            lg.addHandler(h)

    _BATCH_LOG_HANDLERS.extend(handlers)


@contextmanager
def _manifest_trace_context(
    manifest_name: str, collect_trace: bool
) -> Iterator[Optional[List[str]]]:
    token_l = _MANIFEST_LABEL.set(manifest_name)
    lines: Optional[List[str]] = [] if collect_trace else None
    token_t = _FETCH_TRACE_LINES.set(lines)
    try:
        yield lines
    finally:
        _MANIFEST_LABEL.reset(token_l)
        _FETCH_TRACE_LINES.reset(token_t)


def _print_fetch_hints(manifest_path: Path, data: dict, *, verbose: int) -> None:
    """Explain which repo-relative paths will be turned into raw GitHub URLs."""
    if verbose < 1:
        return
    repo = data.get("repo")
    print(f"--- fetch context: {manifest_path.name} ---", file=sys.stderr)
    print(f"  repo (manifest): {repo!r}", file=sys.stderr)
    if not repo:
        print("  (no repo — relative paths stay local)", file=sys.stderr)
        return
    if "gitlab." in str(repo).lower() or str(repo).rstrip("/").endswith("gitlab.com"):
        print(
            "  GitLab repo — relative paths use /-/raw/{default_branch}/… "
            "(private projects may need auth; API sets branch when reachable).",
            file=sys.stderr,
        )
        return
    if "github.com" not in str(repo):
        print(
            "  (not GitHub — only GitHub/GitLab relative paths are auto-resolved to raw URLs)",
            file=sys.stderr,
        )
        return
    try:
        from src.core.packaging.github_raw_urls import (
            github_raw_file_url,
            parse_github_owner_repo,
        )
    except ImportError:
        return
    parsed = parse_github_owner_repo(str(repo))
    if parsed:
        print(f"  github owner/repo: {parsed[0]!r} / {parsed[1]!r}", file=sys.stderr)

    bom = data.get("bom")
    if isinstance(bom, dict):
        ext = bom.get("external_file")
        if isinstance(ext, str) and ext.strip():
            try:
                raw = github_raw_file_url(str(repo), ext.strip())
                print(
                    f"  bom.external_file: repo-relative {ext!r} -> {raw}",
                    file=sys.stderr,
                )
                print(
                    "    hint: if this 404s, the path may not exist on the default branch "
                    "(or use null external_file and keep the *-bom.json sidecar).",
                    file=sys.stderr,
                )
            except ValueError as e:
                print(
                    f"  bom.external_file: could not build raw URL: {e}",
                    file=sys.stderr,
                )
    elif isinstance(bom, str) and bom.strip():
        try:
            raw = github_raw_file_url(str(repo), bom.strip())
            print(f"  bom (string): {bom.strip()!r} -> {raw}", file=sys.stderr)
        except ValueError as e:
            print(f"  bom: could not build raw URL: {e}", file=sys.stderr)


def _build_options_output_dir(output_dir: Path) -> str:
    """Match ``PackageService`` resolution: relative paths are under repo root."""
    resolved = output_dir.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _collect_main_manifests(manifests_dir: Path) -> List[Path]:
    paths: List[Path] = []
    for p in sorted(manifests_dir.glob("*.json")):
        if not p.is_file():
            continue
        if p.name.endswith("-bom.json"):
            continue
        paths.append(p)
    return paths


def _expected_remote_blob_keys(
    package_name: str, version: str, metadata: Any
) -> Set[str]:
    import os

    org, project = package_name.split("/", 1)
    prefix = (
        os.environ.get("OHM_PACKAGE_STORAGE_PREFIX", "packages").strip() or "packages"
    )
    base = f"{prefix}/{org}/{project}/{version}"
    keys = {
        f"{base}/manifest.json",
        f"{base}/build-info.json",
        f"{base}/file-manifest.json",
    }
    for finfo in metadata.file_inventory:
        rel = str(finfo.local_path).replace("\\", "/")
        keys.add(f"{base}/files/{rel}")
    return keys


async def _list_remote_keys(manager: Any, prefix: str) -> List[str]:
    out: List[str] = []
    async for obj in manager.list_objects(prefix=prefix):
        out.append(obj["key"])
    return out


async def _verify_remote_package(
    manager: Any,
    metadata: Any,
    push_result: Dict[str, Any],
) -> Dict[str, Any]:
    import os

    org, project = metadata.package_name.split("/", 1)
    top = os.environ.get("OHM_PACKAGE_STORAGE_PREFIX", "packages").strip() or "packages"
    list_prefix = f"{top}/{org}/{project}/{metadata.version}/"
    remote_keys = set(await _list_remote_keys(manager, list_prefix))
    expected = _expected_remote_blob_keys(
        metadata.package_name, metadata.version, metadata
    )
    missing = sorted(expected - remote_keys)
    push_failed = bool(push_result.get("failed_files"))
    valid = not push_failed and not missing
    return {
        "valid": valid,
        "missing_remote_keys": missing,
        "remote_blob_count": len(remote_keys),
        "expected_blob_count": len(expected),
        "push_failed_files": push_result.get("failed_files", []),
    }


async def _process_one(
    manifest_path: Path,
    output_dir: Path,
    package_service: Any,
    remote_storage: Any,
    storage_manager: Any,
    *,
    do_push: bool,
    verbose: int,
    collect_trace: bool,
    manifest_data: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    from src.core.models.package import BuildOptions

    record: Dict[str, Any] = {
        "manifest_file": manifest_path.name,
        "package_name": None,
        "version": None,
        "build_ok": False,
        "verify_ok": False,
        "push_ok": None,
        "remote_verify_ok": None,
        "error": None,
        "verify_detail": None,
        "push_detail": None,
        "remote_detail": None,
    }

    with _manifest_trace_context(manifest_path.name, collect_trace) as trace_lines:
        if manifest_data is None:
            try:
                with manifest_path.open(encoding="utf-8") as fh:
                    manifest_data = json.load(fh)
            except Exception as e:
                record["error"] = f"load_json: {e}"
                if collect_trace and trace_lines is not None:
                    record["fetch_trace"] = trace_lines
                return "error", record

        _print_fetch_hints(manifest_path, manifest_data, verbose=verbose)

        try:
            options = BuildOptions(output_dir=_build_options_output_dir(output_dir))
            metadata = await package_service.build_package_from_dict(
                manifest_data, options
            )
            record["package_name"] = metadata.package_name
            record["version"] = metadata.version
            record["build_ok"] = True
        except Exception as e:
            if isinstance(e, PackageAssetDownloadError):
                record["error"] = f"build_required_asset: {e}"
            else:
                record["error"] = f"build: {e}"
            if collect_trace and trace_lines is not None:
                record["fetch_trace"] = trace_lines
            return "error", record

        try:
            verify_result = await package_service.verify_package_metadata(metadata)
            record["verify_detail"] = verify_result
            record["verify_ok"] = bool(verify_result.get("valid"))
            if not record["verify_ok"]:
                record["error"] = "verify_failed"
                if collect_trace and trace_lines is not None:
                    record["fetch_trace"] = trace_lines
                return "error", record
        except Exception as e:
            record["error"] = f"verify: {e}"
            if collect_trace and trace_lines is not None:
                record["fetch_trace"] = trace_lines
            return "error", record

        if not do_push:
            record["push_ok"] = None
            record["remote_verify_ok"] = None
            if collect_trace and trace_lines is not None:
                record["fetch_trace"] = trace_lines
            return "ok", record

        package_path = Path(metadata.package_path)
        if not package_path.is_dir():
            record["error"] = f"package_path missing: {package_path}"
            if collect_trace and trace_lines is not None:
                record["fetch_trace"] = trace_lines
            return "error", record

        try:
            # Same entry point as CLI fallback_push (PackageRemoteStorage.push_package).
            if remote_storage is None:
                raise RuntimeError("remote_storage is required when push is enabled")
            push_result = await remote_storage.push_package(metadata, package_path)
            record["push_detail"] = push_result
            record["push_ok"] = not bool(push_result.get("failed_files"))
            if not record["push_ok"]:
                record["error"] = "push_failed"
                if collect_trace and trace_lines is not None:
                    record["fetch_trace"] = trace_lines
                return "error", record
        except Exception as e:
            record["error"] = f"push: {e}"
            record["push_ok"] = False
            if collect_trace and trace_lines is not None:
                record["fetch_trace"] = trace_lines
            return "error", record

        try:
            remote_result = await _verify_remote_package(
                storage_manager, metadata, push_result
            )
            record["remote_detail"] = remote_result
            record["remote_verify_ok"] = bool(remote_result.get("valid"))
            if not record["remote_verify_ok"]:
                record["error"] = "remote_verify_failed"
                if collect_trace and trace_lines is not None:
                    record["fetch_trace"] = trace_lines
                return "error", record
        except Exception as e:
            record["error"] = f"remote_verify: {e}"
            record["remote_verify_ok"] = False
            if collect_trace and trace_lines is not None:
                record["fetch_trace"] = trace_lines
            return "error", record

        if collect_trace and trace_lines is not None:
            record["fetch_trace"] = trace_lines

    return "ok", record


async def _run() -> int:
    import src.config.storage_config  # noqa: F401 — load .env early

    default_container = (
        os.getenv("AZURE_OKH_PACKAGE_CONTAINER")
        or os.getenv("AZURE_STORAGE_CONTAINER")
        or "okh-golden-dataset"
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--okh-id",
        type=str,
        default=None,
        metavar="UUID",
        help=(
            "Build exactly one package from this OKH manifest UUID in remote storage "
            "(uses OKHService; requires Azure/local storage config). "
            "Ignores --manifests-dir file list when set."
        ),
    )
    parser.add_argument(
        "--from-remote-okh",
        action="store_true",
        help=(
            "Build packages for every OKH manifest found in remote storage (okh/ prefix). "
            "Mutually exclusive with --okh-id; ignores --manifests-dir. "
            "Uses the same storage config as the API (.env)."
        ),
    )
    parser.add_argument(
        "--manifests-dir",
        type=Path,
        default=REPO_ROOT / "tmp/oshwa/okh-manifests",
        help="Directory of *.json OKH manifests (excludes *-bom.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "tmp/oshwa/built-packages",
        help="Package build root (org/project/version created beneath)",
    )
    parser.add_argument(
        "--container",
        default=default_container,
        help="Blob container (default: AZURE_OKH_PACKAGE_CONTAINER or AZURE_STORAGE_CONTAINER)",
    )
    parser.add_argument(
        "--create-container",
        action="store_true",
        help="Create container if missing (requires key with create permission)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="More stderr logging for packaging (-v=INFO, -vv=DEBUG). "
        "Prints BOM/repo URL hints before each build.",
    )
    parser.add_argument(
        "--trace-report",
        action="store_true",
        help="Add fetch_trace (WARNING+ packaging lines) to --report JSON without noisy -v",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Append DEBUG packaging logs to this UTF-8 file. "
            "When omitted, a timestamped file is written under tmp/oshwa/ "
            "unless --no-log-file is set."
        ),
    )
    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Skip the default timestamped log under tmp/oshwa/ (--log-file still applies).",
    )
    parser.add_argument(
        "--fetch-retries",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Sets OHM_PACKAGE_FETCH_MAX_RETRIES for this run (0 = one HTTP attempt per URL, "
            "faster batch; 3 matches previous default). Clamped to 0..10."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print manifest count and exit (no build). "
        "With --from-remote-okh, configures storage to count remote manifests.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Build and verify locally only; do not push or list remote",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N manifests (order: sorted filenames)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON array of per-manifest results to this path",
    )
    args = parser.parse_args()

    if args.log_file is not None:
        log_path: Optional[Path] = args.log_file.expanduser().resolve()
    elif args.no_log_file:
        log_path = None
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = (REPO_ROOT / "tmp" / "oshwa" / f"batch-packages-{ts}.log").resolve()

    fr = max(0, min(10, int(args.fetch_retries)))
    os.environ["OHM_PACKAGE_FETCH_MAX_RETRIES"] = str(fr)

    collect_trace = bool(args.verbose >= 1 or args.trace_report)
    _configure_batch_logging(args.verbose, collect_trace, log_path)

    if log_path is not None:
        print(f"Package log file: {log_path}", file=sys.stderr)

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    single_okh_id: Optional[UUID] = None
    if args.okh_id:
        try:
            single_okh_id = UUID(args.okh_id.strip())
        except ValueError:
            print(f"Invalid --okh-id (expected UUID): {args.okh_id!r}", file=sys.stderr)
            return 1

    if args.from_remote_okh and single_okh_id is not None:
        print("Use either --from-remote-okh or --okh-id, not both.", file=sys.stderr)
        return 1

    paths: List[Path] = []
    if single_okh_id is None and not args.from_remote_okh:
        manifests_dir = args.manifests_dir.expanduser().resolve()
        if not manifests_dir.is_dir():
            print(f"Manifest directory not found: {manifests_dir}", file=sys.stderr)
            return 1
        paths = _collect_main_manifests(manifests_dir)
        if args.limit is not None:
            paths = paths[: max(0, args.limit)]
        print(f"Manifests: {manifests_dir} ({len(paths)} file(s))")
    elif args.from_remote_okh:
        print("Manifests: remote OKH storage (all discoverable under okh/)")
        if args.limit is not None:
            print(
                f"Note: will process at most {args.limit} manifest(s) after stable sort.",
                file=sys.stderr,
            )
    else:
        if args.limit is not None:
            print("Note: --limit ignored when --okh-id is set.", file=sys.stderr)
        print(f"Single manifest from storage: okh id {single_okh_id}")

    print(f"Build output: {output_dir}")

    os.environ.setdefault("STORAGE_PROVIDER", "azure_blob")

    from src.config.storage_config import (
        create_storage_config,
        get_default_storage_config,
    )
    from src.core.packaging.remote_storage import PackageRemoteStorage
    from src.core.services.okh_service import OKHService
    from src.core.services.package_service import PackageService
    from src.core.services.storage_service import StorageService

    storage_service = await StorageService.get_instance()
    if not args.no_push:
        config = create_storage_config("azure_blob", bucket_name=args.container)
        await storage_service.configure(config)
    elif single_okh_id is not None or args.from_remote_okh:
        await storage_service.configure(get_default_storage_config())

    need_blob = (
        (not args.no_push) or (single_okh_id is not None) or args.from_remote_okh
    )

    if args.dry_run:
        if args.from_remote_okh:
            if not storage_service.manager:
                print(
                    "Storage not configured; cannot count remote OKH.", file=sys.stderr
                )
                return 1
            okh_service = await OKHService.get_instance()
            _manifests, total = await okh_service.list(page=1, page_size=500000)
            lim = ""
            if args.limit is not None:
                lim = f" (would cap at {args.limit} after sort order from service)"
            print(f"  would process: {total} remote OKH manifest(s){lim}")
            return 0
        if single_okh_id is not None:
            print(f"  would process: okh id {single_okh_id}")
        else:
            for p in paths[:15]:
                print(f"  would process: {p.name}")
            if len(paths) > 15:
                print(f"  ... and {len(paths) - 15} more")
        return 0
    if need_blob and not storage_service.manager:
        print("Storage manager not available after configure()", file=sys.stderr)
        return 1

    storage_manager = storage_service.manager if need_blob else None
    remote_storage: Optional[PackageRemoteStorage] = None
    if not args.no_push:
        remote_storage = PackageRemoteStorage(storage_service)

        if args.create_container:
            ok = await storage_manager.create_bucket(args.container)
            if not ok:
                print(
                    f"Failed to create container {args.container!r}.",
                    file=sys.stderr,
                )
                return 1

    package_service = await PackageService.get_instance()
    results: List[Dict[str, Any]] = []
    errors = 0

    try:
        if single_okh_id is not None:
            okh_service = await OKHService.get_instance()
            manifest_obj = await okh_service.get(single_okh_id)
            if not manifest_obj:
                print(
                    f"OKH manifest not found in storage: {single_okh_id}",
                    file=sys.stderr,
                )
                return 1
            manifest_dict = manifest_obj.to_dict()
            virtual_path = REPO_ROOT / "tmp" / f"okh-{single_okh_id}.json"
            status, record = await _process_one(
                virtual_path,
                output_dir,
                package_service,
                remote_storage,
                storage_manager,
                do_push=not args.no_push,
                verbose=args.verbose,
                collect_trace=collect_trace,
                manifest_data=manifest_dict,
            )
            results.append(record)
            label = record.get("package_name") or str(single_okh_id)
            if status == "ok":
                print(f"OK  {label}")
            else:
                errors += 1
                print(f"ERR {label}: {record.get('error')}", file=sys.stderr)
        elif args.from_remote_okh:
            from src.core.models.okh import OKHManifest

            okh_service = await OKHService.get_instance()
            page = 1
            page_size = 100_000
            total: Optional[int] = None
            remote_manifests: List[OKHManifest] = []
            while True:
                batch, t = await okh_service.list(page=page, page_size=page_size)
                if total is None:
                    total = t
                remote_manifests.extend(batch)
                if not batch or len(remote_manifests) >= (total or 0):
                    break
                page += 1

            remote_manifests.sort(key=lambda m: ((m.title or "").lower(), str(m.id)))
            if args.limit is not None:
                remote_manifests = remote_manifests[: max(0, args.limit)]

            for manifest_obj in remote_manifests:
                manifest_dict = manifest_obj.to_dict()
                virtual_path = REPO_ROOT / "tmp" / f"okh-{manifest_obj.id}.json"
                status, record = await _process_one(
                    virtual_path,
                    output_dir,
                    package_service,
                    remote_storage,
                    storage_manager,
                    do_push=not args.no_push,
                    verbose=args.verbose,
                    collect_trace=collect_trace,
                    manifest_data=manifest_dict,
                )
                results.append(record)
                label = record.get("package_name") or str(manifest_obj.id)
                if status == "ok":
                    print(f"OK  {label}")
                else:
                    errors += 1
                    print(f"ERR {label}: {record.get('error')}", file=sys.stderr)
        else:
            for manifest_path in paths:
                status, record = await _process_one(
                    manifest_path,
                    output_dir,
                    package_service,
                    remote_storage,
                    storage_manager,
                    do_push=not args.no_push,
                    verbose=args.verbose,
                    collect_trace=collect_trace,
                )
                results.append(record)
                label = record.get("package_name") or manifest_path.name
                if status == "ok":
                    print(f"OK  {label}")
                else:
                    errors += 1
                    print(f"ERR {label}: {record.get('error')}", file=sys.stderr)
    finally:
        await package_service.cleanup()

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(results, indent=2, default=str), encoding="utf-8"
        )
        print(f"Wrote report: {args.report}")

    n = len(results)
    print(f"Done. {n - errors} ok, {errors} error(s).")
    return 1 if errors else 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
