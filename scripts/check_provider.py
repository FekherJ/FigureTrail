"""Run two explicit Gemini connectivity checks; this is not an analysis evaluation."""

import argparse
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from app.llm import (
    DIMENSIONS,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
    GeminiProvider,
    ProviderError,
    create_client,
)

PROMPT = "Return the JSON object with status set to ready. This is a connection check."
EMBEDDING_INPUT = "task: search result | query: public report numerical evidence"
ROOT = Path(__file__).resolve().parents[1]


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["ready"]


def generation_check(provider: GeminiProvider, record: dict) -> None:
    result, call = provider.generate_json(
        PROMPT,
        ConnectionResponse,
        run_id=record["run_id"],
        max_output_tokens=64,
        metadata={"prompt_version": "connection-v1"},
    )
    record.update(call)
    record["validated_response"] = result.model_dump()


def embedding_check(provider: GeminiProvider, record: dict) -> None:
    _, call = provider.embed_text(EMBEDDING_INPUT, run_id=record["run_id"])
    record.update(call)


def run_checks(provider: GeminiProvider, report: dict, destination: Path) -> None:
    def save():
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    run_id = report.setdefault("run_id", str(uuid4()))
    save()
    started = perf_counter()
    for name, model, check in (
        ("structured_generation", GENERATION_MODEL, generation_check),
        ("text_embedding", EMBEDDING_MODEL, embedding_check),
    ):
        if perf_counter() - started >= 60:
            report["status"] = "deadline_reached"
            break
        record = {
            "check": name,
            "run_id": run_id,
            "requested_model": model,
            "status": "started",
            "usage": None,
        }
        report["checks"].append(record)
        save()
        try:
            check(provider, record)
        except ProviderError as error:
            record.update(error.record)
        save()
        if record["status"] != "passed":
            break
    if report["status"] != "deadline_reached":
        report["status"] = (
            "passed"
            if len(report["checks"]) == 2 and all(r["status"] == "passed" for r in report["checks"])
            else "failed"
        )
    report["duration_seconds"] = round(perf_counter() - started, 3)
    save()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow two hosted model requests.")
    if not parser.parse_args().live:
        parser.error("Pass --live to allow hosted requests; no requests were sent.")
    run_id = str(uuid4())
    destination = ROOT / "data/local/provider-checks" / f"{run_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": run_id,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "check_version": "provider-connection-v2",
        "sdk_version": version("google-genai"),
        "status": "started",
        "max_model_requests": 2,
        "automatic_retries": 0,
        "transport_timeout_seconds": 20,
        "max_output_tokens": 64,
        "generation_prompt": PROMPT,
        "embedding_input": EMBEDDING_INPUT,
        "embedding_dimensions": DIMENSIONS,
        "price_date": "2026-10-25",
        "price_source": "https://ai.google.dev/gemini-api/docs/pricing",
        "billing_tier": "not_verified",
        "actual_charge_usd": None,
        "checks": [],
    }
    with create_client() as client:
        run_checks(GeminiProvider(client), report, destination)
    print(json.dumps(report, indent=2))
    print(f"Local record: {destination.relative_to(ROOT).as_posix()}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
