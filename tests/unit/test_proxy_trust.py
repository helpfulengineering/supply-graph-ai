"""Only a named proxy may speak for someone else (#411).

Uvicorn rewrites ``request.client`` from ``X-Forwarded-For`` when the immediate
peer is trusted and ignores the header when it is not, so this trust set decides
whether the address behind every rate limit, log line and metric is a fact or a
claim. It was ``*``.

These assert our configured value against uvicorn's own resolver rather than
reimplementing the parsing: the algorithm is theirs and already correct, the
configuration was ours and was not.
"""

import os

import pytest
from uvicorn.middleware.proxy_headers import _TrustedHosts

from src.config.proxy_trust import DEFAULT_FORWARDED_ALLOW_IPS, forwarded_allow_ips


@pytest.fixture
def trusted() -> _TrustedHosts:
    return _TrustedHosts(DEFAULT_FORWARDED_ALLOW_IPS)


def test_the_default_does_not_trust_every_peer():
    """The bug in one line: '*' means uvicorn believes any caller's own header."""
    assert DEFAULT_FORWARDED_ALLOW_IPS != "*"
    assert "*" not in DEFAULT_FORWARDED_ALLOW_IPS


@pytest.mark.parametrize("peer", ["198.51.100.7", "203.0.113.9", "8.8.8.8"])
def test_a_public_peer_is_not_believed(trusted, peer):
    """A client connecting directly cannot forge its way out of its budget:
    an untrusted peer's forwarded headers are not read at all."""
    assert peer not in trusted


@pytest.mark.parametrize(
    "peer", ["127.0.0.1", "::1", "10.0.0.5", "172.16.4.4", "192.168.1.9"]
)
def test_the_platform_ingress_is_believed(trusted, peer):
    """Loopback and the private ranges — the container is only reachable
    through its ingress, which connects from inside the private network. This
    is also what keeps X-Forwarded-Proto working, which is why the setting was
    widened to '*' in the first place."""
    assert peer in trusted


def test_a_forged_leading_entry_does_not_win(trusted):
    """The failure this closes.

    A caller sends `X-Forwarded-For: 198.51.100.7`; the ingress appends the
    address it actually saw. Resolution walks from the right and stops at the
    first untrusted host, so the appended one wins and the forged one is
    ignored. Under '*' uvicorn returned the leftmost entry instead — the forged
    one — which is what made the rate limit evadable.
    """
    host, _ = trusted.get_trusted_client_address("198.51.100.7, 203.0.113.42")
    assert host == "203.0.113.42"


def test_two_clients_behind_one_proxy_resolve_separately(trusted):
    """Otherwise every browser user shares a single budget."""
    first, _ = trusted.get_trusted_client_address("203.0.113.1")
    second, _ = trusted.get_trusted_client_address("203.0.113.2")
    assert first != second


def test_star_remains_available_but_has_to_be_asked_for(monkeypatch):
    """A deployment that genuinely fronts everything with its own proxy can
    still opt in; what changed is that it is no longer the default."""
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")
    assert forwarded_allow_ips() == "*"
    monkeypatch.delenv("FORWARDED_ALLOW_IPS")
    assert forwarded_allow_ips() == DEFAULT_FORWARDED_ALLOW_IPS


def test_an_empty_setting_falls_back_rather_than_trusting_nothing(monkeypatch):
    """An unset-looking value must not silently resolve to a trust set that
    breaks X-Forwarded-Proto behind an ingress."""
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "")
    assert forwarded_allow_ips() == DEFAULT_FORWARDED_ALLOW_IPS


def test_the_deployed_gunicorn_config_uses_this_value():
    """The value has one home. A literal copied into gunicorn.conf.py would be
    the duplicated-config shape that drifts silently."""
    conf = os.path.join(
        os.path.dirname(__file__), "..", "..", "deploy", "docker", "gunicorn.conf.py"
    )
    with open(conf, encoding="utf-8") as handle:
        source = handle.read()
    assert "proxy_trust" in source
    assert '"*"' not in source.split("forwarded_allow_ips")[1][:200]
