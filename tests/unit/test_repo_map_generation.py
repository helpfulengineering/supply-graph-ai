"""Tests for the .repo-map.md generator.

The map is a generated file gated on byte-equality, so the properties worth
pinning are the ones that gate can be broken by: it must depend on tracked
content and nothing else, it must never quietly omit symbols, and the
committed copy must not be stale.

The directory-name test is a regression guard. The `Repository:` header was
once taken from the checkout directory, so the committed map recorded whoever
generated it last (`ohm-ux-overhaul-a6737b`) while CI regenerated its own
(`OHM`). The drift check could not pass for anyone whose directory was named
differently, and because that check gates the `quality` job — which every
other job needs — the whole pipeline was skipped on every push.
"""

import importlib.util
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "generate_repo_map.py"
_COMMITTED_MAP = _REPO_ROOT / ".repo-map.md"


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_repo_map", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generator()

_MODULE = '''"""A fixture module."""


class Widget:
    def run(self):
        return 1


def helper():
    return 2
'''


def _make_repo(parent: Path, dir_name: str, project_name: str = "fixture") -> Path:
    """A minimal git repo whose only variable is the directory it sits in."""
    repo = parent / dir_name
    (repo / "pkg").mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "{project_name}"\n', encoding="utf-8"
    )
    (repo / "pkg" / "mod.py").write_text(_MODULE, encoding="utf-8")
    # Tracked-file discovery goes through `git ls-files`; without a repo it
    # falls back to a filesystem walk and would exercise a different path.
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return repo


# --------------------------------------------------------------------------
# Repository identity
# --------------------------------------------------------------------------


def test_identity_comes_from_the_project_name(tmp_path):
    repo = _make_repo(tmp_path, "any-directory-name", project_name="supply-graph-ai")
    assert gen.repo_identity(repo) == "supply-graph-ai"


def test_identity_falls_back_to_the_directory_without_a_pyproject(tmp_path):
    repo = tmp_path / "loose-tree"
    repo.mkdir()
    assert gen.repo_identity(repo) == "loose-tree"


def test_identity_falls_back_when_the_pyproject_is_unreadable(tmp_path):
    repo = tmp_path / "broken"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("this is not = valid [toml", encoding="utf-8")
    assert gen.repo_identity(repo) == "broken"


def test_identity_falls_back_when_the_project_name_is_missing(tmp_path):
    repo = tmp_path / "nameless"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    assert gen.repo_identity(repo) == "nameless"


# --------------------------------------------------------------------------
# Reproducibility — the property the drift gate depends on
# --------------------------------------------------------------------------


def test_map_does_not_depend_on_the_checkout_directory_name(tmp_path):
    """Identical content in differently named directories must map identically."""
    worktree = _make_repo(tmp_path / "a", "ohm-ux-overhaul-a6737b")
    runner = _make_repo(tmp_path / "b", "OHM")

    assert gen.generate_combined_map(worktree, worktree) == gen.generate_combined_map(
        runner, runner
    )


def test_map_is_deterministic_across_runs(tmp_path):
    repo = _make_repo(tmp_path, "repo")
    assert gen.generate_combined_map(repo, repo) == gen.generate_combined_map(
        repo, repo
    )


def test_map_records_the_symbols_it_found(tmp_path):
    repo = _make_repo(tmp_path, "repo")
    content = gen.generate_combined_map(repo, repo)

    assert "Repository: fixture" in content
    assert "Widget" in content
    assert "helper" in content


# --------------------------------------------------------------------------
# Unparseable sources must be loud, never silently dropped
# --------------------------------------------------------------------------


def test_parse_failures_are_detected_in_a_generated_map(tmp_path):
    repo = _make_repo(tmp_path, "repo")
    (repo / "pkg" / "broken.py").write_text("def (\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)

    assert gen.parse_failures_in(gen.generate_combined_map(repo, repo))


def test_a_clean_map_reports_no_parse_failures(tmp_path):
    repo = _make_repo(tmp_path, "repo")
    assert gen.parse_failures_in(gen.generate_combined_map(repo, repo)) == []


def test_generator_refuses_to_write_a_map_with_missing_symbols(tmp_path):
    """An unparseable file must fail the run, not become a placeholder on disk."""
    repo = _make_repo(tmp_path, "repo")
    (repo / "pkg" / "broken.py").write_text("def (\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    out = tmp_path / "out"

    result = subprocess.run(
        [
            "python",
            str(_SCRIPT),
            "--target",
            str(repo),
            "--output",
            str(out),
            "--filename",
            "map.md",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "unparseable" in result.stderr
    assert not (out / "map.md").exists(), "a corrupt map must never reach disk"


# --------------------------------------------------------------------------
# The --check gate
# --------------------------------------------------------------------------


def _run_check(repo: Path, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "python",
            str(_SCRIPT),
            "--target",
            str(repo),
            "--output",
            str(out),
            "--filename",
            "map.md",
            "--check",
        ],
        capture_output=True,
        text=True,
    )


def test_check_passes_when_the_map_is_current(tmp_path):
    repo = _make_repo(tmp_path, "repo")
    out = tmp_path / "out"
    out.mkdir()
    (out / "map.md").write_text(gen.generate_combined_map(repo, out), encoding="utf-8")

    assert _run_check(repo, out).returncode == 0


def test_check_fails_when_the_map_has_drifted(tmp_path):
    repo = _make_repo(tmp_path, "repo")
    out = tmp_path / "out"
    out.mkdir()
    (out / "map.md").write_text(
        gen.generate_combined_map(repo, out) + "drift", encoding="utf-8"
    )

    result = _run_check(repo, out)
    assert result.returncode == 1
    assert "DRIFT" in result.stdout


def test_check_fails_when_the_map_is_absent(tmp_path):
    repo = _make_repo(tmp_path, "repo")
    out = tmp_path / "out"
    out.mkdir()

    assert _run_check(repo, out).returncode == 1


def test_check_does_not_write(tmp_path):
    """The gate runs in `make ready`, which must verify without mutating."""
    repo = _make_repo(tmp_path, "repo")
    out = tmp_path / "out"
    out.mkdir()

    _run_check(repo, out)

    assert not (out / "map.md").exists()


# --------------------------------------------------------------------------
# The committed map
# --------------------------------------------------------------------------


def test_committed_map_is_not_stale():
    current = _COMMITTED_MAP.read_text(encoding="utf-8")
    assert (
        gen.generate_combined_map(_REPO_ROOT, _REPO_ROOT) == current
    ), ".repo-map.md is stale — run `make repo-map` and commit the result."


def test_committed_map_records_no_parse_failures():
    """Guards the whole class: a too-old interpreter degrades the map in place."""
    failures = gen.parse_failures_in(_COMMITTED_MAP.read_text(encoding="utf-8"))
    assert failures == [], (
        "the committed map is missing symbols for these files — it was "
        f"generated by an interpreter that could not parse them: {failures}"
    )


def test_committed_map_names_the_project_not_a_directory():
    header = _COMMITTED_MAP.read_text(encoding="utf-8").splitlines()[3]
    assert header == "Repository: supply-graph-ai", (
        "the map header must come from pyproject.toml; a checkout-derived name "
        "makes the drift gate unpassable for every other checkout."
    )
