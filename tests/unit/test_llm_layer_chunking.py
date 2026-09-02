"""The LLM generation layer must not split a payload the model can hold.

Chunked map-reduce issues one sequential request per chunk. A 4,000-token
budget against a 200,000-token context window turned a single OpenFlexure
generation into eight sequential calls and 173 seconds of wall clock.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.core.generation.layers.llm import LLMGenerationLayer
from src.core.generation.models import (
    DocumentInfo,
    FileInfo,
    LayerConfig,
    PlatformType,
    ProjectData,
)
from src.core.llm.models.requests import LLMRequestConfig, LLMRequestType
from src.core.llm.models.responses import (
    LLMResponse,
    LLMResponseMetadata,
    LLMResponseStatus,
)
from src.core.llm.providers.base import LLMProviderType
from src.core.llm.service import LLMService, LLMServiceConfig
from src.core.services.base import ServiceStatus

_MANIFEST_JSON = (
    '{"title": "OpenFlexure Microscope", "version": "7.0.0", '
    '"function": "A 3D printable microscope with a precise mechanical stage.", '
    '"description": "An open-source microscope built around a printed flexure stage."}'
)


class RecordingLLMService(LLMService):
    """A real LLMService with only the provider round-trip replaced.

    Everything above ``generate`` — chunk splitting, the map/reduce workflow,
    schema validation — is the production code path.
    """

    def __init__(self, config: Optional[LLMServiceConfig] = None):
        super().__init__("RecordingLLMService", config)
        self.prompts: List[str] = []

    async def initialize(self) -> None:
        self.status = ServiceStatus.ACTIVE

    async def generate(
        self,
        prompt: str,
        request_type: LLMRequestType = LLMRequestType.GENERATION,
        config: Optional[LLMRequestConfig] = None,
        provider: Optional[LLMProviderType] = None,
    ) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(
            content=_MANIFEST_JSON,
            status=LLMResponseStatus.SUCCESS,
            metadata=LLMResponseMetadata(
                provider="anthropic",
                model="claude-sonnet-4-5-20250929",
                tokens_used=0,
                cost=0.0,
                processing_time=0.0,
            ),
        )


def project_with_files(count: int) -> ProjectData:
    """A repository of *count* files, shaped like a real hardware project."""
    files = [
        FileInfo(
            path=f"models/subassembly_{n:04d}/printed_part_{n:04d}.stl",
            size=2048,
            content="",
            file_type="model",
        )
        for n in range(count)
    ]
    files.append(
        FileInfo(
            path="README.md",
            size=3000,
            content="# OpenFlexure Microscope\n\n" + ("A printed microscope. " * 100),
            file_type="markdown",
        )
    )
    return ProjectData(
        platform=PlatformType.GITLAB,
        url="https://gitlab.com/openflexure/openflexure-microscope",
        metadata={"name": "openflexure-microscope", "description": "A microscope"},
        files=files,
        documentation=[
            DocumentInfo(
                title="README.md",
                path="README.md",
                doc_type="readme",
                content="A printed microscope.",
            )
        ],
        raw_content={},
    )


@pytest.mark.asyncio
async def test_payload_within_context_window_uses_a_single_request():
    """OpenFlexure fits in a Sonnet context window many times over."""
    service = RecordingLLMService()
    layer = LLMGenerationLayer(llm_service=service)

    result = await layer.process(project_with_files(424))

    assert result.errors == []
    assert len(service.prompts) == 1, (
        f"expected one LLM request for a payload the model can hold, "
        f"got {len(service.prompts)}"
    )


def map_stage_prompts(prompts: List[str]) -> List[str]:
    """The map-stage requests, i.e. every request but the final reduce."""
    return [p for p in prompts if "Synthesize the final response" not in p]


@pytest.mark.asyncio
async def test_chunking_splits_repository_data_not_the_instructions():
    """When chunking does trigger, it must split the repo, not the preamble.

    The whole prompt used to go in as one chunkable section, so the first
    chunks held nothing but the role preamble and the Phase 1-5 workflow text
    — full-length generations spent asking the model to build a manifest out
    of instructions it had been handed no repository for.
    """
    service = RecordingLLMService()
    layer = LLMGenerationLayer(
        layer_config=LayerConfig(
            llm_config={"chunked_mode_enabled": True, "chunk_max_tokens": 2000}
        ),
        llm_service=service,
    )

    result = await layer.process(project_with_files(600))

    assert result.errors == []
    mapped = map_stage_prompts(service.prompts)
    assert len(mapped) > 1, "expected the payload to be split across map calls"
    for index, prompt in enumerate(mapped):
        for instruction in (
            "You are an expert OKH (Open Know-How) manifest generator",
            "OKH (Open Know-How) Manifest Schema Reference",
        ):
            assert instruction in prompt, (
                f"map request {index} is missing {instruction!r}; the "
                "instructions were chunked away instead of repeated per chunk"
            )
        assert "printed_part_" in prompt, (
            f"map request {index} carries no repository content \u2014 it is a chunk "
            "of pure boilerplate"
        )


@pytest.mark.asyncio
async def test_file_listing_is_capped_and_says_so():
    """A large repo must not be able to reopen the multi-call path.

    The listing was every path the extractor found, so prompt size scaled with
    the repository and a big enough project chunked again no matter what the
    context window was.
    """
    service = RecordingLLMService()
    layer = LLMGenerationLayer(llm_service=service)

    project = project_with_files(10_000)
    # A path the manifest actually needs, sitting far past any cap.
    project.files.append(
        FileInfo(path="hardware/bom.csv", size=512, content="", file_type="csv")
    )

    result = await layer.process(project)

    assert result.errors == []
    assert len(service.prompts) == 1, "a capped listing must still fit one request"
    prompt = service.prompts[0]
    assert (
        "more files not shown" in prompt
    ), "a truncated listing must say so, or the model reads it as the whole repo"
    assert (
        "hardware/bom.csv" in prompt
    ), "the cap dropped a BOM path the manifest depends on"


@pytest.mark.asyncio
async def test_prompt_size_stops_scaling_with_the_repository():
    """Twenty times the files must not mean twenty times the prompt."""

    async def prompt_for(file_count: int) -> str:
        service = RecordingLLMService()
        layer = LLMGenerationLayer(llm_service=service)
        result = await layer.process(project_with_files(file_count))
        assert result.errors == []
        return service.prompts[0]

    small = await prompt_for(500)
    large = await prompt_for(10_000)

    assert len(large) < len(small) * 1.2, (
        f"prompt grew from {len(small):,} to {len(large):,} chars for 20x the "
        "files; the listing still scales with the repository"
    )


@pytest.mark.asyncio
async def test_small_context_model_still_chunks():
    """The budget follows the model, so a small window is not overflowed.

    Guards the failure mode of simply raising the old constant: a local model
    with an 8k window would then be handed a prompt it cannot hold.
    """

    class SmallContextService(RecordingLLMService):
        def context_window_tokens(self) -> int:
            return 8192

    service = SmallContextService()
    layer = LLMGenerationLayer(llm_service=service)

    result = await layer.process(project_with_files(424))

    assert result.errors == []
    assert (
        len(map_stage_prompts(service.prompts)) > 1
    ), "a prompt larger than the model's context window must be chunked"
