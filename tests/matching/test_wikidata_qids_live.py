"""Opt-in check that every wikidata_qid names the entity we think it does.

Wikidata QIDs are the shared anchor OHM and Maps of Making join on, and a wrong
one fails silently: the SPARQL join simply returns nothing, or — worse — agrees
with a partner who copied the same mistake, so both sides look consistent while
pointing at an asteroid. Nothing in the type system or the offline suite can
catch that, because the QID is only meaningful to a third party.

Six were wrong when this was written (welding named the Byzantine Empire,
laser cutting a list of Dutch mayors). This is the test that would have caught
them. Live because the truth lives at Wikidata; skipped unless WIKIDATA_LIVE=1.
"""

from __future__ import annotations

import os
import re

import pytest

WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

# Wikimedia's User-Agent policy rejects generic clients with a 403.
WIKIDATA_HEADERS = {
    "User-Agent": "OpenHardwareManager-TaxonomyCheck/1.0 "
    "(https://github.com/binaryLady/OHM)"
}


def _wikidata_live_enabled() -> bool:
    return os.environ.get("WIKIDATA_LIVE", "").strip() in {"1", "true", "TRUE", "yes"}


pytestmark = [
    pytest.mark.allow_network,
    pytest.mark.skipif(
        not _wikidata_live_enabled(),
        reason="Set WIKIDATA_LIVE=1 to verify taxonomy QIDs against Wikidata",
    ),
]


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 2}


def _qid_processes():
    """Every (canonical_id, definition) in the YAML that carries a QID.

    Read from the YAML rather than the singleton because that file is what a
    human edits when adding one, and it is where a wrong value gets typed.
    """
    from src.core.taxonomy import DEFAULT_TAXONOMY_PATH, load_from_yaml

    return [
        (d.canonical_id, d)
        for d in load_from_yaml(DEFAULT_TAXONOMY_PATH)
        if d.wikidata_qid
    ]


def test_every_taxonomy_qid_resolves_to_a_plausible_entity():
    import httpx

    processes = _qid_processes()
    assert processes, "No QIDs in the taxonomy to verify"

    mismatches = []
    with httpx.Client(
        timeout=20.0, follow_redirects=True, headers=WIKIDATA_HEADERS
    ) as client:
        for canonical_id, definition in processes:
            qid = definition.wikidata_qid
            response = client.get(WIKIDATA_ENTITY_URL.format(qid=qid))
            response.raise_for_status()
            entity = next(iter(response.json()["entities"].values()))
            label = (entity.get("labels", {}).get("en") or {}).get("value")

            if not label:
                mismatches.append(f"{canonical_id} -> {qid} has no English label")
                continue

            # The label should share a word with the process's own vocabulary.
            # Deliberately loose: it is here to catch "Byzantine Empire", not to
            # adjudicate whether "numerical control" is the best name for CNC.
            vocabulary = _tokens(definition.display_name) | {
                tok for alias in definition.aliases for tok in _tokens(alias)
            }
            if not (_tokens(label) & vocabulary):
                mismatches.append(f"{canonical_id} -> {qid} is {label!r}")

    assert not mismatches, "Wikidata QIDs name the wrong entity:\n  " + "\n  ".join(
        mismatches
    )
