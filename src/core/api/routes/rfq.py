"""
RFQ Generation API Route

POST /api/rfq/generate — accepts selected match solutions and returns
Request for Quotation documents (text + JSON artifacts).

This is a demo-phase implementation using a simple template. The template
logic is adapted from demo/rfq_generator.py to work with the current
match response payload shape (facility.location, facility.contact, tree.*).
"""

import io
import re
import uuid
import zipfile
from pathlib import Path
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from src.core.api.dependencies import require_write
from src.core.federation.package_pointer import package_dir_to_archive_bytes
from src.core.services.contact_export import facility_contact, facility_location
from src.core.services.package_service import PackageService
from src.core.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/rfq", tags=["rfq"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RFQSolutionInput(BaseModel):
    """A single match solution, as returned by POST /api/match."""

    facility_id: str
    facility_name: str
    confidence: float
    score: float
    rank: int
    # tree contains capabilities_used, materials_required, etc.
    tree: Dict[str, Any]
    # full facility object for location / contact
    facility: Dict[str, Any]
    # Human-readable match explanation, when the match response included one
    # (see MatchExplanation.to_human_readable). Used for the cooking-domain
    # RFQ's match summary section.
    explanation_human: Optional[str] = None


class RFQGenerateRequest(BaseModel):
    # "manufacturing" (default, OKH design + facility) or "cooking" (recipe +
    # kitchen). Selects which of the okh_* / recipe_* fields below are used.
    domain: str = "manufacturing"
    okh_id: Optional[str] = None
    okh_title: Optional[str] = None
    okh_function: Optional[str] = None
    okh_version: Optional[str] = None
    # Full OKH manifest — included so the recipient has everything they need.
    # When present, a manifest appendix and package-pull instructions are added.
    okh_manifest: Optional[Dict[str, Any]] = None
    recipe_id: Optional[str] = None
    recipe_title: Optional[str] = None
    # Full recipe (ingredients/instructions/equipment) — embedded in the
    # generated document so the kitchen has everything they need.
    recipe: Optional[Dict[str, Any]] = None
    quantity: int = 1
    solutions: List[RFQSolutionInput]

    # Who is asking. Optional, all of it: the RFQ is sent by the requester over
    # their own email, so the recipient already has a reply-to even when the
    # document carries none. Naming them here makes the document answerable on
    # its own — forwarded, printed, or read weeks later — which is what an RFQ
    # that leaves OHM has to survive.
    requester_name: Optional[str] = None
    requester_organisation: Optional[str] = None
    requester_email: Optional[str] = None
    response_due: Optional[str] = None
    # Filename of the design package sent alongside. The RFQ cannot derive it:
    # packages are named {org}-{project}-{version}, and the RFQ knows only the
    # design. Naming a file that is not attached is worse than naming none, so
    # absent means the section says what to attach instead.
    attachment_name: Optional[str] = None


class RFQDocument(BaseModel):
    rfq_number: str
    facility_name: str
    facility_id: str
    confidence: float
    rank: int
    quantity: int
    text: str
    # Included when the caller provided the full OKH manifest
    okh_manifest: Optional[Dict[str, Any]] = None


class RFQGenerateResponse(BaseModel):
    status: str = "success"
    message: str = "RFQ documents generated successfully"
    timestamp: str
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

_TEMPLATE = """\
REQUEST FOR QUOTATION (RFQ)

Date: {date}
RFQ Number: {rfq_number}
Valid Until: {valid_until}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ISSUED TO:
  Facility:     {facility_name}
  Location:     {facility_location}
{facility_contact_block}
ISSUED BY:
{requester_block}  Design ID:    {okh_id}
  Prepared with Open Hardware Manager

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUBJECT:  Manufacturing Quotation Request — {design_name} ({version})

1. DESIGN OVERVIEW
  Name:         {design_name}
  Version:      {version}
  Function:     {function}
  License:      {license}
  Repository:   {repo_url}
{description_block}
2. SCOPE OF WORK
  Quantity:     {quantity} unit(s)
  Processes:    {process_list}
{dimensions_block}{quality_block}{materials_block}
3. MATCHED CAPABILITIES
{matched_capabilities_block}
4. DESIGN DATA PACKAGE
{attachment_block}
5. QUOTATION REQUIREMENTS
  Please provide a response that includes all applicable items:
  · Unit price and total price for the quantity above
  · NRE / tooling / setup charges (if any)
  · Lead time from PO to first-article and production delivery
  · Production schedule for the stated quantity
  · Payment terms and accepted currencies
  · Shipping options, Incoterms, and estimated freight cost
  · Quality documentation: inspection plan, first-article report (FAI)
  · Any capability constraints, substitutions, or design-for-manufacture notes
  · Minimum order quantity (MOQ) if applicable
{response_to_block}
6. TERMS & CONDITIONS
  · This RFQ does not constitute a purchase order or commitment to buy.
  · All submitted pricing and technical information will be treated as
    confidential unless explicitly marked otherwise by the vendor.
  · The design is released under the license stated above; any manufacturing
    engagement is subject to compliance with those license terms.

Thank you for your consideration.
"""


def _rfq_number() -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    short = str(uuid.uuid4())[:8]
    return f"RFQ-{date_str}-{short}"


def _extract_location(facility: Dict[str, Any]) -> str:
    """City and country, shared with the contact export (#501)."""
    return facility_location(facility)


#: Label for each contact field, in the order an RFQ should offer them.
#:
#: Email first among the channels: this document exists to be sent to the
#: facility, and email is how most people would answer it. It was missing
#: entirely until #501 — the block read ``landline`` and ``mobile`` and
#: skipped ``email``, ``whatsapp`` and ``mailing_list``, so the most useful
#: way to reach someone was absent from a document addressed to them.
_CONTACT_LABELS: tuple[tuple[str, str], ...] = (
    ("contact_person", "Contact"),
    ("organisation", "Organisation"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("mobile", "Mobile"),
    ("whatsapp", "WhatsApp"),
    ("website", "Website"),
    ("mailing_list", "Mailing list"),
)


def _extract_contact_block(facility: Dict[str, Any]) -> str:
    """Return a formatted contact block (indented, trailing newline), or empty.

    Extraction is :func:`facility_contact`, shared with the contact export, so
    OKW's two-deep nesting — ``facility.contact`` is an Agent and
    ``agent.contact`` is a Contact — is navigated in exactly one place.
    Navigating it here as well is how this block came to omit ``email`` while
    the export carried it.
    """
    found = facility_contact(facility)
    lines = [
        f"  {label + ':':<14}{found[key]}"
        for key, label in _CONTACT_LABELS
        if found.get(key)
    ]
    return ("\n".join(lines) + "\n") if lines else ""


def _cap_label(cap: str) -> str:
    """Convert a capability URI or raw string to a readable label."""
    if "wikipedia.org/wiki/" in cap:
        return cap.split("/wiki/")[-1].replace("_", " ").title()
    return cap


def _extract_processes_from_manifest(manifest: Optional[Dict[str, Any]]) -> str:
    """Extract required manufacturing processes from the OKH manifest."""
    if not manifest:
        return "See design documentation"
    procs = manifest.get("manufacturing_processes") or []
    if not procs:
        specs = manifest.get("manufacturing_specs") or {}
        procs = [
            r.get("process_name")
            for r in specs.get("process_requirements", [])
            if r.get("process_name")
        ]
    if not procs:
        return "See design documentation"
    return ", ".join(str(p) for p in procs)


def _extract_matched_capabilities_block(solution: "RFQSolutionInput") -> str:
    """
    Summarise why this facility was selected:
    capabilities matched, confidence, and any unmet requirements.
    """
    tree = solution.tree
    lines: List[str] = []

    caps = tree.get("capabilities_used", [])
    if caps:
        cap_labels = [_cap_label(c) for c in caps if isinstance(c, str)]
        lines.append(f"  Matched processes:  {', '.join(cap_labels) or '—'}")

    lines.append(f"  Match confidence:   {round(solution.confidence * 100)}%")
    lines.append(f"  Match rank:         #{solution.rank}")

    missing = tree.get("missing_capabilities", [])
    if missing:
        missing_labels = [_cap_label(c) for c in missing if isinstance(c, str)]
        lines.append(f"  Unmet requirements: {', '.join(missing_labels)}")
        lines.append(
            "  Note: Please advise whether the unmet requirements above can be"
        )
        lines.append("        accommodated through partnerships or subcontracting.")
    else:
        lines.append("  All required capabilities matched.")

    return "\n".join(lines)


def _extract_manifest_extras(
    manifest: Optional[Dict[str, Any]],
    solution: Optional["RFQSolutionInput"] = None,
) -> Dict[str, str]:
    """
    Extract RFQ-relevant fields from the OKH manifest.

    Returns a dict of pre-formatted text blocks used by _TEMPLATE.
    Does NOT include raw BOM part numbers — those are component procurement
    data and do not belong in a manufacturing RFQ.
    """
    if not manifest:
        return {
            "license": "—",
            "repo_url": "—",
            "description_block": "",
            "dimensions_block": "",
            "quality_block": "",
            "materials_block": "",
            "matched_capabilities_block": "  See match data.",
        }

    # License
    license_info = manifest.get("license", {})
    if isinstance(license_info, dict):
        hw = license_info.get("hardware") or license_info.get("documentation") or "—"
    else:
        hw = str(license_info) if license_info else "—"

    repo_url = manifest.get("repo") or manifest.get("documentation_home") or "—"

    # Optional description block
    desc = manifest.get("description") or manifest.get("intended_use") or ""
    description_block = (f"  Description:  {desc}\n") if desc else ""

    # Manufacturing specs — outer dimensions
    specs = manifest.get("manufacturing_specs") or {}
    dims = specs.get("outer_dimensions")
    if dims and isinstance(dims, dict):
        w = dims.get("width") or dims.get("x")
        h = dims.get("height") or dims.get("y")
        d = dims.get("depth") or dims.get("z") or dims.get("thickness")
        unit = dims.get("unit", "mm")
        parts_dim = [f"{v} {unit}" for v in [w, h, d] if v is not None]
        dimensions_block = (
            f"  Dimensions:   {' × '.join(parts_dim)}\n" if parts_dim else ""
        )
    else:
        dimensions_block = ""

    # Quality standards
    quality_stds = specs.get("quality_standards") or []
    if quality_stds:
        quality_block = f"  Quality:      {', '.join(str(q) for q in quality_stds)}\n"
    else:
        quality_block = "  Quality:      Per standard good manufacturing practice\n"

    # High-level materials (manifest-level, NOT BOM component references)
    materials = manifest.get("materials") or []
    mat_names: List[str] = []
    for m in materials:
        if isinstance(m, dict):
            name = m.get("name") or m.get("material_id") or ""
            if name:
                mat_names.append(name)
        elif isinstance(m, str):
            mat_names.append(m)
    materials_block = (f"  Materials:    {', '.join(mat_names)}\n") if mat_names else ""

    # Matched capabilities block
    if solution is not None:
        matched_capabilities_block = _extract_matched_capabilities_block(solution)
    else:
        matched_capabilities_block = "  See match data."

    return {
        "license": hw,
        "repo_url": repo_url,
        "description_block": description_block,
        "dimensions_block": dimensions_block,
        "quality_block": quality_block,
        "materials_block": materials_block,
        "matched_capabilities_block": matched_capabilities_block,
    }


# ---------------------------------------------------------------------------
# Blocks that make the document survive leaving OHM
# ---------------------------------------------------------------------------


def _requester_block(request: "RFQGenerateRequest") -> str:
    """Who is asking, when they said so.

    An RFQ is answered by a human who may have been forwarded it. Without a
    name the document is a quotation request from nobody; the sender's email
    address is on the message, but not in the thing that gets printed, filed
    or passed to whoever actually prices the job.
    """
    rows = (
        ("Requester", request.requester_name),
        ("Organisation", request.requester_organisation),
        ("Email", request.requester_email),
    )
    lines = [f"  {label + ':':<14}{value}" for label, value in rows if value]
    return ("\n".join(lines) + "\n") if lines else ""


def _attachment_block(request: "RFQGenerateRequest") -> str:
    """What was sent with this, or what to send.

    This used to print two OHM API calls. That assumes the reader can reach the
    instance, which is exactly backwards: an RFQ goes to a workshop that has
    never heard of OHM, over ordinary email. So the design travels as an
    attachment, and this names it.
    """
    contents = (
        "  Contains the OKH manifest, design and fabrication files, assembly\n"
        "  documentation, and the bill of materials, as published under the\n"
        "  license stated above.\n"
    )
    if request.attachment_name:
        return f"  Attached:     {request.attachment_name}\n{contents}"
    return (
        "  The design package is sent alongside this request.\n"
        f"{contents}"
        "  If it did not arrive, reply and it will be sent again.\n"
    )


def _response_to_block(request: "RFQGenerateRequest") -> str:
    """Where the quotation goes, and by when.

    Section 5 asked for a response and never said where to send it. Reply-to
    is the default because that is true whatever else is missing: this arrived
    as an email from the requester.
    """
    lines = []
    if request.response_due:
        lines.append(f"  Please respond by {request.response_due}.")
    if request.requester_email:
        who = request.requester_name or "the requester"
        lines.append(f"  Send your quotation to {who} at {request.requester_email},")
        lines.append("  or simply reply to the message this arrived with.")
    else:
        lines.append("  Please reply to the message this request arrived with.")
    return "\n" + "\n".join(lines) + "\n"


def _render_rfq(
    *,
    solution: RFQSolutionInput,
    okh_title: str,
    okh_id: str,
    okh_function: Optional[str],
    okh_version: Optional[str],
    quantity: int,
    request: "RFQGenerateRequest",
    okh_manifest: Optional[Dict[str, Any]] = None,
) -> str:
    extras = _extract_manifest_extras(okh_manifest, solution)
    now = datetime.now()
    valid_until = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    return _TEMPLATE.format(
        date=now.strftime("%Y-%m-%d"),
        rfq_number=_rfq_number(),
        valid_until=valid_until,
        facility_name=solution.facility_name,
        facility_contact_block=_extract_contact_block(solution.facility),
        facility_location=_extract_location(solution.facility),
        design_name=okh_title,
        okh_id=okh_id,
        version=okh_version or "—",
        function=okh_function or "See design documentation",
        license=extras["license"],
        repo_url=extras["repo_url"],
        description_block=extras["description_block"],
        process_list=_extract_processes_from_manifest(okh_manifest),
        dimensions_block=extras["dimensions_block"],
        quality_block=extras["quality_block"],
        materials_block=extras["materials_block"],
        matched_capabilities_block=extras["matched_capabilities_block"],
        quantity=quantity,
        requester_block=_requester_block(request),
        attachment_block=_attachment_block(request),
        response_to_block=_response_to_block(request),
    )


# ---------------------------------------------------------------------------
# Cooking-domain template (recipe + kitchen)
# ---------------------------------------------------------------------------

_COOKING_TEMPLATE = """\
REQUEST FOR QUOTATION (RFQ)

Date: {date}
RFQ Number: {rfq_number}
Valid Until: {valid_until}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ISSUED TO:
  Kitchen:      {facility_name}
  Location:     {facility_location}
{facility_contact_block}
ISSUED BY:
{requester_block}  Recipe ID:    {recipe_id}
  Prepared with Open Hardware Manager

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUBJECT:  Kitchen Quotation Request — {recipe_name}

1. RECIPE OVERVIEW
  Name:         {recipe_name}
  Ingredients:  {ingredient_list}
  Equipment:    {equipment_list}

2. SCOPE OF WORK
  Quantity:     {quantity} batch(es)

3. MATCH SUMMARY
{match_summary_block}
4. QUOTATION REQUIREMENTS
  Please provide a response that includes all applicable items:
  · Price per batch and total price for the quantity above
  · Lead time from order to delivery or pickup
  · Substitutions available for any missing ingredients or equipment noted above
  · Dietary or allergen considerations
  · Minimum order quantity (MOQ) if applicable
{response_to_block}
5. TERMS & CONDITIONS
  · This RFQ does not constitute a purchase order or commitment to buy.
  · All submitted pricing and details will be treated as confidential unless
    explicitly marked otherwise by the kitchen.

Thank you for your consideration.
"""


def _extract_recipe_lists(recipe: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Format a recipe's ingredients/equipment as comma-separated lists."""
    if not recipe:
        return {
            "ingredient_list": "See recipe details",
            "equipment_list": "See recipe details",
        }
    ingredients = recipe.get("ingredients") or []
    equipment = recipe.get("equipment") or []
    return {
        "ingredient_list": ", ".join(str(i) for i in ingredients) or "None listed",
        "equipment_list": ", ".join(str(e) for e in equipment) or "None listed",
    }


def _extract_cooking_match_summary(solution: "RFQSolutionInput") -> str:
    """Summarise why this kitchen was selected.

    Prefers the human-readable match explanation attached by POST /api/match
    (ingredient/tool coverage), falling back to bare confidence/rank when the
    match request did not ask for an explanation.
    """
    if solution.explanation_human:
        return "\n".join(
            f"  {line}" for line in solution.explanation_human.splitlines()
        )
    return (
        f"  Match confidence: {round(solution.confidence * 100)}%\n"
        f"  Match rank:       #{solution.rank}"
    )


def _render_cooking_rfq(
    *,
    solution: RFQSolutionInput,
    recipe_title: str,
    recipe_id: str,
    quantity: int,
    request: "RFQGenerateRequest",
    recipe: Optional[Dict[str, Any]] = None,
) -> str:
    lists = _extract_recipe_lists(recipe)
    now = datetime.now()
    valid_until = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    return _COOKING_TEMPLATE.format(
        date=now.strftime("%Y-%m-%d"),
        rfq_number=_rfq_number(),
        valid_until=valid_until,
        facility_name=solution.facility_name,
        facility_contact_block=_extract_contact_block(solution.facility),
        facility_location=_extract_location(solution.facility),
        recipe_name=recipe_title,
        recipe_id=recipe_id,
        ingredient_list=lists["ingredient_list"],
        equipment_list=lists["equipment_list"],
        match_summary_block=_extract_cooking_match_summary(solution),
        quantity=quantity,
        requester_block=_requester_block(request),
        response_to_block=_response_to_block(request),
    )


def _render_all(request: "RFQGenerateRequest") -> List[Dict[str, Any]]:
    """Render one RFQ per selected facility.

    Shared by ``/generate`` and ``/bundle`` so the document a caller reads on
    screen is byte-for-byte the one that lands in the zip.
    """
    is_cooking = request.domain == "cooking"
    rfqs: List[Dict[str, Any]] = []
    for sol in request.solutions:
        rfq_num = _rfq_number()
        if is_cooking:
            text = _render_cooking_rfq(
                solution=sol,
                recipe_title=request.recipe_title or "Unknown recipe",
                recipe_id=request.recipe_id or "unknown",
                quantity=request.quantity,
                request=request,
                recipe=request.recipe,
            )
        else:
            text = _render_rfq(
                solution=sol,
                okh_title=request.okh_title or "Unknown design",
                okh_id=request.okh_id or "unknown",
                okh_function=request.okh_function,
                okh_version=request.okh_version,
                quantity=request.quantity,
                request=request,
                okh_manifest=request.okh_manifest,
            )
        rfqs.append(
            RFQDocument(
                rfq_number=rfq_num,
                facility_name=sol.facility_name,
                facility_id=sol.facility_id,
                confidence=sol.confidence,
                rank=sol.rank,
                quantity=request.quantity,
                text=text,
                okh_manifest=None if is_cooking else request.okh_manifest,
            ).model_dump()
        )

    return rfqs


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=RFQGenerateResponse)
async def generate_rfq(request: RFQGenerateRequest) -> RFQGenerateResponse:
    """
    Generate RFQ documents for selected match solutions.

    Accepts a subset of match results (as returned by POST /api/match) plus
    either OKH design metadata (domain="manufacturing", the default) or
    recipe metadata (domain="cooking"). Returns one RFQ document per selected
    solution.
    """
    is_cooking = request.domain == "cooking"
    subject_id = request.recipe_id if is_cooking else request.okh_id
    logger.info(
        f"Generating RFQs for domain={request.domain} subject_id={subject_id} "
        f"({len(request.solutions)} solution(s), qty={request.quantity})"
    )

    rfqs = _render_all(request)

    return RFQGenerateResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={
            "rfqs": rfqs,
            "total_rfqs": len(rfqs),
            "okh_id": request.okh_id,
            "okh_title": request.okh_title,
            "recipe_id": request.recipe_id,
            "recipe_title": request.recipe_title,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def _resolve_design_package(okh_id: Optional[str]) -> Optional[Tuple[bytes, str]]:
    """The design package for this design, as (bytes, filename), or None.

    Reuses a built package when one exists and builds when it does not, because
    building downloads every asset the manifest declares and a coordinator
    assembling an email should not pay that twice.

    Returns ``None`` rather than raising for every failure mode — no id, not a
    UUID, no manifest, a build that could not fetch an asset. A bundle missing
    its attachment is still worth sending: the RFQs are the part that cannot be
    reconstructed by hand, and the document says plainly what should have been
    attached.
    """
    if not okh_id:
        return None
    try:
        manifest_id = UUID(okh_id)
    except (ValueError, AttributeError):
        logger.info(
            "RFQ bundle: %r is not a manifest id; sending without a package", okh_id
        )
        return None

    try:
        service = await PackageService.get_instance()
        built = await service.list_built_packages()
        metadata = next(
            (m for m in built if str(m.okh_manifest_id) == str(manifest_id)), None
        )
        if metadata is None:
            metadata = await service.build_package_from_storage(manifest_id)
        return package_dir_to_archive_bytes(Path(metadata.package_path))
    except Exception as exc:  # noqa: BLE001 — the bundle degrades, it does not fail
        logger.warning(
            "RFQ bundle: no design package for %s (%s). Sending the RFQs alone.",
            okh_id,
            exc,
        )
        return None


def _bundle_filename(request: "RFQGenerateRequest") -> str:
    subject = request.okh_title or request.recipe_title or "rfq"
    slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-") or "rfq"
    return f"rfq-{slug}-{datetime.now().strftime('%Y-%m-%d')}.zip"


def _rfq_filename(rfq: Dict[str, Any]) -> str:
    """``<rfq number>-<facility>.txt``.

    The number already carries its own ``RFQ-`` prefix. The facility is in the
    name because whoever sends these has one file per workshop open at once and
    picks by who it is for, not by serial number.
    """
    facility = re.sub(r"[^a-z0-9]+", "-", (rfq["facility_name"] or "").lower()).strip(
        "-"
    )
    return f"{rfq['rfq_number']}-{facility or 'facility'}.txt"


@router.post(
    "/bundle",
    summary="RFQ documents and the design package, as one download",
    description=(
        "Everything needed to send a quotation request by ordinary email: one "
        "RFQ per selected facility, plus the design package they refer to.\n\n"
        "The recipient is a workshop that has never heard of OHM, so nothing in "
        "the documents points back at this instance — the design travels as an "
        "attachment, and each RFQ names it.\n\n"
        "Degrades rather than fails: if the design package cannot be built, the "
        "RFQs are returned on their own and say what should accompany them.\n\n"
        "Requires write permission, unlike /generate, because it may build a "
        "package that does not exist yet — which persists one."
    ),
    responses={200: {"content": {"application/zip": {}}}},
)
async def bundle_rfq(
    request: RFQGenerateRequest,
    _user=Depends(require_write),
) -> Response:
    package = await _resolve_design_package(request.okh_id)

    # Render after resolving, so each RFQ can name the file actually enclosed
    # rather than a filename someone hoped for.
    if package is not None:
        request = request.model_copy(update={"attachment_name": package[1]})
    rfqs = _render_all(request)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for rfq in rfqs:
            archive.writestr(_rfq_filename(rfq), rfq["text"])
        if package is not None:
            archive.writestr(package[1], package[0])

    filename = _bundle_filename(request)
    logger.info(
        "RFQ bundle: %d document(s)%s",
        len(rfqs),
        f" + {package[1]}" if package else " (no design package)",
    )
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
