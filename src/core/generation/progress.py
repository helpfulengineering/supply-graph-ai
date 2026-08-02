"""Weighted progress reporting for OKH generate-from-url.

Fractions are start-of-stage cumulatives so a long stage (especially ``llm``)
advances the bar when it begins rather than only when it finishes.

Weights are provisional, skewed toward measured reality that LLM work dominates
large-repo runs; renormalize after dropping inactive stages (e.g. ``no_llm``).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence

from src.core.generation.models import GenerationMetadata

ProgressCallback = Callable[[str, float, Optional[str]], None]

# Relative weights (not percentages). LLM is intentionally largest.
_STAGE_WEIGHTS: Dict[str, float] = {
    "clone": 12.0,
    "direct": 5.0,
    "heuristic": 8.0,
    "nlp": 15.0,
    "llm": 40.0,
    "bom_verification": 5.0,
    "bom_normalization": 8.0,
    "quality": 5.0,
    "materials_routing": 2.0,
}


def planned_stages(*, include_clone: bool = True, use_llm: bool = False) -> List[str]:
    """Return the ordered public stages for a generate-from-url run."""
    stages: List[str] = []
    if include_clone:
        stages.append("clone")
    stages.extend(["direct", "heuristic", "nlp"])
    if use_llm:
        stages.append("llm")
    stages.extend(
        [
            "bom_verification",
            "bom_normalization",
            "quality",
            "materials_routing",
        ]
    )
    return stages


class ProgressEmitter:
    """Emit monotonic (stage, fraction, message) updates for a fixed stage plan."""

    def __init__(
        self,
        stages: Sequence[str],
        *,
        callback: Optional[ProgressCallback] = None,
        metadata: Optional[GenerationMetadata] = None,
    ) -> None:
        if not stages:
            raise ValueError("At least one progress stage is required")
        self._stages = list(stages)
        self._callback = callback
        self._metadata = metadata
        self._last = 0.0
        total = sum(_STAGE_WEIGHTS.get(s, 1.0) for s in self._stages)
        running = 0.0
        self._cum: Dict[str, float] = {}
        for stage in self._stages:
            running += _STAGE_WEIGHTS.get(stage, 1.0) / total
            self._cum[stage] = running
        # Final stage lands exactly at 1.0
        self._cum[self._stages[-1]] = 1.0

    def fraction_for(self, stage: str) -> float:
        return self._cum.get(stage, self._last)

    def emit(self, stage: str, message: Optional[str] = None) -> None:
        fraction = max(self._last, self.fraction_for(stage))
        self._last = fraction
        if self._metadata is not None:
            label = message or stage
            self._metadata.add_processing_log(f"{stage}: {label} ({fraction:.2f})")
        if self._callback is not None:
            self._callback(stage, fraction, message)
