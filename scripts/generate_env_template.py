#!/usr/bin/env python3
"""Regenerate the schema-owned block of ``env.template`` from the config schema.

The typed schema (:class:`src.config.schema.Settings`) is the source of truth for
Slice-1 settings. This script emits one entry per schema field — name, one-line
description, default, and secret-vs-not — into the marked block of ``env.template``,
leaving the hand-maintained remainder untouched. As later slices migrate more
settings onto the schema, the block grows automatically.

Usage:
    python scripts/generate_env_template.py           # rewrite the block in place
    python scripts/generate_env_template.py --check    # exit 1 if the block is stale

CI runs the in-place form followed by ``git diff --exit-code env.template``
(the same lockfile pattern used for the repository map).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config.schema import Settings  # noqa: E402

_ENV_TEMPLATE = _REPO_ROOT / "env.template"
_BEGIN = "# === BEGIN GENERATED: schema-owned settings — regenerate with 'make env-template' ==="
_END = "# === END GENERATED ==="


def _is_secret(field) -> bool:
    extra = field.json_schema_extra or {}
    return bool(isinstance(extra, dict) and extra.get("secret"))


def render_block() -> str:
    """Render the generated block body (between, but excluding, the markers)."""
    lines = [
        "# Managed by scripts/generate_env_template.py — do not edit by hand.",
        "# Non-secret values are also checked in per environment under",
        "# config/environments/<ENVIRONMENT>.toml; anything set here overrides them.",
        "",
    ]
    for name, field in Settings.model_fields.items():
        env_name = name.upper()
        if field.description:
            lines.append(f"# {field.description}")
        if _is_secret(field):
            lines.append(
                f"# {env_name}=   # SECRET — set in .env / secretRef, never commit"
            )
        elif field.default is None:
            # Optional (no default): comment out so a copied .env stays minimal.
            lines.append(f"# {env_name}=")
        else:
            lines.append(f"{env_name}={field.default}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_template(current: str) -> str:
    """Return ``current`` with the marked block replaced by a fresh render."""
    if _BEGIN not in current or _END not in current:
        raise SystemExit(
            f"env.template is missing the generated-block markers.\n"
            f"Add these two lines where the block should live:\n{_BEGIN}\n{_END}"
        )
    head, rest = current.split(_BEGIN, 1)
    _, tail = rest.split(_END, 1)
    return f"{head}{_BEGIN}\n{render_block()}{_END}{tail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if env.template's generated block is stale.",
    )
    args = parser.parse_args()

    current = _ENV_TEMPLATE.read_text(encoding="utf-8")
    updated = render_template(current)

    if args.check:
        if current != updated:
            print(
                "env.template is stale. Run `make env-template` and commit the result.",
                file=sys.stderr,
            )
            return 1
        print("env.template is up to date.")
        return 0

    if current != updated:
        _ENV_TEMPLATE.write_text(updated, encoding="utf-8")
        print("Regenerated env.template schema block.")
    else:
        print("env.template already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
