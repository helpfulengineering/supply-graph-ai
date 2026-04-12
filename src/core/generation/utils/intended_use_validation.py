"""
Heuristics for filtering bad ``intended_use`` values.

Only the LLM layer may set ``intended_use``; the generation engine drops any other
source. These checks apply to LLM output (and partial-JSON recovery) only.
"""


def is_obvious_noise_intended_use(value: str) -> bool:
    """README cross-refs, truncated markdown, and dependency blurbs."""
    v = value.strip()
    if not v:
        return True
    vl = v.lower()
    markers = (
        "please see",
        "see [",
        "description is in the",
        "better than nothing",
        "previous major version",
        "devices of this project",
    )
    if any(m in vl for m in markers):
        return True
    if "readme" in vl:
        return True
    tail = v.rstrip()
    if tail.endswith("[") or tail.endswith("(see"):
        return True
    if tail.count("(") > tail.count(")"):
        return True
    return False
