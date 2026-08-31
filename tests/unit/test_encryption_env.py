"""Credential encryption reads OHM_ names, and still honours the old ones (#371).

The same encryption protects LLM credentials today and storage-provider
credentials next, so an ``LLM_``-prefixed name is already wrong and every future
credential type would inherit it. Renaming a variable that gates decryption is
the kind of change that bricks a deployment if the fallback is missed, so the
fallback is what most of this covers.
"""

import logging

import pytest

from src.config import encryption_env
from src.config.encryption_env import encryption_names, encryption_setting

SUFFIXES = ["KEY", "SALT", "PASSWORD"]


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for suffix in SUFFIXES:
        for name in encryption_names(suffix):
            monkeypatch.delenv(name, raising=False)
    encryption_env._warned.clear()


@pytest.mark.parametrize("suffix", SUFFIXES)
def test_unset_is_none(suffix):
    assert encryption_setting(suffix) is None


@pytest.mark.parametrize("suffix", SUFFIXES)
def test_the_new_name_is_read(monkeypatch, suffix):
    preferred, _ = encryption_names(suffix)
    monkeypatch.setenv(preferred, "value")

    assert encryption_setting(suffix) == "value"


@pytest.mark.parametrize("suffix", SUFFIXES)
def test_an_existing_deployment_keeps_working(monkeypatch, suffix, caplog):
    """The criterion that matters: configured only with the old names, it still
    reads — and says so once."""
    _, deprecated = encryption_names(suffix)
    monkeypatch.setenv(deprecated, "existing")

    with caplog.at_level(logging.WARNING):
        assert encryption_setting(suffix) == "existing"

    assert deprecated in caplog.text
    assert encryption_names(suffix)[0] in caplog.text


@pytest.mark.parametrize("suffix", SUFFIXES)
def test_the_new_name_wins_when_both_are_set(monkeypatch, suffix):
    preferred, deprecated = encryption_names(suffix)
    monkeypatch.setenv(deprecated, "old")
    monkeypatch.setenv(preferred, "new")

    assert encryption_setting(suffix) == "new"


@pytest.mark.parametrize("suffix", SUFFIXES)
def test_an_empty_new_name_falls_back_rather_than_blanking(monkeypatch, suffix):
    """`.env` files carry empty keys as placeholders. An empty value means "not
    configured", not "configured to nothing" — otherwise adding the new name as
    a blank placeholder would silently disable an existing deployment."""
    preferred, deprecated = encryption_names(suffix)
    monkeypatch.setenv(preferred, "   ")
    monkeypatch.setenv(deprecated, "old")

    assert encryption_setting(suffix) == "old"


def test_the_deprecation_notice_is_logged_once(monkeypatch, caplog):
    """Encryption settings are read on every credential access; a notice per
    read is noise an operator learns to scroll past."""
    _, deprecated = encryption_names("KEY")
    monkeypatch.setenv(deprecated, "old")

    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            encryption_setting("KEY")

    assert caplog.text.count(deprecated) == 1


def test_both_spellings_are_treated_as_secrets():
    """Listing only one would mean the other is not fetched from the secrets
    manager — a silent difference in where a credential may live."""
    from src.config import settings

    source = (settings.__file__ or "").replace(".pyc", ".py")
    with open(source, encoding="utf-8") as handle:
        text = handle.read()

    for suffix in SUFFIXES:
        for name in encryption_names(suffix):
            assert f'"{name}"' in text, f"{name} is not in the sensitive-keys list"
