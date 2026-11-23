"""Budget planning and matched paired execution without hosted requests."""

from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from evals.agent import execute_pairs, plan_comparison
from evals.analysis import score
import test_analysis_evaluation as evaluation_fixtures


class AgentEvaluationTests(unittest.TestCase):
    def test_worst_case_plan_counts_both_modes_and_rewritten_query_embeddings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "absent"
            cases = [{"id": "C01", "question": "A question?", "report_ids": None}]
            plan = plan_comparison(root, cases, "semantic", root / "journal.sqlite")
            self.assertEqual(plan["maximum_generation_requests"], 5)
            self.assertEqual(plan["maximum_embedding_requests"], 3)
            self.assertEqual(plan["additional_allowance_reservation_eur"], "5.05")
            self.assertFalse(root.exists())

    def test_both_modes_get_same_question_scope_and_storage_fault_stops_campaign(self):
        cases = [
            {"id": f"C{i:02d}", "question": f"Question {i}", "report_ids": None} for i in (1, 2)
        ]
        fixed = Mock(return_value={"status": "success"})
        agent = Mock(return_value={"status": "success"})
        with (
            patch("evals.agent.analyze", fixed),
            patch("evals.agent.run_agent", agent),
            patch("evals.agent.wait_for_generation_slot", return_value=0),
        ):
            pairs = execute_pairs(cases, "semantic", Mock(), Mock(), Path("missing.sqlite"), Mock())
        self.assertEqual(
            [call.args[0] for call in fixed.call_args_list], ["Question 1", "Question 2"]
        )
        self.assertEqual(
            [call.args[0] for call in agent.call_args_list], ["Question 1", "Question 2"]
        )
        self.assertEqual(len(pairs), 2)
        fixed.side_effect = OSError("private")
        agent.reset_mock()
        with (
            patch("evals.agent.analyze", fixed),
            patch("evals.agent.run_agent", agent),
            patch("evals.agent.wait_for_generation_slot", return_value=0),
        ):
            pairs = execute_pairs(cases, "semantic", Mock(), Mock(), Path("missing.sqlite"), Mock())
        agent.assert_not_called()
        self.assertEqual(pairs[-1]["agent"]["error_code"], "campaign_recording_failure")

    def test_cli_is_read_only_by_default_and_budget_rejection_precedes_clients(self):
        from evals import agent as cli

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixture = root / "evals/queries/finqa-b05.json"
            fixture.parent.mkdir(parents=True)
            fixture.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "partition": "development",
                        "cases": [
                            {"id": "C01", "question": "Public question?", "report_ids": None}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            create = Mock(side_effect=AssertionError("No client expected"))
            with (
                patch.multiple(
                    cli, ROOT=root, JOURNAL=root / "data/local/runs.sqlite", create_client=create
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                with patch("sys.argv", ["evals.agent"]):
                    self.assertEqual(cli.main(), 0)
                self.assertFalse((root / "data").exists())
                self.assertFalse((root / "evals/results").exists())
                with (
                    patch("sys.argv", ["evals.agent", "--live"]),
                    patch.object(
                        cli, "plan_comparison", return_value={"fits_local_allowance": False}
                    ),
                    self.assertRaises(SystemExit) as error,
                ):
                    cli.main()
                self.assertEqual(error.exception.code, 2)
                create.assert_not_called()

    def test_subset_scoring_preserves_case_identity_and_counts_all_agent_calls(self):
        results, references = evaluation_fixtures.AnalysisEvaluationTests().scored_fixture()
        result = deepcopy(results[0])
        result["case_id"] = "C07"
        result["calls"] = [
            {"call_id": str(i), "kind": "generation", "usage": None} for i in range(3)
        ]
        metrics = score(
            [result], references, positive_ids=["C07"], negative_cases=(), evidence_limit=None
        )
        self.assertEqual(metrics["correct_answers"], 1)
        self.assertEqual(metrics["provider"]["generation_records"], 3)
        self.assertEqual(metrics["negative_cases"], 0)
        result["retrieval"]["hits"].insert(0, {"cell_ids": []})
        from app.service import CONFIGURATION

        with patch.dict(CONFIGURATION, k=1):
            self.assertEqual(
                score([result], references, positive_ids=["C07"], negative_cases=())[
                    "correct_answers"
                ],
                0,
            )
            self.assertEqual(
                score(
                    [result],
                    references,
                    positive_ids=["C07"],
                    negative_cases=(),
                    evidence_limit=None,
                )["correct_answers"],
                1,
            )

        with self.assertRaises(ValueError):
            score([result], references, positive_ids=["C01"], negative_cases=())
