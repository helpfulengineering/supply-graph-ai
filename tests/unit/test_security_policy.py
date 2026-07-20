"""Unit tests for the Security Mode policy provider (Slice 0)."""

import pytest

from src.config.security_policy import (
    SecurityMode,
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


def test_policy_is_immutable():
    policy = get_security_policy()
    with pytest.raises(Exception):
        policy.grant_ttl_days = 1  # type: ignore[misc]


@pytest.mark.parametrize("mode", ["crisis", "shielded"])
def test_reserved_modes_not_implemented(mode):
    with pytest.raises(NotImplementedError):
        get_security_policy(mode)


def test_parse_security_mode_normalizes_and_validates():
    assert parse_security_mode("  PEACETIME ") is SecurityMode.PEACETIME
    assert parse_security_mode(None) is SecurityMode.PEACETIME
    assert parse_security_mode(SecurityMode.CRISIS) is SecurityMode.CRISIS
    with pytest.raises(ValueError):
        parse_security_mode("nonsense")
