"""Scoped lexical/semantic retrieval from a validated, source-only index."""

from contextlib import closing
from hashlib import sha256
from pathlib import Path
import re
import sqlite3
from time import perf_counter
from uuid import uuid4

import numpy as np

from app.corpus import read_current
from app.embeddings import EMBEDDING_CONFIG, checked_vector
from app.storage import load_index

STOP_WORDS = frozenset(
    "a an and are as at be by did do does for from how in is it of on or that the their "
    "these this to was were what when which with".split()
)
RETRIEVAL_CONFIG = {
    "version": "figuretrail-retrieval-v1",
    "lexical_query": "literal unicode words joined with OR",
    "stop_words": sorted(STOP_WORDS),
    "max_lexical_terms": 64,
    "lexical_score": "SQLite FTS5 BM25; lower is better",
    "semantic_score": "float64 cosine similarity; higher is better",
    "query_format": EMBEDDING_CONFIG["query_format"],
    "tie_break": "corpus ordinal ascending",
    "default_k": 5,
    "max_k": 20,
}


def query_input(question: str) -> str:
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Question must contain 1-2000 characters and non-whitespace text.")
    return EMBEDDING_CONFIG["query_format"].format(query=question)


def lexical_terms(question: str) -> list[str]:
    query_input(question)
    terms = dict.fromkeys(re.findall(r"[^\W_]+", question.casefold()))
    return [term for term in terms if term not in STOP_WORDS][:64]


class Retriever:
    def __init__(
        self,
        directory: Path,
        expected_corpus_version: str | None = None,
        *,
        query_cache=None,
        provider=None,
        pacer=None,
    ):
        self.directory = directory
        self.manifest, self.corpus, vectors = load_index(directory, expected_corpus_version)
        self.query_cache, self.provider, self.pacer = query_cache, provider, pacer
        values = vectors.astype(np.float64)
        self.vectors = values / np.linalg.norm(values, axis=1, keepdims=True)
        self.vectors.setflags(write=False)
        self.report_ids = {source["report_id"] for source in self.corpus["sources"]}

    def validate_request(self, question, method, k, report_ids):
        query_input(question)
        if not isinstance(method, str) or method not in {"lexical", "semantic"}:
            raise ValueError("Method must be lexical or semantic.")
        if type(k) is not int or not 1 <= k <= RETRIEVAL_CONFIG["max_k"]:
            raise ValueError("k must be an integer from 1 to 20.")
        if report_ids is not None:
            if (
                not isinstance(report_ids, list)
                or not 1 <= len(report_ids) <= 40
                or any(
                    not isinstance(value, str) or value not in self.report_ids
                    for value in report_ids
                )
            ):
                raise ValueError("Explicit report scope must contain known report IDs.")
            report_ids = sorted(set(report_ids))
        return report_ids

    def _query_vector(self, question: str, run_id: str, *, deadline=None, cancelled=None):
        if self.query_cache is None:
            raise ValueError("Semantic retrieval requires a query embedding cache.")
        text = query_input(question)
        item = self.query_cache.get(text)
        call, wait = None, 0.0
        cache_hit = item is not None
        if item is None:
            if self.provider is None or self.pacer is None:
                raise ValueError("Query embedding is missing; explicitly allow a live request.")
            limits = {"deadline": deadline, "cancelled": cancelled} if deadline is not None else {}
            wait = self.pacer.wait(len(text.encode()) + 64, **limits)
            vector, call = self.provider.embed_text(
                text,
                run_id=run_id,
                **limits,
                metadata={
                    "purpose": "retrieval_query",
                    "format_version": EMBEDDING_CONFIG["format_version"],
                    "question_sha256": sha256(question.encode()).hexdigest(),
                },
            )
            # Save the returned vector before the caller writes progress/results.
            item = self.query_cache.put(text, vector, call)
        vector = checked_vector(item["vector"]).astype(np.float64)
        vector /= np.linalg.norm(vector)
        return vector, {
            "cache_hit": cache_hit,
            "embedding_key": item["key"],
            "provider_call_id": item["metadata"]["call_id"],
            "provider_run_id": item["metadata"]["run_id"],
            "pacing_wait_seconds": wait,
            "call": call,
        }

    def search(
        self,
        question: str,
        *,
        method="lexical",
        k=5,
        report_ids=None,
        run_id=None,
        deadline=None,
        cancelled=None,
    ):
        started = perf_counter()
        scope = self.validate_request(question, method, k, report_ids)
        eligible = np.array(
            [
                i
                for i, chunk in enumerate(self.corpus["chunks"])
                if scope is None or chunk["report_id"] in scope
            ],
            dtype=np.int64,
        )
        event, fts_query = None, None
        terms = lexical_terms(question) if method == "lexical" else None
        if method == "lexical":
            # User text never becomes FTS syntax or executable SQL.
            fts_query = " OR ".join('"' + term + '"' for term in terms)
            ranked = []
            if fts_query:
                sql = (
                    "SELECT c.ordinal, bm25(chunk_fts) AS score FROM chunk_fts "
                    "JOIN chunks c ON c.ordinal + 1 = chunk_fts.rowid "
                    "WHERE chunk_fts MATCH ?"
                )
                params = [fts_query]
                if scope is not None:
                    sources = sorted({self.corpus["chunks"][i]["source_id"] for i in eligible})
                    sql += " AND c.source_id IN (" + ",".join("?" for _ in sources) + ")"
                    params.extend(sources)
                sql += " ORDER BY score ASC, c.ordinal ASC LIMIT ?"
                params.append(k)
                uri = (self.directory / "corpus.sqlite").resolve().as_uri() + "?mode=ro"
                with closing(sqlite3.connect(uri, uri=True)) as database:
                    database.execute("PRAGMA query_only=ON")
                    ranked = database.execute(sql, params).fetchall()
            engine_seconds = perf_counter() - started
        else:
            vector, event = self._query_vector(
                question, run_id or str(uuid4()), deadline=deadline, cancelled=cancelled
            )
            engine_started = perf_counter()
            # ponytail: exact O(n*d) scan for <=500 chunks; consider ANN only after a size/latency need.
            scores = np.clip(self.vectors[eligible] @ vector, -1.0, 1.0)
            order = np.lexsort((eligible, -scores))[:k]
            ranked = [(int(eligible[i]), float(scores[i])) for i in order]
            engine_seconds = perf_counter() - engine_started
        hits = []
        for rank, (ordinal, score) in enumerate(ranked, 1):
            chunk = self.corpus["chunks"][ordinal]
            hits.append(
                {
                    "rank": rank,
                    "score": float(score),
                    "chunk_id": chunk["chunk_id"],
                    "source_id": chunk["source_id"],
                    "report_id": chunk["report_id"],
                    "kind": chunk["kind"],
                    "text": chunk["text"],
                    "cell_ids": list(chunk["cell_ids"]),
                }
            )
        return {
            "status": "passed",
            "method": method,
            "question": question,
            "report_ids": scope,
            "k": k,
            "eligible_chunks": len(eligible),
            "hits": hits,
            "score_direction": "lower_is_better" if method == "lexical" else "higher_is_better",
            "query_terms": terms,
            "fts_query": fts_query,
            "query_embedding": event,
            "engine_seconds": round(engine_seconds, 6),
            "duration_seconds": round(perf_counter() - started, 6),
            "corpus_version": self.manifest["corpus_version"],
            "index_version": self.manifest["index_version"],
        }


def load_current(root: Path, **kwargs) -> Retriever:
    prepared = read_current(root / "data/corpus/prepared", "corpus_version")
    directory = read_current(root / "data/corpus/indexes", "index_version")
    return Retriever(directory, prepared.name, **kwargs)
