"""Source arithmetic, domain boundaries and the shared fixed workflow; no live calls."""

from contextlib import closing
from copy import deepcopy
from decimal import ROUND_DOWN, localcontext
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.calculator import EvidenceError, calculate
from app.corpus import prepare_corpus
from app.llm import ProviderError
from app.schemas import CellSelection
from app.service import analyze, model_input
from test_corpus import fixture


def plan(ids, operation="ratio_percent"):
    return CellSelection(status="ready", operation=operation, cell_ids=ids)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.journal = Path(self.folder.name) / "runs.sqlite"
        self.corpus, _ = prepare_corpus(*fixture())
        self.chunks = [
            chunk for chunk in self.corpus["chunks"] if chunk["source_id"] == "DVN/2007/page_58.pdf"
        ]
        self.ids = ["DVN/2007/page_58.pdf#table[1][1]", "DVN/2007/page_58.pdf#table[3][1]"]
        self.question = "What percentage of estimated 2008 production in MMBoe comes from Canada?"

    def test_decimal_ratio_rounding_and_source_values(self):
        with localcontext() as outside_context:
            outside_context.prec = 2
            outside_context.rounding = ROUND_DOWN
            value = calculate(plan(self.ids), self.question, self.corpus["cells"], self.chunks)
        self.assertEqual(value["value"], "24.69135802469135802469135802")
        self.assertEqual(value["display"], "24.69 %")
        self.assertEqual(value["operands"][0]["value"], "60")
        self.assertEqual(value["operands"][0]["context"]["year"], 2008)
        self.assertEqual(value["operands"][0]["context"]["unit"], "MMBoe")
        self.assertEqual(value["operands"][0]["context"]["scale"], 1000000)

    def test_growth_decline_order_and_dated_periods(self):
        table = [["Dollars in millions", "2018", "2017"], ["Profit", "$1,211", "$1,194"]]
        raw = [
            {
                "filename": "PUBLIC/2018/page.pdf",
                "pre_text": [],
                "post_text": [],
                "table": table,
                "table_ori": table,
            }
        ]
        from app.corpus import encode
        from hashlib import sha256

        encoded = encode(raw)
        corpus, _ = prepare_corpus(
            encoded,
            {
                "selection_version": "finqa-corpus-v1",
                "raw_sha256": sha256(encoded).hexdigest(),
                "source_filenames": ["PUBLIC/2018/page.pdf"],
            },
        )
        ids = [cell["cell_id"] for cell in corpus["cells"]]
        result = calculate(
            plan(ids, "percent_change"),
            "What is profit growth from 2017 to 2018?",
            corpus["cells"],
            corpus["chunks"],
        )
        self.assertEqual(result["display"], "1.42 %")
        reversed_values = deepcopy(corpus["cells"])
        reversed_values[0]["source_value"] = "$1,000"
        self.assertEqual(
            calculate(
                plan(ids, "percent_change"),
                "What is profit growth from 2017 to 2018?",
                reversed_values,
                corpus["chunks"],
            )["display"],
            "-16.25 %",
        )
        with self.assertRaises(EvidenceError):
            calculate(
                plan(ids[::-1], "percent_change"),
                "What is profit growth from 2017 to 2018?",
                corpus["cells"],
                corpus["chunks"],
            )
        for cell, header in zip(
            corpus["cells"], ["December 31, 2018", "December 31, 2017"], strict=True
        ):
            cell["column_header"] = header
        with self.assertRaises(EvidenceError):
            calculate(
                plan(ids, "percent_change"),
                "What is profit growth from December 30, 2017 to December 31, 2018?",
                corpus["cells"],
                corpus["chunks"],
            )

    def test_missing_invalid_inaccessible_and_nonpositive_operands(self):
        for change, code in (
            ({"source_value": "—"}, "unusable_source_value"),
            ({"source_value": "NaN"}, "unusable_source_value"),
            ({"source_value": "0"}, "nonpositive_denominator"),
            ({"source_value": "-2"}, "nonpositive_denominator"),
        ):
            cells = deepcopy(self.corpus["cells"])
            next(cell for cell in cells if cell["cell_id"] == self.ids[1]).update(change)
            with self.subTest(change=change), self.assertRaises(EvidenceError) as error:
                calculate(plan(self.ids), self.question, cells, self.chunks)
            self.assertEqual(error.exception.code, code)
        for ids, chunks in (
            ([self.ids[0], "invented#table[2][1]"], self.chunks),
            (self.ids, self.chunks[:1]),
        ):
            with self.assertRaises(EvidenceError) as error:
                calculate(plan(ids), self.question, self.corpus["cells"], chunks)
            self.assertEqual(error.exception.code, "invalid_cell_reference")

    def test_units_scales_and_requested_period_cannot_be_assumed(self):
        for question in (
            self.question.replace("2008", "2035"),
            self.question.replace("estimated", "actual"),
            self.question.replace("MMBoe", "Bcf"),
            "What percentage comes from Canada?",
        ):
            with self.subTest(question=question), self.assertRaises(EvidenceError):
                calculate(plan(self.ids), question, self.corpus["cells"], self.chunks)
        cells = deepcopy(self.corpus["cells"])
        next(cell for cell in cells if cell["cell_id"] == self.ids[0])["column_header"] = (
            "Gas (Bcf)"
        )
        with self.assertRaises(EvidenceError) as error:
            calculate(plan(self.ids), self.question, cells, self.chunks)
        self.assertEqual(error.exception.code, "incompatible_units_or_scales")
        cells = deepcopy(self.corpus["cells"])
        for cell in cells:
            cell["column_header"] = "Amount"
        with self.assertRaises(EvidenceError) as error:
            calculate(plan(self.ids), self.question, cells, self.chunks)
        self.assertEqual(error.exception.code, "ambiguous_unit")
        # Explicitly different monetary scales must not be silently converted.
        chunks = deepcopy(self.chunks)
        for cell in cells:
            cell["source_value"] = "$" + cell["source_value"]
        for chunk in chunks:
            scale = "thousands" if self.ids[0] in chunk["cell_ids"] else "millions"
            chunk["text"] = (
                "Before table:\nEstimates for 2008.\nColumns: Dollars in "
                + scale
                + " | Amount\nRow"
            )
        with self.assertRaises(EvidenceError) as error:
            calculate(plan(self.ids), self.question, cells, chunks)
        self.assertEqual(error.exception.code, "incompatible_units_or_scales")

    def retriever(self, hits=None):
        retriever = Mock()
        retriever.validate_request.return_value = None
        retriever.manifest = {
            "corpus_version": "simulated-corpus",
            "index_version": "simulated-index",
        }
        retriever.corpus = self.corpus
        retriever.search.return_value = {
            "hits": self.chunks if hits is None else hits,
            "query_embedding": None,
        }
        return retriever

    def test_shared_workflow_only_one_search_generation_and_no_reference_context(self):
        retriever, provider = self.retriever(), Mock()
        provider.generate_json.return_value = (plan(self.ids), {"status": "passed", "usage": None})
        result = analyze(self.question, retriever, provider, journal=self.journal)
        self.assertEqual(result["status"], "success")
        retriever.search.assert_called_once()
        provider.generate_json.assert_called_once()
        supplied = json.loads(provider.generate_json.call_args.args[0])
        self.assertEqual(set(supplied), {"question", "chunks"})
        self.assertEqual(
            {cell["cell_id"] for chunk in supplied["chunks"] for cell in chunk["cells"]},
            {cell for chunk in self.chunks for cell in chunk["cell_ids"]},
        )
        self.assertNotIn("ANNOTATION-SECRET", json.dumps(supplied))
        self.assertEqual(
            {line for hit in self.chunks for line in hit["text"].splitlines()},
            {line for hit in supplied["chunks"] for line in hit["text"].splitlines()},
        )
        self.assertLess(
            sum(len(hit["text"]) for hit in supplied["chunks"]),
            sum(len(hit["text"]) for hit in self.chunks),
        )

        with closing(sqlite3.connect(self.journal)) as database:
            saved = json.loads(
                database.execute(
                    "SELECT record_json FROM analyses WHERE run_id=?", (result["run_id"],)
                ).fetchone()[0]
            )
        self.assertEqual(saved, result)

    def test_explicit_outcomes_and_preserved_provider_failures(self):
        for state in ("insufficient_evidence", "unsupported_request"):
            provider = Mock()
            provider.generate_json.return_value = (
                CellSelection(status=state, operation=None, cell_ids=[]),
                {"status": "passed", "usage": None},
            )
            result = analyze(self.question, self.retriever(), provider, journal=self.journal)
            self.assertEqual(result["status"], state)
            self.assertIsNone(result["calculation"])
        provider = Mock()
        provider.generate_json.side_effect = ProviderError(
            "simulated_quota", {"status": "failed", "usage": None}
        )
        result = analyze(self.question, self.retriever(), provider, journal=self.journal)
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["call"]["usage"])
        provider.generate_json.assert_called_once()
        provider.generate_json.side_effect = ProviderError(
            "budget_limit", {"status": "blocked", "usage": None}
        )
        self.assertEqual(
            analyze(self.question, self.retriever(), provider, journal=self.journal)["status"],
            "blocked",
        )

    def test_preflight_deadline_empty_hits_and_recording_failures_stop_calls(self):
        provider = Mock()
        result = analyze(self.question, self.retriever([]), provider, journal=self.journal)
        self.assertEqual(result["error_code"], "no_numeric_candidates")
        provider.generate_json.assert_not_called()
        result = analyze(
            self.question,
            self.retriever(),
            provider,
            journal=self.journal,
            clock=Mock(side_effect=[0, 61]),
        )
        self.assertEqual(result["status"], "blocked")
        provider.generate_json.assert_not_called()
        invalid = self.retriever()
        invalid.validate_request.side_effect = ValueError("invalid explicit scope")
        with self.assertRaises(ValueError):
            analyze(self.question, invalid, provider, journal=self.journal)
        invalid.search.assert_not_called()
        with patch(
            "app.service.save_analysis",
            side_effect=sqlite3.OperationalError("simulated recording failure"),
        ):
            with self.assertRaises(sqlite3.OperationalError):
                analyze(self.question, self.retriever(), provider, journal=self.journal)
        provider.generate_json.assert_not_called()
        with self.assertRaises(EvidenceError):
            model_input(
                self.question, [{**self.chunks[0], "text": "x" * 20001}], self.corpus["cells"]
            )


if __name__ == "__main__":
    unittest.main()
