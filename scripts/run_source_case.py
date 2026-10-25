"""Run the controlled B03 source case; no retrieval or numerical answer generation."""

import argparse
import json
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import monotonic
from uuid import uuid4

from app.llm import GeminiProvider, ProviderError, create_client
from app.schemas import CellSelection, SourceDocument

ROOT = Path(__file__).resolve().parents[1]
QUESTION = "what percentage of the total oil and gas mmboe comes from canada?"
MISSING_QUESTION = "What percentage of total actual production in MMBoe came from Canada in 2035?"


def run_source_case(provider, source, question, instruction, deadline):
    run_id = str(uuid4())
    plan, call = provider.generate_json(
        source.model_input(question),
        CellSelection,
        run_id=run_id,
        instruction=instruction,
        deadline=deadline,
        metadata={
            "prompt_version": "cell-selection-v1",
            "source_id": source.filename,
            "source_sha256": sha256(source.model_dump_json().encode()).hexdigest(),
            "code_sha256": sha256(
                b"".join(
                    (ROOT / path).read_bytes()
                    for path in ("app/llm.py", "app/schemas.py", "scripts/run_source_case.py")
                )
            ).hexdigest(),
        },
    )
    result = {"run_id": run_id, "plan": plan.model_dump(), "call": call}
    try:
        result["resolved_evidence"] = source.resolve_selection(plan)
        result["status"] = "references_validated"
    except ValueError:
        result.update(status="failed", error_code="invalid_cell_reference")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow hosted generation requests.")
    parser.add_argument("--repetitions", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--scenario", choices=("ratio", "missing-period"), default="ratio")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to allow hosted requests; no requests were sent.")
    source = SourceDocument.model_validate_json(
        (ROOT / "data/samples/finqa-b01-source.json").read_text(encoding="utf-8")
    )
    instruction = (ROOT / "prompts/cell_selection.md").read_text(encoding="utf-8")
    results = []
    deadline = monotonic() + 60
    question = QUESTION if args.scenario == "ratio" else MISSING_QUESTION
    with create_client() as client:
        provider = GeminiProvider(client)
        for _ in range(args.repetitions):
            try:
                results.append(run_source_case(provider, source, question, instruction, deadline))
                if results[-1]["status"] == "failed":
                    break
            except ProviderError as error:
                results.append(
                    {"run_id": error.record["run_id"], "status": "failed", "call": error.record}
                )
                break

    # The evaluator reads expected cells only after all model requests have finished.
    reviewed = json.loads(
        (ROOT / "evals/cases/finqa-b01-reviewed.json").read_text(encoding="utf-8")
    )
    expected = next(case for case in reviewed["cases"] if case["key"] == "ratio")
    expected_ids = [source.cell_id(*operand["cell"]) for operand in expected["operands"]]
    for result in results:
        plan = result.get("plan", {})
        result["matches_reviewed_selection"] = (
            plan.get("status") == "ready"
            and plan.get("operation") == expected["operation"]
            and plan.get("cell_ids") == expected_ids
        )
        result["matches_expected_outcome"] = (
            result["matches_reviewed_selection"]
            if args.scenario == "ratio"
            else plan.get("status") == "insufficient_evidence"
        )
    durations = [r["call"]["duration_seconds"] for r in results if r["call"]["status"] == "passed"]
    report = {
        "scope": "Controlled source selection only; not retrieval, calculation or a benchmark.",
        "question": question,
        "scenario": args.scenario,
        "source_id": source.filename,
        "requested_repetitions": args.repetitions,
        "results": results,
        "median_generation_seconds": median(durations) if durations else None,
        "latency_gate_met": len(durations) == 3 and median(durations) <= 5,
        "all_selections_match": len(results) == args.repetitions
        and all(r["matches_expected_outcome"] for r in results),
    }
    destination = ROOT / "data/local/source-case-pilots" / f"{uuid4()}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Local record: {destination.relative_to(ROOT).as_posix()}")
    return 0 if report["all_selections_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
