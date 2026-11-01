"""CLI-owned SDK clients close on success and failure; no hosted calls."""

from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.llm import ProviderError
from evals import retrieval as evaluation_cli
from scripts import search as search_cli

ROOT = Path(__file__).resolve().parents[1]


class CLILifecycleTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        fixtures = {
            "evals/queries/finqa-b05.json": {
                "version": 1,
                "partition": "development",
                "cases": [{"id": "C01", "question": "Canada production", "report_ids": None}],
            },
            "evals/cases/finqa-b01-reviewed.json": {
                "cases": [
                    {
                        "case_id": "PUBLIC/2008/page.pdf-1",
                        "application_question": "Canada production",
                        "operands": [{"cell": [1, 1]}],
                    }
                ]
            },
        }
        for relative, data in fixtures.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
        for relative in (
            "app/retrieval.py",
            "evals/retrieval.py",
            "app/embeddings.py",
            "app/llm.py",
        ):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        self.journal = self.root / "journal.sqlite"
        with closing(sqlite3.connect(self.journal)) as database, database:
            database.execute("CREATE TABLE calls (allowance_eur TEXT)")

    def run_cli(self, module, arguments, *, fault=None, cached=False):
        client, create, provider, pacer = Mock(), Mock(), Mock(), Mock()
        create.return_value = client
        cache = Mock()
        cache.get.return_value = {"cached": True} if cached else None
        retriever = Mock()
        retriever.manifest = {
            "corpus_version": "simulated-corpus",
            "index_version": "simulated-index",
            "counts": {"chunks": 1},
        }
        retriever.search.side_effect = lambda question, **kwargs: {
            "status": "passed",
            "method": kwargs["method"],
            "hits": [{"cell_ids": ["PUBLIC/2008/page.pdf#table[1][1]"]}],
            "duration_seconds": 0.1,
            "engine_seconds": 0.01,
        }
        if fault == "provider":
            provider.side_effect = ValueError("simulated provider setup failure")
        elif fault == "pacer":
            pacer.side_effect = sqlite3.OperationalError("simulated pacing setup failure")
        elif fault == "search":
            retriever.search.side_effect = ProviderError("simulated_quota", {"status": "failed"})
        elif fault == "storage":
            retriever.search.side_effect = sqlite3.OperationalError("simulated storage failure")
        with (
            patch.multiple(
                module,
                ROOT=self.root,
                JOURNAL=self.journal,
                load_current=Mock(return_value=retriever),
                create_client=create,
                GeminiProvider=provider,
                EmbeddingCache=Mock(return_value=cache),
                EmbeddingPacer=pacer,
            ),
            patch("sys.argv", [module.__name__, *arguments]),
            redirect_stdout(io.StringIO()),
        ):
            code = module.main()
        return code, client, create, provider

    def test_search_closes_client_on_success_and_failures(self):
        for fault in (None, "provider", "pacer", "search", "storage"):
            with self.subTest(fault=fault):
                code, client, create, provider = self.run_cli(
                    search_cli, ["Canada production", "--method", "semantic", "--live"], fault=fault
                )
                self.assertEqual(code, 0 if fault is None else 1)
                create.assert_called_once_with()
                provider.assert_called_once_with(client)
                client.close.assert_called_once_with()

    def test_search_without_live_does_not_create_client(self):
        for arguments in (["Canada production"], ["Canada production", "--method", "semantic"]):
            with self.subTest(arguments=arguments):
                code, _, create, provider = self.run_cli(search_cli, arguments, cached=True)
                self.assertEqual(code, 0)
                create.assert_not_called()
                provider.assert_not_called()

    def test_evaluator_closes_client_on_success_and_failures(self):
        for fault in (None, "provider", "pacer", "search", "storage"):
            with self.subTest(fault=fault):
                code, client, create, provider = self.run_cli(
                    evaluation_cli, ["--mode", "compare", "--live"], fault=fault
                )
                self.assertEqual(code, 0 if fault is None else 1)
                create.assert_called_once_with()
                provider.assert_called_once_with(client)
                client.close.assert_called_once_with()

    def test_evaluator_cached_or_lexical_run_does_not_create_client(self):
        for arguments in ([], ["--mode", "compare"], ["--mode", "compare", "--live"]):
            with self.subTest(arguments=arguments):
                code, _, create, provider = self.run_cli(evaluation_cli, arguments, cached=True)
                self.assertEqual(code, 0)
                create.assert_not_called()
                provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
