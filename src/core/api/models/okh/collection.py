"""Collection import / diff response models (#373).

Derived from payloads captured in ``tests/api/golden/okh_diff_collection.json``
and ``okh_import_collection.json`` before these models existed — and captured
with **non-empty** lists, because an empty one freezes the envelope and says
nothing about the item, which is what a client actually reads.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CollectionEntry(BaseModel):
    """One manifest as a collection archive describes it.

    Deliberately identity-only: a collection diff answers "which records differ",
    and the content lives in the archive. Same shape in every bucket below.
    """

    content_hash: str
    title: Optional[str] = None
    version: Optional[str] = None


class CollectionDiffResponse(BaseModel):
    """``POST /api/okh/diff-collection`` — what each side has that the other does not."""

    status: str
    only_in_archive: List[CollectionEntry] = Field(default_factory=list)
    only_local: List[CollectionEntry] = Field(default_factory=list)
    request_id: Optional[str] = None


class CollectionImportResponse(BaseModel):
    """``POST /api/okh/import-collection`` — how each manifest was classified.

    ``dry_run`` distinguishes a report from a write, and ``imported`` counts
    what actually landed, which is zero on a dry run.
    """

    status: str
    dry_run: bool
    imported: int
    new: List[CollectionEntry] = Field(default_factory=list)
    duplicate: List[CollectionEntry] = Field(default_factory=list)
    conflict: List[CollectionEntry] = Field(default_factory=list)
    request_id: Optional[str] = None


class OKHTemplateResponse(BaseModel):
    """``GET /api/okh/template`` — a blank manifest to fill in.

    ``template`` stays free-form on purpose. It is an instance of the OKH
    manifest schema, which is already modelled in ``src/core/models/okh.py``;
    restating its shape here would be a second copy that drifts from the first,
    and the copy that filters is the one a client sees. The envelope around it
    is what this route owns, so the envelope is what it declares.
    """

    success: bool
    model_name: str
    template: dict
