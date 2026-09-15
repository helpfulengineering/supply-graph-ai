"""The contact list a coordinator actually acts on (#498).

Written against the real OKW nesting, which is two deep: `facility.contact` is
an **Agent** and `agent.contact` is a **Contact`. Getting that wrong is not
hypothetical — the RFQ template navigates the same structure and omits `email`.
"""

from __future__ import annotations

import csv
import io
import json

import pytest

from src.core.services.contact_export import (
    COLUMNS,
    contact_rows,
    export_filename,
    facility_contact,
    facility_location,
    to_csv,
    to_json,
)

pytestmark = pytest.mark.unit

FACILITY = {
    "name": "Bristol Fab Lab",
    "location": {"city": "Bristol", "country": "UK"},
    "contact": {
        "name": "Bristol Makers CIC",
        "contact_person": "Ada Okafor",
        "website": "https://example.org",
        "mailing_list": "list@example.org",
        "contact": {
            "email": "ada@example.org",
            "landline": "+44 117 000 0000",
            "mobile": "+44 7700 000000",
            "whatsapp": "+44 7700 000000",
        },
    },
}

SOLUTION = {
    "facility_id": "f-1",
    "facility_name": "Bristol Fab Lab",
    "confidence": 0.8712,
    "facility": FACILITY,
    "tree": {"capabilities_used": ["3d-printing", "laser-cutting"]},
}


def test_contact_reaches_two_levels_down():
    """The Agent/Contact nesting, including the field RFQ forgets."""
    got = facility_contact(FACILITY)
    assert got["email"] == "ada@example.org"
    assert got["contact_person"] == "Ada Okafor"
    assert got["organisation"] == "Bristol Makers CIC"
    assert got["phone"] == "+44 117 000 0000"
    assert got["mobile"] == "+44 7700 000000"
    assert got["whatsapp"] == "+44 7700 000000"
    assert got["mailing_list"] == "list@example.org"


@pytest.mark.parametrize(
    "facility",
    [
        {},
        {"contact": None},
        {"contact": "not-a-dict"},
        {"contact": {"contact": None}},
        {"contact": {"contact": "not-a-dict"}},
    ],
)
def test_missing_or_malformed_contact_is_empty_not_an_error(facility):
    """Facility data is other people's; a bad shape must not fail the export."""
    assert facility_contact(facility) == {}


def test_location_says_so_when_absent():
    assert facility_location({"location": {"city": "Bristol"}}) == "Bristol"
    assert facility_location({}) == "Location not specified"


def test_a_row_carries_what_you_would_phone_someone_with():
    (row,) = contact_rows([SOLUTION])
    assert row["facility_name"] == "Bristol Fab Lab"
    assert row["location"] == "Bristol, UK"
    assert row["email"] == "ada@example.org"
    assert row["matched_processes"] == "3d-printing; laser-cutting"
    assert row["confidence"] == "0.87"
    assert set(row) == set(COLUMNS)


def test_order_is_the_callers_order():
    """The results view ranks by match quality; the export must agree with it."""
    second = {**SOLUTION, "facility_id": "f-2", "facility_name": "Second"}
    rows = contact_rows([SOLUTION, second])
    assert [r["facility_id"] for r in rows] == ["f-1", "f-2"]


def test_csv_is_readable_by_a_csv_reader_and_says_it_is_a_snapshot():
    text = to_csv(
        contact_rows([SOLUTION]), design="Ventilator", matched_at="2026-09-14T10:00:00Z"
    )
    assert "# Open Hardware Manager — facilities matched to Ventilator" in text
    assert "snapshot" in text
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    rows = list(csv.DictReader(io.StringIO(body)))
    assert len(rows) == 1
    assert rows[0]["email"] == "ada@example.org"
    assert list(rows[0]) == list(COLUMNS)


def test_json_carries_the_same_provenance():
    payload = json.loads(
        to_json(
            contact_rows([SOLUTION]),
            design="Ventilator",
            matched_at="2026-09-14T10:00:00Z",
        )
    )
    assert payload["design"] == "Ventilator"
    assert payload["matched_at"] == "2026-09-14T10:00:00Z"
    assert payload["contacts"][0]["email"] == "ada@example.org"


def test_filename_carries_the_design_and_the_date():
    """Two exports in a directory are diffed by a human; the date must be in the name."""
    assert (
        export_filename("Open Source Ventilator", "csv", "2026-09-14T10:00:00Z")
        == "contacts-open-source-ventilator-2026-09-14.csv"
    )
    assert export_filename(None, "json", "2026-09-14T10:00:00Z").startswith(
        "contacts-match-2026-09-14"
    )


def test_a_facility_with_no_contact_details_still_exports():
    """A row with no way to reach them is still evidence they matched."""
    (row,) = contact_rows([{"facility_id": "f-3", "facility": {"name": "Quiet Lab"}}])
    assert row["facility_name"] == "Quiet Lab"
    assert row["email"] == ""
    assert row["location"] == "Location not specified"
