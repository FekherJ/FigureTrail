"""Exercise native tool calls and execution boundaries with a simulated provider."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from app.llm import GeminiProvider, create_client
from app.schemas import SourceDocument
from scripts.check_tool_call import run_check


class ToolCallTests(unittest.TestCase):
    def test_native_call_and_rejected_requests(self):
        table = [["", "Total (MMBoe)"], ["Canada", "60"], ["Total", "243"]]
        source = SourceDocument(
            filename="public/report",
            pre_text=["Estimates for 2008."],
            post_text=[],
            table=table,
            table_ori=table,
        )
        ids = [source.cell_id(1, 1), source.cell_id(2, 1)]

        def native(arguments, name="read_evidence"):
            return {"functionCall": {"name": name, "args": arguments, "id": "test-call"}}

        valid = native({"cell_ids": ids})
        cases = (
            ("valid", [valid], "STOP", "passed", 1),
            ("unknown tool", [native({"cell_ids": ids}, "run_shell")], "STOP", "failed", 0),
            ("parallel calls", [valid, valid], "STOP", "failed", 0),
            ("text pretending to be a call", [{"text": json.dumps(valid)}], "STOP", "failed", 0),
            ("extra argument", [native({"cell_ids": ids, "path": "private"})], "STOP", "failed", 0),
            ("wrong type", [native({"cell_ids": "not-a-list"})], "STOP", "failed", 0),
            ("duplicate IDs", [native({"cell_ids": [ids[0], ids[0]]})], "STOP", "failed", 0),
            ("too many IDs", [native({"cell_ids": ids + ["third"]})], "STOP", "failed", 0),
            ("truncated", [valid], "MAX_TOKENS", "failed", 0),
            (
                "other report",
                [native({"cell_ids": [ids[0], "other#table[2][1]"]})],
                "STOP",
                "failed",
                1,
            ),
            ("header cell", [native({"cell_ids": [source.cell_id(0, 1)]})], "STOP", "failed", 1),
        )
        for label, parts, finish, status, executions in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as folder:

                def respond(request, **kwargs):
                    sent = json.loads(request.content)
                    self.assertEqual(sent["generationConfig"]["maxOutputTokens"], 256)
                    self.assertEqual(sent["toolConfig"]["functionCallingConfig"]["mode"], "AUTO")
                    declarations = sent["tools"][0]["functionDeclarations"]
                    self.assertEqual([tool["name"] for tool in declarations], ["read_evidence"])
                    self.assertFalse(
                        declarations[0]["parameters_json_schema"]["additionalProperties"]
                    )
                    return httpx.Response(
                        200,
                        request=request,
                        json={
                            "modelVersion": "gemini-3.5-flash-lite",
                            "usageMetadata": {"totalTokenCount": 20},
                            "candidates": [
                                {
                                    "finishReason": finish,
                                    "content": {
                                        "role": "model",
                                        "parts": [
                                            {"text": "private-thought-marker", "thought": True}
                                        ]
                                        + parts,
                                    },
                                }
                            ],
                        },
                    )

                destination = Path(folder) / "result.json"
                report = {"run_id": "simulated-tool-check", "status": "started", "tool_event": None}
                with (
                    patch.dict("os.environ", {"GEMINI_API_KEY": "fake-test-key"}),
                    create_client() as client,
                    patch("httpx.Client.send", side_effect=respond) as send,
                    patch.object(
                        SourceDocument,
                        "read_evidence",
                        autospec=True,
                        side_effect=SourceDocument.read_evidence,
                    ) as read,
                ):
                    run_check(
                        GeminiProvider(client, Path(folder) / "calls.sqlite"),
                        source,
                        "Use the allowed tool.",
                        report,
                        destination,
                    )
                self.assertEqual(send.call_count, 1)
                self.assertEqual(read.call_count, executions)
                self.assertEqual(report["status"], status)
                self.assertEqual(report["call"]["usage"]["total_tokens"], 20)
                saved = destination.read_text(encoding="utf-8")
                self.assertNotIn("fake-test-key", saved)
                self.assertNotIn("private-thought-marker", saved)
                if status == "passed":
                    self.assertEqual(
                        [cell["source_value"] for cell in report["tool_event"]["result"]],
                        ["60", "243"],
                    )
                else:
                    self.assertNotIn("result", report.get("tool_event") or {})

    def test_quota_failure_stops_after_one_request(self):
        with tempfile.TemporaryDirectory() as folder:

            def respond(request, **kwargs):
                return httpx.Response(
                    429,
                    request=request,
                    json={
                        "error": {
                            "code": 429,
                            "status": "RESOURCE_EXHAUSTED",
                            "message": "fake-test-key must stay private",
                        }
                    },
                )

            source = SourceDocument(
                filename="source",
                pre_text=[],
                post_text=[],
                table=[["", "Value"], ["A", "1"]],
                table_ori=[["", "Value"], ["A", "1"]],
            )
            report = {"run_id": "simulated-quota", "status": "started", "tool_event": None}
            destination = Path(folder) / "result.json"
            with (
                patch.dict("os.environ", {"GEMINI_API_KEY": "fake-test-key"}),
                create_client() as client,
                patch("httpx.Client.send", side_effect=respond) as send,
            ):
                run_check(
                    GeminiProvider(client, Path(folder) / "calls.sqlite"),
                    source,
                    "Use the allowed tool.",
                    report,
                    destination,
                )
            self.assertEqual(send.call_count, 1)
            self.assertEqual(report["status"], "failed")
            self.assertIsNone(report["tool_event"])
            self.assertIsNone(report["call"]["usage"])
            self.assertEqual(report["call"]["reserved_eur"], report["call"]["allowance_eur"])
            self.assertNotIn("fake-test-key", destination.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
