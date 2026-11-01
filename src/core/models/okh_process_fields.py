"""Derive an OKH manifest's process copies from its process list (#562).

A manufacturing process is written three times in a manifest: the
``manufacturing_processes`` list, ``manufacturing_specs.process_requirements``,
and its TSDC code in ``tsdc``. People edit the list, so the other two follow
it on every local write. Apply this to what is about to be stored, never to
what is already stored: these fields are inside the content hash.
"""

import copy
from typing import Any, Dict, List, Optional

from ..taxonomy.process_taxonomy import taxonomy
from .okh import OKHManifest

_process_name = OKHManifest._coerce_process_list_entry


def _key(name: str) -> str:
    return taxonomy.normalize(name) or name.strip().lower()


def _tsdc_for(name: str) -> Optional[str]:
    canonical = taxonomy.normalize(name)
    return (canonical and taxonomy.get_tsdc_code(canonical)) or None


def _process_code(code: Any) -> Optional[str]:
    """The TSDC code ``code`` is, if it is one that names a process."""
    tsdc = isinstance(code, str) and _tsdc_for(code)
    return tsdc if tsdc and tsdc.upper() == code.strip().upper() else None


def _bare_requirement(name: str) -> Dict[str, Any]:
    return {
        "process_name": name,
        "parameters": {},
        "validation_criteria": {},
        "required_tools": [],
        "notes": "",
    }


def _derive_requirements(names: List[str], existing: List[Any]) -> List[Any]:
    by_key: Dict[str, List[Any]] = {}
    for requirement in existing:
        name = _process_name(requirement)
        if name:
            by_key.setdefault(_key(name), []).append(requirement)
    derived: List[Any] = []
    seen = set()
    for name in names:
        key = _key(name)
        if key in seen:
            continue
        seen.add(key)
        derived.extend(by_key.get(key) or [_bare_requirement(name)])
    return derived


def _derive_tsdc(names: List[str], existing: List[Any]) -> List[str]:
    wanted = list(dict.fromkeys(c for c in map(_tsdc_for, names) if c))
    kept = [c for c in existing if _process_code(c) in (None, *wanted)]
    return kept + [c for c in wanted if c not in kept]


def derive_process_fields(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``manifest`` whose process copies match its process list.

    Requirements for listed processes keep their detail; requirements for
    unlisted ones go, and listed ones without a requirement get a bare one.
    TSDC codes that name a process follow the list; other codes are kept. An
    empty list derives nothing — some sources (OKH-LOSH imports) carry their
    processes only as TSDC codes, and those must not be wiped.
    """
    names = [
        n
        for n in (
            _process_name(e) for e in manifest.get("manufacturing_processes") or []
        )
        if n
    ]
    if not names:
        return manifest
    derived = copy.deepcopy(manifest)
    specs = derived.get("manufacturing_specs")
    if isinstance(specs, dict):
        specs["process_requirements"] = _derive_requirements(
            names, specs.get("process_requirements") or []
        )
    derived["tsdc"] = _derive_tsdc(names, derived.get("tsdc") or [])
    return derived
