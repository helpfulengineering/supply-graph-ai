"""Turn match results into a contact list a coordinator can act on (#498).

The product of a match is an answer to "who can build this", and the useful
thing to do with that answer is **leave OHM with it** — phone people, email
them, put them in a spreadsheet. That is what this produces.

Deliberately a pure formatter: solutions in, bytes out, no storage access and
no lookups. Two reasons.

*Matched facilities cannot be re-fetched.* A match may return Maps-of-Making
rows, whose ids are synthetic stubs (``uuid5(NAMESPACE_URL, mom_iri)``), so
``OKWService.get`` cannot find them. Looking facilities up server-side would
silently drop exactly the wider-network facilities a coordinator most needs.

*An export is a snapshot.* It reflects the match that produced it, not the
world as of now, which is why the timestamp rides in the header and the
filename. A list that silently refreshed itself would be a different and more
dangerous object — see #498 on why stored solutions were removed rather than
kept and warned about.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

#: Column order. Contact routes first, because the point is to make contact;
#: the match quality is context for choosing whom to call first.
COLUMNS: tuple[str, ...] = (
    "facility_name",
    "location",
    "contact_person",
    "organisation",
    "email",
    "phone",
    "mobile",
    "whatsapp",
    "website",
    "mailing_list",
    "matched_processes",
    "confidence",
    "facility_id",
)


def facility_location(facility: Dict[str, Any]) -> str:
    """City and country, or an explicit absence."""
    loc = facility.get("location") or {}
    parts = [loc.get("city") or "", loc.get("country") or ""]
    return ", ".join(p for p in parts if p) or "Location not specified"


def facility_contact(facility: Dict[str, Any]) -> Dict[str, str]:
    """The reachable-by fields, flattened.

    OKW nests these two deep: ``facility.contact`` is an **Agent** (person or
    organisation) and ``agent.contact`` is a **Contact** (the actual channels).
    Navigating that in more than one place is how the RFQ template came to omit
    ``email``, which is the field a coordinator would reach for first.
    """
    agent = facility.get("contact") or {}
    if not isinstance(agent, dict):
        return {}
    channels = agent.get("contact") or {}
    if not isinstance(channels, dict):
        channels = {}
    found = {
        "contact_person": agent.get("contact_person") or "",
        "organisation": agent.get("name") or "",
        "website": agent.get("website") or "",
        "mailing_list": agent.get("mailing_list") or "",
        "email": channels.get("email") or "",
        "phone": channels.get("landline") or "",
        "mobile": channels.get("mobile") or "",
        "whatsapp": channels.get("whatsapp") or "",
    }
    return {k: str(v) for k, v in found.items() if v}


def _matched_processes(solution: Dict[str, Any]) -> str:
    tree = solution.get("tree") or {}
    if not isinstance(tree, dict):
        return ""
    used = tree.get("capabilities_used") or []
    if not isinstance(used, list):
        return ""
    return "; ".join(str(c) for c in used if c)


def contact_rows(solutions: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """One row per matched facility, in the order given.

    Order is the caller's, not re-sorted here: the results view ranks by match
    quality and the export should agree with what was on screen.
    """
    rows: List[Dict[str, str]] = []
    for solution in solutions:
        facility = solution.get("facility") or {}
        if not isinstance(facility, dict):
            facility = {}
        row = {column: "" for column in COLUMNS}
        row.update(facility_contact(facility))
        row["facility_name"] = str(
            solution.get("facility_name") or facility.get("name") or ""
        )
        row["location"] = facility_location(facility)
        row["matched_processes"] = _matched_processes(solution)
        confidence = solution.get("confidence")
        row["confidence"] = "" if confidence is None else f"{float(confidence):.2f}"
        row["facility_id"] = str(solution.get("facility_id") or "")
        rows.append(row)
    return rows


def _provenance(design: Optional[str], matched_at: Optional[str]) -> Dict[str, str]:
    return {
        "design": design or "unspecified",
        "matched_at": matched_at or datetime.now(timezone.utc).isoformat(),
        "source": "Open Hardware Manager",
    }


def to_csv(
    rows: Sequence[Dict[str, str]],
    design: Optional[str] = None,
    matched_at: Optional[str] = None,
) -> str:
    """CSV, with provenance as comment lines above the header.

    Comment lines rather than extra columns: a spreadsheet shows them once at
    the top instead of repeating the design on every row, and they survive being
    forwarded. The cost is that a strict parser must skip lines starting with
    ``#`` — which is why the JSON form exists for tooling.
    """
    meta = _provenance(design, matched_at)
    out = io.StringIO()
    out.write(f"# Open Hardware Manager — facilities matched to {meta['design']}\n")
    out.write(f"# Matched at {meta['matched_at']}\n")
    out.write("# This is a snapshot. Facilities change; re-run the match to refresh.\n")
    writer = csv.DictWriter(out, fieldnames=list(COLUMNS), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return out.getvalue()


def to_json(
    rows: Sequence[Dict[str, str]],
    design: Optional[str] = None,
    matched_at: Optional[str] = None,
) -> str:
    """JSON, with the same provenance as an object rather than comments."""
    return json.dumps(
        {**_provenance(design, matched_at), "contacts": list(rows)},
        indent=2,
        ensure_ascii=False,
    )


def export_filename(design: Optional[str], fmt: str, when: Optional[str] = None) -> str:
    """``contacts-<design>-<date>.<fmt>`` — the date is part of the artifact.

    A coordinator comparing two exports to see which spaces went offline is
    diffing two files in a directory, so the date has to be in the name.
    """
    stamp = (when or datetime.now(timezone.utc).isoformat())[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", (design or "match").lower()).strip("-")
    return f"contacts-{slug or 'match'}-{stamp}.{fmt}"
