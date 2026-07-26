"""Guards against re-introducing full spaCy pipeline runs in BOM collection.

Generation on one real repository (RespiraWorks/Ventilator) spent ~107s of its
~112s of CPU inside spaCy, called from two places in ``BOMCollector``:

  * ``_find_bom_sections_with_nlp`` parsed the whole document and then never
    read the result — 135 parses, ~53s, for nothing.
  * ``_analyze_bom_likelihood`` ran the full pipeline (tagger, parser, NER)
    2,117 times but used only ``token.text`` — a neural network doing a
    word-membership test, ~54s.

Fixing both took generation from 120s to 17s with byte-identical output. The
regression would be silent: correct results, seven times slower. So these tests
assert the *cost*, not the output — the full pipeline must never be invoked from
these paths.
"""

from __future__ import annotations

import pytest

from src.core.generation.bom_models import BOMCollector


class _PipelineTripwire:
    """Stands in for a spaCy Language.

    Calling it (``nlp(text)``) means the full pipeline ran, which is the thing
    being guarded against. Tokenizing is cheap and allowed.
    """

    def __init__(self):
        self.tokenizer_calls = 0

    def __call__(self, text):  # pragma: no cover - failing here is the point
        raise AssertionError(
            "Full spaCy pipeline invoked. Use `nlp.tokenizer(text)` when only "
            "token.text is needed — the pipeline costs ~50x more and adds "
            "annotations this code does not read."
        )

    def tokenizer(self, text):
        self.tokenizer_calls += 1
        return [_Token(word) for word in str(text).split()]


class _Token:
    __slots__ = ("text",)

    def __init__(self, text: str):
        self.text = text


@pytest.fixture
def collector() -> BOMCollector:
    c = BOMCollector()
    c._nlp = _PipelineTripwire()
    return c


def test_bom_likelihood_uses_the_tokenizer_not_the_pipeline(collector):
    score = collector._analyze_bom_likelihood(
        "Bill of materials: 4x M3 bolt, 2x bearing, resistor 10k"
    )
    assert 0.0 <= score <= 1.0
    assert collector._nlp.tokenizer_calls == 1


def test_bom_likelihood_still_scores_on_keywords(collector):
    """Cheaper must not mean inert — keyword hits still raise the score."""
    bom_like = collector._analyze_bom_likelihood(
        "bom components quantity material part"
    )
    plain = collector._analyze_bom_likelihood("the quick brown fox")
    assert bom_like > plain


def test_section_finding_does_not_parse_the_document(collector):
    """Sectioning is textual; it must not parse the document to do it."""
    content = "# Bill of Materials\n\n4x M3 bolt\n\n# Licence\n\nMIT\n"
    sections = collector._find_bom_sections_with_nlp(content, "README.md")
    assert isinstance(sections, list)


def test_no_nlp_available_is_handled(collector):
    """Both paths degrade rather than raising when spaCy is unavailable."""
    collector._nlp = None
    assert collector._analyze_bom_likelihood("anything") == 0.0
    assert collector._find_bom_sections_with_nlp("anything", "README.md") == []
