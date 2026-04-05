import json
from pathlib import Path
from urllib import request


def main() -> None:
    base = Path("synthetic_data/okh")
    url = "http://localhost:8001/v1/api/match"
    headers = {"Content-Type": "application/json"}

    checked = 0
    found_file = None
    found_body = None

    for fp in sorted(base.glob("*.json")):
        checked += 1
        okh = json.loads(fp.read_text())
        payload = {
            "okh_manifest": okh,
            "max_depth": 0,
            "allow_facility_combinations": True,
            "max_facilities_per_solution": 3,
            "combination_strategy": "greedy",
            "return_alternative_solutions": True,
            "min_confidence": 0.0,
            "max_results": 10,
        }
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue

        data = body.get("data", {})
        summary = data.get("match_summary", {}) or {}
        if summary.get("facility_combination_applied") is True:
            found_file = fp
            found_body = body
            break

    print(f"checked={checked}")
    if found_file is None or found_body is None:
        print("found=none")
        return

    out = Path("tmp/step2-composite-applied-search-response.json")
    out.write_text(json.dumps(found_body, indent=2, default=str))
    summary = found_body.get("data", {}).get("match_summary", {}) or {}

    print(f"found_file={found_file}")
    print(f"saved_response={out}")
    print(
        "summary="
        + json.dumps(
            {
                "facility_combination_requested": summary.get(
                    "facility_combination_requested"
                ),
                "facility_combination_applied": summary.get(
                    "facility_combination_applied"
                ),
                "coverage_complete": summary.get("coverage_complete"),
                "matched_count": summary.get("matched_count"),
                "required_count": summary.get("required_count"),
            }
        )
    )


if __name__ == "__main__":
    main()
