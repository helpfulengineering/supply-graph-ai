"""Multi-loop triage harness for post-deploy verification.

Each loop (parity, RED, synthetic smoke, client drift) is a loadable module
that implements the shared ``LoopModule`` protocol. Modules come online
independently; the runner starts whichever are enabled in
``harness.config.json``.
"""

from harness.protocol import Finding, LoopReport, LoopStatus

__all__ = ["Finding", "LoopReport", "LoopStatus"]
