"""DomainRegistry's validator slot: auto-wrap removed (#509).

`register_domain()` used to unconditionally wrap any registered async
`Validator` (`validation/engine.py`) in `ValidatorAdapter`. That adapter's
sync `.validate()` bridge raises `RuntimeError` the instant it's called from
a running event loop — which every real caller in this codebase is, since
it's an async FastAPI app. All 8 live `register_domain()` call sites worked
around this by registering a legacy sync stub instead
(`ManufacturingOKHValidatorCompat`, `CookingValidatorCompat`), so the wrap
path was never exercised by anything real and stayed broken indefinitely.
#507 found this the hard way debugging `POST /match/validate` and worked
around it locally, bypassing the registry entirely rather than fixing it.

These tests exercise the registry directly: a real async `Validator`
registered through `register_domain()` must come back unwrapped and must be
directly callable from a running event loop — the contract
`ValidationEngine._validate_with_domain_context` already assumes (it
branches on `inspect.iscoroutinefunction`, which only sees the truth if
nothing has substituted a sync-only wrapper in between).
"""

from __future__ import annotations

import pytest

from src.core.domains.manufacturing.okh_extractor import OKHExtractor
from src.core.domains.manufacturing.okh_matcher import OKHMatcher
from src.core.domains.manufacturing.validation.compatibility import (
    ManufacturingOKHValidatorCompat,
)
from src.core.domains.manufacturing.validation.okh_validator import (
    ManufacturingOKHValidator,
)
from src.core.registry.domain_registry import (
    DomainMetadata,
    DomainRegistry,
    DomainStatus,
)

pytestmark = pytest.mark.unit

_INCOMPLETE_MANIFEST = {
    "title": "Incomplete Widget",
    "repo": "https://github.com/example/widget",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Author",
    "function": "A widget",
    "manufacturing_processes": ["3D printing"],
}


@pytest.fixture
def registry_snapshot():
    """`DomainRegistry` is process-global class state, and other tests in
    the same session depend on "manufacturing"/"cooking" being registered
    with their real, production validators — restore exactly what was
    there, not just delete what this test added."""
    domains = dict(DomainRegistry._domains)
    type_mappings = dict(DomainRegistry._type_mappings)
    yield
    DomainRegistry._domains = domains
    DomainRegistry._type_mappings = type_mappings


def _manufacturing_metadata() -> DomainMetadata:
    return DomainMetadata(
        name="manufacturing",
        display_name="Manufacturing & Hardware Production",
        description="test",
        version="0.0.0",
        status=DomainStatus.ACTIVE,
        supported_input_types={"okh", "okw"},
        supported_output_types={"supply_tree", "manufacturing_plan"},
    )


def _register_manufacturing(validator) -> None:
    DomainRegistry.register_domain(
        domain_name="manufacturing",
        extractor=OKHExtractor(),
        matcher=OKHMatcher(),
        validator=validator,
        metadata=_manufacturing_metadata(),
    )


def test_register_domain_stores_a_real_async_validator_unwrapped(registry_snapshot):
    validator = ManufacturingOKHValidator()
    _register_manufacturing(validator)

    stored = DomainRegistry.get_validator("manufacturing")

    assert stored is validator


@pytest.mark.asyncio
async def test_registered_async_validator_is_awaitable_from_a_running_event_loop(
    registry_snapshot,
):
    _register_manufacturing(ManufacturingOKHValidator())

    from src.core.validation.context import ValidationContext

    context = ValidationContext(
        name="test", domain="manufacturing", quality_level="professional"
    )
    stored = DomainRegistry.get_validator("manufacturing")

    # Pre-fix, this raised `RuntimeError: Cannot use async validator in
    # sync context` from inside ValidatorAdapter, before ever reaching real
    # validation logic — register_domain's auto-wrap lost the fact that
    # `validator` was actually async the moment it stored it.
    result = await stored.validate(_INCOMPLETE_MANIFEST, context)

    assert result.valid is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_register_domain_components_wires_manufacturing_to_the_real_validator():
    """Regression guard: `main.py` must register the real async validator
    for manufacturing, not the legacy Compat stub whose `.validate()`
    hardcodes `return True` regardless of input."""
    from src.core.main import register_domain_components

    await register_domain_components()

    validator = DomainRegistry.get_validator("manufacturing")

    assert isinstance(validator, ManufacturingOKHValidator)
    assert not isinstance(validator, ManufacturingOKHValidatorCompat)
