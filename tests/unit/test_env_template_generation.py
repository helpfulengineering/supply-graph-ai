"""Tests for the env.template generator (config Slice 1 / #238).

Pin the lockfile behaviour: the generated block is deterministic, covers every
schema field, and the committed env.template is not stale.
"""

import importlib.util
from pathlib import Path

from src.config.schema import Settings

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "generate_env_template.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_env_template", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generator()


def test_block_is_deterministic():
    assert gen.render_block() == gen.render_block()


def test_block_covers_every_schema_field():
    block = gen.render_block()
    for name in Settings.model_fields:
        assert name.upper() in block, f"{name} missing from generated block"


def test_secret_field_is_commented_and_labeled():
    block = gen.render_block()
    # The one secret in Slice 1 must be commented out and flagged, never active.
    assert "# AZURE_STORAGE_KEY=" in block
    assert "SECRET" in block
    assert "\nAZURE_STORAGE_KEY=" not in block  # not an active assignment


def test_non_secret_default_is_active():
    block = gen.render_block()
    assert "\nENVIRONMENT=development" in "\n" + block
    assert "\nSTORAGE_PROVIDER=local" in "\n" + block


def test_committed_template_is_not_stale():
    current = gen._ENV_TEMPLATE.read_text(encoding="utf-8")
    assert (
        gen.render_template(current) == current
    ), "env.template is stale — run `make env-template` and commit the result."
