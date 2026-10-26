"""Run the fixed evidence-to-calculation workflow; --live permits hosted requests."""

import argparse
import json
from pathlib import Path
import sqlite3

from app.embeddings import EmbeddingCache, EmbeddingPacer
from app.llm import GeminiProvider, JOURNAL, create_client
from app.retrieval import load_current
from app.service import analyze

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--method", choices=("lexical", "semantic"), default="semantic")
    parser.add_argument("--report-id", action="append", dest="report_ids")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error(
            "Pass --live to permit at most one generation and any missing query embedding. No requests were sent."
        )
    try:
        retriever = load_current(ROOT)
        retriever.validate_request(args.question, args.method, 5, args.report_ids)
        with create_client() as client:
            provider = GeminiProvider(client)
            if args.method == "semantic":
                retriever.query_cache = EmbeddingCache(ROOT / "data/local/query-embeddings.sqlite")
                retriever.provider, retriever.pacer = provider, EmbeddingPacer(JOURNAL)
            result = analyze(
                args.question, retriever, provider, method=args.method, report_ids=args.report_ids
            )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] not in ("blocked", "failed") else 1
    except (OSError, sqlite3.Error, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "error_code": "analysis_setup_or_recording_failed",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
