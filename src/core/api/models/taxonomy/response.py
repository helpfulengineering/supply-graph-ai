"""Response models for the taxonomy routes.

Derived from the payloads the routes already returned, captured in
``tests/api/golden/`` before these models existed — not from reading the route
bodies. ``response_model`` filters undeclared fields, so a model written from
the code rather than from the wire can silently delete something a client
reads. See ``docs/architecture/api-response-contracts.md``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ..base import SuccessResponse


class ProcessDefinition(BaseModel):
    """One canonical process, with its aliases and place in the tree."""

    canonical_id: str
    display_name: str
    tsdc_code: Optional[str] = None
    parent: Optional[str] = None
    aliases: List[str]
    children: List[str]
    wikidata_iri: Optional[str] = None


class TaxonomyIndexData(BaseModel):
    total: int
    #: Absolute path to the YAML the taxonomy was loaded from, or "built-in".
    source: str
    processes: List[ProcessDefinition]


class TaxonomyIndexResponse(SuccessResponse):
    data: TaxonomyIndexData


class TaxonomyReloadData(BaseModel):
    """What the reload changed. Atomic: on failure the route raises instead."""

    added: List[str]
    removed: List[str]
    total: int
    source: str
    version: Optional[str] = None


class TaxonomyReloadResponse(SuccessResponse):
    data: TaxonomyReloadData


class TaxonomyValidationData(BaseModel):
    valid: bool
    total_processes: int
    errors: List[str]
    source: str


class TaxonomyValidationResponse(SuccessResponse):
    data: TaxonomyValidationData
