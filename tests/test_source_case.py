"""Source boundaries and cumulative limits; no live model credentials required."""

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from app.llm import GeminiProvider, ProviderError, create_client
from app.schemas import CellSelection, SourceDocument
from scripts.run_source_case import run_source_case


def source_fixture():
    table = [["", "Total (MMBoe)"], ["Canada", "60"], ["Total", "243"]]
    return {
        "filename": "public/report",
        "pre_text": ["Estimated production for 2008."],
        "post_text": [],
        "table": table,
        "table_ori": table,
    }


class SourceCaseTests(unittest.TestCase):
    def test_source_and_plan_boundaries(self):
        data = source_fixture()
        with self.assertRaises(ValidationError):
            SourceDocument.model_validate({**data, "answer": "24.69%"})
        source = SourceDocument.model_validate(data)
        payload = json.loads(source.model_input("What percentage comes from Canada?"))
        self.assertEqual(set(payload), {"question", "source"})
        self.assertEqual(payload["source"]["table_rows"][1][1]["text"], "60")
        for plan in (
            {"status": "ready", "operation": "ratio_percent", "cell_ids": ["x", "x"]},
            {"status": "insufficient_evidence", "operation": "ratio_percent", "cell_ids": []},
            {"status": "ready", "operation": "ratio_percent", "cell_ids": ["x", "y"], "answer": 1},
        ):
            with self.subTest(plan=plan), self.assertRaises(ValidationError):
                CellSelection.model_validate(plan)
        plan = CellSelection(
            status="ready",
            operation="ratio_percent",
            cell_ids=[source.cell_id(1, 1), "other/report#table[2][1]"],
        )
        with self.assertRaises(ValueError):
            source.resolve_selection(plan)

    def test_budget_blocks_the_network_and_records_the_block(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict("os.environ", {"GEMINI_API_KEY": "fake-test-key"}),
            create_client() as client,
            patch("httpx.Client.send") as send,
        ):
            journal = Path(folder) / "calls.sqlite"
            provider = GeminiProvider(client, journal)
            with closing(sqlite3.connect(journal)) as database, database:
                database.execute("UPDATE calls SET allowance_eur = '24.50'")
            with self.assertRaises(ProviderError) as failure:
                provider.generate_json("Test", CellSelection, run_id="blocked-test")
            self.assertEqual(str(failure.exception), "budget_limit")
            send.assert_not_called()
            with closing(sqlite3.connect(journal)) as database:
                records = [
                    json.loads(row[0]) for row in database.execute("SELECT record_json FROM calls")
                ]
            self.assertEqual(records[-1]["status"], "blocked")

    def test_invalid_cell_is_not_a_success_and_usage_is_retained(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict("os.environ", {"GEMINI_API_KEY": "fake-test-key"}),
            create_client() as client,
        ):
            source = SourceDocument.model_validate(source_fixture())
            output = {
                "status": "ready",
                "operation": "ratio_percent",
                "cell_ids": [source.cell_id(1, 1), "invented#table[2][1]"],
            }

            def respond(request, **kwargs):
                sent = json.loads(request.content)
                self.assertEqual(sent["generationConfig"]["maxOutputTokens"], 1000)
                self.assertNotIn("answer", sent["contents"][0]["parts"][0]["text"])
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "modelVersion": "gemini-3.5-flash-lite",
                        "usageMetadata": {
                            "promptTokenCount": 10,
                            "candidatesTokenCount": 10,
                            "totalTokenCount": 20,
                        },
                        "candidates": [
                            {
                                "finishReason": "STOP",
                                "content": {
                                    "role": "model",
                                    "parts": [{"text": json.dumps(output)}],
                                },
                            }
                        ],
                    },
                )

            with patch("httpx.Client.send", side_effect=respond) as send:
                result = run_source_case(
                    GeminiProvider(client, Path(folder) / "calls.sqlite"),
                    source,
                    "What share comes from Canada?",
                    "Select cells.",
                    None,
                )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_code"], "invalid_cell_reference")
            self.assertEqual(result["call"]["usage"]["total_tokens"], 20)
            self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
