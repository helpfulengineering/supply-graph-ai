"""Core chunking primitives for long-context LLM workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, Literal, Optional, Protocol


class TokenEstimator(Protocol):
    """Protocol for token estimation functions."""

    def __call__(self, text: str) -> int:
        ...


def default_token_estimator(text: str) -> int:
    """
    Conservative fallback estimator with no external dependencies.

    Uses a simple chars-to-tokens approximation that is intentionally conservative.
    """
    if not text:
        return 0
    # Conservative approximation used as default when no tokenizer backend is available.
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class TokenBudget:
    """Resolved token budget for a specific request."""

    context_window_tokens: int
    system_tokens: int
    instruction_tokens: int
    reserved_output_tokens: int
    safety_margin_tokens: int
    payload_tokens_available: int
    request_type: str
    provider: Optional[str] = None
    model: Optional[str] = None


@dataclass
class TokenBudgetPolicy:
    """Policy inputs used to derive a TokenBudget."""

    context_window_tokens: int
    system_tokens: int = 0
    instruction_tokens: int = 0
    reserved_output_tokens: int = 1024
    safety_margin_tokens: int = 256
    reserved_output_by_request_type: Dict[str, int] = field(default_factory=dict)
    context_window_by_provider: Dict[str, int] = field(default_factory=dict)
    context_window_by_model: Dict[str, int] = field(default_factory=dict)


BoundaryPreference = Literal["paragraph", "line", "character"]


@dataclass
class ChunkingConfig:
    """Chunking settings for splitting large input text."""

    max_chunk_tokens: int
    overlap_tokens: int = 0
    boundary_preference: Iterable[BoundaryPreference] = ("paragraph", "line", "character")

    def __post_init__(self) -> None:
        if self.max_chunk_tokens <= 0:
            raise ValueError("max_chunk_tokens must be > 0")
        if self.overlap_tokens < 0:
            raise ValueError("overlap_tokens must be >= 0")
        if self.overlap_tokens >= self.max_chunk_tokens:
            raise ValueError("overlap_tokens must be < max_chunk_tokens")


@dataclass(frozen=True)
class TextChunk:
    """A chunk of source text and its position in the original string."""

    index: int
    text: str
    start_char: int
    end_char: int
    source_id: Optional[str] = None
    estimated_tokens: int = 0


def build_token_budget(
    policy: TokenBudgetPolicy,
    request_type: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> TokenBudget:
    """Build a request-specific token budget and fail fast on impossible budgets."""
    context_window = policy.context_window_tokens
    if provider and provider in policy.context_window_by_provider:
        context_window = policy.context_window_by_provider[provider]
    if model and model in policy.context_window_by_model:
        context_window = policy.context_window_by_model[model]

    reserved_output = policy.reserved_output_by_request_type.get(
        request_type, policy.reserved_output_tokens
    )

    payload_available = (
        context_window
        - policy.system_tokens
        - policy.instruction_tokens
        - reserved_output
        - policy.safety_margin_tokens
    )
    if payload_available <= 0:
        raise ValueError(
            "Token budget invalid: fixed overhead exceeds or equals context window"
        )

    return TokenBudget(
        context_window_tokens=context_window,
        system_tokens=policy.system_tokens,
        instruction_tokens=policy.instruction_tokens,
        reserved_output_tokens=reserved_output,
        safety_margin_tokens=policy.safety_margin_tokens,
        payload_tokens_available=payload_available,
        request_type=request_type,
        provider=provider,
        model=model,
    )


def split_text_into_chunks(
    text: str,
    config: ChunkingConfig,
    estimate_tokens_fn: Optional[Callable[[str], int]] = None,
    source_id: Optional[str] = None,
) -> list[TextChunk]:
    """
    Split text into chunks by token budget with overlap and boundary preferences.

    The estimator is expected to be monotonic with respect to text length.
    """
    if not text:
        return []

    estimate = estimate_tokens_fn or default_token_estimator
    chunks: list[TextChunk] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        remaining = text[start:]
        if estimate(remaining) <= config.max_chunk_tokens:
            end = text_len
        else:
            end = _max_end_for_budget(text, start, config.max_chunk_tokens, estimate)
            end = _apply_boundary_preference(
                text, start, end, tuple(config.boundary_preference)
            )
            if end <= start:
                end = min(text_len, start + 1)

        chunk_text = text[start:end]
        chunks.append(
            TextChunk(
                index=len(chunks),
                text=chunk_text,
                start_char=start,
                end_char=end,
                source_id=source_id,
                estimated_tokens=estimate(chunk_text),
            )
        )

        if end >= text_len:
            break

        if config.overlap_tokens > 0:
            overlap_start = _suffix_start_for_overlap(
                text, start, end, config.overlap_tokens, estimate
            )
            next_start = overlap_start if overlap_start > start else end
        else:
            next_start = end

        # Safety against non-progress loops.
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def _max_end_for_budget(
    text: str, start: int, max_tokens: int, estimate: Callable[[str], int]
) -> int:
    """Binary-search the largest end index within token budget."""
    lo = start + 1
    hi = len(text)
    best = lo

    while lo <= hi:
        mid = (lo + hi) // 2
        token_count = estimate(text[start:mid])
        if token_count <= max_tokens:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return max(start + 1, best)


def _apply_boundary_preference(
    text: str,
    start: int,
    end: int,
    preferences: tuple[BoundaryPreference, ...],
) -> int:
    """Try to move end left to a natural boundary for readability."""
    if end - start <= 1:
        return end

    window = text[start:end]
    for pref in preferences:
        if pref == "paragraph":
            marker = "\n\n"
        elif pref == "line":
            marker = "\n"
        else:
            continue

        idx = window.rfind(marker)
        if idx > 0:
            candidate = start + idx + len(marker)
            if candidate > start:
                return candidate

    return end


def _suffix_start_for_overlap(
    text: str,
    chunk_start: int,
    chunk_end: int,
    overlap_tokens: int,
    estimate: Callable[[str], int],
) -> int:
    """Return the earliest suffix start whose token count is <= overlap_tokens."""
    if overlap_tokens <= 0:
        return chunk_end

    best_start = chunk_end
    for i in range(chunk_end - 1, chunk_start - 1, -1):
        suffix = text[i:chunk_end]
        if estimate(suffix) <= overlap_tokens:
            best_start = i
        else:
            break

    return best_start
