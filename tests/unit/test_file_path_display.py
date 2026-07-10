"""Tests for file path display normalization."""

import pytest

from src.core.utils.file_path_display import (
    ROOT_DIRECTORY_LABEL,
    file_basename,
    file_directory,
    normalize_display_path,
)


def test_relative_path_unchanged():
    assert normalize_display_path("design/model.stl") == "design/model.stl"


def test_github_raw_url():
    url = "https://github.com/o/r/raw/main/docs/assembly/README.md"
    assert normalize_display_path(url) == "docs/assembly/README.md"


def test_github_blob_url():
    url = "https://github.com/o/r/blob/main/design/foo.step"
    assert normalize_display_path(url) == "design/foo.step"


def test_githubusercontent_url():
    url = "https://raw.githubusercontent.com/o/r/main/stl/part.stl"
    assert normalize_display_path(url) == "stl/part.stl"


def test_gitlab_raw_url():
    url = "https://gitlab.com/o/r/-/raw/main/docs/guide.pdf"
    assert normalize_display_path(url) == "docs/guide.pdf"


def test_rejects_traversal():
    with pytest.raises(ValueError):
        normalize_display_path("../secret.txt")


def test_file_directory_root():
    assert file_directory("README.md") == ROOT_DIRECTORY_LABEL


def test_file_directory_nested():
    assert file_directory("docs/assembly/README.md") == "docs/assembly"


def test_file_basename():
    assert file_basename("docs/assembly/README.md") == "README.md"
