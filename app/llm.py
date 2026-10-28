"""Gemini requests, conservative local allowances and sanitized call records."""

import json
import math
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from time import monotonic, perf_counter
from uuid import uuid4

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

# Generation returns structured responses or tool calls; embeddings represent text as numbers.
GENERATION_MODEL = "gemini-3.5-flash-lite"
EMBEDDING_MODEL = "gemini-embedding-2"
DIMENSIONS = 768
PRICE_DATE = "2026-10-25"
INPUT_USD_PER_MILLION = Decimal("0.30")
OUTPUT_USD_PER_MILLION = Decimal("2.50")
PLANNING_EUR_PER_USD = Decimal("2")  # Planning buffer, not a market exchange rate.
LIMIT_EUR = Decimal("25")
JOURNAL = Path(__file__).resolve().parents[1] / "data/local/runs.sqlite"


class ProviderError(RuntimeError):
    def __init__(self, code: str, record: dict):
        super().__init__(code)
        self.record = record


def create_client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    return genai.Client(
        api_key=key,
        vertexai=False,
        http_options=types.HttpOptions(
            api_version="v1beta",
            timeout=20_000,
            # One total attempt prevents hidden retries from multiplying usage.
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


class GeminiProvider:
    """One SDK client and one cumulative journal; no network call during construction."""

    def __init__(self, client: genai.Client, journal: Path = JOURNAL):
        self.client = client
        self.journal = journal
        journal.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(journal)) as database, database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS calls "
                "(call_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, allowance_eur TEXT NOT NULL, "
                "record_json TEXT NOT NULL)"
            )
            # Covers the two pre-journal connection requests; this is not a measured charge.
            opening = {
                "kind": "opening_allowance",
                "reason": "pre-journal connection checks",
                "actual_charge_eur": None,
                "allowance_eur": "0.02",
            }
            database.execute(
                "INSERT OR IGNORE INTO calls VALUES (?, ?, ?, ?)",
                ("opening-allowance-v1", "pre-journal", "0.02", json.dumps(opening)),
            )

    def _reserve(self, record: dict, allowance: Decimal) -> None:
        """Reserve local budget and record a call before any network request.

        Args:
            record: Mutable call dictionary; receives a blocked state if budget is exhausted.
            allowance: Decimal EUR allowance to reserve, not a confirmed provider charge.

        Returns:
            None on reservation. A budget block raises ProviderError after recording it;
            storage failures also stop the caller before network access.
        """
        with closing(sqlite3.connect(self.journal)) as database, database:
            # Check and reserve together so two calls cannot use the same remaining allowance.
            # Release the database lock before waiting for Gemini.
            database.execute("BEGIN IMMEDIATE")
            total = sum(
                (Decimal(row[0]) for row in database.execute("SELECT allowance_eur FROM calls")),
                Decimal(0),
            )
            if total + allowance > LIMIT_EUR:
                allowance = Decimal(0)
                record.update(status="blocked", error_code="budget_limit", allowance_eur="0")
            database.execute(
                "INSERT INTO calls VALUES (?, ?, ?, ?)",
                (record["call_id"], record["run_id"], str(allowance), json.dumps(record)),
            )
        if record["status"] == "blocked":
            raise ProviderError("budget_limit", record)

    def _call(self, kind, run_id, perform, parse, metadata, *, deadline=None, cancelled=None):
        """Apply shared budget, error and accounting rules to one SDK operation.

        Args:
            kind: "generation" or "embedding", selecting the model/accounting category.
            run_id: Parent execution ID; this call also gets its own call_id.
            perform: Function with no arguments that sends the actual SDK request.
            parse: Function taking (response, record) and returning a validated result.
            metadata: Non-secret context and input fingerprints saved with the call.
            deadline: Optional absolute monotonic time after which no call may start.
            cancelled: Optional Event requesting a cooperative stop before network access.

        Returns:
            A pair: parsed result and sanitized call dictionary. Provider/validation
            failures raise ProviderError carrying that dictionary; unknown usage keeps
            its allowance. Uses this instance's SDK client and shared journal.
        """
        allowance = Decimal("1") if kind == "generation" else Decimal("0.01")
        record = {
            "call_id": str(uuid4()),
            "run_id": run_id,
            "kind": kind,
            "status": "started",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "requested_model": GENERATION_MODEL if kind == "generation" else EMBEDDING_MODEL,
            "sdk_version": version("google-genai"),
            "automatic_retries": 0,
            "price_date": PRICE_DATE,
            "planning_eur_per_usd": str(PLANNING_EUR_PER_USD),
            "reserved_eur": str(allowance),
            "allowance_eur": str(allowance),
            "usage": None,
            "estimated_paid_cost_usd": None,
            "actual_charge_eur": None,
            "metadata": metadata,
        }
        self._reserve(record, allowance)  # No network if reservation/recording fails.
        started = perf_counter()
        result, attempted = None, False
        try:
            if (deadline is not None and monotonic() >= deadline) or (
                cancelled is not None and cancelled.is_set()
            ):
                raise TimeoutError("Execution deadline reached before network access.")
            attempted = True
            response = perform()
            if kind == "generation":
                usage = response.usage_metadata
                record["returned_model"] = response.model_version
                record["usage"] = {
                    name: getattr(usage, field, None)
                    for name, field in (
                        ("input_tokens", "prompt_token_count"),
                        ("output_tokens", "candidates_token_count"),
                        ("thought_tokens", "thoughts_token_count"),
                        ("total_tokens", "total_token_count"),
                    )
                }
                count = record["usage"]["total_tokens"]
                if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                    # Price every reported token at the highest rate; retain absent counters as null.
                    upper_usd = Decimal(count) * OUTPUT_USD_PER_MILLION / 1_000_000
                    record["estimated_paid_cost_usd"] = str(upper_usd)
                    allowance = min(allowance, upper_usd * PLANNING_EUR_PER_USD)
            result = parse(response, record)
            record["status"] = "passed"
        except Exception as error:
            # Raw provider errors may contain request data; store safe metadata only.
            code = getattr(error, "code", None)
            record.update(
                status="failed",
                error_type=type(error).__name__,
                http_status=code if isinstance(code, int) else None,
            )
            record["error_code"] = (
                "invalid_output"
                if isinstance(error, (ValueError, ValidationError))
                else f"provider_http_{code}"
                if isinstance(code, int)
                else "provider_error"
            )
            if not attempted:
                record.update(status="blocked", error_code="deadline_reached")
                allowance = Decimal(0)  # No network attempt was made.
            elif isinstance(error, TimeoutError) or type(error).__name__ in {
                "ReadTimeout",
                "ConnectTimeout",
                "WriteTimeout",
                "PoolTimeout",
            }:
                record["error_code"] = "provider_timeout"
        record["duration_seconds"] = round(perf_counter() - started, 3)
        record["allowance_eur"] = str(allowance)
        # Unknown usage retains the reservation, including after a timeout or process interruption.
        with closing(sqlite3.connect(self.journal)) as database, database:
            database.execute(
                "UPDATE calls SET allowance_eur = ?, record_json = ? WHERE call_id = ?",
                (str(allowance), json.dumps(record), record["call_id"]),
            )
        if record["status"] in {"failed", "blocked"}:
            raise ProviderError(record["error_code"], record) from None
        return result, record

    def _generation_config(
        self,
        text: str,
        instruction: str,
        max_output_tokens: int,
        deadline: float | None,
    ):
        """Prepare bounded SDK generation settings without sending a request.

        Args:
            text: User/context payload whose size and fingerprint are checked.
            instruction: Separate system instructions for the model.
            max_output_tokens: Requested output-token ceiling, at most 1000.
            deadline: Optional absolute monotonic stop time used for the transport timeout.

        Returns:
            A pair: SDK configuration and safe input/settings metadata for the journal.
        """
        if not text or len(text) > 22_000 or len(instruction) > 5_000:
            raise ValueError("Generation input is empty or exceeds its size limit.")
        if not 1 <= max_output_tokens <= 1000:
            raise ValueError("Output tokens must be between 1 and 1000.")
        remaining = 20 if deadline is None else min(20, deadline - monotonic())
        if remaining <= 0:
            raise TimeoutError("The execution deadline has been reached.")
        tags = {
            "input_sha256": sha256(text.encode()).hexdigest(),
            "instruction_sha256": sha256(instruction.encode()).hexdigest(),
            "max_output_tokens": max_output_tokens,
            "timeout_seconds": remaining,
        }
        config = types.GenerateContentConfig(
            system_instruction=instruction or None,
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
            # Application code must control tool execution explicitly.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=types.HttpOptions(timeout=max(1, int(remaining * 1000))),
        )
        return config, tags

    def generate_json(
        self,
        text: str,
        schema: type[BaseModel],
        *,
        run_id: str,
        instruction: str = "",
        metadata: dict | None = None,
        max_output_tokens: int = 1000,
        deadline: float | None = None,
        cancelled=None,
    ):
        """Request structured JSON and validate it against the supplied Pydantic model.

        Args:
            text: JSON string containing the question and retrieved source evidence.
            schema: Pydantic model class defining allowed output, usually CellSelection.
            run_id: Execution ID shared with retrieval and the saved analysis.
            instruction: Trusted system prompt, separate from the untrusted payload.
            metadata: Non-secret version/purpose information for the call journal.
            max_output_tokens: Ceiling on generated tokens; default and maximum are 1000.
            deadline: Optional absolute monotonic stop time, not a duration in seconds.
            cancelled: Optional Event requesting a cooperative stop before sending.

        Returns:
            A pair: validated schema instance and sanitized call record. _call() invokes
            the local perform/parse functions and records failures; JSON validity alone
            does not establish that the selected evidence answers the question.
        """
        config, tags = self._generation_config(text, instruction, max_output_tokens, deadline)
        config.response_mime_type = "application/json"
        config.response_json_schema = schema.model_json_schema()

        def parse(response, record):
            """Validate the SDK response and return an instance of the enclosing schema.

            Args:
                response: Gemini SDK response, including completion status and JSON text.
                record: Mutable call dictionary receiving the validated_output field.
            """
            if (
                not response.candidates
                or response.candidates[0].finish_reason != types.FinishReason.STOP
            ):
                raise ValueError("Generation was blocked, truncated or incomplete.")
            # A valid JSON plan can still select the wrong evidence; source checks follow.
            result = schema.model_validate_json(response.text)
            record["validated_output"] = result.model_dump(mode="json")
            return result

        def perform():
            """Send the enclosing text/config to Gemini and return the raw SDK response.

            Takes no parameters: text, config, deadline and cancelled come from generate_json().
            The shared _call() wrapper invokes this after budget reservation.
            """
            if deadline is not None:
                remaining = deadline - monotonic()
                if remaining <= 0 or (cancelled is not None and cancelled.is_set()):
                    raise TimeoutError("Execution deadline reached.")
                config.http_options.timeout = max(1, int(min(20, remaining) * 1000))
            return self.client.models.generate_content(
                model=GENERATION_MODEL, contents=text, config=config
            )

        return self._call(
            "generation",
            run_id,
            perform,
            parse,
            {**(metadata or {}), **tags},
            deadline=deadline,
            cancelled=cancelled,
        )

    def request_tool(
        self,
        text: str,
        arguments_schema: type[BaseModel],
        *,
        tool_name: str,
        description: str,
        run_id: str,
        instruction: str = "",
        metadata: dict | None = None,
        deadline: float | None = None,
        cancelled=None,
    ):
        config, tags = self._generation_config(text, instruction, 256, deadline)
        parameters = arguments_schema.model_json_schema()
        config.tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=tool_name, description=description, parameters_json_schema=parameters
                    )
                ]
            )
        ]
        config.tool_config = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        )
        tags.update(
            allowed_tool=tool_name,
            tool_choice="AUTO",
            tool_schema_sha256=sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest(),
        )

        def parse(response, record):
            if len(response.candidates or []) != 1:
                raise ValueError("Expected one tool-call candidate.")
            candidate = response.candidates[0]
            if candidate.finish_reason != types.FinishReason.STOP or not candidate.content:
                raise ValueError("Tool generation was blocked, truncated or incomplete.")
            calls = [
                part.function_call
                for part in candidate.content.parts or []
                if part.function_call is not None
            ]
            # Native calls only: text that looks like a tool request is not executable.
            if len(calls) != 1 or calls[0].name != tool_name:
                raise ValueError("Expected exactly one call to the allowed tool.")
            arguments = arguments_schema.model_validate(calls[0].args)
            record["validated_output"] = {
                "name": tool_name,
                "arguments": arguments.model_dump(mode="json"),
                "provider_call_id": calls[0].id,
            }
            return arguments

        def perform():
            if deadline is not None:
                remaining = deadline - monotonic()
                if remaining <= 0 or (cancelled is not None and cancelled.is_set()):
                    raise TimeoutError("Execution deadline reached.")
                config.http_options.timeout = max(1, int(min(20, remaining) * 1000))
            return self.client.models.generate_content(
                model=GENERATION_MODEL, contents=text, config=config
            )

        return self._call(
            "generation",
            run_id,
            perform,
            parse,
            {**(metadata or {}), **tags},
            deadline=deadline,
            cancelled=cancelled,
        )

    def embed_text(
        self, text: str, *, run_id: str, metadata: dict | None = None, deadline=None, cancelled=None
    ):
        """Represent one formatted text input as a checked 768-number embedding.

        Args:
            text: Input already formatted for the document or question embedding task.
            run_id: Parent execution ID for accounting and trace lookup.
            metadata: Optional non-secret purpose/configuration context for the journal.
            deadline: Optional absolute monotonic stop time, not a timeout duration.
            cancelled: Optional Event requesting a cooperative stop before sending.

        Returns:
            A pair: finite, approximately unit-length vector as a list and its call record.
            This method sends/validates the request; the caller handles vector caching.
        """
        if not text or len(text) > 20_000:
            raise ValueError("Embedding input is empty or exceeds its size limit.")

        def parse(response, record):
            """Check one returned embedding and add its validation details to the record.

            Args:
                response: Gemini SDK embedding response containing a list of vectors.
                record: Mutable call dictionary receiving dimensions, norm and finite-value checks.

            Returns:
                The single validated vector as a list of numbers.
            """
            if not response.embeddings or len(response.embeddings) != 1:
                raise ValueError("Expected exactly one embedding.")
            values = response.embeddings[0].values
            if not values or len(values) != DIMENSIONS or not all(math.isfinite(x) for x in values):
                raise ValueError("Invalid embedding dimensions or values.")
            # A vector's norm is its length; require length 1 for similarity comparisons.
            norm = math.sqrt(math.fsum(x * x for x in values))
            if not math.isclose(norm, 1, rel_tol=1e-3, abs_tol=1e-3):
                raise ValueError("Embedding is not normalized.")
            record.update(dimensions=DIMENSIONS, norm=norm, finite_values=True)
            return values

        def perform():
            """Send the enclosing text to the embedding model and return its SDK response.

            Takes no parameters: text, deadline and cancelled come from embed_text().
            The shared _call() wrapper invokes this after budget reservation.
            """
            remaining = 20 if deadline is None else min(20, deadline - monotonic())
            if remaining <= 0 or (cancelled is not None and cancelled.is_set()):
                raise TimeoutError("Execution deadline reached.")
            return self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=DIMENSIONS,
                    http_options=types.HttpOptions(timeout=max(1, int(remaining * 1000))),
                ),
            )

        return self._call(
            "embedding",
            run_id,
            perform,
            parse,
            {
                "format_version": "search-prefix-v1",
                **(metadata or {}),
                "input_sha256": sha256(text.encode()).hexdigest(),
                "input_token_allowance": len(text.encode()) + 64,
            },
            deadline=deadline,
            cancelled=cancelled,
        )
