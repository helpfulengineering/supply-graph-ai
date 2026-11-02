"""The generation sidecar, as stored beside a manifest (#566).

This is how a run produced a design. It is not authorship provenance and it is
not part of the manifest: ``manifest_content_hash`` covers the whole manifest
dict, so this record lives in its own object, keyed by the manifest id.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class GenerationProvenanceRecord(BaseModel):
    """One run's account of how a manifest was produced.

    ``extra`` is allowed because a record is a sidecar the generator already
    built. Dropping a key the model does not name would make the saved copy
    smaller than the file the same run offers for download.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # `schema` is the on-the-wire name. The attribute cannot be called that:
    # it would shadow BaseModel.schema.
    schema_version: str = Field(alias="schema")
    generated_at: Optional[str] = None
    source_url: Optional[str] = None
    stages: list[dict[str, Any]] = Field(default_factory=list)
    fields: dict[str, dict[str, Any]] = Field(default_factory=dict)
