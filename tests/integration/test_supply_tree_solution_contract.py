"""Capture the real responses before modelling them (#373).

The procedure from #370, which exists because a ``response_model`` silently
filters any field it does not declare: freeze the payload the route actually
returns, add the model, then prove the payload is unchanged. Deriving a model
by reading the handler is how #369's two bugs got in.

The fixture runs a **real match** rather than hand-building a solution. Match
auto-saves its result, so the solution these routes serve is one the product
actually produces — a hand-built one silently omitted ``matching_metrics`` and
left ``component_count`` at zero, which is the kind of gap a golden then
blesses as correct.

Frozen structurally — keys kept, leaves reduced to a mark — because the
integration client is session-scoped and values depend on what other tests
created.

    BLESS_SUPPLY_TREE=1 .venv/bin/python -m pytest \
        tests/integration/test_supply_tree_solution_contract.py
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.models.supply_trees import (
    SupplyTree,
    SupplyTreeSolution,
    ValidationResult,
)
from tests.record_fixtures import okh_manifest_dict, okw_facility_dict

pytestmark = pytest.mark.integration

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "api" / "golden"
BLESS = "BLESS_SUPPLY_TREE"


_UUID_KEY = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def _structure(node):
    if isinstance(node, dict):
        # A dict keyed by generated ids is a map: the keys are data, not shape.
        # `dependency_graph` is keyed by tree UUID, so keeping the keys would
        # re-freeze a fresh id on every run and fail the comparison forever.
        # Values are homogeneous by construction, so one stands for all.
        if node and all(_UUID_KEY.match(str(k)) for k in node):
            return {"<id>": _structure(next(iter(node.values())))}
        return {k: _structure(v) for k, v in sorted(node.items())}
    if isinstance(node, list):
        merged: dict = {}
        for item in node:
            shaped = _structure(item)
            if not isinstance(shaped, dict):
                return ["*"]
            for key, value in shaped.items():
                merged.setdefault(key, value)
        return [dict(sorted(merged.items()))] if merged else []
    return "*"


def _check(body, name: str) -> None:
    golden = GOLDEN_DIR / f"{name}.json"
    shape = _structure(body)
    if os.getenv(BLESS):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(shape, indent=2, sort_keys=True) + "\n")
        pytest.skip("golden re-blessed")
    assert golden.exists(), f"No golden at {golden}. Capture with {BLESS}=1."
    assert shape == json.loads(golden.read_text()), (
        f"{name} changed shape. If a response_model was just added, it is "
        "filtering a field the route used to return."
    )


def _register(client, display_name: str) -> dict:
    """Register a fresh account and return its Authorization header."""
    registration = client.post(
        "/api/identity/register", json={"display_name": display_name}
    )
    assert registration.status_code == 201, registration.text
    return {"Authorization": f"Bearer {registration.json()['key']['token']}"}


def _save(client, auth: dict, solution: SupplyTreeSolution) -> str:
    """Store a solution through the real save route and return its id."""
    payload = json.loads(json.dumps(solution.to_dict(), default=str))
    saved = client.post(
        f"/api/supply-tree/solution/{uuid4()}/save",
        json={"solution": payload, "ttl_days": 1, "tags": ["contract-fixture"]},
        headers=auth,
    )
    assert saved.status_code == 200, saved.text
    return saved.json()["data"]["solution_id"]


def _tree(**kwargs) -> SupplyTree:
    """A supply tree with the fields every match fills in."""
    kwargs.setdefault("facility_name", "FabLab Drome")
    kwargs.setdefault("okh_reference", "okh-vent")
    kwargs.setdefault("okw_reference", str(uuid4()))
    kwargs.setdefault("confidence_score", 0.9)
    kwargs.setdefault("match_type", "direct")
    return SupplyTree(**kwargs)


@pytest.fixture
def saved_solution(client, monkeypatch):
    """A registered caller and one solution, produced by a real match.

    Solutions are owner-scoped: an anonymous save records no owner and is
    listed for nobody, so an unauthenticated fixture would freeze an empty
    ``result`` and say nothing about the row shape a client actually reads.
    Each call registers its own account, so the listing is exactly this
    fixture's solutions and not whatever else the session created.
    """
    # Storage-only facilities. The default is the union of storage and the Map
    # of Manufacturers, and MoM is a network call — which the suite's network
    # guard blocks, failing the test with a host rather than a matching result.
    monkeypatch.setenv("OKW_SOURCE", "storage")

    registration = client.post(
        "/api/identity/register", json={"display_name": "Supply Tree Fixture"}
    )
    assert registration.status_code == 201, registration.text
    auth = {"Authorization": f"Bearer {registration.json()['key']['token']}"}

    okh = client.post(
        "/api/okh/create", json={"content": okh_manifest_dict()}, headers=auth
    )
    assert okh.status_code == 201, okh.text
    okw = client.post(
        "/api/okw/create", json={"content": okw_facility_dict()}, headers=auth
    )
    assert okw.status_code == 201, okw.text

    match = client.post(
        "/api/match",
        json={
            "okh_id": okh.json()["okh"]["id"],
            "max_depth": 0,
            "min_confidence": 0.0,
            # Auto-save is opt-in, and is what puts a solution behind these
            # routes at all.
            "save_solution": True,
            "solution_tags": ["contract-fixture"],
        },
        headers=auth,
    )
    assert match.status_code == 200, match.text

    listing = client.get("/api/supply-tree/solutions", headers=auth)
    assert listing.status_code == 200, listing.text
    rows = listing.json()["data"]["result"]
    assert rows, "match did not auto-save a solution; the goldens would be vacuous"
    return auth, rows[0]["id"]


def test_solutions_list_shape(client, saved_solution):
    auth, _ = saved_solution
    response = client.get("/api/supply-tree/solutions", headers=auth)
    assert response.status_code == 200, response.text
    _check(response.json(), "supply_tree_solutions_list")


def test_solution_get_shape(client, single_tree_solution):
    auth, solution_id = single_tree_solution
    response = client.get(f"/api/supply-tree/solution/{solution_id}", headers=auth)
    assert response.status_code == 200, response.text
    _check(response.json(), "supply_tree_solution_get")


def test_solution_staleness_shape(client, saved_solution):
    auth, solution_id = saved_solution
    response = client.get(
        f"/api/supply-tree/solution/{solution_id}/staleness", headers=auth
    )
    assert response.status_code == 200, response.text
    _check(response.json(), "supply_tree_solution_staleness")


def test_solution_visualization_shape(client, saved_solution):
    auth, solution_id = saved_solution
    response = client.get(
        f"/api/supply-tree/solution/{solution_id}/visualization", headers=auth
    )
    assert response.status_code == 200, response.text
    _check(response.json(), "supply_tree_solution_visualization")


def test_solution_extend_shape(client, saved_solution):
    auth, solution_id = saved_solution
    response = client.post(
        f"/api/supply-tree/solution/{solution_id}/extend",
        json={"additional_days": 5},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    _check(response.json(), "supply_tree_solution_extend")


def test_solution_delete_shape(client, saved_solution):
    auth, solution_id = saved_solution
    response = client.delete(f"/api/supply-tree/solution/{solution_id}", headers=auth)
    assert response.status_code == 200, response.text
    _check(response.json(), "supply_tree_solution_delete")


@pytest.fixture
def single_tree_solution(client):
    """Exactly one tree, stored through the real save route.

    The detail payload is *conditional on tree count*: ``to_dict`` emits a
    compatibility ``tree`` key only when the solution holds one tree. Deriving
    this golden from a match made it depend on how many facilities happened to
    be in shared storage — it held alone and broke in the full suite, where
    earlier tests had created more facilities, the match returned several
    trees, and ``tree`` vanished. Constructing the solution pins the branch.
    """
    auth = _register(client, "Single Tree Fixture")
    solution = SupplyTreeSolution(
        all_trees=[_tree()],
        score=0.9,
        metadata={"okh_id": "okh-vent", "matching_mode": "single-level"},
    )
    return auth, _save(client, auth, solution)


@pytest.fixture
def nested_solution(client):
    """A solution whose trees are related, stored through the real save route.

    The match-driven fixture cannot produce one: edges exist only where a tree
    carries ``parent_tree_id`` or ``depends_on``, and only nested matching sets
    those. Nested matching currently returns 500 — the handler is annotated
    ``-> dict[str, Any]`` and that branch returns a ``SuccessResponse`` object,
    so response validation fails. Filed as #439.

    Building the solution is still an observation rather than an invention: the
    payload goes through ``SupplyTreeSolution.from_dict`` and comes back out of
    storage the same way any other solution does. What it buys is a non-empty
    ``edges`` array, so the model for it is derived from a response that has
    one.
    """
    auth = _register(client, "Nested Fixture")

    parent = _tree(facility_name="Assembly Hall", production_stage="final")
    child = _tree(
        facility_name="Machine Shop",
        confidence_score=0.8,
        parent_tree_id=parent.id,
        component_id="bracket",
        component_name="Bracket",
        component_quantity=2,
        component_unit="pcs",
        production_stage="component",
        depth=1,
        component_path=["bracket"],
    )
    parent.child_tree_ids = [child.id]
    parent.depends_on = [child.id]

    # Every optional field is set on purpose. ``to_dict`` emits seven keys only
    # when they are not None — component_mapping, dependency_graph,
    # production_sequence, validation_result and the two totals. A golden taken
    # from a solution that left them unset would not contain them, the model
    # derived from it would not declare them, and ``response_model`` would then
    # filter them off any solution that did have them.
    solution = SupplyTreeSolution(
        all_trees=[parent, child],
        root_trees=[parent],
        score=0.85,
        metrics={"direct_matches": 2},
        component_mapping={"bracket": [child]},
        dependency_graph={parent.id: [child.id]},
        production_sequence=[[child.id], [parent.id]],
        validation_result=ValidationResult(
            is_valid=True,
            errors=["sample error"],
            warnings=["sample warning"],
            unmatched_components=["widget"],
            circular_dependencies=[[parent.id, child.id]],
            missing_dependencies=[child.id],
        ),
        total_estimated_cost=1234.5,
        total_estimated_time="3 days",
        metadata={"okh_id": "okh-vent", "matching_mode": "nested"},
    )
    return auth, _save(client, auth, solution)


def test_nested_solution_visualization_has_edges(client, nested_solution):
    """The edge shape, captured from a bundle that actually contains one."""
    auth, solution_id = nested_solution
    response = client.get(
        f"/api/supply-tree/solution/{solution_id}/visualization", headers=auth
    )
    assert response.status_code == 200, response.text
    edges = response.json()["data"]["supply_tree"]["edges"]
    assert edges, "fixture produced no edges; the edge model would be vacuous"
    _check(response.json(), "supply_tree_solution_visualization_nested")


def test_nested_solution_get_shape(client, nested_solution):
    """A nested solution serialises more keys than a single-level one.

    ``SupplyTreeSolution.to_dict`` emits the component mapping, dependency
    graph, production sequence and validation result only when the solution is
    nested. Freezing just the single-level detail payload would leave those
    undeclared, and a ``response_model`` filters what it does not declare — so
    the nested branch would lose exactly the fields that make it nested.
    """
    auth, solution_id = nested_solution
    response = client.get(f"/api/supply-tree/solution/{solution_id}", headers=auth)
    assert response.status_code == 200, response.text
    _check(response.json(), "supply_tree_solution_get_nested")
