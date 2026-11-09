"""Plan/run fixed-workflow evaluations or compare matched saved reports offline."""

import argparse
from collections import Counter
from contextlib import closing
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from datetime import datetime
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import re
import sqlite3
from statistics import median
from time import perf_counter, sleep, time
from uuid import uuid4

from app.corpus import digest, write_atomic
from app.embeddings import EmbeddingCache, EmbeddingPacer, input_key
from app.llm import (
    EMBEDDING_ALLOWANCE_EUR,
    GENERATION_ALLOWANCE_EUR,
    GeminiProvider,
    JOURNAL,
    LIMIT_EUR,
    create_client,
)
from app.retrieval import load_current, query_input
from app.service import CONFIGURATION, analyze, execution_identity
from evals.retrieval import Queries

ROOT = Path(__file__).resolve().parents[1]
SCORING_POLICY = {
    "version": "analysis-evaluation-v2",
    "numeric_tolerance": "reference absolute tolerance in percentage points",
    "correct_answer": "success, complete proof, ordered cells, operation, finite value and known units/scales/years",
    "negative_outcome": "exact expected status and no calculation",
    "denominators": "all planned cases, including failures and unattempted blocks",
    "latency": "analysis attempts exclude campaign pacing, include failures; nearest-rank p95",
    "case_order": "positive fixture order, then negative fixture order",
}
# Keep headroom below the observed 15 RPM free-tier generation quota.
GENERATION_RPM = 12
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


def finite_number(value):
    try:
        number = Decimal(value)
        return number if number.is_finite() else None
    except InvalidOperation, TypeError, ValueError:
        return None


def provider_metrics(results):
    """Count this campaign's call records; cached historical calls are not new usage."""
    calls = {}
    for item in results:
        embedding = ((item.get("retrieval") or {}).get("query_embedding") or {}).get("call")
        for call in (item.get("call"), embedding):
            if call and call.get("call_id"):
                calls[call["call_id"]] = call
    calls = list(calls.values())
    unknown_cost = sum(call.get("estimated_paid_cost_usd") is None for call in calls)
    known_cost = sum(
        (
            Decimal(call["estimated_paid_cost_usd"])
            for call in calls
            if call.get("estimated_paid_cost_usd") is not None
        ),
        Decimal(0),
    )
    tokens = {}
    for field in ("input_tokens", "output_tokens", "thought_tokens", "total_tokens"):
        values = [(call.get("usage") or {}).get(field) for call in calls]
        tokens[field] = sum(values) if all(type(value) is int for value in values) else None
    return {
        "call_records": len(calls),
        "generation_records": sum(call["kind"] == "generation" for call in calls),
        "embedding_records": sum(call["kind"] == "embedding" for call in calls),
        "reported_tokens": tokens,
        "calls_with_unknown_usage": sum(
            type((call.get("usage") or {}).get("total_tokens")) is not int for call in calls
        ),
        "known_estimated_paid_cost_usd": str(known_cost),
        "calls_with_unknown_cost": unknown_cost,
        "estimated_paid_cost_usd": str(known_cost) if not unknown_cost else None,
        "actual_charge_eur": None,
    }


def score(results, references):
    """Score only after execution; references never become analysis inputs."""
    positive = [item for item in results if item["case_id"].startswith("C")]
    negatives = [item for item in results if item["case_id"].startswith("N")]
    if (
        not positive
        or len(positive) != len(references["cases"])
        or len(negatives) != len(NEGATIVE_CASES)
        or len(results) != len(positive) + len(negatives)
    ):
        raise ValueError("Evaluation/reference case counts differ.")
    for index, (item, reference) in enumerate(zip(positive, references["cases"], strict=True), 1):
        if (
            item["case_id"] != f"C{index:02d}"
            or item["question"] != reference["application_question"]
        ):
            raise ValueError("Evaluation/reference questions or case IDs differ.")
        match = re.fullmatch(r"(.+\.pdf)-\d+", reference["case_id"])
        if not match:
            raise ValueError("Invalid reference source ID.")
        expected_ids = [
            f"{match[1]}#table[{cell['cell'][0]}][{cell['cell'][1]}]"
            for cell in reference["operands"]
        ]
        selection, calculation = item.get("selection") or {}, item.get("calculation") or {}
        hits = (item.get("retrieval") or {}).get("hits", [])[: CONFIGURATION["k"]]
        found = {cell_id for hit in hits for cell_id in hit["cell_ids"]}
        expected = finite_number(reference["expected_percent"])
        tolerance = finite_number(reference["exe_ans_tolerance"])
        if expected is None or tolerance is None or tolerance < 0:
            raise ValueError("Invalid numerical reference/tolerance.")
        answer = finite_number(calculation.get("value"))
        evaluation = {
            "expected_cell_ids": expected_ids,
            "expected_operation": reference["operation"],
            "expected_percent": reference["expected_percent"],
            "tolerance": reference["exe_ans_tolerance"],
            "cell_recall_at_k": len(found.intersection(expected_ids)) / len(expected_ids),
            "complete_proof_at_k": set(expected_ids).issubset(found),
            "ordered_cells_correct": selection.get("cell_ids") == expected_ids,
            "operation_correct": selection.get("operation") == reference["operation"],
            "numeric_within_tolerance": answer is not None and abs(answer - expected) <= tolerance,
        }
        # These labels come from the reviewed reference, independently of the runtime parser.
        contexts = [operand.get("context", {}) for operand in calculation.get("operands", [])]
        unit = reference.get("unit")
        scale = {"million": 1000000, "thousand": 1000}.get(reference.get("scale"))
        expected_unit = {
            "dollar ($)": ("$", scale),
            "MMBoe": ("MMBoe", 1000000),
            "square foot": ("square feet", scale),
        }.get(unit)
        evaluation["unit_context_correct"] = (
            None
            if expected_unit is None
            else len(contexts) == 2
            and all(
                (context.get("unit"), context.get("scale")) == expected_unit for context in contexts
            )
        )
        years = [
            re.findall(r"\b(?:19|20)\d{2}\b", cell.get("period", ""))
            for cell in reference["operands"]
        ]
        evaluation["period_years_correct"] = (
            None
            if any(len(year) != 1 for year in years)
            else len(contexts) == 2
            and all(
                context.get("year") == int(year[0])
                for context, year in zip(contexts, years, strict=True)
            )
        )
        evaluation["correct_answer"] = (
            item["status"] == "success"
            and all(
                evaluation[key]
                for key in (
                    "complete_proof_at_k",
                    "ordered_cells_correct",
                    "operation_correct",
                    "numeric_within_tolerance",
                )
            )
            and evaluation["unit_context_correct"] is not False
            and evaluation["period_years_correct"] is not False
        )
        if evaluation["correct_answer"]:
            category = "correct"
        elif item["status"] in ("failed", "blocked"):
            category = item.get("error_code") or "technical_failure"
        elif not evaluation["complete_proof_at_k"]:
            category = "incomplete_retrieval"
        elif item["status"] != "success":
            category = item.get("error_code") or "domain_abstention"
        else:
            category = next(
                key
                for key in (
                    "ordered_cells_correct",
                    "operation_correct",
                    "unit_context_correct",
                    "period_years_correct",
                    "numeric_within_tolerance",
                )
                if evaluation[key] is False
            )
        evaluation["error_category"] = category
        item["evaluation"] = evaluation
    for item, case in zip(negatives, NEGATIVE_CASES, strict=True):
        if item["case_id"] != case["id"] or item["question"] != case["question"]:
            raise ValueError("Negative case identity differs.")
        item["evaluation"] = {
            "expected_status": case["expected_status"],
            "correct_outcome": item["status"] == case["expected_status"]
            and item.get("calculation") is None,
        }
    durations = sorted(
        item["duration_seconds"]
        for item in positive
        if item.get("attempted", True) and item.get("duration_seconds") is not None
    )
    return {
        "development_cases": len(positive),
        "correct_answers": sum(item["evaluation"]["correct_answer"] for item in positive),
        "answer_accuracy": sum(item["evaluation"]["correct_answer"] for item in positive)
        / len(positive),
        "answer_successes": sum(item["status"] == "success" for item in positive),
        "answer_abstentions": sum(
            item["status"] in ("insufficient_evidence", "unsupported_request") for item in positive
        ),
        "blocked": sum(item["status"] == "blocked" for item in positive),
        "technical_failures": sum(item["status"] == "failed" for item in positive),
        "complete_proofs_at_k": sum(item["evaluation"]["complete_proof_at_k"] for item in positive),
        "mean_cell_recall_at_k": sum(item["evaluation"]["cell_recall_at_k"] for item in positive)
        / len(positive),
        "correct_cell_selections": sum(
            item["evaluation"]["ordered_cells_correct"] for item in positive
        ),
        "unit_scored_cases": sum(
            item["evaluation"]["unit_context_correct"] is not None for item in positive
        ),
        "correct_unit_contexts": sum(
            item["evaluation"]["unit_context_correct"] is True for item in positive
        ),
        "year_scored_cases": sum(
            item["evaluation"]["period_years_correct"] is not None for item in positive
        ),
        "correct_period_years": sum(
            item["evaluation"]["period_years_correct"] is True for item in positive
        ),
        "latency_attempted_cases": len(durations),
        "median_development_seconds": median(durations) if durations else None,
        "p95_development_seconds": durations[ceil(0.95 * len(durations)) - 1]
        if durations
        else None,
        "negative_cases": len(negatives),
        "correct_negative_outcomes": sum(
            item["evaluation"]["correct_outcome"] for item in negatives
        ),
        "error_categories": dict(
            Counter(item["evaluation"]["error_category"] for item in positive)
        ),
        "provider": provider_metrics(results),
    }


def plan_campaign(root, cases, method, journal):
    """Read-only quota plan; it does not construct clients, caches or journals."""
    if method not in ("lexical", "semantic"):
        raise ValueError("Unknown retrieval method.")
    allowance = Decimal(0)
    opening = Decimal("0.02")
    if journal.exists():
        with closing(
            sqlite3.connect(journal.resolve().as_uri() + "?mode=ro", uri=True)
        ) as database:
            allowance = sum(
                (Decimal(row[0]) for row in database.execute("SELECT allowance_eur FROM calls")),
                Decimal(0),
            )
        opening = Decimal(0)
    missing = set()
    if method == "semantic":
        wanted = {input_key(query_input(case["question"])) for case in cases}
        cache = root / "data/local/query-embeddings.sqlite"
        keys = set()
        if cache.exists():
            with closing(
                sqlite3.connect(cache.resolve().as_uri() + "?mode=ro", uri=True)
            ) as database:
                keys = {row[0] for row in database.execute("SELECT cache_key FROM embeddings")}
        missing = wanted - keys
    reservation = (
        len(cases) * GENERATION_ALLOWANCE_EUR + len(missing) * EMBEDDING_ALLOWANCE_EUR + opening
    )
    return {
        "method": method,
        "planned_cases": len(cases),
        "maximum_generation_requests": len(cases),
        "maximum_embedding_requests": len(missing),
        "additional_allowance_reservation_eur": str(reservation),
        "current_allowance_eur": str(allowance),
        "local_limit_eur": str(LIMIT_EUR),
        "fits_local_allowance": allowance + reservation <= LIMIT_EUR,
        "actual_charge_eur": None,
    }


def wait_for_generation_slot(journal, *, clock=time, pause=sleep):
    """Pace one sequential campaign using recent shared-journal generation history.

    Failed/blocked call records count conservatively. The caller owns campaign
    serialization; this is not a cross-process reservation or provider quota guarantee.
    """
    waited = 0.0
    while journal.exists():
        now = clock()
        with closing(
            sqlite3.connect(journal.resolve().as_uri() + "?mode=ro", uri=True)
        ) as database:
            calls = [
                json.loads(row[0]) for row in database.execute("SELECT record_json FROM calls")
            ]
        recent = sorted(
            datetime.fromisoformat(call["created_at_utc"]).timestamp()
            for call in calls
            if call["kind"] == "generation"
            and now - datetime.fromisoformat(call["created_at_utc"]).timestamp() < 60
        )
        if len(recent) < GENERATION_RPM:
            break
        delay = min(1.0, max(0.01, recent[-GENERATION_RPM] + 60.1 - now))
        pause(delay)
        waited += delay
    return waited


def run_cases(cases, method, retriever, provider, *, journal, save, wait=None):
    """Execute question/scope only; recording faults block all remaining cases."""
    results, stop_code = [], None
    for case in cases:
        if stop_code:
            result = {
                "status": "blocked",
                "error_code": stop_code,
                "calculation": None,
                "duration_seconds": 0,
                "attempted": False,
            }
        else:
            started, waited, attempted = perf_counter(), 0.0, False
            try:
                if wait is not None:
                    waited = wait()
                started = perf_counter()
                attempted = True
                result = analyze(
                    case["question"],
                    retriever,
                    provider,
                    method=method,
                    report_ids=case["report_ids"],
                    journal=journal,
                )
            except (OSError, sqlite3.Error) as error:
                result = {
                    "status": "failed",
                    "error_code": "analysis_or_recording_failed",
                    "error_type": type(error).__name__,
                    "calculation": None,
                    "duration_seconds": perf_counter() - started,
                }
                stop_code = "campaign_recording_failure"
            except ValueError:
                result = {
                    "status": "failed",
                    "error_code": "invalid_analysis_input",
                    "calculation": None,
                    "duration_seconds": perf_counter() - started,
                }
            result["attempted"] = attempted
            result["campaign_wait_seconds"] = waited
            if result.get("error_code") == "budget_limit":
                stop_code = "campaign_budget_limit"
            elif result.get("error_code") == "provider_http_429":
                stop_code = "campaign_provider_quota"
        results.append(
            {"case_id": case["id"], "question": case["question"], "method": method, **result}
        )
        save(results)  # An output-storage failure propagates before another analysis can start.
        print(
            json.dumps(
                {
                    "case_id": case["id"],
                    "method": method,
                    "status": result["status"],
                    "error_code": result.get("error_code"),
                }
            ),
            flush=True,
        )
    return results


def compare_reports(first, second):
    """Compare completed, matched v2 campaigns without rerunning model requests."""
    if {first.get("method"), second.get("method")} != {"lexical", "semantic"}:
        raise ValueError("Supply one lexical and one semantic report.")
    for report in (first, second):
        if report.get("status") != "completed" or report.get("scoring_policy") != SCORING_POLICY:
            raise ValueError(
                "Comparison requires completed reports with the current scoring policy."
            )
    for field in (
        "case_fixture_sha256",
        "reference_sha256",
        "evaluator_sha256",
        "corpus_version",
        "index_version",
        "prompt_sha256",
        "campaign_pacing",
    ):
        if not first.get(field) or first[field] != second.get(field):
            raise ValueError(f"Comparison inputs differ: {field}.")
    if first["workflow_identity"]["code_sha256"] != second["workflow_identity"]["code_sha256"]:
        raise ValueError("Comparison workflow code differs.")
    configurations = [
        deepcopy(report["workflow_identity"]["configuration"]) for report in (first, second)
    ]
    for configuration in configurations:
        configuration["retrieval"].pop("method")
    if configurations[0] != configurations[1]:
        raise ValueError("Comparison settings differ beyond retrieval method.")
    left, right = sorted((first, second), key=lambda report: report["method"])
    if [(item["case_id"], item["question"]) for item in left["results"]] != [
        (item["case_id"], item["question"]) for item in right["results"]
    ]:
        raise ValueError("Comparison result cases differ.")
    return {
        "scoring_policy": SCORING_POLICY,
        "lexical_run_id": left["run_id"],
        "semantic_run_id": right["run_id"],
        "lexical": left["metrics"],
        "semantic": right["metrics"],
        "accuracy_delta_percentage_points": 100
        * (right["metrics"]["answer_accuracy"] - left["metrics"]["answer_accuracy"]),
        "cases": [
            {
                "case_id": a["case_id"],
                "lexical_status": a["status"],
                "semantic_status": b["status"],
                "lexical_evaluation": a["evaluation"],
                "semantic_evaluation": b["evaluation"],
            }
            for a, b in zip(left["results"], right["results"], strict=True)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("lexical", "semantic"), default="semantic")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run the planned generations and missing query embeddings.",
    )
    parser.add_argument("--compare-results", nargs=2, type=Path, metavar=("LEXICAL", "SEMANTIC"))
    args = parser.parse_args()
    if args.compare_results:
        if args.live:
            parser.error("Saved-report comparison cannot use --live.")
        print(
            json.dumps(
                compare_reports(*(json.loads(path.read_bytes()) for path in args.compare_results)),
                indent=2,
            )
        )
        return 0
    fixture_path = ROOT / "evals/queries/finqa-b05.json"
    fixture_bytes = fixture_path.read_bytes()
    fixture = Queries.model_validate_json(fixture_bytes)
    if [query.id for query in fixture.cases] != [
        f"C{i:02d}" for i in range(1, len(fixture.cases) + 1)
    ]:
        raise ValueError("Positive fixture IDs must be unique and ordered from C01.")
    cases = [
        {"id": query.id, "question": query.question, "report_ids": query.report_ids}
        for query in fixture.cases
    ]
    cases += [
        {key: case[key] for key in ("id", "question", "report_ids")} for case in NEGATIVE_CASES
    ]
    plan = plan_campaign(ROOT, cases, args.method, JOURNAL)
    print(json.dumps({"plan": plan, "live_allowed": args.live}), flush=True)
    if not args.live:
        return 0
    if not plan["fits_local_allowance"]:
        parser.error(
            "Campaign worst-case reservations exceed the remaining local allowance; no requests were sent."
        )
    retriever = load_current(ROOT)
    for case in cases:
        retriever.validate_request(
            case["question"], args.method, CONFIGURATION["k"], case["report_ids"]
        )
    report = {
        "run_id": str(uuid4()),
        "status": "started",
        "partition": "development",
        "method": args.method,
        "query_fixture_sha256": sha256(fixture_bytes).hexdigest(),
        "case_fixture_sha256": digest(cases),
        "evaluator_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "scoring_policy": SCORING_POLICY,
        "workflow_identity": execution_identity(args.method, None),
        "prompt_sha256": sha256((ROOT / "prompts/analysis_selection.md").read_bytes()).hexdigest(),
        "corpus_version": retriever.manifest["corpus_version"],
        "index_version": retriever.manifest["index_version"],
        "plan": plan,
        "campaign_pacing": {"generation_rpm": GENERATION_RPM, "history": "shared-journal"},
        "results": [],
    }
    path = ROOT / f"evals/results/local/analysis/{report['run_id']}.json"

    def save(results):
        report["results"] = results
        write_atomic(path, json.dumps(report, indent=2).encode())

    save([])
    client = None
    campaign_started = perf_counter()
    try:
        if args.method == "semantic":
            retriever.query_cache = EmbeddingCache(ROOT / "data/local/query-embeddings.sqlite")
            for case in cases:
                retriever.query_cache.get(query_input(case["question"]))
        client = create_client()
        provider = GeminiProvider(client)
        if args.method == "semantic":
            retriever.provider, retriever.pacer = provider, EmbeddingPacer(JOURNAL)
        report["results"] = run_cases(
            cases,
            args.method,
            retriever,
            provider,
            journal=JOURNAL,
            save=save,
            wait=lambda: wait_for_generation_slot(JOURNAL),
        )
    finally:
        if client is not None:
            client.close()
    # Expected answers/evidence are opened only after every planned execution outcome exists.
    reference_bytes = (ROOT / "evals/cases/finqa-b01-reviewed.json").read_bytes()
    report["reference_sha256"] = sha256(reference_bytes).hexdigest()
    report["metrics"] = score(report["results"], json.loads(reference_bytes))
    report["campaign_duration_seconds"] = round(perf_counter() - campaign_started, 6)
    report["generation_wait_seconds"] = sum(
        item.get("campaign_wait_seconds", 0) for item in report["results"]
    )
    report["status"] = "completed"
    save(report["results"])
    print(
        json.dumps(
            {
                "run_id": report["run_id"],
                "path": path.relative_to(ROOT).as_posix(),
                "metrics": report["metrics"],
            },
            indent=2,
        )
    )
    return 1 if any(item["status"] in ("failed", "blocked") for item in report["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
