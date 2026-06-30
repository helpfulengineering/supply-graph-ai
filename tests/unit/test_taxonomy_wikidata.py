"""Unit tests for Wikidata QID support in the process taxonomy (MoM integration)."""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.core.taxonomy import taxonomy
from src.core.taxonomy.process_taxonomy import (
    ProcessDefinition,
    ProcessTaxonomy,
    load_from_yaml,
)


class TestLiveTaxonomyWikidataIris:
    """Exercises the real module-level singleton loaded from processes.yaml."""

    def test_known_process_returns_wikidata_iri(self):
        assert (
            taxonomy.get_wikidata_iri("laser_cutting")
            == "https://www.wikidata.org/entity/Q3062349"
        )

    def test_process_without_qid_returns_none(self):
        defn = taxonomy.get_definition("testing")
        assert defn is not None
        assert defn.wikidata_qid is None
        assert taxonomy.get_wikidata_iri("testing") is None

    def test_unknown_canonical_id_returns_none(self):
        assert taxonomy.get_wikidata_iri("not_a_real_process") is None


class TestProcessTaxonomyWikidataMap:
    """Exercises _build()'s wikidata map construction in isolation."""

    def test_custom_definitions_build_wikidata_map(self):
        custom = ProcessTaxonomy(
            definitions=[
                ProcessDefinition(
                    canonical_id="foo_process",
                    display_name="Foo Process",
                    wikidata_qid="Q12345",
                ),
                ProcessDefinition(
                    canonical_id="bar_process",
                    display_name="Bar Process",
                ),
            ]
        )

        assert (
            custom.get_wikidata_iri("foo_process")
            == "https://www.wikidata.org/entity/Q12345"
        )
        assert custom.get_wikidata_iri("bar_process") is None
        assert custom.get_wikidata_iri("missing_process") is None


class TestLoadFromYamlWikidataField:
    def test_wikidata_qid_loaded_from_yaml(self, tmp_path):
        yaml_path = tmp_path / "processes.yaml"
        yaml_path.write_text(
            """
version: "test"
processes:
  foo_process:
    display_name: "Foo Process"
    wikidata_qid: "Q999"
  bar_process:
    display_name: "Bar Process"
""",
            encoding="utf-8",
        )

        definitions = load_from_yaml(yaml_path)
        by_id = {d.canonical_id: d for d in definitions}

        assert by_id["foo_process"].wikidata_qid == "Q999"
        assert by_id["bar_process"].wikidata_qid is None

        loaded = ProcessTaxonomy(definitions=definitions)
        assert (
            loaded.get_wikidata_iri("foo_process")
            == "https://www.wikidata.org/entity/Q999"
        )
        assert loaded.get_wikidata_iri("bar_process") is None
