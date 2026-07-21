"""Unit tests for the Security Mode policy provider (Slices 0 + 8)."""

import pytest

from src.config.security_policy import (
    SecurityMode,
    allows_full_metadata_logging,
    get_security_policy,
    parse_security_mode,
)


def test_peacetime_is_default():
    policy = get_security_policy()
    assert policy.mode is SecurityMode.PEACETIME


def test_peacetime_preset_values():
    policy = get_security_policy("peacetime")
    assert policy.custodial_keys_allowed is True
    assert policy.grant_ttl_days == 90
    assert policy.recovery == "reissuance"
    assert policy.trust_bootstrap == "tofu_registry"
    assert policy.mdns_advertise is True
    assert policy.metadata_logging == "full"
    assert policy.registry_attestations == "trust_on_follow"
    assert policy.anonymous_submission_allowed is True


def test_crisis_preset_values():
    policy = get_security_policy("crisis")
    assert policy.mode is SecurityMode.CRISIS
    assert policy.custodial_keys_allowed is True
    assert policy.grant_ttl_days == 180
    assert policy.recovery == "reissuance"
    assert policy.trust_bootstrap == "tofu_friendly"
    assert policy.mdns_advertise is True
    assert policy.metadata_logging == "full"
    assert policy.registry_attestations == "trust_on_follow"
    assert policy.require_auth_for_writes is True
    assert policy.anonymous_submission_allowed is True


def test_shielded_preset_values():
    policy = get_security_policy("shielded")
    assert policy.mode is SecurityMode.SHIELDED
    assert policy.custodial_keys_allowed is False
    assert policy.grant_ttl_days == 7
    assert policy.recovery == "none"
    assert policy.trust_bootstrap == "explicit_only"
    assert policy.mdns_advertise is False
    assert policy.metadata_logging == "minimal"
    assert policy.registry_attestations == "ca_pinned"
    assert policy.require_auth_for_writes is True
    assert policy.anonymous_submission_allowed is False
    assert allows_full_metadata_logging(policy) is False


def test_policy_is_immutable():
    policy = get_security_policy()
    with pytest.raises(Exception):
        policy.grant_ttl_days = 1  # type: ignore[misc]


def test_parse_security_mode_normalizes_and_validates():
    assert parse_security_mode("  PEACETIME ") is SecurityMode.PEACETIME
    assert parse_security_mode(None) is SecurityMode.PEACETIME
    assert parse_security_mode(SecurityMode.CRISIS) is SecurityMode.CRISIS
    with pytest.raises(ValueError):
        parse_security_mode("nonsense")


@pytest.mark.parametrize(
    "environment,expected",
    [
        ("production", True),
        ("development", False),
        ("test", False),
    ],
)
def test_peacetime_write_enforcement_follows_environment(
    monkeypatch, environment, expected
):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", environment)
    policy = get_security_policy("peacetime")
    assert policy.require_auth_for_writes is expected


def test_crisis_and_shielded_always_require_write_auth(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    assert get_security_policy("crisis").require_auth_for_writes is True
    assert get_security_policy("shielded").require_auth_for_writes is True


def test_to_public_dict_includes_mode_value():
    data = get_security_policy("shielded").to_public_dict()
    assert data["mode"] == "shielded"
    assert data["mdns_advertise"] is False
