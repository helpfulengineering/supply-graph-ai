"""Shared contract for triage loop modules.

Every module implements four stages — discover → observe → judge → report —
so loops can be enabled independently and still emit a uniform Finding feed
for triage (bug / perf / gap).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable


class FindingKind(str, Enum):
    """Category of triage signal."""

    BUG = "bug"
    PERF = "perf"
    GAP = "gap"


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class LoopStatus(str, Enum):
    """Whether a module is still a stub or is producing real judgements."""

    STUB = "stub"
    ONLINE = "online"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Finding:
    """One triage-ready signal produced by a loop module."""

    module: str
    kind: FindingKind
    severity: Severity
    title: str
    evidence: dict[str, Any] = field(default_factory=dict)
    suggested_state: str = "needs-triage"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["severity"] = self.severity.value
        return d


@dataclass
class Inventory:
    """What the module knows exists (static catalog)."""

    items: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class Observations:
    """Live or computed signal payload for a single loop tick."""

    data: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class LoopReport:
    """Uniform output of one module tick."""

    module: str
    status: LoopStatus
    findings: list[Finding] = field(default_factory=list)
    inventory: Optional[Inventory] = None
    observations: Optional[Observations] = None
    summary: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """True when the loop ran and produced no error-severity findings."""
        if self.status == LoopStatus.FAILED:
            return False
        if self.status == LoopStatus.STUB:
            return True  # stubs never fail the harness
        return not any(f.severity == Severity.ERROR for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "status": self.status.value,
            "ok": self.ok,
            "summary": self.summary,
            "error": self.error,
            "findings": [f.to_dict() for f in self.findings],
            "inventory": asdict(self.inventory) if self.inventory else None,
            "observations": asdict(self.observations) if self.observations else None,
        }


@runtime_checkable
class LoopModule(Protocol):
    """Loadable triage loop. Implementers live under ``harness.modules``."""

    name: str
    status: LoopStatus

    def discover(self) -> Inventory:
        """Enumerate the static surface this loop watches."""
        ...

    def observe(self) -> Observations:
        """Collect live signals or compute diffs for this tick."""
        ...

    def judge(self, observations: Observations) -> list[Finding]:
        """Turn observations into triage findings."""
        ...

    def run(self) -> LoopReport:
        """Execute one full tick: discover → observe → judge → report."""
        ...
