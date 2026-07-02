"""CI guard: the spaCy model must be a real, loadable, locked dependency.

The other spaCy tests mock the library to check fallback/logging behaviour.
This one exercises the *actually installed* model. It exists because the model
repeatedly went missing when it was installed out-of-band (`python -m spacy
download`) instead of pinned in uv.lock: uv's exact sync deleted it on the next
`uv run`/`uv sync`. Now that it is a locked dependency, any regression (unpin,
spaCy major bump breaking model compat, botched provisioning) fails loudly here
instead of silently degrading matching to the string/heuristic layers.

Reuses `check_spacy_model()` from scripts/verify_dev_env.py so the contributor
setup path (`make setup`), the local gate (`make ready`), and CI share one
source of truth.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_dev_env.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_dev_env", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_spacy_model_is_installed_and_loadable():
    """The pinned spaCy model must load in a properly provisioned environment."""
    verifier = _load_verifier()
    # Raises RuntimeError if the model is missing/unloadable; the message tells
    # the contributor to run `make setup`.
    detail = verifier.check_spacy_model()
    assert "en_core_web" in detail, f"unexpected model reported: {detail!r}"
