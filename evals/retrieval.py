"""Measure development retrieval; references are loaded only after candidate retrieval."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from statistics import median
from time import perf_counter
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.corpus import digest, write_atomic
from app.embeddings import EMBEDDING_CONFIG, EmbeddingCache, EmbeddingPacer
from app.llm import GeminiProvider, JOURNAL, LIMIT_EUR, ProviderError, create_client
from app.retrieval import RETRIEVAL_CONFIG, load_current, query_input

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_K = 5
METRIC_K = (1, 3, 5)


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^C\d{2}$")
    question: str = Field(min_length=1, max_length=2000)
    report_ids: list[str] | None = None


class Queries(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal[1]
    partition: Literal["development"]
    cases: list[Query] = Field(min_length=1, max_length=100)


def retrieve_cases(retriever, queries, methods, run_id):
    results = []
    for query in queries:
        for method in methods:
            try:
                # Case IDs and references are bookkeeping only, never search inputs.
                result = retriever.search(
                    query.question,
                    method=method,
                    k=PRIMARY_K,
                    report_ids=query.report_ids,
                    run_id=run_id,
                )
            except ProviderError as error:
                result = {
                    "status": "failed",
                    "method": method,
                    "hits": [],
                    "error_code": str(error),
                    "call": error.record,
                }
            except (OSError, ValueError, sqlite3.Error) as error:
                result = {
                    "status": "failed",
                    "method": method,
                    "hits": [],
                    "error_type": type(error).__name__,
                    "error_code": "retrieval_failed",
                }
            results.append({"case_id": query.id, **result})
    return results


def score_results(results, references):
    expected = {}
    for index, case in enumerate(references["cases"], 1):
        match = re.fullmatch(r"(.+\.pdf)-\d+", case["case_id"])
        if match is None:
            raise ValueError("Unsupported reference source identifier.")
        expected[f"C{index:02d}"] = {
            f"{match[1]}#table[{operand['cell'][0]}][{operand['cell'][1]}]"
            for operand in case["operands"]
        }
    methods = sorted({result["method"] for result in results})
    metrics = {}
    for method in methods:
        entries = [item for item in results if item["method"] == method]
        if len(entries) != len(expected) or {item["case_id"] for item in entries} != set(expected):
            raise ValueError("Evaluation cases and references must match exactly once per method.")
        for item in entries:
            required = expected[item["case_id"]]
            if not required:
                raise ValueError("A reference must require evidence cells.")
            item["required_cell_ids"] = sorted(required)
            item["evidence_metrics"] = {}
            for k in METRIC_K:
                found = {cell for hit in item["hits"][:k] for cell in hit["cell_ids"]}
                recovered = required & found if item["status"] == "passed" else set()
                item["evidence_metrics"][str(k)] = {
                    "evidence_recall": len(recovered) / len(required),
                    "complete_proof": recovered == required,
                    "missing_cell_ids": sorted(required - recovered),
                }
        metrics[method] = {
            "cases": len(entries),
            "failures": sum(item["status"] != "passed" for item in entries),
            "at_k": {
                str(k): {
                    "evidence_recall": sum(
                        item["evidence_metrics"][str(k)]["evidence_recall"] for item in entries
                    )
                    / len(entries),
                    "complete_proof_count": sum(
                        item["evidence_metrics"][str(k)]["complete_proof"] for item in entries
                    ),
                    "complete_proof_rate": sum(
                        item["evidence_metrics"][str(k)]["complete_proof"] for item in entries
                    )
                    / len(entries),
                }
                for k in METRIC_K
            },
            "median_total_seconds": median(
                item["duration_seconds"] for item in entries if item["status"] == "passed"
            )
            if any(item["status"] == "passed" for item in entries)
            else None,
            "median_engine_seconds": median(
                item["engine_seconds"] for item in entries if item["status"] == "passed"
            )
            if any(item["status"] == "passed" for item in entries)
            else None,
        }
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("lexical", "compare"), default="lexical")
    parser.add_argument(
        "--live", action="store_true", help="Allow missing query embeddings in compare mode."
    )
    args = parser.parse_args()
    if args.live and args.mode != "compare":
        parser.error("--live applies only to compare mode.")
    run_id = str(uuid4())
    destination = ROOT / f"evals/results/local/retrieval/{run_id}.json"
    report = {
        "run_id": run_id,
        "status": "started",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "live_allowed": args.live,
        "primary_k": PRIMARY_K,
        "metric_k": list(METRIC_K),
        "results": [],
    }
    try:
        query_path = ROOT / "evals/queries/finqa-b05.json"
        fixture = Queries.model_validate_json(query_path.read_bytes())
        if len({query.id for query in fixture.cases}) != len(fixture.cases):
            raise ValueError("Duplicate query IDs.")
        setup_started = perf_counter()
        retriever = load_current(ROOT)
        report.update(
            index_load_seconds=round(perf_counter() - setup_started, 6),
            corpus_version=retriever.manifest["corpus_version"],
            index_version=retriever.manifest["index_version"],
            corpus_counts=retriever.manifest["counts"],
            retrieval_configuration=RETRIEVAL_CONFIG,
            query_fixture_sha256=sha256(query_path.read_bytes()).hexdigest(),
            code_sha256=sha256(
                b"".join(
                    (ROOT / name).read_bytes()
                    for name in (
                        "app/retrieval.py",
                        "evals/retrieval.py",
                        "app/embeddings.py",
                        "app/llm.py",
                    )
                )
            ).hexdigest(),
        )
        methods = ("lexical",) if args.mode == "lexical" else ("lexical", "semantic")
        for query in fixture.cases:
            retriever.validate_request(query.question, methods[-1], PRIMARY_K, query.report_ids)
        if args.mode == "compare":
            cache = EmbeddingCache(ROOT / "data/local/query-embeddings.sqlite")
            missing = sum(cache.get(query_input(query.question)) is None for query in fixture.cases)
            with closing(sqlite3.connect(JOURNAL)) as database:
                allowance = sum(
                    (
                        Decimal(row[0])
                        for row in database.execute("SELECT allowance_eur FROM calls")
                    ),
                    Decimal(0),
                )
            report["plan"] = {
                "missing_query_embeddings": missing,
                "additional_reserved_eur": str(Decimal("0.01") * missing),
                "current_allowance_eur": str(allowance),
                "embedding_configuration": EMBEDDING_CONFIG,
            }
            print(json.dumps({"plan": report["plan"]}), flush=True)
            if missing and not args.live:
                raise ValueError(
                    "Query embeddings are missing; pass --live. No requests were sent."
                )
            if allowance + Decimal("0.01") * missing > LIMIT_EUR:
                raise ValueError("Query campaign would exceed the local allowance limit.")
            retriever.query_cache = cache
            if missing:
                retriever.provider = GeminiProvider(create_client())
                retriever.pacer = EmbeddingPacer(JOURNAL)
        report["configuration_sha256"] = digest(RETRIEVAL_CONFIG)
        write_atomic(destination, json.dumps(report, indent=2).encode())
        report["results"] = retrieve_cases(retriever, fixture.cases, methods, run_id)
        # Persist candidates before opening the answer/evidence references for scoring.
        write_atomic(destination, json.dumps(report, indent=2).encode())
        reference_path = ROOT / "evals/cases/finqa-b01-reviewed.json"
        references = json.loads(reference_path.read_text(encoding="utf-8"))
        report["reference_sha256"] = sha256(reference_path.read_bytes()).hexdigest()
        if {query.id: query.question for query in fixture.cases} != {
            f"C{index:02d}": case["application_question"]
            for index, case in enumerate(references["cases"], 1)
        }:
            raise ValueError("Questions and scoring references do not match.")
        report["metrics"] = score_results(report["results"], references)
        report["status"] = (
            "passed" if all(item["status"] == "passed" for item in report["results"]) else "failed"
        )
    except (OSError, ValueError, sqlite3.Error, ProviderError) as error:
        report.update(
            status="failed",
            error_type=type(error).__name__,
            error_code=str(error) if isinstance(error, ProviderError) else "evaluation_failed",
        )
        print(f"Retrieval evaluation failed: {type(error).__name__}")
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_atomic(destination, json.dumps(report, indent=2).encode())
    print(
        json.dumps(
            {
                "status": report["status"],
                "run_id": run_id,
                "path": destination.relative_to(ROOT).as_posix(),
                "metrics": report.get("metrics"),
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
