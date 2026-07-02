"""Tests for src/cli/progress.py.

Verifies that:
  - emit_status_line always writes to stderr (err=True) regardless of output_format.
  - build_status_line produces the expected format string.
  - should_render_progress returns True for all format values.
"""

from __future__ import annotations

from unittest.mock import call, patch

import pytest

from src.cli.progress import (
    build_status_line,
    emit_status_line,
    should_render_progress,
)

# ---------------------------------------------------------------------------
# build_status_line
# ---------------------------------------------------------------------------


def test_build_status_line_format():
    assert build_status_line("Loading", 1, 4) == "Status [1/4]: Loading"


def test_build_status_line_last_step():
    assert build_status_line("Done", 4, 4) == "Status [4/4]: Done"


# ---------------------------------------------------------------------------
# should_render_progress
# ---------------------------------------------------------------------------


def test_should_render_progress_json():
    """Progress rendering must be enabled even in JSON mode."""
    assert should_render_progress("json") is True


def test_should_render_progress_text():
    assert should_render_progress("text") is True


def test_should_render_progress_default():
    assert should_render_progress("") is True


# ---------------------------------------------------------------------------
# emit_status_line — stderr routing
# ---------------------------------------------------------------------------


def test_emit_status_line_writes_to_stderr_in_json_mode():
    """In JSON mode stdout must stay clean; progress must go to stderr."""
    with patch("src.cli.progress.click.echo") as mock_echo:
        emit_status_line(output_format="json", step="Extracting", index=2, total=4)

    mock_echo.assert_called_once()
    _args, kwargs = mock_echo.call_args
    assert kwargs.get("err") is True, "emit_status_line must set err=True in JSON mode"


def test_emit_status_line_writes_to_stderr_in_text_mode():
    """Progress always goes to stderr even in plain text mode."""
    with patch("src.cli.progress.click.echo") as mock_echo:
        emit_status_line(output_format="text", step="Saving", index=3, total=4)

    _args, kwargs = mock_echo.call_args
    assert kwargs.get("err") is True, "emit_status_line must always use err=True"


def test_emit_status_line_message_content():
    """The emitted message should match build_status_line output."""
    with patch("src.cli.progress.click.echo") as mock_echo:
        emit_status_line(output_format="json", step="Reviewing", index=3, total=4)

    emitted_text = mock_echo.call_args[0][0]
    assert emitted_text == "Status [3/4]: Reviewing"
