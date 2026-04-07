"""
RFQ Generation API Route

POST /api/rfq/generate — accepts selected match solutions and returns
Request for Quotation documents (text + JSON artifacts).

This is a demo-phase implementation using a simple template. The template
logic is adapted from demo/rfq_generator.py to work with the current
match response payload shape (facility.location, facility.contact, tree.*).
"""

import re
import uuid
from datetime import datetime, timezone
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


class RFQGenerateRequest(BaseModel):
    okh_id: str
    okh_title: str
    okh_function: Optional[str] = None
    okh_version: Optional[str] = None
    quantity: int = 1
    solutions: List[RFQSolutionInput]
    # Full OKH manifest — included so the recipient has everything they need.
    # When present, a manifest appendix and package-pull instructions are added.
    okh_manifest: Optional[Dict[str, Any]] = None


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

To: {facility_name}
Contact: {facility_contact}
Location: {facility_location}

Subject: Request for Quotation — {design_name}

DESIGN INFORMATION:
  Design Name:  {design_name}
  Design ID:    {okh_id}
  Version:      {version}
  Function:     {function}
  License:      {license}
  Repository:   {repo_url}

MANUFACTURING REQUIREMENTS:
  Processes:    {process_list}
  Materials:    {material_list}
  Quantity:     {quantity} unit(s)
  Quality:      {quality_level}
  Timeline:     To be determined
{parts_section}
Please provide a quotation that includes:
  · Unit price and total price for the quantity specified
  · Lead time and production schedule
  · Payment terms
  · Shipping options and estimated costs
  · Any capability constraints or substitution notes

DESIGN PACKAGE:
  The full OKH manifest for this design is attached to this RFQ as a JSON
  document. To obtain the complete design package (CAD files, documentation,
  source files), use the OHM API:

    POST /v1/api/package/build/{okh_id}

  Or download a pre-built package if available:

    GET  /v1/api/package/build/{okh_id}  (trigger build)
    GET  /v1/api/package/<name>/<version>/download

  The full manifest is included in the JSON export of this RFQ.

{contact_info}
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


def _extract_contact(facility: Dict[str, Any]) -> str:
    contact = facility.get("contact", {})
    if not contact:
        return "Contact information not available"
    lines: List[str] = []
    if contact.get("contact_person"):
        lines.append(f"Contact: {contact['contact_person']}")
    if contact.get("name"):
        lines.append(f"Organisation: {contact['name']}")
    if contact.get("website"):
        lines.append(f"Website: {contact['website']}")
    nested = contact.get("contact", {})
    if isinstance(nested, dict):
        if nested.get("landline"):
            lines.append(f"Phone: {nested['landline']}")
        if nested.get("mobile"):
            lines.append(f"Mobile: {nested['mobile']}")
    return "\n".join(lines) if lines else "Contact information not available"


def _extract_processes(tree: Dict[str, Any]) -> str:
    caps = tree.get("capabilities_used", [])
    names: List[str] = []
    for cap in caps:
        if isinstance(cap, str) and "wikipedia.org/wiki/" in cap:
            names.append(cap.split("/wiki/")[-1].replace("_", " ").title())
        elif isinstance(cap, str):
            names.append(cap)
    return ", ".join(names) if names else "See design requirements"


def _extract_materials(tree: Dict[str, Any]) -> str:
    mats = tree.get("materials_required", [])
    names: List[str] = []
    for mat in mats:
        if isinstance(mat, str) and "MaterialSpec" in mat:
            name_m = re.search(r"name='([^']+)'", mat)
            qty_m = re.search(r"quantity=([^,)]+)", mat)
            unit_m = re.search(r"unit='([^']+)'", mat)
            name = name_m.group(1) if name_m else "Unknown"
            qty = qty_m.group(1) if qty_m else None
            unit = unit_m.group(1) if unit_m else ""
            if qty and qty not in ("None", "N/A"):
                names.append(f"{name} ({qty} {unit})")
            else:
                names.append(name)
        elif isinstance(mat, dict):
            name = mat.get("name", mat.get("material_id", "Unknown"))
            qty = mat.get("quantity")
            unit = mat.get("unit", "")
            names.append(f"{name} ({qty} {unit})" if qty else name)
        else:
            names.append(str(mat))
    return ", ".join(names) if names else "See design specifications"


def _extract_manifest_extras(manifest: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Pull additional fields from the full OKH manifest when available."""
    if not manifest:
        return {"license": "—", "repo_url": "—", "parts_section": ""}

    license_info = manifest.get("license", {})
    if isinstance(license_info, dict):
        hw = license_info.get("hardware") or license_info.get("documentation") or "—"
    else:
        hw = str(license_info) if license_info else "—"

    repo_url = manifest.get("repo") or manifest.get("documentation_home") or "—"

    # Build parts list if present
    parts = manifest.get("parts") or []
    if parts:
        part_lines = []
        for p in parts[:10]:
            if isinstance(p, dict):
                name = p.get("name") or p.get("id") or "Part"
                qty = p.get("quantity", "")
                mat = p.get("material") or ""
                line = f"    - {name}"
                if qty:
                    line += f" ×{qty}"
                if mat:
                    line += f" [{mat}]"
                part_lines.append(line)
        if len(parts) > 10:
            part_lines.append(f"    … and {len(parts) - 10} more parts")
        parts_section = "Parts:\n" + "\n".join(part_lines) + "\n"
    else:
        parts_section = ""

    return {"license": hw, "repo_url": repo_url, "parts_section": parts_section}


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
    extras = _extract_manifest_extras(okh_manifest)
    return _TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d"),
        rfq_number=_rfq_number(),
        facility_name=solution.facility_name,
        facility_contact=_extract_contact(solution.facility),
        facility_location=_extract_location(solution.facility),
        design_name=okh_title,
        okh_id=okh_id,
        version=okh_version or "—",
        function=okh_function or "See design documentation",
        license=extras["license"],
        repo_url=extras["repo_url"],
        parts_section=extras["parts_section"],
        process_list=_extract_processes(solution.tree),
        material_list=_extract_materials(solution.tree),
        quantity=quantity,
        quality_level="professional",
        contact_info="Thank you for your consideration.",
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=RFQGenerateResponse)
async def generate_rfq(request: RFQGenerateRequest) -> RFQGenerateResponse:
    """
    Generate RFQ documents for selected match solutions.

    Accepts a subset of match results (as returned by POST /api/match) plus
    OKH design metadata. Returns one RFQ document per selected solution.
    """
    logger.info(
        f"Generating RFQs for okh_id={request.okh_id} "
        f"({len(request.solutions)} solution(s), qty={request.quantity})"
    )

    rfqs: List[Dict[str, Any]] = []
    for sol in request.solutions:
        rfq_num = _rfq_number()
        text = _render_rfq(
            solution=sol,
            okh_title=request.okh_title,
            okh_id=request.okh_id,
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
                okh_manifest=request.okh_manifest,
            ).model_dump()
        )

    return RFQGenerateResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={
            "rfqs": rfqs,
            "total_rfqs": len(rfqs),
            "okh_id": request.okh_id,
            "okh_title": request.okh_title,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
