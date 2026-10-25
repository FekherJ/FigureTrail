"""Build the local SQLite/vector bundle; only --live permits missing embeddings."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from time import perf_counter
from uuid import uuid4

from app.corpus import load_prepared, read_current, write_atomic
from app.embeddings import EMBEDDING_CONFIG, EmbeddingCache, EmbeddingPacer, document_input
from app.llm import GeminiProvider, JOURNAL, LIMIT_EUR, ProviderError, create_client
from app.storage import current_index, publish_index

ROOT = Path(__file__).resolve().parents[1]


def journal_allowance(path: Path) -> Decimal:
    if not path.exists():
        return Decimal("0.02")
    with closing(sqlite3.connect(path)) as database:
        return sum(
            (Decimal(row[0]) for row in database.execute("SELECT allowance_eur FROM calls")),
            Decimal(0),
        )


def collect_embeddings(corpus, cache, report, save, provider=None, pacer=None, progress=print):
    items = []
    last_progress = perf_counter()
    for ordinal, chunk in enumerate(corpus["chunks"]):
        text = document_input(chunk["text"])
        cached = cache.get(text)
        if cached is not None:
            report["cache_hits"] += 1
        else:
            if provider is None or pacer is None:
                raise ValueError("Embeddings are missing; pass --live to allow provider requests.")
            report["pacing_wait_seconds"] += pacer.wait(len(text.encode()) + 64)
            try:
                vector, call = provider.embed_text(
                    text,
                    run_id=report["run_id"],
                    metadata={
                        "format_version": EMBEDDING_CONFIG["format_version"],
                        "purpose": "document_index",
                        "corpus_version": corpus["manifest"]["corpus_version"],
                        "chunk_id": chunk["chunk_id"],
                    },
                )
            except ProviderError as error:
                report["calls"].append(error.record)
                save()
                raise
            report["calls"].append(call)
            # The provider journal is already durable; preserve the vector before progress I/O.
            cached = cache.put(text, vector, call)
            save()
        items.append(cached)
        report["completed_rows"] = ordinal + 1
        save()
        if (ordinal + 1) % 10 == 0 or perf_counter() - last_progress >= 20:
            progress(
                f"Indexed embeddings: {ordinal + 1}/{len(corpus['chunks'])}; requests: {len(report['calls'])}; cache hits: {report['cache_hits']}",
                flush=True,
            )
            last_progress = perf_counter()
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--live", action="store_true", help="Allow embedding requests for cache misses."
    )
    modes.add_argument(
        "--check", action="store_true", help="Verify the current bundle without model calls."
    )
    args = parser.parse_args()
    report = None
    try:
        prepared_path = read_current(ROOT / "data/corpus/prepared", "corpus_version").with_suffix(
            ".json"
        )
        corpus = load_prepared(prepared_path)
        output_root = ROOT / "data/corpus/indexes"
        if args.check:
            destination, (manifest, _, vectors) = current_index(
                output_root, corpus["manifest"]["corpus_version"]
            )
            print(
                json.dumps(
                    {
                        "status": "verified",
                        "index_version": manifest["index_version"],
                        "path": destination.relative_to(ROOT).as_posix(),
                        "counts": manifest["counts"],
                        "matrix_shape": list(vectors.shape),
                        "model_requests": 0,
                    },
                    indent=2,
                )
            )
            return 0
        cache = EmbeddingCache(ROOT / "data/local/embeddings.sqlite")
        unique_inputs = set(document_input(chunk["text"]) for chunk in corpus["chunks"])
        missing = [text for text in unique_inputs if cache.get(text) is None]
        allowance = journal_allowance(JOURNAL)
        plan = {
            "chunks": len(corpus["chunks"]),
            "unique_inputs": len(unique_inputs),
            "missing_embeddings": len(missing),
            "additional_reserved_allowance_eur": str(Decimal("0.01") * len(missing)),
            "current_allowance_eur": str(allowance),
            "input_pacing_allowance": sum(len(text.encode()) + 64 for text in missing),
            "pacing_rpm": 80,
            "pacing_input_allowance_per_minute": 24000,
        }
        print(json.dumps({"plan": plan}), flush=True)
        if missing and not args.live:
            raise ValueError(
                "Missing embeddings; use --live for the first build. No requests were sent."
            )
        if allowance + Decimal("0.01") * len(missing) > LIMIT_EUR:
            raise ValueError("The complete campaign would exceed the local allowance limit.")
        if any(len(text.encode()) + 64 > 8192 for text in missing):
            raise ValueError("An input exceeds the conservative per-request allowance.")
        run_id = str(uuid4())
        report_path = ROOT / "data/local/index-builds" / f"{run_id}.json"
        report = {
            "run_id": run_id,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "started",
            "plan": plan,
            "corpus_version": corpus["manifest"]["corpus_version"],
            "embedding_configuration": EMBEDDING_CONFIG.copy(),
            "calls": [],
            "cache_hits": 0,
            "completed_rows": 0,
            "pacing_wait_seconds": 0.0,
            "builder_code_sha256": sha256(
                b"".join(
                    (ROOT / name).read_bytes()
                    for name in (
                        "app/corpus.py",
                        "app/llm.py",
                        "app/embeddings.py",
                        "app/storage.py",
                        "scripts/build_index.py",
                    )
                )
            ).hexdigest(),
        }

        def save():
            write_atomic(report_path, json.dumps(report, indent=2).encode() + b"\n")

        save()
        started = perf_counter()
        if missing:
            with create_client() as client:
                provider = GeminiProvider(client)
                embeddings = collect_embeddings(
                    corpus, cache, report, save, provider, EmbeddingPacer(provider.journal)
                )
        else:
            embeddings = collect_embeddings(corpus, cache, report, save)
        destination = publish_index(corpus, embeddings, output_root)
        manifest, _, vectors = current_index(output_root, corpus["manifest"]["corpus_version"])[1]
        report.update(
            status="passed",
            index_version=manifest["index_version"],
            index_path=destination.relative_to(ROOT).as_posix(),
            matrix_shape=list(vectors.shape),
            duration_seconds=round(perf_counter() - started, 3),
            final_allowance_eur=str(journal_allowance(JOURNAL)),
        )
        save()
        print(json.dumps({key: value for key, value in report.items() if key != "calls"}, indent=2))
        print(f"Local build record: {report_path.relative_to(ROOT).as_posix()}")
        return 0
    except (OSError, ValueError, sqlite3.Error, ProviderError) as error:
        if report is not None:
            report.update(
                status="failed",
                error_type=type(error).__name__,
                error_code=str(error) if isinstance(error, ProviderError) else "index_build_failed",
            )
            save()
        parser.exit(1, f"Index build stopped: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
