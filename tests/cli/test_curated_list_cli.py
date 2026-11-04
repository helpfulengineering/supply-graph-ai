"""Publish and edit a curated list from the command line (#580)."""

from click.testing import CliRunner

from src.cli.base import CLIConfig, CLIContext
from src.cli.federation import federation_group

DOCUMENT = {
    "list_id": "list-1",
    "name": "Field designs",
    "publisher_did": "did:key:zSpace",
    "sequence": 1,
    "entries": [
        {"content_hash": "sha256:aaa"},
        {"content_hash": "sha256:bbb", "supersedes": "sha256:old"},
    ],
    "signature": "00",
}


def _invoke(monkeypatch, args, payload):
    seen = {}

    async def fake(cli_ctx, method, path, json=None, params=None):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = json
        if params is not None:
            seen["params"] = params
        return payload

    monkeypatch.setattr("src.cli.federation._send", fake)
    result = CliRunner().invoke(federation_group, args, obj=CLIContext(CLIConfig()))
    return result, seen


def test_publish_sends_the_pins_and_the_publisher(monkeypatch):
    result, seen = _invoke(
        monkeypatch,
        [
            "lists",
            "publish",
            "--name",
            "Field designs",
            "--pin",
            "sha256:aaa",
            "--pin",
            "sha256:bbb",
            "--replaces",
            "sha256:bbb=sha256:old",
            "--publisher",
            "did:key:zSpace",
        ],
        DOCUMENT,
    )
    assert result.exit_code == 0, result.output
    assert seen["method"] == "POST"
    assert seen["path"] == "/lists"
    assert seen["json"] == {
        "name": "Field designs",
        "publisher_did": "did:key:zSpace",
        "entries": [
            {"content_hash": "sha256:aaa"},
            {"content_hash": "sha256:bbb", "supersedes": "sha256:old"},
        ],
    }
    assert "sequence 1" in result.output
    assert "replaces sha256:old" in result.output


def test_update_sends_the_next_membership(monkeypatch):
    result, seen = _invoke(
        monkeypatch,
        [
            "lists",
            "update",
            "list-1",
            "--name",
            "Field designs",
            "--pin",
            "sha256:bbb",
        ],
        {**DOCUMENT, "sequence": 2, "entries": [{"content_hash": "sha256:bbb"}]},
    )
    assert result.exit_code == 0, result.output
    assert seen == {
        "method": "PUT",
        "path": "/lists/list-1",
        "json": {"name": "Field designs", "entries": [{"content_hash": "sha256:bbb"}]},
    }
    assert "sequence 2" in result.output


def test_subscribe_names_the_peer_and_the_list(monkeypatch):
    result, seen = _invoke(
        monkeypatch,
        [
            "lists",
            "subscribe",
            "--peer",
            "http://peer.example",
            "--list",
            "field-designs",
        ],
        {
            "list_id": "field-designs",
            "name": "Field designs",
            "publisher_did": "did:key:zSpace",
            "peer_url": "http://peer.example",
            "sequence": 1,
        },
    )
    assert result.exit_code == 0, result.output
    assert seen["method"] == "POST"
    assert seen["path"] == "/lists/subscriptions"
    assert seen["json"] == {
        "peer_url": "http://peer.example",
        "list_id": "field-designs",
    }
    assert "Field designs" in result.output
    assert "http://peer.example" in result.output


def test_unsubscribe_forgets_the_list(monkeypatch):
    result, seen = _invoke(
        monkeypatch,
        [
            "lists",
            "unsubscribe",
            "--peer",
            "http://peer.example",
            "--list",
            "field-designs",
        ],
        None,
    )
    assert result.exit_code == 0, result.output
    assert seen["method"] == "DELETE"
    assert seen["path"] == "/lists/subscriptions"
    assert seen["params"] == {
        "peer_url": "http://peer.example",
        "list_id": "field-designs",
    }
    assert "Unsubscribed" in result.output
