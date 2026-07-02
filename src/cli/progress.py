"""Shared progress indicator helpers for OHM CLI commands."""

import click


def should_render_progress(output_format: str) -> bool:
    """Return True when human-readable progress lines should be shown."""
    return True


def build_status_line(step: str, index: int, total: int) -> str:
    """Build a stable, parseable CLI status line."""
    return f"Status [{index}/{total}]: {step}"


def emit_status_line(output_format: str, step: str, index: int, total: int) -> None:
    """Emit status lines to stderr.

    In JSON mode stdout must stay clean for piping, so progress always goes to
    stderr.  In text mode it also goes to stderr so it doesn't mix with any
    printed output.
    """
    click.echo(build_status_line(step=step, index=index, total=total), err=True)
