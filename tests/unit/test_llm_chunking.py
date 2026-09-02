"""Chunk splitting must fill its budget.

``_apply_boundary_preference`` takes the *last* paragraph break in the window.
Real prompts are a blank-line-separated preamble followed by a long block with
no blank lines in it — an indent-2 JSON listing — so that break sits near the
window's start and the chunk closes far below budget.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.core.llm.chunking import (
    ChunkingConfig,
    default_token_estimator,
    split_text_into_chunks,
)

# A preamble whose paragraph breaks all fall early, then a listing with none.
PREAMBLE = "\n\n".join(f"Instruction paragraph {n}." for n in range(8))
LISTING = "\n".join(f'    "models/subassembly/part_{n:05d}.stl",' for n in range(1200))
PROMPT = PREAMBLE + "\n\n" + LISTING

# The production shape: the last paragraph break sits past the overlap but well
# short of the budget, so the following chunk stepped back and closed on that
# same break — covering no new text. Measured on the real prompt as a
# 1,461-token chunk followed by a 256-token one.
_PARAGRAPH = "Instruction paragraph with enough text to matter. " * 4
MID_PREAMBLE = "\n\n".join(_PARAGRAPH for _ in range(12))
STALLING_PROMPT = MID_PREAMBLE + "\n\n" + LISTING


def test_chunks_fill_their_budget():
    config = ChunkingConfig(max_chunk_tokens=1000, overlap_tokens=64)

    chunks = split_text_into_chunks(PROMPT, config)

    underfilled = [
        (c.index, c.estimated_tokens)
        for c in chunks[:-1]
        if c.estimated_tokens < config.max_chunk_tokens // 2
    ]
    assert not underfilled, (
        f"chunks closed below half their {config.max_chunk_tokens}-token budget: "
        f"{underfilled}; a boundary near the window start was preferred over a "
        "full chunk"
    )


def test_every_chunk_advances():
    """Overlap steps back; the next chunk must still end further forward.

    A chunk that closes at the previous chunk's end costs a full sequential
    LLM call and covers no new text.
    """
    config = ChunkingConfig(max_chunk_tokens=1000, overlap_tokens=64)

    chunks = split_text_into_chunks(STALLING_PROMPT, config)

    stalled = [
        (c.index, c.start_char, c.end_char)
        for previous, c in zip(chunks, chunks[1:])
        if c.end_char <= previous.end_char
    ]
    assert not stalled, f"chunks covering no new text: {stalled}"


def test_chunks_cover_the_whole_text():
    """Splitting must not drop content between chunks."""
    config = ChunkingConfig(max_chunk_tokens=1000, overlap_tokens=64)

    chunks = split_text_into_chunks(PROMPT, config)

    assert chunks[0].start_char == 0
    assert chunks[-1].end_char == len(PROMPT)
    for previous, c in zip(chunks, chunks[1:]):
        assert (
            c.start_char <= previous.end_char
        ), f"gap between chunk {previous.index} and {c.index}"
