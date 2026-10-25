"""Verify one native read_evidence call; no retrieval or agent loop."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic, perf_counter
from uuid import uuid4

from app.llm import GeminiProvider, ProviderError, create_client
from app.schemas import EvidenceRead, SourceDocument

ROOT = Path(__file__).resolve().parents[1]
QUESTION = "What percentage of the total oil and gas MMBoe comes from Canada?"
DESCRIPTION = (
    "Read one or two numeric cells from the supplied report, returning original values and labels."
)


def run_check(provider, source, instruction, report, destination):
    started = perf_counter()

    def save():
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    save()
    try:
        arguments, call = provider.request_tool(
            source.model_input(QUESTION),
            EvidenceRead,
            tool_name="read_evidence",
            description=DESCRIPTION,
            run_id=report["run_id"],
            instruction=instruction,
            deadline=monotonic() + 60,
            metadata={
                "prompt_version": "tool-call-check-v1",
                "source_id": source.filename,
                "source_sha256": sha256(source.model_dump_json().encode()).hexdigest(),
                "code_sha256": sha256(
                    b"".join(
                        (ROOT / name).read_bytes()
                        for name in ("app/llm.py", "app/schemas.py", "scripts/check_tool_call.py")
                    )
                ).hexdigest(),
            },
        )
        report["call"] = call
        report["tool_event"] = {
            "name": "read_evidence",
            "arguments": arguments.model_dump(),
            "status": "blocked",
        }
        # The tool can read this in-memory source only; there is no dynamic dispatch or file access.
        report["tool_event"]["result"] = source.read_evidence(arguments.cell_ids)
        report["tool_event"]["status"] = "executed"
        report["status"] = "passed"
    except ProviderError as error:
        report.update(status="failed", error_code=str(error), call=error.record)
    except ValueError:
        report.update(status="failed", error_code="invalid_evidence_or_input")
    report["duration_seconds"] = round(perf_counter() - started, 3)
    save()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow one hosted generation request.")
    if not parser.parse_args().live:
        parser.error("Pass --live to allow one hosted request; no requests were sent.")
    source = SourceDocument.model_validate_json(
        (ROOT / "data/samples/finqa-b01-source.json").read_text(encoding="utf-8")
    )
    instruction = (ROOT / "prompts/tool_call_check.md").read_text(encoding="utf-8")
    run_id = str(uuid4())
    destination = ROOT / "data/local/tool-checks" / f"{run_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run_id,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "check_version": "native-tool-call-v1",
        "scope": "One generation request and at most one local evidence read; no agent loop or tool-result continuation.",
        "status": "started",
        "max_model_requests": 1,
        "max_tool_executions": 1,
        "question": QUESTION,
        "tool_event": None,
    }
    with create_client() as client:
        run_check(GeminiProvider(client), source, instruction, report, destination)

    # References score the completed run; they never select the evidence supplied to the model.
    reviewed = json.loads(
        (ROOT / "evals/cases/finqa-b01-reviewed.json").read_text(encoding="utf-8")
    )
    expected = next(case for case in reviewed["cases"] if case["key"] == "ratio")
    expected_ids = {source.cell_id(*operand["cell"]) for operand in expected["operands"]}
    actual_ids = {cell["cell_id"] for cell in (report.get("tool_event") or {}).get("result", [])}
    report["matches_reviewed_cells"] = report["status"] == "passed" and actual_ids == expected_ids
    if not report["matches_reviewed_cells"]:
        report.update(status="failed", error_code=report.get("error_code", "wrong_evidence"))
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Local record: {destination.relative_to(ROOT).as_posix()}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
