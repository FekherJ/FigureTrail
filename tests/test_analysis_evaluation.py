"""Initial answer scoring retains abstentions and transport failures in denominators."""

from contextlib import closing, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import Mock, patch
import unittest

from evals import analysis as evaluation
from evals.analysis import (
    NEGATIVE_CASES,
    SCORING_POLICY,
    compare_reports,
    plan_campaign,
    provider_metrics,
    run_cases,
    score,
)


class AnalysisEvaluationTests(unittest.TestCase):
    def test_correct_answer_failure_and_negative_outcomes_are_scored_separately(self):
        references = {
            "cases": [
                {
                    "case_id": "A/2000/page.pdf-1",
                    "application_question": "First question",
                    "operation": "ratio_percent",
                    "operands": [{"cell": [1, 1]}, {"cell": [2, 1]}],
                    "expected_percent": "25",
                    "exe_ans_tolerance": "0.000005",
                },
                {
                    "case_id": "B/2000/page.pdf-1",
                    "application_question": "Second question",
                    "operation": "ratio_percent",
                    "operands": [{"cell": [1, 1]}, {"cell": [2, 1]}],
                    "expected_percent": "50",
                    "exe_ans_tolerance": "0.000005",
                },
            ]
        }
        results = [
            {
                "case_id": "C01",
                "question": "First question",
                "status": "success",
                "duration_seconds": 1,
                "selection": {
                    "operation": "ratio_percent",
                    "cell_ids": ["A/2000/page.pdf#table[1][1]", "A/2000/page.pdf#table[2][1]"],
                },
                "retrieval": {
                    "hits": [
                        {"cell_ids": ["A/2000/page.pdf#table[1][1]", "A/2000/page.pdf#table[2][1]"]}
                    ]
                },
                "calculation": {"value": "25"},
            },
            {
                "case_id": "C02",
                "question": "Second question",
                "status": "failed",
                "duration_seconds": 20,
                "calculation": None,
            },
            *[
                {
                    "case_id": case["id"],
                    "question": case["question"],
                    "status": case["expected_status"],
                    "calculation": None,
                }
                for case in NEGATIVE_CASES
            ],
        ]
        metrics = score(results, references)
        self.assertEqual(metrics["development_cases"], 2)
        self.assertEqual(metrics["correct_answers"], 1)
        self.assertEqual(metrics["technical_failures"], 1)
        self.assertEqual(metrics["correct_negative_outcomes"], 2)
        altered = deepcopy(results)
        altered[0]["selection"]["cell_ids"].reverse()
        self.assertEqual(score(altered, references)["correct_answers"], 0)
        altered[1]["status"] = "insufficient_evidence"
        altered_metrics = score(altered, references)
        self.assertEqual(altered_metrics["answer_abstentions"], 1)
        self.assertEqual(altered_metrics["development_cases"], 2)

    def scored_fixture(self):
        reference = {
            "case_id": "A/2000/page.pdf-1",
            "application_question": "Share in 2001?",
            "operation": "ratio_percent",
            "unit": "dollar ($)",
            "scale": "million",
            "operands": [
                {"cell": [1, 1], "period": "Fiscal year 2001"},
                {"cell": [2, 1], "period": "Fiscal year 2001"},
            ],
            "expected_percent": "25",
            "exe_ans_tolerance": "0.000005",
        }
        ids = ["A/2000/page.pdf#table[1][1]", "A/2000/page.pdf#table[2][1]"]
        result = {
            "case_id": "C01",
            "question": reference["application_question"],
            "status": "success",
            "attempted": True,
            "duration_seconds": 1,
            "selection": {"operation": "ratio_percent", "cell_ids": ids},
            "retrieval": {"hits": [{"cell_ids": ids}]},
            "calculation": {
                "value": "25",
                "operands": [
                    {"context": {"unit": "$", "scale": 1000000, "year": 2001}} for _ in ids
                ],
            },
        }
        negatives = [
            {
                "case_id": c["id"],
                "question": c["question"],
                "status": c["expected_status"],
                "attempted": True,
                "duration_seconds": 1,
                "calculation": None,
            }
            for c in NEGATIVE_CASES
        ]
        return [result, *negatives], {"cases": [reference]}

    def test_wrong_evidence_units_years_and_nonfinite_values_are_not_correct_answers(self):
        results, refs = self.scored_fixture()
        self.assertEqual(score(deepcopy(results), refs)["correct_answers"], 1)
        for fault in ("evidence", "unit", "scale", "year", "nan"):
            with self.subTest(fault=fault):
                altered = deepcopy(results)
                if fault == "evidence":
                    altered[0]["retrieval"]["hits"] = []
                elif fault == "nan":
                    altered[0]["calculation"]["value"] = "NaN"
                else:
                    altered[0]["calculation"]["operands"][0]["context"][fault] = "wrong"
                self.assertEqual(score(altered, refs)["correct_answers"], 0)

    def test_negative_identity_mismatch_is_rejected(self):
        results, refs = self.scored_fixture()
        results[-2], results[-1] = results[-1], results[-2]
        with self.assertRaises(ValueError):
            score(results, refs)

    def test_plan_is_read_only_and_counts_unique_missing_embeddings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "absent-project"
            journal = root / "data/local/runs.sqlite"
            cases = [
                {"id": f"C{i:02d}", "question": "Same question?", "report_ids": None}
                for i in (1, 2)
            ]
            plan = plan_campaign(root, cases, "semantic", journal)
            self.assertEqual(plan["maximum_generation_requests"], 2)
            self.assertEqual(plan["maximum_embedding_requests"], 1)
            self.assertEqual(plan["additional_allowance_reservation_eur"], "2.03")
            self.assertFalse(root.exists())
            journal.parent.mkdir(parents=True)
            with closing(sqlite3.connect(journal)) as database, database:
                database.execute("CREATE TABLE calls (allowance_eur TEXT)")
                database.execute("INSERT INTO calls VALUES ('24')")
            before = journal.read_bytes()
            blocked = plan_campaign(root, cases, "lexical", journal)
            self.assertFalse(blocked["fits_local_allowance"])
            self.assertEqual(blocked["maximum_embedding_requests"], 0)
            self.assertEqual(journal.read_bytes(), before)
            self.assertFalse((root / "data/local/query-embeddings.sqlite").exists())

    def test_campaign_storage_failure_blocks_every_remaining_analysis(self):
        cases = [
            {"id": f"C{i:02d}", "question": f"Question {i}", "report_ids": None} for i in (1, 2, 3)
        ]
        execute = Mock(side_effect=sqlite3.OperationalError("simulated storage failure"))
        with patch.object(evaluation, "analyze", execute), redirect_stdout(io.StringIO()):
            results = run_cases(
                cases, "lexical", Mock(), Mock(), journal=Path("temporary.sqlite"), save=Mock()
            )
        execute.assert_called_once()
        self.assertEqual([item["status"] for item in results], ["failed", "blocked", "blocked"])
        self.assertEqual([item["attempted"] for item in results], [True, False, False])
        self.assertTrue(
            all(item["error_code"] == "campaign_recording_failure" for item in results[1:])
        )
        self.assertEqual(set(execute.call_args.kwargs), {"method", "report_ids", "journal"})

    def test_report_write_failure_stops_before_another_analysis(self):
        cases = [
            {"id": f"C{i:02d}", "question": f"Question {i}", "report_ids": None} for i in (1, 2)
        ]
        execute = Mock(return_value={"status": "success", "duration_seconds": 1})
        with patch.object(evaluation, "analyze", execute), self.assertRaises(OSError):
            run_cases(
                cases,
                "semantic",
                Mock(),
                Mock(),
                journal=Path("temporary.sqlite"),
                save=Mock(side_effect=OSError("simulated report failure")),
            )
        execute.assert_called_once()

    def comparison_reports(self):
        results, references = self.scored_fixture()
        common = {
            "status": "completed",
            "scoring_policy": deepcopy(SCORING_POLICY),
            **{
                field: "same"
                for field in (
                    "case_fixture_sha256",
                    "reference_sha256",
                    "evaluator_sha256",
                    "corpus_version",
                    "index_version",
                    "prompt_sha256",
                    "campaign_pacing",
                )
            },
        }
        reports = []
        for method in ("lexical", "semantic"):
            report = {
                **deepcopy(common),
                "run_id": method,
                "method": method,
                "workflow_identity": {
                    "code_sha256": "same",
                    "configuration": {"k": 5, "retrieval": {"method": method}},
                },
                "plan": {"planned_cases": len(results)},
                "results": deepcopy(results),
            }
            report["metrics"] = score(report["results"], references)
            reports.append(report)
        return reports, references

    def test_comparison_matches_inputs_and_preserves_case_differences(self):
        (lexical, semantic), references = self.comparison_reports()
        self.assertEqual(compare_reports(lexical, semantic)["accuracy_delta_percentage_points"], 0)
        semantic["results"][0]["selection"]["cell_ids"].reverse()
        semantic["metrics"] = score(semantic["results"], references)
        compared = compare_reports(semantic, lexical)
        self.assertEqual(compared["accuracy_delta_percentage_points"], -100)
        self.assertFalse(compared["cases"][0]["semantic_evaluation"]["correct_answer"])
        for field in ("reference_sha256", "evaluator_sha256", "corpus_version", "index_version"):
            with self.subTest(field=field):
                changed = deepcopy(semantic)
                changed[field] = "different"
                with self.assertRaises(ValueError):
                    compare_reports(lexical, changed)
        changed = deepcopy(semantic)
        changed["workflow_identity"]["configuration"]["k"] = 3
        with self.assertRaises(ValueError):
            compare_reports(lexical, changed)

    def test_unknown_usage_cost_and_unattempted_latency_remain_explicit(self):
        results, references = self.scored_fixture()
        results[0]["call"] = {
            "call_id": "failed-call",
            "kind": "generation",
            "usage": None,
            "estimated_paid_cost_usd": None,
        }
        results[0]["retrieval"]["query_embedding"] = {
            "call": None,
            "provider_call_id": "historical-cached-call",
        }
        results[-1]["call"] = {
            "call_id": "known-call",
            "kind": "generation",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 2,
                "thought_tokens": 0,
                "total_tokens": 12,
            },
            "estimated_paid_cost_usd": "0.01",
        }
        metrics = provider_metrics(results)
        self.assertEqual(metrics["call_records"], 2)
        self.assertEqual(metrics["calls_with_unknown_usage"], 1)
        self.assertIsNone(metrics["reported_tokens"]["total_tokens"])
        self.assertIsNone(metrics["estimated_paid_cost_usd"])
        self.assertEqual(metrics["known_estimated_paid_cost_usd"], "0.01")
        blocked = {
            "case_id": "C02",
            "question": "Another question?",
            "status": "blocked",
            "attempted": False,
            "duration_seconds": 0,
            "calculation": None,
        }
        results.insert(1, blocked)
        references["cases"].append(
            {**deepcopy(references["cases"][0]), "application_question": blocked["question"]}
        )
        metrics = score(results, references)
        self.assertEqual(metrics["development_cases"], 2)
        self.assertEqual(metrics["answer_accuracy"], 0.5)
        self.assertEqual(metrics["latency_attempted_cases"], 1)
        self.assertEqual(metrics["median_development_seconds"], 1)

    def test_cli_plans_without_clients_and_loads_references_after_execution(self):
        results, references = self.scored_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "evals/queries").mkdir(parents=True)
            (root / "evals/cases").mkdir()
            (root / "prompts").mkdir()
            (root / "prompts/analysis_selection.md").write_text(
                "Trusted test prompt", encoding="utf-8"
            )
            (root / "evals/queries/finqa-b05.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "partition": "development",
                        "cases": [
                            {"id": "C01", "question": results[0]["question"], "report_ids": None}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            reference_path = root / "evals/cases/finqa-b01-reviewed.json"
            reference_path.write_text(json.dumps(references), encoding="utf-8")
            events = []
            original_read = Path.read_bytes

            def read(path):
                if path == reference_path:
                    events.append("references")
                return original_read(path)

            def execute(question, retriever, provider, **kwargs):
                self.assertEqual(set(kwargs), {"method", "report_ids", "journal"})
                events.append("analysis")
                return deepcopy(next(item for item in results if item["question"] == question))

            client, create = Mock(), Mock()
            create.return_value = client
            retriever = Mock()
            retriever.manifest = {"corpus_version": "test-corpus", "index_version": "test-index"}
            provider_factory = Mock(return_value=Mock())
            with (
                patch.multiple(
                    evaluation,
                    ROOT=root,
                    JOURNAL=root / "data/local/runs.sqlite",
                    create_client=create,
                    GeminiProvider=provider_factory,
                    load_current=Mock(return_value=retriever),
                    execution_identity=Mock(return_value={"code_sha256": "test-code"}),
                    analyze=Mock(side_effect=execute),
                ),
                redirect_stdout(io.StringIO()),
            ):
                with patch("sys.argv", ["evals.analysis"]):
                    self.assertEqual(evaluation.main(), 0)
                create.assert_not_called()
                self.assertFalse((root / "data").exists())
                self.assertFalse((root / "evals/results").exists())
                with (
                    patch("sys.argv", ["evals.analysis", "--method", "lexical", "--live"]),
                    patch.object(Path, "read_bytes", read),
                ):
                    self.assertEqual(evaluation.main(), 0)
                self.assertEqual(events, ["analysis", "analysis", "analysis", "references"])
                client.close.assert_called_once()
                client.close.reset_mock()
                provider_factory.side_effect = sqlite3.OperationalError(
                    "simulated provider setup failure"
                )
                with (
                    patch("sys.argv", ["evals.analysis", "--method", "lexical", "--live"]),
                    self.assertRaises(sqlite3.Error),
                ):
                    evaluation.main()
                client.close.assert_called_once()

    def test_quota_error_blocks_subsequent_calls_without_retry(self):
        cases = [
            {"id": f"C{i:02d}", "question": f"Question {i}", "report_ids": None} for i in (1, 2, 3)
        ]
        execute = Mock(
            return_value={
                "status": "failed",
                "error_code": "provider_http_429",
                "duration_seconds": 1,
            }
        )
        with patch.object(evaluation, "analyze", execute), redirect_stdout(io.StringIO()):
            results = run_cases(
                cases, "semantic", Mock(), Mock(), journal=Path("temporary.sqlite"), save=Mock()
            )
        execute.assert_called_once()
        self.assertEqual([item["status"] for item in results], ["failed", "blocked", "blocked"])
        self.assertTrue(
            all(item["error_code"] == "campaign_provider_quota" for item in results[1:])
        )

    def test_generation_pacing_uses_journal_history_and_ignores_embeddings(self):
        with tempfile.TemporaryDirectory() as folder:
            journal = Path(folder) / "runs.sqlite"
            now, pauses = [10000.0], []
            stamp = datetime.fromtimestamp(now[0] - 1, timezone.utc).isoformat()
            with closing(sqlite3.connect(journal)) as database, database:
                database.execute("CREATE TABLE calls (record_json TEXT)")
                for _ in range(evaluation.GENERATION_RPM):
                    database.execute(
                        "INSERT INTO calls VALUES (?)",
                        (
                            json.dumps(
                                {"kind": "generation", "created_at_utc": stamp, "status": "failed"}
                            ),
                        ),
                    )
                database.execute(
                    "INSERT INTO calls VALUES (?)",
                    (json.dumps({"kind": "embedding", "created_at_utc": stamp}),),
                )
            before = journal.read_bytes()

            def pause(seconds):
                pauses.append(seconds)
                now[0] += seconds

            waited = evaluation.wait_for_generation_slot(journal, clock=lambda: now[0], pause=pause)
            self.assertTrue(pauses)
            self.assertGreaterEqual(waited, 59)
            self.assertLessEqual(waited, 61)
            self.assertTrue(all(0 < seconds <= 1 for seconds in pauses))
            self.assertEqual(journal.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
