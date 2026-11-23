"""Plan or run a budget-bounded paired fixed/agent development comparison."""

import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.agent import AGENT_CONFIG, run_agent
from app.corpus import write_atomic
from app.embeddings import EmbeddingCache, EmbeddingPacer
from app.llm import (
    EMBEDDING_ALLOWANCE_EUR,
    GENERATION_ALLOWANCE_EUR,
    GeminiProvider,
    JOURNAL,
    LIMIT_EUR,
    create_client,
    wait_for_generation_slot,
)
from app.retrieval import load_current
from app.service import CONFIGURATION, analyze, execution_identity
from evals.analysis import plan_campaign, score
from evals.retrieval import Queries

ROOT = Path(__file__).resolve().parents[1]


def plan_comparison(root, cases, method, journal):
    """Read-only worst-case plan: fixed plus four agent turns and two query embeddings."""
    plan = plan_campaign(root, cases, method, journal)
    extra_embeddings = len(cases) * AGENT_CONFIG["max_searches"] if method == "semantic" else 0
    extra = len(cases) * AGENT_CONFIG["max_generation_calls"] * GENERATION_ALLOWANCE_EUR
    extra += extra_embeddings * EMBEDDING_ALLOWANCE_EUR
    reservation = Decimal(plan["additional_allowance_reservation_eur"]) + extra
    return {
        **plan,
        "maximum_generation_requests": len(cases) * (1 + AGENT_CONFIG["max_generation_calls"]),
        "maximum_embedding_requests": plan["maximum_embedding_requests"] + extra_embeddings,
        "additional_allowance_reservation_eur": str(reservation),
        "fits_local_allowance": Decimal(plan["current_allowance_eur"]) + reservation <= LIMIT_EUR,
    }


def execute_pairs(cases, method, retriever, provider, journal, save):
    """Run each original question in both modes; stop the campaign on storage/quota blocks."""
    pairs, stop = [], None
    for case in cases:
        pair = {"case_id": case["id"], "question": case["question"]}
        pairs.append(pair)
        for mode, workflow in (("fixed", analyze), ("agent", run_agent)):
            if stop:
                pair[mode] = {
                    "status": "blocked",
                    "error_code": stop,
                    "calculation": None,
                    "attempted": False,
                }
            else:
                try:
                    wait_for_generation_slot(journal)
                    pair[mode] = workflow(
                        case["question"],
                        retriever,
                        provider,
                        method=method,
                        report_ids=case["report_ids"],
                        journal=journal,
                    )
                    pair[mode]["attempted"] = True
                    if pair[mode].get("error_code") in ("budget_limit", "provider_http_429"):
                        stop = "campaign_budget_or_quota_limit"
                except OSError, sqlite3.Error:
                    pair[mode] = {
                        "status": "failed",
                        "error_code": "recording_unavailable",
                        "calculation": None,
                        "attempted": True,
                    }
                    stop = "campaign_recording_failure"
            save(pairs)  # Report write errors propagate before another paid action.
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Repeat to choose a declared development subset; default is all ten.",
    )
    parser.add_argument("--method", choices=("lexical", "semantic"), default="semantic")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    fixture_bytes = (ROOT / "evals/queries/finqa-b05.json").read_bytes()
    fixture = Queries.model_validate_json(fixture_bytes)
    ids = args.case_ids or [case.id for case in fixture.cases]
    if len(set(ids)) != len(ids) or not set(ids) <= {case.id for case in fixture.cases}:
        parser.error("Choose distinct known case IDs from the development fixture.")
    cases = [case.model_dump() for case in fixture.cases if case.id in ids]
    plan = plan_comparison(ROOT, cases, args.method, JOURNAL)
    print(
        json.dumps(
            {"case_ids": [case["id"] for case in cases], "plan": plan, "live_allowed": args.live}
        ),
        flush=True,
    )
    if not args.live:
        return 0
    if not plan["fits_local_allowance"]:
        parser.error(
            "Worst-case paired reservations exceed the remaining allowance; no calls were made."
        )
    retriever = load_current(ROOT)
    for case in cases:
        retriever.validate_request(
            case["question"], args.method, CONFIGURATION["k"], case["report_ids"]
        )
    report = {
        "run_id": str(uuid4()),
        "partition": "development",
        "status": "started",
        "method": args.method,
        "case_ids": [case["id"] for case in cases],
        "plan": plan,
        "fixture_sha256": sha256(fixture_bytes).hexdigest(),
        "evaluator_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "workflow_identity": execution_identity(args.method, None),
        "corpus_version": retriever.manifest["corpus_version"],
        "index_version": retriever.manifest["index_version"],
        "fixed_prompt_sha256": sha256(
            (ROOT / "prompts/analysis_selection.md").read_bytes()
        ).hexdigest(),
        "agent_prompt_sha256": sha256((ROOT / "prompts/agent.md").read_bytes()).hexdigest(),
        "evidence_metric": "fixed top five versus union of agent searches (at most ten); not a same-k retrieval comparison",
        "pairs": [],
    }
    path = ROOT / f"evals/results/local/agent/{report['run_id']}.json"

    def save(pairs):
        report["pairs"] = pairs
        write_atomic(path, json.dumps(report, indent=2).encode() + b"\n")

    save([])
    with create_client() as client:
        provider = GeminiProvider(client)
        if args.method == "semantic":
            retriever.provider = provider
            retriever.query_cache = EmbeddingCache(ROOT / "data/local/query-embeddings.sqlite")
            retriever.pacer = EmbeddingPacer(JOURNAL)
        report["pairs"] = execute_pairs(cases, args.method, retriever, provider, JOURNAL, save)
    # Only after both modes finish are answers and annotated cells opened for scoring.
    reference_bytes = (ROOT / "evals/cases/finqa-b01-reviewed.json").read_bytes()
    report["reference_sha256"] = sha256(reference_bytes).hexdigest()
    references = json.loads(reference_bytes)["cases"]
    by_id = {f"C{i:02d}": reference for i, reference in enumerate(references, 1)}
    subset = {"cases": [by_id[case["id"]] for case in cases]}
    report["metrics"] = {}
    for mode in ("fixed", "agent"):
        results = [
            {"case_id": pair["case_id"], "question": pair["question"], **pair[mode]}
            for pair in report["pairs"]
        ]
        report["metrics"][mode] = score(
            results,
            subset,
            positive_ids=report["case_ids"],
            negative_cases=(),
            evidence_limit=None if mode == "agent" else 5,
        )
        for pair, result in zip(report["pairs"], results, strict=True):
            pair[mode]["evaluation"] = result["evaluation"]
    report["status"] = "completed"
    save(report["pairs"])
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
    return int(
        any(
            pair[mode]["status"] in ("failed", "blocked")
            for pair in report["pairs"]
            for mode in ("fixed", "agent")
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
