"""Smoke tests for batch progress/timeout helpers (no network)."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts import okh_generation_batch as batch


def test_write_report_roundtrip(tmp_path: Path) -> None:
    args = argparse.Namespace(
        repositories_json=batch.REPO_ROOT
        / "tests/data/okh_generation/repositories.json",
        layer=None,
        save_clones=False,
        llm_chunk_max_tokens=0,
        llm_chunk_overlap_tokens=0,
        repo_timeout_seconds=600,
    )
    out = tmp_path / "report.json"
    batch._write_report(
        out,
        args=args,
        layer_tag="4L",
        use_llm=True,
        llm_chunked=True,
        use_clone=True,
        selected=[{"id": "x"}],
        rows=[{"id": "x", "status": "ok"}],
        errors=0,
    )
    data = out.read_text(encoding="utf-8")
    assert '"processed_count": 1' in data
    assert '"repo_timeout_seconds": 600' in data
