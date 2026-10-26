"""Initial answer scoring retains abstentions and transport failures in denominators."""

from copy import deepcopy
import unittest

from evals.analysis import NEGATIVE_CASES, score


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


if __name__ == "__main__":
    unittest.main()
