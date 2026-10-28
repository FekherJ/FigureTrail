"""HTTP contracts and deadline/security boundaries; SDK responses are simulated."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from google.genai import errors, types

from app.corpus import prepare_corpus, write_prepared
from app.embeddings import EmbeddingCache, EmbeddingPacer, PACING_INPUT_ALLOWANCE
from app.llm import GeminiProvider, ProviderError
from app.main import create_app
from app.schemas import AnalysisResponse
from app.service import CONFIGURATION
from app.storage import publish_index
from test_corpus import fixture
from test_index import FakeProvider, populate

QUESTION = "What percentage of estimated 2008 production in MMBoe comes from Canada?"
BODY = {"question": QUESTION, "report_ids": ["DVN/2007"], "mode": "fixed"}
IDS = ["DVN/2007/page_58.pdf#table[1][1]", "DVN/2007/page_58.pdf#table[3][1]"]


def generation(status="ready", ids=IDS):
    plan = {
        "status": status,
        "operation": "ratio_percent" if status == "ready" else None,
        "cell_ids": ids if status == "ready" else [],
    }
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(parts=[types.Part(text=json.dumps(plan))]),
                finish_reason="STOP",
            )
        ],
        model_version="simulated-model",
        usage_metadata=None,
    )


class APITests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        corpus, _ = prepare_corpus(*fixture())
        write_prepared(corpus, self.root / "data/corpus/prepared")
        rows, _ = populate(
            corpus,
            EmbeddingCache(self.root / "documents.sqlite"),
            FakeProvider(),
            self.root / "absent.sqlite",
        )
        publish_index(corpus, rows, self.root / "data/corpus/indexes")
        self.journal = self.root / "data/local/runs.sqlite"
        self.generate = Mock(return_value=generation())
        self.embed = Mock(
            return_value=types.EmbedContentResponse(
                embeddings=[types.ContentEmbedding(values=[1.0] + [0.0] * 767)]
            )
        )
        self.sdk = SimpleNamespace(
            models=SimpleNamespace(generate_content=self.generate, embed_content=self.embed)
        )
        self.factory = Mock(side_effect=lambda journal: GeminiProvider(self.sdk, journal))

    def client(self, **kwargs):
        return TestClient(
            create_app(self.root, provider_factory=self.factory),
            base_url="http://127.0.0.1",
            **kwargs,
        )

    def test_health_reports_and_openapi_are_key_free_and_read_only(self):
        with patch.dict("os.environ", {}, clear=True), self.client() as client:
            self.assertIsNotNone(client.get("/health").json()["corpus_version"])
            reports = client.get("/reports").json()
            self.assertEqual(
                [r["report_id"] for r in reports["reports"]], ["DVN/2007", "OTHER/2014"]
            )
            spec = client.get("/openapi.json").json()
            self.assertEqual(
                set(spec["paths"]), {"/health", "/reports", "/analyses", "/analyses/{run_id}"}
            )
            self.assertEqual(
                spec["components"]["schemas"]["AnalysisRequest"]["additionalProperties"], False
            )
            self.assertEqual(
                spec["paths"]["/analyses"]["post"]["responses"]["422"]["content"][
                    "application/json"
                ]["schema"]["$ref"],
                "#/components/schemas/APIError",
            )
            self.assertEqual(client.get("/docs").status_code, 200)
        self.factory.assert_not_called()
        self.assertFalse(self.journal.exists())

    def test_success_is_typed_saved_and_lookup_makes_no_calls(self):
        with self.client() as client:
            response = client.post("/analyses", json=BODY)
            self.assertEqual(response.status_code, 200, response.text)
            result = AnalysisResponse.model_validate(response.json())
            self.assertEqual(result.status, "success")
            self.assertEqual(result.calculation.display, "24.69 %")
            self.assertEqual([o.value for o in result.calculation.operands], ["60", "243"])
            self.assertEqual(len(result.evidence), 5)
            self.assertEqual(len(result.calls), 2)
            self.assertTrue(all(value is None for value in result.calls[-1].usage.values()))
            self.assertEqual(client.get(f"/analyses/{result.run_id}").json(), response.json())
            repeated = client.post("/analyses", json=BODY)
            self.assertEqual(repeated.status_code, 200, repeated.text)
            self.assertNotEqual(repeated.json()["run_id"], result.run_id)
        self.assertEqual(self.generate.call_count, 2)
        self.embed.assert_called_once()  # The second analysis reuses the query vector.
        for call in (self.generate.call_args, self.embed.call_args):
            self.assertTrue(0 < call.kwargs["config"].http_options.timeout <= 20_000)
        self.assertNotIn("ANNOTATION-SECRET", self.generate.call_args.kwargs["contents"])

    def test_invalid_input_never_initializes_provider_or_journal(self):
        with self.client() as client:
            for body in (
                {},
                {**BODY, "question": " "},
                {**BODY, "question": "x" * 2001},
                {**BODY, "question": 123},
                {**BODY, "mode": "agent"},
                {**BODY, "report_ids": []},
                {**BODY, "report_ids": ["unknown"]},
                {**BODY, "report_ids": [True]},
                {**BODY, "report_ids": "DVN/2007"},
                {**BODY, "model": "override"},
            ):
                with self.subTest(body=body):
                    self.assertEqual(client.post("/analyses", json=body).status_code, 422)
            self.assertEqual(
                client.post(
                    "/analyses",
                    content=b'{"question":',
                    headers={"Content-Type": "application/json"},
                ).status_code,
                422,
            )
            self.assertEqual(client.get("/analyses/not-a-uuid").status_code, 422)
            missing = client.get(f"/analyses/{uuid4()}")
            self.assertEqual(missing.status_code, 404)
        self.factory.assert_not_called()
        self.assertFalse(self.journal.exists())

    def test_host_origin_json_and_body_limits_precede_provider(self):
        with self.client() as client:
            for host in ("evil.example", "127.0.0.1.evil.example", "testserver"):
                self.assertEqual(client.get("/health", headers={"Host": host}).status_code, 400)
            for origin in (
                "https://evil.example",
                "null",
                "http://localhost",
                "http://127.0.0.1:9000",
            ):
                response = client.post("/analyses", json=BODY, headers={"Origin": origin})
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("access-control-allow-origin", response.headers)
            for headers in (
                {},
                {"Content-Type": "text/plain"},
                {"Content-Type": "application/x-www-form-urlencoded"},
            ):
                self.assertEqual(
                    client.post("/analyses", content=b"{}", headers=headers).status_code, 415
                )
            self.assertEqual(
                client.post(
                    "/analyses",
                    content=iter([b"x" * 17000, b"y" * 17000]),
                    headers={"Content-Type": "application/json"},
                ).status_code,
                413,
            )
            self.assertEqual(
                client.get("/health", headers={"Origin": "http://127.0.0.1"}).status_code, 200
            )
        self.factory.assert_not_called()

    def test_domain_abstentions_are_successful_http_exchanges(self):
        with self.client() as client:
            for status in ("insufficient_evidence", "unsupported_request"):
                self.generate.return_value = generation(status)
                response = client.post("/analyses", json=BODY)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], status)
                self.assertIsNone(response.json()["calculation"])

    def test_provider_errors_are_sanitized_saved_and_not_retried(self):
        with self.client() as client:
            for code, status in ((429, 502), (504, 504)):
                self.generate.side_effect = errors.APIError(
                    code, {"error": {"message": "SECRET-ERROR-DETAIL"}}
                )
                before = self.generate.call_count
                response = client.post("/analyses", json=BODY)
                self.assertEqual(response.status_code, status, response.text)
                value = response.json()
                self.assertEqual(value["error_code"], f"provider_http_{code}")
                self.assertEqual(client.get(f"/analyses/{value['run_id']}").json(), value)
                self.assertEqual(self.generate.call_count, before + 1)
                self.assertNotIn("SECRET-ERROR-DETAIL", response.text)
                self.assertIsNone(value["calls"][-1]["usage"])

    def test_invalid_model_cells_and_json_are_technical_errors(self):
        with self.client() as client:
            self.generate.return_value = generation(ids=[IDS[0], "invented"])
            response = client.post("/analyses", json=BODY)
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.json()["error_code"], "invalid_cell_reference")
            self.generate.return_value = types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(parts=[types.Part(text="not json")]),
                        finish_reason="STOP",
                    )
                ]
            )
            response = client.post("/analyses", json=BODY)
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.json()["error_code"], "invalid_output")

    def test_budget_block_and_storage_failure_stop_network(self):
        with self.client() as client, patch("app.llm.LIMIT_EUR", 0):
            response = client.post("/analyses", json=BODY)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(response.json()["error_code"], "budget_limit")
        self.generate.assert_not_called()
        self.embed.assert_not_called()
        with (
            self.client() as client,
            patch(
                "app.service.save_analysis",
                side_effect=sqlite3.OperationalError("SECRET-STORAGE-ERROR"),
            ),
        ):
            response = client.post("/analyses", json=BODY)
            self.assertEqual(response.status_code, 503)
            self.assertIsNotNone(response.json()["run_id"])
            self.assertNotIn("SECRET-STORAGE-ERROR", response.text)
        self.generate.assert_not_called()
        self.embed.assert_not_called()

    def test_missing_key_and_missing_index_are_preflight_failures(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            TestClient(create_app(self.root), base_url="http://127.0.0.1") as client,
        ):
            self.assertEqual(client.post("/analyses", json=BODY).status_code, 503)
            self.assertIsNone(client.post("/analyses", json=BODY).json()["run_id"])
        self.assertFalse(self.journal.exists())
        with (
            tempfile.TemporaryDirectory() as folder,
            TestClient(create_app(Path(folder)), base_url="http://127.0.0.1") as client,
        ):
            self.assertEqual(client.get("/health").json(), {"status": "ok", "corpus_version": None})
            self.assertEqual(client.get("/reports").status_code, 503)
            self.assertEqual(client.post("/analyses", json=BODY).status_code, 503)
        (self.root / "data/corpus/indexes/current.json").write_text("{}")
        with self.assertRaises(ValueError), self.client():
            pass

    def test_concurrent_request_is_rejected_and_get_remains_available(self):
        entered, release = Event(), Event()

        def slow(**kwargs):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release its worker.")
            return generation()

        self.generate.side_effect = slow
        with self.client() as client, ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.post, "/analyses", json=BODY)
            try:
                self.assertTrue(entered.wait(4))
                self.assertEqual(client.post("/analyses", json=BODY).status_code, 409)
                self.assertEqual(client.get("/health").status_code, 200)
                with closing(sqlite3.connect(self.journal)) as db:
                    run_id = db.execute("SELECT run_id FROM analyses").fetchone()[0]
                self.assertEqual(client.get(f"/analyses/{run_id}").json()["status"], "started")
            finally:
                release.set()
            self.assertEqual(future.result(5).status_code, 200)
        self.generate.assert_called_once()

    def test_timeout_keeps_slot_until_embedding_stops_and_prevents_generation(self):
        entered, release = Event(), Event()
        embedding = self.embed.return_value

        def slow(**kwargs):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release its worker.")
            return embedding

        self.embed.side_effect = slow
        with self.client() as client, patch.dict(CONFIGURATION, deadline_seconds=0.15):
            try:
                started = monotonic()
                response = client.post("/analyses", json=BODY)
                elapsed = monotonic() - started
                self.assertTrue(entered.is_set())
                self.assertEqual(response.status_code, 504, response.text)
                self.assertLess(elapsed, 2)
                run_id = response.json()["run_id"]
                self.assertIsNotNone(run_id)
                self.assertEqual(client.post("/analyses", json=BODY).status_code, 409)
            finally:
                release.set()
            for _ in range(100):
                saved = client.get(f"/analyses/{run_id}").json()
                if saved["status"] != "started":
                    break
                sleep(0.01)
            self.assertEqual(saved["status"], "blocked", saved)
            self.assertEqual(saved["error_code"], "deadline_reached")
            self.assertIsNone(saved["calculation"])
        self.embed.assert_called_once()
        self.generate.assert_not_called()

    def test_corrupt_journal_is_not_reported_as_a_missing_run(self):
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        self.journal.write_bytes(b"not sqlite")
        with self.client() as client:
            self.assertEqual(client.get(f"/analyses/{uuid4()}").status_code, 503)

    def test_expired_pacing_and_provider_reservation_do_not_send_requests(self):
        timer = [0.0]

        def advance(seconds):
            timer[0] += seconds

        pacer = EmbeddingPacer(self.root / "absent.sqlite", clock=lambda: timer[0], sleep=advance)
        pacer.events.append((0, PACING_INPUT_ALLOWANCE))
        with self.assertRaises(TimeoutError):
            pacer.wait(100, deadline=0.5)
        self.assertEqual(timer[0], 0.5)
        provider = GeminiProvider(self.sdk, self.journal)
        with self.assertRaises(ProviderError) as error:
            provider.embed_text("query", run_id=str(uuid4()), deadline=monotonic() - 1)
        self.assertEqual(error.exception.record["status"], "blocked")
        self.assertEqual(error.exception.record["allowance_eur"], "0")
        self.embed.assert_not_called()

    def test_late_generation_is_saved_as_blocked_with_unknown_usage_retained(self):
        entered, release = Event(), Event()

        def slow(**kwargs):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release its worker.")
            return generation()

        self.generate.side_effect = slow
        with self.client() as client, patch.dict(CONFIGURATION, deadline_seconds=0.15):
            try:
                response = client.post("/analyses", json=BODY)
                self.assertEqual(response.status_code, 504, response.text)
                self.assertTrue(entered.is_set())
                run_id = response.json()["run_id"]
                self.assertEqual(client.post("/analyses", json=BODY).status_code, 409)
            finally:
                release.set()
            for _ in range(100):
                saved = client.get(f"/analyses/{run_id}").json()
                if saved["status"] != "started":
                    break
                sleep(0.01)
            self.assertEqual(saved["status"], "blocked", saved)
            self.assertIsNone(saved["calculation"])
            self.assertEqual(saved["calls"][-1]["allowance_eur"], "1")
            self.assertTrue(all(v is None for v in saved["calls"][-1]["usage"].values()))
        self.generate.assert_called_once()

    def test_deadline_expiring_during_budget_reservation_blocks_generation(self):
        provider = GeminiProvider(self.sdk, self.journal)
        with (
            patch("app.llm.monotonic", side_effect=[0, 2]),
            self.assertRaises(ProviderError) as error,
        ):
            provider.generate_json("question", AnalysisResponse, run_id=str(uuid4()), deadline=1)
        self.assertEqual(error.exception.record["error_code"], "deadline_reached")
        self.assertEqual(error.exception.record["allowance_eur"], "0")
        self.generate.assert_not_called()

    def test_transport_timeout_is_distinct_from_domain_abstention(self):
        import httpx

        self.generate.side_effect = httpx.ReadTimeout("SECRET-TRANSPORT-DETAIL")
        with self.client() as client:
            response = client.post("/analyses", json=BODY)
            self.assertEqual(response.status_code, 504, response.text)
            self.assertEqual(response.json()["status"], "failed")
            self.assertEqual(response.json()["error_code"], "provider_timeout")
            self.assertNotIn("SECRET-TRANSPORT-DETAIL", response.text)
        self.generate.assert_called_once()

    def test_real_local_http_server_with_simulated_sdk(self):
        import httpx
        import socket
        from threading import Thread
        import uvicorn

        server = uvicorn.Server(
            uvicorn.Config(create_app(self.root, provider_factory=self.factory), log_level="error")
        )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
            thread.start()
            try:
                for _ in range(100):
                    if server.started or not thread.is_alive():
                        break
                    sleep(0.02)
                self.assertTrue(server.started)
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False
                ) as client:
                    self.assertEqual(client.get("/health").status_code, 200)
                    self.assertEqual(len(client.get("/reports").json()["reports"]), 2)
                    response = client.post("/analyses", json=BODY)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["calculation"]["display"], "24.69 %")
                    self.assertEqual(
                        client.get(f"/analyses/{response.json()['run_id']}").json(), response.json()
                    )
                    self.assertEqual(client.post("/analyses", content=b"{}").status_code, 415)
            finally:
                server.should_exit = True
                thread.join(5)
            self.assertFalse(thread.is_alive(), "Verification server did not stop.")
        self.generate.assert_called_once()
        self.embed.assert_called_once()


if __name__ == "__main__":
    unittest.main()
