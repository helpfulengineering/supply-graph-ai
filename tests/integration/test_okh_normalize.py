"""POST /api/okh/normalize: the derived process copies, without storing (#562).

The Generate editor builds its download in the browser, so it asks the node
for the derived copies rather than carrying a second copy of the taxonomy.
"""


def test_normalize_returns_the_derived_copies_without_an_account(client):
    draft = {
        "title": "Frugal IoT sensor",
        "manufacturing_processes": ["PCB Fabrication"],
        "manufacturing_specs": {
            "process_requirements": [
                {"process_name": "PCB Fabrication"},
                {"process_name": "Sheet Metal Forming"},
            ]
        },
        "tsdc": ["PCB", "SHEET"],
    }

    resp = client.post("/api/okh/normalize", json={"content": draft})

    assert resp.status_code == 200, resp.text
    content = resp.json()["content"]
    assert content["title"] == "Frugal IoT sensor"
    assert content["tsdc"] == ["PCB"]
    assert [
        r["process_name"]
        for r in content["manufacturing_specs"]["process_requirements"]
    ] == ["PCB Fabrication"]
