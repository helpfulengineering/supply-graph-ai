"""Acceptance: every generation problem #561's reporter hit, replayed offline.

The reporter generated a manifest from their electronics repository and listed
what came out wrong. Each test below is one of those problems, written as the
outcome they should have seen, and run against a stand-in for their repository
(``tests/data/issue_561``) with no LLM and no network.

Each is a strict expected failure naming the sub-issue that fixes it. When the
fix lands the test passes, strict mode fails the run, and the fix PR deletes
the marker. Nothing here can go quietly stale.
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from tests.data.issue_561 import stand_in
from tests.record_fixtures import okh_manifest_dict

pytestmark = pytest.mark.integration


def _open(issue: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{issue}: {why}")


@pytest_asyncio.fixture
async def generated(tmp_path):
    """The manifest and quality report, as Generate produced them for #561."""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import LayerConfig
    from src.core.generation.platforms.local_git import LocalGitExtractor
    from src.core.llm.availability import resolve_llm_availability

    project = await LocalGitExtractor().extract_from_local_path(
        stand_in.build(tmp_path)
    )
    config = LayerConfig.for_generate_from_url(no_llm=True).with_llm_availability(
        await resolve_llm_availability(requested=False)
    )
    result = await GenerationEngine(config=config).generate_manifest_async(
        project, include_file_metadata=True
    )
    return result.to_okh_manifest(), result.quality_report


def _files(manifest):
    for key in ("design_files", "manufacturing_files", "making_instructions"):
        yield from manifest.get(key) or []


@pytest.mark.asyncio
async def test_the_schematic_is_recognised_as_the_schematic(generated):
    """'This is pretty obviously the schematic.'"""
    manifest, _ = generated
    [schematic] = [f for f in _files(manifest) if f["path"] == "SCHEMATIC.pdf"]
    metadata = schematic.get("metadata") or {}
    assert "defaulting" not in str(metadata.get("reason", ""))
    assert metadata.get("confidence", 0) > 0.3


@pytest.mark.asyncio
async def test_a_pcb_repository_has_no_sheet_metal_process(generated):
    """'It decided we need "Sheet metal forming". No idea why.'"""
    manifest, _ = generated
    processes = manifest["manufacturing_processes"]
    assert "PCB Fabrication" in processes
    assert "Sheet Metal Forming" not in processes
    requirements = manifest["manufacturing_specs"]["process_requirements"]
    assert "Sheet Metal Forming" not in {r["process_name"] for r in requirements}


@pytest.mark.asyncio
@_open("#564", "the version is invented, not read from the design")
async def test_the_version_is_the_one_the_design_declares(generated):
    """'It invented a version number of 0.2.4 ... its at 0.2.'

    The repository has no release, tag or version file; the KiCad schematic's
    title block declares the revision.
    """
    manifest, _ = generated
    assert manifest.get("version") == "0.2"


@pytest.mark.asyncio
@_open("#564", "BOM files are found but not linked")
async def test_the_bom_links_the_repositorys_bom_file(generated):
    """'It doesn't actually have the filename or link.'"""
    manifest, _ = generated
    assert manifest["bom"]["external_file"] in (
        "BOM.csv",
        "fabrication/BOM_JLCPCB.csv",
    )


@pytest.mark.asyncio
@_open("#564", "BOM rows are not read into components")
async def test_the_bom_lists_the_components(generated):
    """'... or the components.'"""
    manifest, _ = generated
    names = str(manifest["bom"])
    assert manifest["bom"]["summary"]["total_components"] >= len(stand_in.BOM_ROWS)
    assert all(row in names for row in stand_in.BOM_ROWS)


def _register(client):
    resp = client.post("/api/identity/register", json={"display_name": "Mitra"})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['key']['token']}"}


def test_a_removed_process_is_gone_from_every_place_it_was_stored(client):
    """'The YAML also included "Sheet metal forming" when I had removed that.'

    The process list is what a person edits; the derived copies must follow it
    on write, whichever client wrote it.
    """
    headers = _register(client)
    record_id = str(uuid4())
    content = {
        **okh_manifest_dict(),
        "id": record_id,
        "manufacturing_processes": ["PCB Fabrication"],
        "manufacturing_specs": {
            "process_requirements": [
                {"process_name": "PCB Fabrication"},
                {"process_name": "Sheet Metal Forming"},
            ]
        },
        "tsdc": ["PCB", "SHEET"],
    }
    created = client.post("/api/okh/create", json={"content": content}, headers=headers)
    assert created.status_code == 201, created.text
    try:
        stored = client.get(f"/api/okh/{record_id}", headers=headers).json()
        assert "Sheet Metal Forming" not in str(stored)
        assert "SHEET" not in (stored.get("tsdc") or [])
    finally:
        client.delete(f"/api/okh/{record_id}", headers=headers)
