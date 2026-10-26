"""Inspect ranked source chunks; only --live permits missing question embeddings."""

import argparse
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.embeddings import EmbeddingCache, EmbeddingPacer
from app.llm import GeminiProvider, JOURNAL, ProviderError, create_client
from app.retrieval import load_current

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--method", choices=("lexical", "semantic"), default="lexical")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--report-id", action="append", dest="report_ids")
    parser.add_argument("--live", action="store_true", help="Allow a missing query embedding.")
    args = parser.parse_args()
    if args.live and args.method != "semantic":
        parser.error("--live applies only to semantic retrieval.")
    try:
        retriever = load_current(ROOT)
        retriever.validate_request(args.question, args.method, args.k, args.report_ids)
        if args.method == "semantic":
            retriever.query_cache = EmbeddingCache(ROOT / "data/local/query-embeddings.sqlite")
            if args.live:
                retriever.provider = GeminiProvider(create_client())
                retriever.pacer = EmbeddingPacer(JOURNAL)
        result = retriever.search(
            args.question,
            method=args.method,
            k=args.k,
            report_ids=args.report_ids,
            run_id=str(uuid4()),
        )
        print(json.dumps(result, indent=2))
        return 0
    except ProviderError as error:
        print(json.dumps({"status": "failed", "error_code": str(error), "call": error.record}))
    except (OSError, ValueError, sqlite3.Error) as error:
        print(
            json.dumps(
                {"status": "failed", "error_type": type(error).__name__, "error": str(error)}
            )
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
