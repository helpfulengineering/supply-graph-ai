"""CLI interprets API package responses (e.g. ``success`` vs ``status``)."""

from __future__ import annotations

from src.cli.package import _cli_pull_display_fields, _cli_result_is_success


def test_cli_result_is_success_api_pull_response() -> None:
    assert _cli_result_is_success(
        {"success": True, "message": "Package x pulled successfully"}
    )


def test_cli_result_is_success_fallback() -> None:
    assert _cli_result_is_success({"status": "success", "message": "ok"})
    assert not _cli_result_is_success({"success": False})
    assert not _cli_result_is_success({"status": "error"})


def test_cli_pull_display_fields_from_api_shape() -> None:
    d = _cli_pull_display_fields(
        {
            "success": True,
            "local_path": "/tmp/pkg",
            "metadata": {
                "package_path": "/packages/o/p/v",
                "size": 42,
                "metadata": {"total_files": 3},
            },
        }
    )
    assert d["package_path"] == "/packages/o/p/v"
    assert d["total_files"] == 3
    assert d["total_size_bytes"] == 42
