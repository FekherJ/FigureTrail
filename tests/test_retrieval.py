"""Offline checks for search boundaries, ranking, caching and evidence scoring."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
from pydantic import ValidationError

from app.corpus import prepare_corpus
from app.embeddings import EmbeddingCache, EmbeddingPacer
from app.llm import ProviderError
from app.retrieval import Retriever, query_input
from app.storage import publish_index
from evals.retrieval import Queries, Query, retrieve_cases, score_results
from test_corpus import fixture
from test_index import FakeProvider, populate


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        corpus, _ = prepare_corpus(*fixture())
        rows, _ = populate(
            corpus,
            EmbeddingCache(self.root / "documents.sqlite"),
            FakeProvider(),
            self.root / "no-journal",
        )
        self.directory = publish_index(corpus, rows, self.root / "indexes")
        self.retriever = Retriever(self.directory)

    def test_lexical_scores_literal_syntax_and_read_only_index(self):
        before = {
            path.name: sha256(path.read_bytes()).hexdigest() for path in self.directory.iterdir()
        }
        first = self.retriever.search("Canada 2014", k=20)
        scores = [hit["score"] for hit in first["hits"]]
        self.assertEqual(scores, sorted(scores))
        self.assertEqual(first["hits"][0]["report_id"], "OTHER/2014")
        self.assertEqual(first["hits"], self.retriever.search("Canada 2014", k=20)["hits"])
        injection = self.retriever.search('Canada OR NOT NEAR("total") : * ; DROP TABLE chunks --')
        self.assertIn('"canada"', injection["fts_query"])
        self.assertEqual(self.retriever.search("the and of")["hits"], [])
        self.assertEqual(
            before,
            {path.name: sha256(path.read_bytes()).hexdigest() for path in self.directory.iterdir()},
        )

    def test_explicit_scope_precedes_top_k_for_both_methods(self):
        retriever = self.retriever
        target = next(
            i
            for i, chunk in enumerate(retriever.corpus["chunks"])
            if chunk["report_id"] == "OTHER/2014"
        )
        self.cache_vector("Canada 2014", retriever.vectors[target])
        for method in ("lexical", "semantic"):
            with self.subTest(method=method):
                self.assertEqual(
                    retriever.search("Canada 2014", method=method, k=1)["hits"][0]["report_id"],
                    "OTHER/2014",
                )
                scoped = retriever.search(
                    "Canada 2014", method=method, k=1, report_ids=["DVN/2007"]
                )
                self.assertEqual(len(scoped["hits"]), 1)
                self.assertEqual(scoped["hits"][0]["report_id"], "DVN/2007")
                self.assertLess(scoped["eligible_chunks"], len(retriever.corpus["chunks"]))

    def cache_vector(self, question, vector):
        cache = EmbeddingCache(self.root / "queries.sqlite")
        text = query_input(question)
        _, record = FakeProvider().embed_text(text, run_id="simulated-query")
        cache.put(text, vector, record)
        self.retriever.query_cache = cache
        return cache

    def test_semantic_query_format_cache_and_cosine(self):
        provider, retriever = FakeProvider(), self.retriever
        retriever.query_cache = EmbeddingCache(self.root / "queries.sqlite")
        retriever.provider = provider
        retriever.pacer = EmbeddingPacer(self.root / "no-journal")
        question = "Canada production"
        first = retriever.search(question, method="semantic")
        self.assertEqual(provider.attempts, 1)
        self.assertFalse(first["query_embedding"]["cache_hit"])
        item = retriever.query_cache.get("task: search result | query: " + question)
        self.assertIsNotNone(item)
        scores = (
            retriever.vectors
            @ item["vector"].astype(np.float64)
            / np.linalg.norm(item["vector"].astype(np.float64))
        )
        expected = np.argsort(-scores, kind="stable")[:5]
        self.assertEqual(
            [hit["chunk_id"] for hit in first["hits"]],
            [retriever.corpus["chunks"][i]["chunk_id"] for i in expected],
        )
        for hit, ordinal in zip(first["hits"], expected, strict=True):
            self.assertAlmostEqual(hit["score"], scores[ordinal], places=7)
        retriever.provider = None
        second = retriever.search(question, method="semantic")
        self.assertTrue(second["query_embedding"]["cache_hit"])
        self.assertEqual(first["hits"], second["hits"])
        self.assertEqual(provider.attempts, 1)

    def test_invalid_requests_and_cache_miss_do_not_call_provider(self):
        retriever = self.retriever
        retriever.provider = Mock()
        for overrides in (
            {"question": " "},
            {"question": "x" * 2001},
            {"method": []},
            {"k": True},
            {"k": 0},
            {"k": 21},
            {"report_ids": []},
            {"report_ids": ["unknown"]},
            {"report_ids": "DVN/2007"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                retriever.search(**{"question": "Canada", "method": "semantic", **overrides})
        retriever.query_cache = EmbeddingCache(self.root / "queries.sqlite")
        with self.assertRaises(ValueError):
            retriever.search("Canada", method="semantic")
        retriever.provider.embed_text.assert_not_called()

    def test_evaluator_inputs_exclude_references_and_keep_failures(self):
        query = Query(id="C01", question="Canada", report_ids=["DVN/2007"])
        retriever = Mock()
        retriever.search.side_effect = ValueError("simulated failure")
        result = retrieve_cases(retriever, [query], ["semantic"], "simulated-run")
        retriever.search.assert_called_once_with(
            "Canada", method="semantic", k=5, report_ids=["DVN/2007"], run_id="simulated-run"
        )
        self.assertEqual(result[0]["status"], "failed")
        self.assertEqual(result[0]["hits"], [])
        with self.assertRaises(ValidationError):
            Queries.model_validate(
                {
                    "version": 1,
                    "partition": "development",
                    "cases": [{**query.model_dump(), "answer": "secret"}],
                }
            )

    def test_storage_failure_blocks_remaining_queries_and_methods(self):
        queries = [Query(id="C01", question="First"), Query(id="C02", question="Second")]
        methods = ["lexical", "semantic"]
        schedule = [(query.id, method) for query in queries for method in methods]
        references = {
            "cases": [
                {"case_id": f"{name}/2000/page.pdf-1", "operands": [{"cell": [1, 1]}]}
                for name in ("A", "B")
            ]
        }
        passed = [
            {
                "status": "passed",
                "method": method,
                "hits": [{"cell_ids": [f"{name}/2000/page.pdf#table[1][1]"]}],
                "duration_seconds": 0.2,
                "engine_seconds": 0.1,
            }
            for name in ("A", "B")
            for method in methods
        ]
        for error_type in (OSError, sqlite3.OperationalError):
            for failure_at in range(len(schedule)):
                with self.subTest(error=error_type.__name__, failure_at=failure_at):
                    retriever = Mock()
                    retriever.search.side_effect = [
                        *deepcopy(passed[:failure_at]),
                        error_type("PRIVATE-STORAGE-DETAIL"),
                        *deepcopy(passed[failure_at + 1 :]),
                    ]
                    results = retrieve_cases(retriever, queries, methods, "storage-test")
                    self.assertEqual(retriever.search.call_count, failure_at + 1)
                    self.assertEqual(
                        [(item["case_id"], item["method"]) for item in results], schedule
                    )
                    self.assertEqual(
                        [item["status"] for item in results],
                        ["passed"] * failure_at + ["failed"] + ["blocked"] * (3 - failure_at),
                    )
                    self.assertEqual(results[failure_at]["error_code"], "retrieval_storage_failed")
                    self.assertEqual(results[failure_at]["error_type"], error_type.__name__)
                    for item in results[failure_at + 1 :]:
                        self.assertEqual(item["error_code"], "campaign_storage_failure")
                        self.assertEqual(item["hits"], [])
                    self.assertNotIn("PRIVATE-STORAGE-DETAIL", json.dumps(results))
                    metrics = score_results(results, references)
                    for method in methods:
                        entries = [item for item in results if item["method"] == method]
                        successes = sum(item["status"] == "passed" for item in entries)
                        self.assertEqual(metrics[method]["cases"], len(queries))
                        self.assertEqual(metrics[method]["failures"], 2 - successes)
                        self.assertEqual(
                            metrics[method]["blocked"],
                            sum(item["status"] == "blocked" for item in entries),
                        )
                        self.assertEqual(
                            metrics[method]["at_k"]["5"]["complete_proof_rate"], successes / 2
                        )

    def test_query_cache_write_failure_stops_further_embedding_requests(self):
        retriever, provider = self.retriever, FakeProvider()
        cache = EmbeddingCache(self.root / "queries.sqlite")
        retriever.query_cache = cache
        retriever.provider = provider
        retriever.pacer = EmbeddingPacer(self.root / "no-journal")
        queries = [Query(id="C01", question="Canada 2008"), Query(id="C02", question="Canada 2014")]
        with (
            patch.object(cache, "put", side_effect=OSError("PRIVATE-CACHE-DETAIL")),
            patch.object(retriever, "search", wraps=retriever.search) as search,
        ):
            results = retrieve_cases(retriever, queries, ["semantic"], "cache-failure-test")
        search.assert_called_once()
        self.assertEqual(provider.attempts, 1)
        self.assertEqual([item["status"] for item in results], ["failed", "blocked"])
        self.assertEqual(results[0]["error_code"], "retrieval_storage_failed")
        self.assertEqual(results[1]["error_code"], "campaign_storage_failure")
        self.assertNotIn("PRIVATE-CACHE-DETAIL", json.dumps(results))

    def test_non_storage_failures_do_not_block_later_cases(self):
        queries = [Query(id="C01", question="First"), Query(id="C02", question="Second")]
        for error in (
            ValueError("PRIVATE-INPUT-DETAIL"),
            ProviderError("simulated_quota", {"status": "failed", "usage": None}),
        ):
            with self.subTest(error=type(error).__name__):
                retriever = Mock()
                retriever.search.side_effect = [
                    error,
                    {"status": "passed", "method": "semantic", "hits": []},
                ]
                results = retrieve_cases(retriever, queries, ["semantic"], "ordinary-error-test")
                self.assertEqual(retriever.search.call_count, 2)
                self.assertEqual([item["status"] for item in results], ["failed", "passed"])
                self.assertEqual(
                    results[0]["error_code"],
                    "retrieval_failed" if isinstance(error, ValueError) else "simulated_quota",
                )

    def test_metrics_require_all_cells_and_count_failed_cases(self):
        references = {
            "cases": [
                {"case_id": "A/2000/page.pdf-1", "operands": [{"cell": [1, 1]}, {"cell": [2, 1]}]},
                {"case_id": "B/2000/page.pdf-1", "operands": [{"cell": [1, 1]}, {"cell": [2, 1]}]},
            ]
        }
        first = "A/2000/page.pdf#table[1][1]"
        second = "A/2000/page.pdf#table[2][1]"
        results = [
            {
                "case_id": "C01",
                "method": "lexical",
                "status": "passed",
                "hits": [{"cell_ids": [first]}, {"cell_ids": [first]}, {"cell_ids": [second]}],
                "duration_seconds": 0.2,
                "engine_seconds": 0.1,
            },
            {"case_id": "C02", "method": "lexical", "status": "failed", "hits": []},
        ]
        metrics = score_results(results, references)["lexical"]
        self.assertEqual(metrics["failures"], 1)
        self.assertEqual(metrics["at_k"]["1"]["evidence_recall"], 0.25)
        self.assertEqual(metrics["at_k"]["1"]["complete_proof_rate"], 0)
        self.assertEqual(metrics["at_k"]["3"]["evidence_recall"], 0.5)
        self.assertEqual(metrics["at_k"]["5"]["complete_proof_rate"], 0.5)
        duplicated = deepcopy(results)
        duplicated[1]["case_id"] = "C01"
        with self.assertRaises(ValueError):
            score_results(duplicated, references)


if __name__ == "__main__":
    unittest.main()
