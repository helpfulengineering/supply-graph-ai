"""The published guides describe the membership push (#638).

The issues in that push do not each edit the guides. This pass does, once.
A page that slips back to "registration is the security mode" fails here.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _read(*parts: str) -> str:
    text = (_ROOT.joinpath(*parts)).read_text(encoding="utf-8")
    return " ".join(text.split())


def test_join_and_write_key_describe_open_invite_and_closed():
    join = _read("docs-site", "docs", "guides", "join-a-node.md")
    write_key = _read("docs-site", "docs", "guides", "get-a-write-key.md")
    for page in (join, write_key):
        assert "`open`" in page
        assert "`invite`" in page
        assert "`closed`" in page
        assert "overrides" in page
        assert "peacetime" in page and "shielded" in page
    assert "/register?invite=" in join
    assert "expires" in join
    assert "revoked" in join
    assert "open registration is on in" not in join
    assert "off only" not in write_key


def test_an_operator_can_read_how_to_set_registration_and_mint_invites():
    page = _read("docs-site", "docs", "guides", "run-your-own-node.md")
    assert "ohm identity registration --set" in page
    assert "ohm identity invite mint" in page
    assert "ohm identity invite list" in page
    assert "ohm identity invite revoke" in page
    assert "Settings → Invites" in page


def test_a_coordinator_reaches_invites_and_the_member_inventory():
    page = _read("docs-site", "docs", "guides", "run-your-own-node.md")
    assert "ohm identity coordinate" in page
    assert "180 days in every" in page
    assert "Settings → Members" in page
    assert "does not read a private record" in page
    assert "who may register" in page


def test_the_guides_describe_organisation_publishing_and_curated_lists():
    design = _read("docs-site", "docs", "guides", "add-a-design.md")
    node = _read("docs-site", "docs", "guides", "run-your-own-node.md")
    assert "On behalf of" in design
    assert "ohm okh attribute" in design
    assert "affiliation" in design
    assert "ohm federation lists subscribe" in node
    assert "superseded" in node
    assert "removed" in node
    assert "ohm federation lists marks" in node


def test_architecture_pages_do_not_leave_registration_as_only_the_mode():
    identity = _read("docs", "architecture", "identity-model.md")
    routes = _read("docs", "architecture", "route-authorization.md")
    modes = _read("docs", "architecture", "security-modes.md")
    assert "Shielded mode refuses registration" not in identity
    assert "`invite`" in identity and "overrides" in identity
    assert "gated by `SecurityPolicy.open_registration`, not by a key" not in routes
    assert "`invite`" in routes and "`closed`" in routes
    assert "overrides" in modes
