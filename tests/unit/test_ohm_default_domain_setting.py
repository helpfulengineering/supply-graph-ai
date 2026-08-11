"""OHM_DEFAULT_DOMAIN: must default to 'manufacturing' when unset.

Regression guard from the cooking-domain-instance plan: the manufacturing
default must never depend on an env var being set.
"""

from __future__ import annotations

import importlib


def test_default_domain_setting_defaults_to_manufacturing(monkeypatch):
    monkeypatch.delenv("OHM_DEFAULT_DOMAIN", raising=False)

    from src.config import settings

    importlib.reload(settings)
    try:
        assert settings.OHM_DEFAULT_DOMAIN == "manufacturing"
    finally:
        importlib.reload(settings)


def test_default_domain_setting_honors_env_override(monkeypatch):
    monkeypatch.setenv("OHM_DEFAULT_DOMAIN", "cooking")

    from src.config import settings

    importlib.reload(settings)
    try:
        assert settings.OHM_DEFAULT_DOMAIN == "cooking"
    finally:
        monkeypatch.delenv("OHM_DEFAULT_DOMAIN", raising=False)
        importlib.reload(settings)
