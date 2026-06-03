"""OKH discovery shape: skip BOM-only JSON and bom.json keys."""

from __future__ import annotations

from src.core.storage.smart_discovery import (
    is_okh_bom_sidecar_storage_key,
    minimal_okh_manifest_dict,
)


def test_is_okh_bom_sidecar_bom_json_filename() -> None:
    assert is_okh_bom_sidecar_storage_key("okh/project/bom.json") is True
    assert is_okh_bom_sidecar_storage_key("okh/foo-bom.json") is True
    assert is_okh_bom_sidecar_storage_key("okh/manifest-okh.json") is False


def test_minimal_okh_manifest_dict_rejects_bom_only() -> None:
    assert (
        minimal_okh_manifest_dict(
            {
                "components": [{"ref": "R1"}],
                "id": "340b030e-e3c6-4869-b947-4a24c52daaf1",
            }
        )
        is False
    )


def test_minimal_okh_manifest_dict_accepts_full_minimal_okh() -> None:
    assert (
        minimal_okh_manifest_dict(
            {
                "title": "T",
                "version": "1",
                "license": {"hardware": "MIT"},
                "licensor": "Alice",
                "documentation_language": "en",
                "function": "f",
            }
        )
        is True
    )
