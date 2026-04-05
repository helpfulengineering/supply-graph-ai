import json
import subprocess
import time
from pathlib import Path


TARGETS = [
    {
        "id": "covid-gliax-faceshield",
        "url": "https://github.com/GliaX/faceshield",
    },
    {
        "id": "covid-respiraworks-ventilator",
        "url": "https://github.com/RespiraWorks/Ventilator",
    },
    {
        "id": "covid-ventmon-inline-monitor",
        "url": "https://github.com/PubInv/ventmon-ventilator-inline-test-monitor",
    },
]


def run_cmd(args: list[str], timeout: int = 900) -> dict:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        elapsed = round(time.perf_counter() - start, 2)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "seconds": elapsed,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.perf_counter() - start, 2)
        return {
            "ok": False,
            "returncode": None,
            "stdout": (exc.stdout or ""),
            "stderr": (exc.stderr or ""),
            "seconds": elapsed,
            "error": "timeout",
        }


def summarize_match(match_path: Path) -> dict:
    try:
        payload = json.loads(match_path.read_text())
    except Exception as exc:
        return {"error": f"failed_to_parse_match_json: {exc}"}
    return {
        "total_solutions": payload.get("total_solutions"),
        "matching_mode": payload.get("matching_mode"),
        "match_summary": payload.get("match_summary", {}),
    }


def main() -> None:
    out_root = Path("tmp/step3")
    out_root.mkdir(parents=True, exist_ok=True)

    rows = []
    for target in TARGETS:
        rid = target["id"]
        repo_dir = out_root / rid
        repo_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = repo_dir / "manifest.okh.json"
        match_path = repo_dir / "match.json"

        row = {
            "id": rid,
            "url": target["url"],
            "generation": {},
            "matching": {},
            "status": "pending",
            "failure_notes": [],
        }

        gen_cmd = [
            "conda",
            "run",
            "-n",
            "supply-graph-ai",
            "ohm",
            "--verbose",
            "okh",
            "generate-from-url",
            target["url"],
            "--clone",
            "--no-review",
            "--format",
            "okh",
            "-o",
            str(repo_dir),
        ]
        gen = run_cmd(gen_cmd, timeout=1200)
        row["generation"] = {
            "ok": gen["ok"],
            "seconds": gen["seconds"],
            "returncode": gen["returncode"],
        }
        (repo_dir / "generation.stdout.log").write_text(gen["stdout"] or "")
        (repo_dir / "generation.stderr.log").write_text(gen["stderr"] or "")

        if not gen["ok"] or not manifest_path.exists():
            row["status"] = "generation_failed"
            row["failure_notes"].append(
                "Manifest generation failed or manifest.okh.json not produced."
            )
            rows.append(row)
            continue

        match_cmd = [
            "conda",
            "run",
            "-n",
            "supply-graph-ai",
            "ohm",
            "--verbose",
            "match",
            "requirements",
            str(manifest_path),
            "--allow-facility-combinations",
            "--max-facilities-per-solution",
            "3",
            "--json",
            "--output",
            str(match_path),
        ]
        match = run_cmd(match_cmd, timeout=900)
        row["matching"] = {
            "ok": match["ok"],
            "seconds": match["seconds"],
            "returncode": match["returncode"],
        }
        (repo_dir / "match.stdout.log").write_text(match["stdout"] or "")
        (repo_dir / "match.stderr.log").write_text(match["stderr"] or "")

        if not match["ok"] or not match_path.exists():
            row["status"] = "matching_failed"
            row["failure_notes"].append(
                "Matching command failed or match.json not produced."
            )
            rows.append(row)
            continue

        match_summary = summarize_match(match_path)
        row["matching"]["result_summary"] = match_summary
        if match_summary.get("total_solutions", 0) == 0:
            row["status"] = "no_matches"
            row["failure_notes"].append(
                "Pipeline completed but returned zero matching solutions."
            )
        else:
            row["status"] = "ok"

        rows.append(row)

    report = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "targets": rows,
        "totals": {
            "ok": sum(1 for r in rows if r["status"] == "ok"),
            "generation_failed": sum(
                1 for r in rows if r["status"] == "generation_failed"
            ),
            "matching_failed": sum(1 for r in rows if r["status"] == "matching_failed"),
            "no_matches": sum(1 for r in rows if r["status"] == "no_matches"),
        },
    }

    report_path = out_root / "step3-pipeline-report.json"
    report_path.write_text(json.dumps(report, indent=2))

    lines = [
        "# Step 3 Pipeline Failure Notes",
        "",
        f"Report: `{report_path}`",
        "",
        "## Results",
        "",
    ]
    for r in rows:
        lines.append(
            f"- `{r['id']}`: `{r['status']}` "
            f"(generation: {r['generation'].get('seconds', 'n/a')}s, "
            f"matching: {r['matching'].get('seconds', 'n/a')}s)"
        )
        for note in r.get("failure_notes", []):
            lines.append(f"  - note: {note}")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    for k, v in report["totals"].items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")

    notes_path = out_root / "step3-failure-notes.md"
    notes_path.write_text("\n".join(lines))
    print(f"wrote {report_path}")
    print(f"wrote {notes_path}")


if __name__ == "__main__":
    main()
