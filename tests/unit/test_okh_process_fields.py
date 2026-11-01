"""The process list is the single source of truth for its derived copies (#562).

A manufacturing process is written three times in an OKH manifest: the
process list, ``manufacturing_specs.process_requirements``, and its TSDC code
in ``tsdc``. People edit the list; these tests pin how the other two follow it.
"""

from src.core.models.okh_process_fields import derive_process_fields


def _requirement(name, **detail):
    return {
        "process_name": name,
        "parameters": {},
        "validation_criteria": {},
        "required_tools": [],
        "notes": "",
        **detail,
    }


def test_a_removed_process_leaves_every_copy():
    """#561: 'The YAML also included "Sheet metal forming" when I had removed that.'"""
    derived = derive_process_fields(
        {
            "manufacturing_processes": ["PCB Fabrication"],
            "manufacturing_specs": {
                "process_requirements": [
                    _requirement("PCB Fabrication"),
                    _requirement("Sheet Metal Forming"),
                ]
            },
            "tsdc": ["PCB", "SHEET"],
        }
    )

    assert [
        r["process_name"]
        for r in derived["manufacturing_specs"]["process_requirements"]
    ] == ["PCB Fabrication"]
    assert derived["tsdc"] == ["PCB"]


def test_a_listed_process_gains_its_requirement_and_code():
    derived = derive_process_fields(
        {
            "manufacturing_processes": ["PCB Fabrication", "3D Printing"],
            "manufacturing_specs": {"process_requirements": []},
            "tsdc": [],
        }
    )

    assert derived["manufacturing_specs"]["process_requirements"] == [
        _requirement("PCB Fabrication"),
        _requirement("3D Printing"),
    ]
    assert derived["tsdc"] == ["PCB", "3DP"]


def test_detail_on_a_kept_process_survives():
    kept = _requirement("pcb", required_tools=["reflow oven"], notes="2-layer")
    derived = derive_process_fields(
        {
            "manufacturing_processes": ["PCB Fabrication"],
            "manufacturing_specs": {"process_requirements": [kept]},
        }
    )

    assert derived["manufacturing_specs"]["process_requirements"] == [kept]


def test_codes_that_are_not_process_codes_are_kept():
    derived = derive_process_fields(
        {"manufacturing_processes": ["PCB Fabrication"], "tsdc": ["NOT-A-PROCESS"]}
    )

    assert derived["tsdc"] == ["NOT-A-PROCESS", "PCB"]


def test_a_process_outside_the_taxonomy_gets_a_requirement_but_no_code():
    derived = derive_process_fields(
        {
            "manufacturing_processes": ["Hand weaving"],
            "manufacturing_specs": {"process_requirements": []},
            "tsdc": [],
        }
    )

    assert derived["manufacturing_specs"]["process_requirements"] == [
        _requirement("Hand weaving")
    ]
    assert derived["tsdc"] == []


def test_a_manifest_without_specs_does_not_grow_them():
    derived = derive_process_fields({"manufacturing_processes": ["PCB Fabrication"]})

    assert "manufacturing_specs" not in derived
    assert derived["tsdc"] == ["PCB"]


def test_an_empty_process_list_derives_nothing():
    """No list means nothing to derive from — OKH-LOSH imports may carry their
    processes only as TSDC codes, and those must not be wiped."""
    manifest = {
        "manufacturing_processes": [],
        "manufacturing_specs": {"process_requirements": [_requirement("CNC")]},
        "tsdc": ["CNC"],
    }

    assert derive_process_fields(manifest) == manifest


def test_the_input_is_not_mutated():
    manifest = {"manufacturing_processes": ["PCB Fabrication"], "tsdc": ["SHEET"]}

    derive_process_fields(manifest)

    assert manifest["tsdc"] == ["SHEET"]


def test_process_entries_given_as_objects_are_read_by_name():
    derived = derive_process_fields(
        {"manufacturing_processes": [{"name": "PCB Fabrication"}], "tsdc": ["SHEET"]}
    )

    assert derived["tsdc"] == ["PCB"]
