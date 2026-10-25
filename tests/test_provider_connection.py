"""Exercise the SDK retry and credential boundaries without network access."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from scripts.check_provider import create_client, run_checks
from app.llm import GeminiProvider


class ProviderConnectionTests(unittest.TestCase):
    def test_quota_error_is_not_retried_and_does_not_leak_the_key(self):
        for failed_endpoint in ("generation", "embedding"):
            with self.subTest(endpoint=failed_endpoint), tempfile.TemporaryDirectory() as folder:
                requests = []

                def respond(request, **kwargs):
                    requests.append(request)
                    if failed_endpoint == "embedding" and len(requests) == 1:
                        return httpx.Response(
                            200,
                            request=request,
                            json={
                                "modelVersion": "gemini-3.5-flash-lite",
                                "candidates": [
                                    {
                                        "content": {
                                            "role": "model",
                                            "parts": [{"text": '{"status":"ready"}'}],
                                        },
                                        "finishReason": "STOP",
                                    }
                                ],
                            },
                        )
                    return httpx.Response(
                        429,
                        request=request,
                        json={
                            "error": {
                                "code": 429,
                                "status": "RESOURCE_EXHAUSTED",
                                "message": "Sensitive fake-test-key must not appear in the record.",
                            }
                        },
                    )

                report = {"status": "started", "checks": []}
                destination = Path(folder) / "record.json"
                with (
                    patch.dict("os.environ", {"GEMINI_API_KEY": "fake-test-key"}),
                    patch("httpx.Client.send", side_effect=respond),
                    create_client() as client,
                ):
                    run_checks(
                        GeminiProvider(client, Path(folder) / "calls.sqlite"), report, destination
                    )
                self.assertEqual(len(requests), 1 if failed_endpoint == "generation" else 2)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["checks"][-1]["http_status"], 429)
                self.assertIsNone(report["checks"][-1]["usage"])
                self.assertEqual(
                    report["checks"][-1]["allowance_eur"],
                    report["checks"][-1]["reserved_eur"],
                )
                self.assertNotIn("fake-test-key", destination.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
