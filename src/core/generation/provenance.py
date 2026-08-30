"""The record of how a generated manifest was produced.

A *sidecar*, never part of the manifest. ``manifest_content_hash`` is taken over
the whole manifest dict with no field exclusions, so provenance embedded in it
would change the design's content address — the value that pins a package, dedups
a collection, and dedups the federation catalogue. The same design generated
twice would become two different designs.

Namespacing the keys and excluding them from the hash is not an escape either:
an ``ohm_``-prefixed key is already inside the hash today, so changing the hash
function would retroactively invalidate every existing pin and catalogue entry.

This mirrors a call already made for record provenance, which lives in its own
store for the same reason (``models/provenance.py``, per
``notes/federated-identity-adr.md`` §4.3).

The pipeline already computes all of this and used to discard it: ``FieldGeneration``
carries the layer, method and source of every field, and ``to_okh_manifest``
exported only a bare confidence float. Nothing here is new instrumentation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import FieldGeneration, ManifestGeneration

SCHEMA = "ohm-generation-provenance/v1"


def _field_record(field_gen: FieldGeneration) -> Dict[str, Any]:
    """Layer, method, confidence and source for one generated field.

    ``raw_source`` is a short label — ``"metadata.name"``, ``"README.md"``,
    ``"no_version_found"`` — not an excerpt of source text. It ships whole
    because it is already small. File and line spans would mean threading
    offsets through every extractor in all four layers, which is a project of
    its own rather than a field (deferred; see #370's follow-up).
    """
    return {
        "layer": field_gen.source_layer.value,
        "method": field_gen.generation_method,
        "confidence": round(float(field_gen.confidence), 3),
        "source": field_gen.raw_source,
    }


def build_provenance(
    result: ManifestGeneration,
    *,
    source_url: Optional[str] = None,
    stages: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build the sidecar for a completed generation.

    Always produced, never behind a flag: the one run worth explaining is
    otherwise the run that recorded nothing. It costs a dict comprehension over
    fields the pipeline already computed.

    ``stages`` defaults to the timeline the engine collected. An async run can
    pass the job event log instead, which carries the same shape.
    """
    fields = {
        name: _field_record(field_gen)
        for name, field_gen in sorted(result.generated_fields.items())
    }
    timeline = (
        stages
        if stages is not None
        else list(getattr(result, "stage_events", []) or [])
    )
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "stages": timeline,
        "fields": fields,
    }
