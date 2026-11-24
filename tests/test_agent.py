"""Bounded native tool decisions using simulated SDK responses only."""

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from google.genai import types

from app.agent import AGENT_CONFIG, run_agent
from app.corpus import prepare_corpus
from app.llm import GeminiProvider, create_client
from app.main import public_result
from app.service import read_analysis
from test_corpus import fixture

QUESTION = "What percentage of estimated 2008 production in MMBoe comes from Canada?"


def native(name, arguments, identifier="native-id"):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name=name, args=arguments, id=identifier
                            ),
                            thought_signature=b"opaque-signature",
                        )
                    ],
                ),
                finish_reason="STOP",
            )
        ],
        model_version="simulated-model",
        usage_metadata=None,
    )


def text_response(text):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=[types.Part(text=text)]),
                finish_reason="STOP",
            )
        ],
        model_version="simulated-model",
    )


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.journal = Path(self.folder.name) / "runs.sqlite"
        self.corpus, _ = prepare_corpus(*fixture())
        self.hits = [
            {**chunk, "rank": i, "score": 1.0}
            for i, chunk in enumerate(
                (c for c in self.corpus["chunks"] if c["source_id"] == "DVN/2007/page_58.pdf"), 1
            )
        ]
        self.chunks = [c["chunk_id"] for c in self.hits if c["cell_ids"]]
        self.ids = ["DVN/2007/page_58.pdf#table[1][1]", "DVN/2007/page_58.pdf#table[3][1]"]
        self.retriever = Mock()
        self.retriever.corpus = self.corpus
        self.retriever.validate_request.return_value = ["DVN/2007"]
        self.retriever.manifest = {"corpus_version": "test-corpus", "index_version": "test-index"}
        self.retriever.search.return_value = {"hits": self.hits, "query_embedding": None}

    def execute(self, responses, **kwargs):
        self.send = Mock(side_effect=responses)
        sdk = SimpleNamespace(models=SimpleNamespace(generate_content=self.send))
        self.provider = GeminiProvider(sdk, self.journal)
        with patch("app.agent.wait_for_generation_slot", return_value=0):
            return run_agent(
                QUESTION,
                self.retriever,
                self.provider,
                journal=self.journal,
                report_ids=["DVN/2007"],
                **kwargs,
            )

    def sequence(self):
        return [
            native("search_evidence", {"query": QUESTION}),
            native("read_evidence", {"chunk_ids": self.chunks}),
            native("calculate", {"operation": "ratio_percent", "cell_ids": self.ids}),
        ]

    def test_native_sequence_preserves_signatures_scope_and_source_calculation(self):
        result = self.execute(self.sequence())
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["calculation"]["display"], "24.69 %")
        self.assertEqual(
            [e["name"] for e in result["tool_events"]],
            ["search_evidence", "read_evidence", "calculate"],
        )
        self.assertEqual(len(result["calls"]), 3)
        self.assertEqual(result["mode"], "agent")
        self.assertEqual(read_analysis(self.journal, result["run_id"]), result)
        self.assertEqual(public_result(result).mode, "agent")
        self.assertEqual(len(public_result(result).calls), 3)
        self.retriever.search.assert_called_once()
        self.assertEqual(self.retriever.search.call_args.kwargs["report_ids"], ["DVN/2007"])
        self.assertNotIn("ANNOTATION-SECRET", str(self.send.call_args_list))
        history = self.send.call_args_list[1].kwargs["contents"]
        self.assertEqual(history[1].parts[0].thought_signature, b"opaque-signature")
        self.assertEqual(history[2].parts[0].function_response.id, "native-id")
        self.assertNotIn("opaque-signature", json.dumps(result))
        self.assertEqual(result["configuration"]["agent"], AGENT_CONFIG)

    def test_search_previews_identify_rows_without_granting_cell_access(self):
        for hit in self.hits:
            hit["text"] = "Shared introductory paragraph. " * 40 + "\n" + hit["text"]
        result = self.execute(
            [
                native("search_evidence", {"query": QUESTION}),
                native("calculate", {"operation": "ratio_percent", "cell_ids": self.ids}),
                text_response(
                    json.dumps(
                        {"status": "insufficient_evidence", "operation": None, "cell_ids": []}
                    )
                ),
            ]
        )
        previews = result["tool_events"][0]["result"]["hits"]
        canada = next(hit for hit in previews if hit["chunk_id"] == self.chunks[0])
        self.assertIn("Canada", canada["preview"])
        self.assertIn("Columns:", canada["preview"])
        self.assertIn("MMBoe", canada["preview"])
        self.assertNotIn("Shared introductory", canada["preview"])
        self.assertEqual(canada["kind"], "table_row")
        self.assertLessEqual(len(canada["preview"]), 400)
        self.assertEqual(result["retrieval"]["hits"], self.hits)
        self.assertEqual(result["tool_events"][1]["status"], "rejected")
        self.assertEqual(result["tool_events"][1]["error_code"], "invalid_cell_reference")
        self.assertIsNone(result["calculation"])

    def test_native_http_round_trip_preserves_ids_without_recording_thoughts(self):
        import base64
        import httpx

        requests = []
        steps = [
            ("search_evidence", {"query": QUESTION}),
            ("read_evidence", {"chunk_ids": self.chunks}),
            ("calculate", {"operation": "ratio_percent", "cell_ids": self.ids}),
        ]

        def respond(request, **kwargs):
            payload = json.loads(request.content)
            requests.append(payload)
            name, arguments = steps[len(requests) - 1]
            self.assertEqual(len(payload["tools"][0]["functionDeclarations"]), 3)
            if len(requests) > 1:
                previous = payload["contents"][-2]["parts"][-1]
                self.assertEqual(
                    previous["thoughtSignature"], base64.b64encode(b"opaque-signature").decode()
                )
                self.assertEqual(
                    payload["contents"][-1]["parts"][0]["functionResponse"]["id"], "native-id"
                )
            return httpx.Response(
                200,
                request=request,
                json={
                    "modelVersion": "simulated-model",
                    "usageMetadata": {"totalTokenCount": 20},
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {
                                "role": "model",
                                "parts": [
                                    {"text": "private-reasoning-marker", "thought": True},
                                    {
                                        "functionCall": {
                                            "name": name,
                                            "args": arguments,
                                            "id": "native-id",
                                        },
                                        "thoughtSignature": base64.b64encode(
                                            b"opaque-signature"
                                        ).decode(),
                                    },
                                ],
                            },
                        }
                    ],
                },
            )

        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "fake-test-key"}),
            create_client() as client,
            patch("httpx.Client.send", side_effect=respond),
            patch("app.agent.wait_for_generation_slot", return_value=0),
        ):
            result = run_agent(
                QUESTION, self.retriever, GeminiProvider(client, self.journal), journal=self.journal
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(requests), 3)
        self.assertNotIn("private-reasoning-marker", json.dumps(result))
        self.assertNotIn("fake-test-key", json.dumps(result))

    def test_cancellation_after_search_and_history_limit_stop_another_request(self):
        from threading import Event

        cancelled = Event()

        def search(*args, **kwargs):
            cancelled.set()
            return {"hits": self.hits, "query_embedding": None}

        self.retriever.search.side_effect = search
        result = self.execute(self.sequence(), cancelled=cancelled)
        self.assertEqual(result["error_code"], "deadline_reached")
        self.send.assert_called_once()
        with patch.dict(AGENT_CONFIG, max_history_characters=1):
            result = self.execute(self.sequence())
        self.assertEqual(result["error_code"], "context_too_large")
        self.send.assert_not_called()

    def test_abstention_and_free_numerical_text(self):
        result = self.execute(
            [
                text_response(
                    json.dumps(
                        {"status": "insufficient_evidence", "operation": None, "cell_ids": []}
                    )
                )
            ]
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.retriever.search.assert_not_called()
        for text in (
            "The answer is 24.69%",
            json.dumps({"status": "ready", "operation": "ratio_percent", "cell_ids": self.ids}),
        ):
            with self.subTest(text=text):
                result = self.execute([text_response(text)])
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["calculation"])

    def test_unknown_tools_extra_arguments_and_unread_cells_are_never_executed(self):
        for bad in (
            native("run_shell", {"command": "anything"}),
            native("search_evidence", {"query": QUESTION, "report_ids": ["OTHER/2014"]}),
            native("read_evidence", {"chunk_ids": ["not-retrieved"]}),
            native("calculate", {"operation": "ratio_percent", "cell_ids": self.ids}),
        ):
            with self.subTest(bad=bad):
                result = self.execute([bad] * 4)
                self.assertNotEqual(result["status"], "success")
                self.assertIsNone(result["calculation"])
                self.assertTrue(all(e["status"] == "rejected" for e in result["tool_events"]))
        self.retriever.search.assert_not_called()

    def test_search_generation_and_tool_limits_stop_subsequent_work(self):
        search = native("search_evidence", {"query": QUESTION})
        result = self.execute([search] * 4)
        self.assertEqual(self.send.call_count, 3)
        self.assertEqual(self.retriever.search.call_count, 2)
        self.assertEqual(result["error_code"], "search_limit")
        self.retriever.search.reset_mock()
        with patch.dict(AGENT_CONFIG, max_tool_calls=1):
            result = self.execute(self.sequence())
        self.assertEqual(result["error_code"], "tool_limit")
        self.assertEqual(self.send.call_count, 1)
        result = self.execute([native("read_evidence", {"chunk_ids": ["missing"]})] * 5)
        self.assertEqual(self.send.call_count, 4)
        self.assertEqual(result["error_code"], "generation_limit")

    def test_parallel_calls_are_rejected_without_executing_tools(self):
        response = native("search_evidence", {"query": QUESTION})
        response.candidates[0].content.parts *= 2
        result = self.execute([response])
        self.assertEqual(result["error_code"], "invalid_output")
        self.retriever.search.assert_not_called()

    def test_storage_budget_deadline_and_provider_errors_stop_calls(self):
        with patch("app.agent.save_analysis", side_effect=sqlite3.OperationalError("private")):
            with self.assertRaises(sqlite3.Error):
                self.execute(self.sequence())
        self.send.assert_not_called()
        with patch("app.llm.LIMIT_EUR", 0):
            result = self.execute(self.sequence())
        self.assertEqual(result["error_code"], "budget_limit")
        self.send.assert_not_called()
        result = self.execute(self.sequence(), deadline=0)
        self.assertEqual(result["error_code"], "deadline_reached")
        self.send.assert_not_called()
        result = self.execute([TimeoutError("private transport detail")])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "provider_timeout")
        self.assertNotIn("private transport detail", json.dumps(result))
        self.send.assert_called_once()

    def test_recording_failure_after_a_tool_prevents_the_next_model_call(self):
        from app.agent import save_analysis

        saves = []

        def save(journal, record):
            if record["tool_events"]:
                raise OSError("simulated recording failure")
            saves.append(deepcopy(record))
            save_analysis(journal, record)

        with patch("app.agent.save_analysis", side_effect=save), self.assertRaises(OSError):
            self.execute(self.sequence())
        self.send.assert_called_once()
        self.assertTrue(saves)


if __name__ == "__main__":
    unittest.main()
