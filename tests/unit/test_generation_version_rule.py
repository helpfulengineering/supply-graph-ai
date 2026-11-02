"""Generation leaves the version blank rather than invent one (#564)."""

from types import SimpleNamespace

import pytest

from src.core.generation.engine import GenerationEngine
from src.core.generation.layers.base import LayerResult
from src.core.generation.layers.llm import LLMGenerationLayer
from src.core.generation.models import GenerationLayer, LayerConfig
from src.core.generation.platforms.local_git import LocalGitExtractor
from src.core.llm.availability import resolve_llm_availability


async def _generate(root):
    project = await LocalGitExtractor().extract_from_local_path(root)
    config = LayerConfig.for_generate_from_url(no_llm=True).with_llm_availability(
        await resolve_llm_availability(requested=False)
    )
    return await GenerationEngine(config=config).generate_manifest_async(project)


@pytest.mark.asyncio
async def test_a_repository_without_a_version_gets_none(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Board V3\n\nA small board.\n")
    result = await _generate(tmp_path)

    assert result.to_okh_manifest()["version"] == ""
    assert "version" in result.missing_fields
    [warning] = [r for r in result.quality_report.recommendations if "No version" in r]
    assert "V3" in warning


@pytest.mark.asyncio
async def test_a_declared_version_is_used_and_its_source_recorded(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Board\n")
    (tmp_path / "VERSION").write_text("1.4\n")
    result = await _generate(tmp_path)

    assert result.to_okh_manifest()["version"] == "1.4"
    assert result.generated_fields["version"].raw_source == "VERSION"


@pytest.mark.asyncio
async def test_the_llm_cannot_set_the_version() -> None:
    stub = SimpleNamespace(config=SimpleNamespace(default_provider="stub"))
    layer = LLMGenerationLayer(llm_service=stub)
    result = LayerResult(GenerationLayer.LLM)

    await layer._extract_fields_from_manifest(
        {"title": "Frugal IoT", "version": "0.2.4"}, result
    )

    assert "title" in result.fields
    assert "version" not in result.fields
