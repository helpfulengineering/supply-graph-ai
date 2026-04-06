"""Shared progress indicator helpers for OHM CLI commands."""

import click


def should_render_progress(output_format: str) -> bool:
    """Return True when human-readable progress lines should be shown."""
    return output_format != "json"


def build_status_line(step: str, index: int, total: int) -> str:
    """Build a stable, parseable CLI status line."""
    return f"Status [{index}/{total}]: {step}"


def emit_status_line(output_format: str, step: str, index: int, total: int) -> None:
    """Emit status lines for human-readable output only."""
    if should_render_progress(output_format):
        click.echo(build_status_line(step=step, index=index, total=total))
