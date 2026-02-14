# WF-3: OKH Generation from Repository URL

**Category**: Advanced
**Priority**: 2 (depends on WF-1 for downstream matching verification)
**Estimated Duration**: 30-120s per URL (LLM-dependent)

---

## Overview

Validates the end-to-end OKH generation pipeline: given a GitHub or GitLab repository URL, the system should extract project metadata, run the 4-layer generation engine (Direct mapping, Heuristic patterns, NLP analysis, LLM reasoning), produce a valid OKH manifest, and return a quality report.

This workflow is unique because it is **LLM-dependent** -- the generation engine's Layer 4 (LLM) and potentially Layer 3 (NLP) require external API calls. The test strategy uses **record/replay** for CI and live LLM calls for nightly/manual runs.

---

## Prerequisites

### Fixtures

- `okh_service` -- Initialized `OKHService` with `GenerationEngine` and `URLRouter` ready.
- `github_extractor` -- Initialized `GitHubExtractor` (may need `GITHUB_TOKEN` for rate limits).
- `generation_engine` -- Initialized `GenerationEngine` with all 4 layers.
- `mock_llm_responses(request)` -- Parameterized fixture that provides pre-recorded LLM responses for CI mode.

### Test Data

| Input | Role |
|-------|------|
| `https://github.com/...` (VentMon repo URL) | Real open hardware project -- ventilator monitor |
| `test-data/microlab/manifest.okh.json` | Expected output baseline for Microlab |
| `test-data/okh-ventmon-T0.4.yml` | Expected output baseline for VentMon |

### Services

- `OKHService` (orchestrates generation)
- `GenerationEngine` (4-layer manifest generation)
- `GitHubExtractor` / `GitLabExtractor` (platform-specific data extraction)
- `URLRouter` (URL validation and platform detection)
- `ManufacturingOKHValidator` (post-generation validation)

### Environment

- `GITHUB_TOKEN` -- Required for GitHub API rate limits (optional but recommended).
- LLM API key (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) -- Required for Layer 4 in live mode; not needed in mock mode.

---

## Steps

### Step 1: Validate and route URL

**Action**: Call `URLRouter().validate_url(url)` and `URLRouter().detect_platform(url)`.

**Expected result**:
- `validate_url()` returns `True` for valid GitHub/GitLab URLs.
- `detect_platform()` returns `PlatformType.GITHUB` or `PlatformType.GITLAB`.
- Invalid URLs raise `ValueError`.

### Step 2: Extract project data

**Action**: Call `GitHubExtractor().extract_project(url)`.

**Expected result**: A `ProjectData` object containing:
- `name` -- Non-empty project name
- `description` -- Project description (may be empty for minimal repos)
- `license` -- License information (if present in repo)
- `files` -- Dict of file paths to contents (README, BOMs, source files)
- `metadata` -- Platform-specific metadata (stars, topics, language, etc.)

### Step 3: Generate manifest via engine

**Action**: Call `GenerationEngine().generate_manifest_async(project_data)`.

**Expected result**: A `ManifestGeneration` object containing:
- Generated fields from all applicable layers
- Layer metadata indicating which layers contributed which fields
- A `quality_report` with overall quality assessment

### Step 4: Convert to OKH manifest

**Action**: Call `result.to_okh_manifest()` to get the OKH dict.

**Expected result**: A dictionary conforming to the OKH schema with:
- `okhv` field set (e.g., `"OKH-LOSHv1.0"`)
- `title` -- Non-empty
- `version` -- Non-empty
- `license` -- Contains at least `hardware` key
- `function` -- Non-empty description
- `manufacturing_processes` -- Non-empty list (at least inferred from project context)

### Step 5: Validate generated manifest

**Action**: Parse the manifest dict into `OKHManifest.from_dict()` and run validation.

**Expected result**:
- Manifest parses without exceptions
- Required fields are present: `title`, `version`, `license`, `function`
- `manufacturing_processes` is populated (either from explicit data or LLM inference)
- `tsdc` codes are assigned where manufacturing processes are identified

### Step 6: Assess quality report

**Action**: Inspect `result.quality_report`.

**Expected result**:
- `overall_quality` is a string (e.g., `"high"`, `"medium"`, `"low"`)
- `required_fields_complete` is a boolean
- `missing_required_fields` is a list (may be empty for high-quality repos)
- `recommendations` is a list of actionable suggestions

### Step 7 (optional): Feed into WF-1 matching

**Action**: Use the generated manifest as input to `matching_service.find_matches_with_manifest()`.

**Expected result**: If the generated manifest has `manufacturing_processes`, matching should produce at least one solution against the synthetic facility pool.

---

## Assertions

### URL Routing Assertions

```python
# Valid URLs are accepted
assert URLRouter().validate_url("https://github.com/user/repo") is True
assert URLRouter().detect_platform("https://github.com/user/repo") == PlatformType.GITHUB

# Invalid URLs are rejected
with pytest.raises(ValueError):
    await okh_service.generate_from_url("not-a-url")
with pytest.raises(ValueError):
    await okh_service.generate_from_url("https://example.com/not-a-repo")
```

### Generation Assertions

```python
# Generation succeeds
result = await okh_service.generate_from_url(repo_url)
assert result["success"] is True
assert result["manifest"] is not None

# Manifest has required fields
manifest = result["manifest"]
assert manifest.get("title"), "Generated manifest must have a title"
assert manifest.get("version"), "Generated manifest must have a version"
assert manifest.get("license"), "Generated manifest must have license info"
assert manifest.get("function"), "Generated manifest must have a function description"
```

### Quality Assertions

```python
# Quality report is present and meaningful
quality = result["quality_report"]
assert quality["overall_quality"] in ("high", "medium", "low")
assert isinstance(quality["required_fields_complete"], bool)
assert isinstance(quality["missing_required_fields"], list)
assert isinstance(quality["recommendations"], list)
```

### Manifest Parsability Assertions

```python
# Generated manifest can be parsed into OKHManifest
okh = OKHManifest.from_dict(result["manifest"])
assert isinstance(okh, OKHManifest)
assert okh.title is not None
assert okh.id is not None
```

---

## Parameterization

| Parameter Axis | Values | Rationale |
|----------------|--------|-----------|
| `repo_url` | VentMon GitHub URL, Microlab GitHub URL | Real open hardware repos with known structure |
| `llm_mode` | `live`, `mock` | Test with real LLM and with pre-recorded responses |
| `skip_review` | `True`, `False` | Test with and without review step |

```python
@pytest.mark.parametrize("repo_url,expected_title_contains", [
    ("https://github.com/PubInv/ventmon-ventilator-inline-test-monitor", "ventmon"),
    # Add more repos as baselines are established
])
@pytest.mark.parametrize("llm_mode", ["live", "mock"])
def test_okh_generation_from_url(repo_url, expected_title_contains, llm_mode, ...):
    ...
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| URL validation + routing | < 100ms | In-memory string parsing |
| Project data extraction (GitHub) | < 15s | Network call; depends on repo size and GitHub API rate limits |
| Layer 1 (Direct mapping) | < 500ms | String extraction from project data |
| Layer 2 (Heuristic) | < 1s | Pattern matching on file contents |
| Layer 3 (NLP) | < 5s | spaCy-based text analysis |
| Layer 4 (LLM) | < 60s | External API call; highly variable |
| Manifest assembly + validation | < 500ms | In-memory operations |
| Total (with LLM) | < 120s | Full pipeline including network |
| Total (mock LLM / no LLM) | < 30s | Without Layer 4 API call |

---

## LLM Handling

### CI Mode (Mocked)

- Pre-record LLM responses for each parameterized `repo_url` using a fixture.
- Store recorded responses in `tests/e2e/fixtures/llm_responses/`.
- Mock the LLM client at the generation engine level to return pre-recorded responses.
- This ensures deterministic, fast, cost-free CI runs.

### Nightly/Manual Mode (Live)

- Use real LLM API calls with actual API keys.
- Mark tests with `@pytest.mark.llm` so they can be skipped in CI.
- Compare live results against baseline expectations (fuzzy matching on fields).
- Record new responses to update the mock fixtures.

### Recording Pattern

```python
@pytest.fixture
def mock_llm_responses(request, llm_mode):
    if llm_mode == "mock":
        fixture_path = f"tests/e2e/fixtures/llm_responses/{request.param}.json"
        with open(fixture_path) as f:
            responses = json.load(f)
        with patch("src.core.generation.layers.llm.LLMLayer.generate") as mock:
            mock.return_value = responses
            yield mock
    else:
        yield None  # Use live LLM
```

---

## Edge Cases

| Scenario | Expected Behaviour |
|----------|--------------------|
| Private GitHub repo (no token) | Raises clear error about authentication, not a generic 404 |
| Repo with no README | Generation proceeds with reduced quality; quality report reflects missing data |
| Repo with no license file | `license` field in manifest is empty/null; quality report flags it |
| Non-hardware repo (e.g., a pure software project) | Generation completes but `manufacturing_processes` is empty; quality report rates low |
| Very large repo (100+ files) | Extraction respects file limits; does not timeout or OOM |
| GitLab URL (different platform) | `URLRouter` detects GitLab; `GitLabExtractor` handles platform differences |
| URL with trailing slash or extra path segments | `URLRouter` normalizes URL before extraction |

---

## Gap Flags

These items should be addressed by **Issue 1.1.2** (test dataset creation):

- [ ] Establish baseline expected outputs for 2-3 known open hardware GitHub repos. Store as JSON files in `tests/e2e/fixtures/expected_manifests/`.
- [ ] Record LLM responses for baseline repos to create mock fixtures in `tests/e2e/fixtures/llm_responses/`.
- [ ] Identify 1-2 GitLab-hosted open hardware projects for cross-platform testing.
- [ ] Create a "minimal repo" fixture (repo with just a README and one STL file) to test generation with sparse input.

---

## Pytest Mapping

- **Target file**: `tests/e2e/test_wf03_okh_generation.py`
- **Fixtures**: `okh_service`, `generation_engine`, `mock_llm_responses`
- **Markers**: `@pytest.mark.e2e`, `@pytest.mark.llm`, `@pytest.mark.slow`
- **Parameterize**: `repo_url` (2-3 URLs), `llm_mode` (`live`, `mock`)
- **Shared conftest**: `tests/e2e/conftest.py`
- **Environment**: `GITHUB_TOKEN`, LLM API keys (for live mode)
