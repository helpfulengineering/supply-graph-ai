"""Compose defaults may not silently contradict the configuration schema.

`docker-compose.yml` restates many settings as `${VAR:-default}`. Most of those
defaults are *correct* to differ from the schema, because Compose knows things
the schema cannot: it ships a Redis, so it wires the Redis URLs; it ships a
worker, so it enables jobs. Those are deployment topology, not disagreement.

`LLM_ENABLED` was the exception, and it cost real behaviour. The schema defaults
it to `true` — it is a kill switch, not an enable switch, so with no provider
configured it changes nothing. Compose set `false`. The effect was that a
self-hoster who added a provider key through **Settings → LLM providers** got
silently nothing: no error, no log, a key stored and ignored. Nothing caught it
because nothing compared the two surfaces.

So this test does not forbid divergence. It forbids *undeclared* divergence:
every difference must be listed below with the topological reason it exists.
Adding a row is cheap and forces the question "why does Compose know better?" to
be answered once, in writing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config.schema import Settings  # noqa: E402

pytestmark = pytest.mark.unit

# Services that run the application. `ohm-cli` is excluded on purpose: it is a
# `cli`-profile test harness, not a node, and its settings describe a throwaway
# container rather than a deployment.
_APP_SERVICES = ("ohm-api", "ohm-worker")

_INTERPOLATION = re.compile(r"^\$\{[A-Z_]+:-(?P<default>.*)\}$")

# Env var -> why Compose's default is allowed to differ from the schema's.
# A row here is a claim that Compose knows something the schema cannot.
#
# Only variables that *contradict* a schema default need a row. Where the schema
# has no default at all — the Redis URLs, CORS_ORIGINS — Compose is supplying a
# value rather than disagreeing with one, so there is nothing to declare.
_TOPOLOGY_OVERRIDES: dict[str, str] = {
    "JOBS_ENABLED": "compose ships a worker, so async jobs are available here",
}


def _compose() -> dict:
    text = (_REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _declared_defaults(service: str) -> dict[str, str]:
    """Env var -> the default Compose applies when the variable is unset.

    Entries that are pure passthrough (`${VAR:-}`, empty default) are skipped:
    they express "use whatever the environment has", which is not a competing
    default.
    """
    entries = _compose()["services"][service].get("environment") or []
    defaults = {}
    for entry in entries:
        key, _, raw = entry.partition("=")
        match = _INTERPOLATION.match(raw)
        value = match.group("default") if match else raw
        if value:
            defaults[key] = value
    return defaults


def _schema_default(env_var: str):
    field = Settings.model_fields.get(env_var.lower())
    return None if field is None else field.default


@pytest.mark.parametrize("service", _APP_SERVICES)
def test_compose_defaults_match_the_schema_unless_declared(service):
    undeclared = []
    for env_var, compose_value in _declared_defaults(service).items():
        schema_value = _schema_default(env_var)
        if schema_value is None:
            continue  # not a Settings field, or has no schema default to contradict
        if env_var in _TOPOLOGY_OVERRIDES:
            continue
        if compose_value.lower() != str(schema_value).lower():
            undeclared.append(
                f"{env_var}: compose={compose_value!r} schema={schema_value!r}"
            )

    assert not undeclared, (
        f"{service} overrides schema defaults without a declared reason:\n  "
        + "\n  ".join(undeclared)
        + "\n\nEither match the schema, or add the variable to "
        "_TOPOLOGY_OVERRIDES with the reason compose knows better."
    )


def test_the_llm_kill_switch_is_not_inverted():
    """The specific regression above, pinned by name.

    A self-hoster adding a key through Settings must get an LLM without also
    discovering an undocumented environment variable.
    """
    for service in _APP_SERVICES:
        assert _declared_defaults(service).get("LLM_ENABLED") == "true", (
            f"{service} disables the LLM by default, so a provider key added "
            "through Settings would be silently ignored"
        )


def test_copying_the_env_template_cannot_disable_background_import():
    """`cp .env.example .env` is the documented way to start configuring a node.

    Compose interpolates `${VAR:-default}` from that same `.env`, so any value
    the template states becomes an override — and the template carries schema
    defaults, where `JOBS_ENABLED` is correctly `False` for a bare container.
    Interpolating it here meant following the documented setup step silently
    disabled background import on a stack that ships a worker to do it.

    Keeping these literal is what makes the template safe to copy.
    """
    compose = _compose()
    for service in _APP_SERVICES:
        entries = compose["services"][service].get("environment") or []
        jobs = next(e for e in entries if e.startswith("JOBS_ENABLED="))
        assert jobs == "JOBS_ENABLED=true", (
            f"{service} interpolates JOBS_ENABLED ({jobs!r}); a .env copied from "
            ".env.example would disable the worker this stack ships"
        )


def test_every_declared_override_is_still_a_real_divergence():
    """Stale allow-list entries are how an allow-list rots into a rubber stamp."""
    live = {
        env_var
        for service in _APP_SERVICES
        for env_var, value in _declared_defaults(service).items()
        if (schema := _schema_default(env_var)) is not None
        and value.lower() != str(schema).lower()
    }
    stale = sorted(set(_TOPOLOGY_OVERRIDES) - live)
    assert not stale, (
        f"_TOPOLOGY_OVERRIDES lists variables that no longer diverge: {stale}. "
        "Remove them so the list keeps meaning something."
    )
