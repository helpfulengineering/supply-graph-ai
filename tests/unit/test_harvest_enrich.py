"""Unit tests for harvest-parts fleet enrichment — GAP-6."""

from __future__ import annotations

from src.core.api.models.okh.request import OKHHarvestRequest


def test_request_model_defaults_enrich_fleet_false():
    req = OKHHarvestRequest(manifest_ids=["abc"])
    assert req.enrich_fleet is False


def test_request_model_accepts_enrich_fleet_true():
    req = OKHHarvestRequest(manifest_ids=["abc"], enrich_fleet=True)
    assert req.enrich_fleet is True


def test_request_model_serialises_enrich_fleet():
    req = OKHHarvestRequest(manifest_ids=["abc"], enrich_fleet=True)
    d = req.model_dump()
    assert d["enrich_fleet"] is True


def test_request_model_combines_enrich_with_filters():
    req = OKHHarvestRequest(
        manifest_ids=["abc"],
        replaceable_only=True,
        enrich_fleet=True,
    )
    assert req.replaceable_only is True
    assert req.enrich_fleet is True
