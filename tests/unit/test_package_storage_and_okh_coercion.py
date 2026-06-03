"""Regression tests for package blob layout helpers and OKH list coercion."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.core.api.models.base import APIStatus
from src.core.api.models.okh.response import OKHResponse
from src.core.models.okh import OKHManifest
from src.core.storage.package_storage import (
    build_info_key_candidates,
    default_package_prefix,
    parse_org_project_version_from_build_info_key,
)


def test_build_info_key_candidates_order() -> None:
    org, proj, ver = "waag", "demo", "1.0.0"
    keys = build_info_key_candidates(org, proj, ver)
    p = default_package_prefix()
    assert keys[0] == f"{p}/{org}/{proj}/{ver}/build-info.json"
    assert keys[1] == f"okh/packages/{org}/{proj}/{ver}/build-info.json"


def test_parse_build_info_key_new_layout() -> None:
    p = default_package_prefix()
    key = f"{p}/org/project/2.1.0/build-info.json"
    parsed = parse_org_project_version_from_build_info_key(key)
    assert parsed == ("org", "project", "2.1.0", "new")


def test_parse_build_info_key_legacy_layout() -> None:
    key = "okh/packages/org/project/2.1.0/build-info.json"
    parsed = parse_org_project_version_from_build_info_key(key)
    assert parsed == ("org", "project", "2.1.0", "legacy")


def test_okh_tool_list_dicts_coerced_for_okh_response() -> None:
    data = {
        "title": "T",
        "version": "1",
        "license": {"hardware": "MIT"},
        "licensor": "Alice",
        "documentation_language": "en",
        "function": "f",
        "id": "00000000-0000-0000-0000-000000000099",
        "tool_list": [
            {"title": "requirements.txt", "extracted_by": "file_pattern"},
            "plain tool",
        ],
        "manufacturing_processes": [{"process_name": "3d-printing"}],
    }
    m = OKHManifest.from_dict(data)
    assert m.tool_list == ["requirements.txt", "plain tool"]
    assert m.manufacturing_processes == ["3d-printing"]

    payload = {
        **m.to_dict(),
        "status": APIStatus.SUCCESS,
        "message": "t",
        "request_id": None,
        "timestamp": datetime.now(),
    }
    OKHResponse.model_validate(payload)


def test_custom_package_prefix_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OHM_PACKAGE_STORAGE_PREFIX", "my-packages")
    # default_package_prefix reads os.environ at call time
    assert default_package_prefix() == "my-packages"
    keys = build_info_key_candidates("a", "b", "1")
    assert keys[0].startswith("my-packages/a/b/1/")
    monkeypatch.delenv("OHM_PACKAGE_STORAGE_PREFIX", raising=False)
