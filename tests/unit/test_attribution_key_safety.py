"""Guards that OHM's namespaced attribution key is safe (Slice 1).

Attribution is persisted under ``ohm_created_by`` rather than ``created_by`` so it
never collides with the OKW schema's own ``created_by`` (an Agent). These tests
prove that an ``ohm_created_by`` key round-trips through ``from_dict`` without
breaking parsing or overwriting schema fields.
"""

from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility
from tests.record_fixtures import okh_manifest_dict, okw_facility_dict


def test_okw_attribution_key_does_not_clobber_agent_created_by():
    attribution = "00000000-0000-0000-0000-000000000001"
    data = okw_facility_dict()
    data["ohm_created_by"] = attribution

    facility = ManufacturingFacility.from_dict(data)

    # Parses fine, and the attribution string never leaks into the OKW schema's
    # ``created_by`` (an Agent) — the two keys are distinct by design.
    assert facility is not None
    assert getattr(facility, "created_by", None) != attribution


def test_okh_ignores_namespaced_attribution_key():
    data = okh_manifest_dict()
    data["ohm_created_by"] = "00000000-0000-0000-0000-000000000001"

    manifest = OKHManifest.from_dict(data)
    assert manifest.title  # parses fine; unknown key ignored
