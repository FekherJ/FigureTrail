"""Initial fixed-workflow campaign; references are opened only after execution."""

import argparse
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from statistics import median
from time import perf_counter
from uuid import uuid4

from app.corpus import write_atomic
from app.embeddings import EmbeddingCache
from app.llm import GeminiProvider, JOURNAL, LIMIT_EUR, create_client
from app.retrieval import load_current, query_input
from app.service import analyze
from evals.retrieval import Queries

ROOT = Path(__file__).resolve().parents[1]
NEGATIVE_CASES = [
    {
        "id": "N01",
        "question": "What percentage of total actual production in MMBoe came from Canada in 2035?",
        "report_ids": None,
        "expected_status": "insufficient_evidence",
    },
    {
        "id": "N02",
        "question": "What is the compound annual growth rate (CAGR) in annual Cabinets segment net sales from 2015 to 2017?",
        "report_ids": None,
        "expected_status": "unsupported_request",
    },
]


def score(results, references):
    positive = [item for item in results if item["case_id"].startswith("C")]
    if len(positive) != len(references["cases"]):
        raise ValueError("Evaluation/reference case counts differ.")
    for index, (item, reference) in enumerate(zip(positive, references["cases"], strict=True), 1):
        if (
            item["case_id"] != f"C{index:02d}"
            or item["question"] != reference["application_question"]
        ):
            raise ValueError("Evaluation/reference questions differ.")
        source_id = re.fullmatch(r"(.+\.pdf)-\d+", reference["case_id"])[1]
        expected_ids = [
            f"{source_id}#table[{cell['cell'][0]}][{cell['cell'][1]}]"
            for cell in reference["operands"]
        ]
        selection, calculation = item.get("selection") or {}, item.get("calculation") or {}
        evaluation = {
            "expected_cell_ids": expected_ids,
            "expected_operation": reference["operation"],
            "expected_percent": reference["expected_percent"],
            "tolerance": reference["exe_ans_tolerance"],
            "ordered_cells_correct": selection.get("cell_ids") == expected_ids,
            "operation_correct": selection.get("operation") == reference["operation"],
            "numeric_within_tolerance": bool(calculation)
            and abs(Decimal(calculation["value"]) - Decimal(reference["expected_percent"]))
            <= Decimal(reference["exe_ans_tolerance"]),
        }
        evaluation["correct_answer"] = item["status"] == "success" and all(
            evaluation[key]
            for key in ("ordered_cells_correct", "operation_correct", "numeric_within_tolerance")
        )
        item["evaluation"] = evaluation
    negatives = [item for item in results if item["case_id"].startswith("N")]
    for item, case in zip(negatives, NEGATIVE_CASES, strict=True):
        item["evaluation"] = {
            "expected_status": case["expected_status"],
            "correct_outcome": item["status"] == case["expected_status"]
            and item.get("calculation") is None,
        }
    return {
        "development_cases": len(positive),
        "correct_answers": sum(item["evaluation"]["correct_answer"] for item in positive),
        "answer_successes": sum(item["status"] == "success" for item in positive),
        "answer_abstentions": sum(
            item["status"] in ("insufficient_evidence", "unsupported_request") for item in positive
        ),
        "blocked": sum(item["status"] == "blocked" for item in positive),
        "technical_failures": sum(item["status"] == "failed" for item in positive),
        "median_development_seconds": median(item["duration_seconds"] for item in positive),
        "negative_cases": len(negatives),
        "correct_negative_outcomes": sum(
            item["evaluation"]["correct_outcome"] for item in negatives
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to allow at most twelve generations. No requests were sent.")
    fixture_path = ROOT / "evals/queries/finqa-b05.json"
    fixture = Queries.model_validate_json(fixture_path.read_bytes())
    retriever = load_current(
        ROOT, query_cache=EmbeddingCache(ROOT / "data/local/query-embeddings.sqlite")
    )
    for query in fixture.cases:
        retriever.validate_request(query.question, "semantic", 5, query.report_ids)
        if retriever.query_cache.get(query_input(query.question)) is None:
            raise ValueError("Complete B05 query caching before this generation-only campaign.")
    with closing(sqlite3.connect(JOURNAL)) as database:
        allowance = sum(
            (Decimal(row[0]) for row in database.execute("SELECT allowance_eur FROM calls")),
            Decimal(0),
        )
    maximum = len(fixture.cases) + len(NEGATIVE_CASES)
    if allowance + maximum > LIMIT_EUR:
        raise ValueError("Campaign reservations exceed the local allowance limit.")
    run_id = str(uuid4())
    path = ROOT / f"evals/results/local/analysis/{run_id}.json"
    report = {
        "run_id": run_id,
        "status": "started",
        "partition": "development",
        "query_fixture_sha256": sha256(fixture_path.read_bytes()).hexdigest(),
        "plan": {
            "maximum_generation_requests": maximum,
            "embedding_requests": 0,
            "additional_allowance_reservation_eur": str(maximum),
            "current_allowance_eur": str(allowance),
        },
        "results": [],
    }

    def save():
        write_atomic(path, json.dumps(report, indent=2).encode())

    print(json.dumps({"plan": report["plan"]}), flush=True)
    save()
    with create_client() as client:
        provider = GeminiProvider(client)
        cases = [
            (query.id, query.question, query.report_ids, "semantic") for query in fixture.cases
        ]
        cases += [
            (item["id"], item["question"], item["report_ids"], "lexical") for item in NEGATIVE_CASES
        ]
        for case_id, question, scope, method in cases:
            started = perf_counter()
            try:
                result = analyze(question, retriever, provider, method=method, report_ids=scope)
            except (OSError, sqlite3.Error, ValueError) as error:
                result = {
                    "question": question,
                    "status": "failed",
                    "calculation": None,
                    "error_type": type(error).__name__,
                    "error_code": "analysis_or_recording_failed",
                    "duration_seconds": perf_counter() - started,
                }
            report["results"].append({"case_id": case_id, **result})
            save()
            print(
                json.dumps(
                    {
                        "case_id": case_id,
                        "status": result["status"],
                        "error_code": result["error_code"],
                        "display": (result.get("calculation") or {}).get("display"),
                    }
                ),
                flush=True,
            )
            if result.get("error_code") == "analysis_or_recording_failed":
                # Do not keep sending requests if a trace cannot be durably recorded.
                for remaining_id, remaining_question, _, _ in cases[len(report["results"]) :]:
                    report["results"].append(
                        {
                            "case_id": remaining_id,
                            "question": remaining_question,
                            "status": "blocked",
                            "error_code": "campaign_recording_failure",
                            "calculation": None,
                            "duration_seconds": 0,
                        }
                    )
                break
    save()
    reference_path = ROOT / "evals/cases/finqa-b01-reviewed.json"
    report["reference_sha256"] = sha256(reference_path.read_bytes()).hexdigest()
    report["metrics"] = score(
        report["results"], json.loads(reference_path.read_text(encoding="utf-8"))
    )
    report["status"] = "completed"
    save()
    print(
        json.dumps(
            {
                "run_id": run_id,
                "path": path.relative_to(ROOT).as_posix(),
                "metrics": report["metrics"],
            },
            indent=2,
        )
    )
    return (
        0 if not any(item["status"] in ("failed", "blocked") for item in report["results"]) else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
