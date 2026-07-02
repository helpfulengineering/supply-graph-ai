"""Verify the local dev environment is fully provisioned.

Fails loudly when a historically fragile dependency is missing, so a broken
environment is caught at setup time (or by `make ready`) instead of silently
degrading at runtime. Currently checks the spaCy model — the dependency that
repeatedly went missing under uv's exact sync before it was pinned in uv.lock.

Run: uv run python scripts/verify_dev_env.py  (or `make setup` / `make verify-env`)
"""

from __future__ import annotations

import sys


def check_spacy_model() -> str:
    """Assert the spaCy English model actually loads; return a version string."""
    from src.core.nlp import load_spacy_english

    nlp = load_spacy_english()
    if nlp is None:
        raise RuntimeError(
            "spaCy English model failed to load. It is a locked dependency — "
            "run `make setup` to (re)provision the environment."
        )
    meta = getattr(nlp, "meta", {})
    # spaCy stores lang and name separately; the canonical model id joins them
    # (e.g. lang="en", name="core_web_md" -> "en_core_web_md").
    lang, name = meta.get("lang"), meta.get("name", "unknown")
    full_name = f"{lang}_{name}" if lang else name
    return f"{full_name} {meta.get('version', '?')}"


def main() -> int:
    ok = True
    for label, fn in [("spaCy NLP model", check_spacy_model)]:
        try:
            print(f"OK    {label}: {fn()}")
        except Exception as exc:  # report any failure clearly
            print(f"FAIL  {label}: {exc}")
            ok = False
    print("\nEnvironment OK." if ok else "\nVerification failed. Run `make setup`.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
