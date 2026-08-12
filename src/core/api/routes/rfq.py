"""
RFQ Generation API Route

POST /api/rfq/generate — accepts selected match solutions and returns
Request for Quotation documents (text + JSON artifacts).

This is a demo-phase implementation using a simple template. The template
logic is adapted from demo/rfq_generator.py to work with the current
match response payload shape (facility.location, facility.contact, tree.*).
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

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
  Platform:     Open Hardware Matching (OHM)
  Design ID:    {okh_id}

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
  The complete design package (CAD files, Gerber/fabrication outputs,
  assembly drawings, and documentation) can be obtained via the OHM API:

    Trigger build:  POST /v1/api/package/build/{okh_id}
    Download:       GET  /v1/api/package/{okh_id}/download

  The full OKH manifest is included in the JSON export of this RFQ.

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
    loc = facility.get("location", {})
    parts = [
        loc.get("city") or "",
        loc.get("country") or "",
    ]
    result = ", ".join(p for p in parts if p)
    return result or "Location not specified"


def _extract_contact_block(facility: Dict[str, Any]) -> str:
    """Return a formatted contact block (indented, trailing newline) or empty string."""
    contact = facility.get("contact", {})
    if not contact:
        return ""
    lines: List[str] = []
    if contact.get("contact_person"):
        lines.append(f"  Contact:      {contact['contact_person']}")
    if contact.get("name"):
        lines.append(f"  Organisation: {contact['name']}")
    if contact.get("website"):
        lines.append(f"  Website:      {contact['website']}")
    nested = contact.get("contact", {})
    if isinstance(nested, dict):
        if nested.get("landline"):
            lines.append(f"  Phone:        {nested['landline']}")
        if nested.get("mobile"):
            lines.append(f"  Mobile:       {nested['mobile']}")
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


def _render_rfq(
    *,
    solution: RFQSolutionInput,
    okh_title: str,
    okh_id: str,
    okh_function: Optional[str],
    okh_version: Optional[str],
    quantity: int,
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
  Platform:     Open Hardware Matching (OHM)
  Recipe ID:    {recipe_id}

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
    )


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

    rfqs: List[Dict[str, Any]] = []
    for sol in request.solutions:
        rfq_num = _rfq_number()
        if is_cooking:
            text = _render_cooking_rfq(
                solution=sol,
                recipe_title=request.recipe_title or "Unknown recipe",
                recipe_id=request.recipe_id or "unknown",
                quantity=request.quantity,
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
