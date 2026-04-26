"""
Programmatic OKH generation from a repository URL or local clone path.

Mirrors the CLI ``generate-from-url`` fallback (direct engine) path so batch
scripts and tests stay aligned with interactive usage.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable, Optional

from .engine import GenerationEngine
from .models import LayerConfig, ManifestGeneration, PlatformType
from .platforms.github import GitHubExtractor
from .platforms.gitlab import GitLabExtractor
from .platforms.local_git import LocalGitExtractor
from .url_router import URLRouter

logger = logging.getLogger(__name__)

LogFn = Callable[[str, str], None]


def _default_log(message: str, level: str = "info") -> None:
    if level == "warning":
        logger.warning("%s", message)
    else:
        logger.info("%s", message)


async def generate_manifest_for_repository(
    url: str,
    *,
    clone: bool = True,
    save_clone: Optional[Path] = None,
    github_token: Optional[str] = None,
    use_llm: bool = True,
    use_bom_normalization: bool = True,
    include_file_metadata: bool = False,
    llm_chunked_mode_enabled: bool = True,
    llm_chunk_max_tokens: Optional[int] = None,
    llm_chunk_overlap_tokens: Optional[int] = None,
    log: Optional[LogFn] = None,
) -> ManifestGeneration:
    """
    Extract project data and run the generation engine.

    Args:
        url: Remote repo URL or existing local clone directory.
        clone: When True and *url* is remote, clone via LocalGitExtractor when supported.
        save_clone: Optional directory to persist the clone (remote + clone only).
        github_token: GitHub API token; defaults to ``GITHUB_TOKEN`` env.
        use_llm: Enable LLM layer (default True; engine skips LLM if unconfigured).
        use_bom_normalization: Enable BOM normalization (matches CLI default).
        include_file_metadata: Per-file metadata in manifest (CLI ``--verbose``).
        llm_chunked_mode_enabled: Chunked LLM map-reduce (default True; set False
            for a single-shot LLM request on smaller repos only).
        llm_chunk_max_tokens: Optional override for per-chunk payload budget.
        llm_chunk_overlap_tokens: Optional override for chunk overlap.
        log: Optional ``(message, level)`` callback; default uses module logger.
    """
    _log = log or _default_log
    router = URLRouter()
    local_input = Path(url)

    if local_input.is_dir():
        _log(f"Local path — extracting from {local_input}", "info")
        extractor = LocalGitExtractor()
        project_data = await extractor.extract_from_local_path(local_input)
    else:
        if not router.validate_url(url):
            raise ValueError(f"Invalid URL or path does not exist: {url}")
        platform = router.detect_platform(url)
        if platform is None:
            raise ValueError(f"Unsupported platform for URL: {url}")
        _log(f"Detected platform: {platform.value}", "info")

        use_clone = clone
        if use_clone and not router.supports_local_cloning(url):
            _log(
                "URL does not support local cloning — falling back to API extraction",
                "warning",
            )
            use_clone = False

        if use_clone:
            _log("Cloning and extracting via LocalGitExtractor", "info")
            persist = Path(save_clone) if save_clone else None
            generator = router.route_to_local_git_extractor()
            project_data = await generator.extract_project(url, persist_path=persist)
        else:
            _log("Fetching project data via platform API", "info")
            token = (
                github_token if github_token is not None else os.getenv("GITHUB_TOKEN")
            )
            if platform == PlatformType.GITHUB:
                generator = GitHubExtractor(github_token=token)
            elif platform == PlatformType.GITLAB:
                generator = GitLabExtractor()
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            project_data = await generator.extract_project(url)

    config = LayerConfig.for_generate_from_url(no_llm=not use_llm)
    config.use_bom_normalization = use_bom_normalization
    if use_llm and not llm_chunked_mode_enabled:
        config.llm_config["chunked_mode_enabled"] = False
    if llm_chunk_max_tokens is not None:
        config.llm_config["chunk_max_tokens"] = int(llm_chunk_max_tokens)
    if llm_chunk_overlap_tokens is not None:
        config.llm_config["chunk_overlap_tokens"] = int(llm_chunk_overlap_tokens)
    engine = GenerationEngine(config=config)
    _log("Running generation engine", "info")
    return await engine.generate_manifest_async(
        project_data, include_file_metadata=include_file_metadata
    )
