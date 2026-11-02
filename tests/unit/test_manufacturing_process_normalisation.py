"""A generated process list contains only taxonomy processes (#564)."""

from src.core.generation.engine import GenerationEngine


def test_a_process_the_taxonomy_does_not_know_is_dropped() -> None:
    """A manufacturing-sounding word is not a process.

    "bend the tabs" and "cast the housing" used to be kept, title-cased,
    because they contained "bend" and "cast".
    """
    got = GenerationEngine()._normalize_manufacturing_processes(
        [
            "PCB Fabrication",
            "3d printing",
            "bend the tabs",
            "cast the housing",
            "pcb fabrication",
        ]
    )
    assert got == ["PCB Fabrication", "3D Printing"]
