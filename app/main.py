"""Local HTTP contracts around the shared, bounded analysis service."""

import asyncio
from contextlib import asynccontextmanager
from copy import copy
import os
from pathlib import Path
import re
import sqlite3
from threading import Event, Lock
from time import monotonic
from uuid import UUID, uuid4

from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.embeddings import EmbeddingCache, EmbeddingPacer
from app.llm import GeminiProvider, create_client
from app.retrieval import load_current
from app.schemas import (
    APIError,
    AnalysisRequest,
    AnalysisResponse,
    HealthResponse,
    ReportsResponse,
)
from app.service import CONFIGURATION, ROOT, analyze, read_analysis

MAX_BODY_BYTES = 32_768


def error_response(code, message, status, run_id=None):
    return JSONResponse(
        APIError(
            status="blocked" if status in (409, 504) else "failed",
            error_code=code,
            message=message,
            run_id=run_id,
        ).model_dump(),
        status_code=status,
    )


class LocalRequestGuard:
    """Check origin/Host and bound JSON bytes before FastAPI parses a request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = scope["headers"]
        hosts = [value.decode("latin1").lower() for key, value in headers if key == b"host"]
        origins = [value.decode("latin1").lower() for key, value in headers if key == b"origin"]
        host = hosts[0] if len(hosts) == 1 else ""
        if not re.fullmatch(r"(?:127\.0\.0\.1|localhost)(?::[0-9]{1,5})?", host):
            return await error_response("invalid_host", "Use a local server address.", 400)(
                scope, receive, send
            )
        if origins and (len(origins) != 1 or origins[0] != scope["scheme"] + "://" + host):
            return await error_response(
                "origin_not_allowed", "Origin must match the server origin.", 403
            )(scope, receive, send)
        if scope["method"] == "POST" and scope["path"] == "/analyses":
            content_types = [value for key, value in headers if key == b"content-type"]
            if (
                len(content_types) != 1
                or content_types[0].split(b";", 1)[0].strip().lower() != b"application/json"
            ):
                return await error_response(
                    "json_required", "Use Content-Type: application/json.", 415
                )(scope, receive, send)
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > MAX_BODY_BYTES:
                    return await error_response(
                        "request_too_large", "JSON body exceeds 32768 bytes.", 413
                    )(scope, receive, send)
                if not message.get("more_body", False):
                    break

            replayed = False

            async def replay():
                nonlocal replayed
                if replayed:
                    return await receive()
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            return await self.app(scope, replay, send)
        await self.app(scope, receive, send)


def public_result(record):
    retrieval = record.get("retrieval") or {}
    embedding = retrieval.get("query_embedding") or {}
    calls = [call for call in (embedding.get("call"), record.get("call")) if call]
    # Project explicit public fields; internal SDK metadata and journal payloads stay local.
    return AnalysisResponse.model_validate(
        {**record, "evidence": retrieval.get("hits", []), "calls": calls}
    )


def result_status(record):
    if record["status"] in ("success", "insufficient_evidence", "unsupported_request"):
        return 200
    if record["error_code"] == "internal_analysis_error":
        return 500
    if record["error_code"] == "deadline_reached":
        return 504
    if record["status"] == "blocked":
        return 409
    if record["error_code"] in ("provider_http_504", "provider_timeout"):
        return 504
    return 502


def create_app(root: Path = ROOT, *, provider_factory=None):
    journal = root / "data/local/runs.sqlite"
    active = Lock()
    tasks = {}

    @asynccontextmanager
    async def lifespan(app):
        pointers = [root / f"data/corpus/{name}/current.json" for name in ("prepared", "indexes")]
        # A fresh checkout still has key-free health/docs. Partial/corrupt bundles fail startup.
        app.state.retriever = load_current(root) if any(p.exists() for p in pointers) else None
        try:
            yield
        finally:
            for cancelled in tasks.values():
                cancelled.set()
            if tasks:
                await asyncio.gather(*list(tasks), return_exceptions=True)

    app = FastAPI(title="FigureTrail", version="0.1.0", lifespan=lifespan)
    app.add_middleware(LocalRequestGuard)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return error_response(
            "invalid_request",
            "Check the request against /docs: question, scope, mode and run ID.",
            422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return error_response(
            "http_error", "The requested route or method is unavailable.", error.status_code
        )

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        return error_response("internal_error", "The request could not be completed.", 500)

    errors = {code: {"model": APIError} for code in (400, 403, 413, 415, 422, 503)}

    @app.get("/health", response_model=HealthResponse)
    async def health():
        retriever = app.state.retriever
        return HealthResponse(
            corpus_version=retriever.manifest["corpus_version"] if retriever else None
        )

    @app.get("/reports", response_model=ReportsResponse, responses=errors)
    async def reports():
        retriever = app.state.retriever
        if retriever is None:
            return error_response(
                "index_unavailable", "Prepare and build the corpus before analysis.", 503
            )
        return ReportsResponse(
            **{key: retriever.manifest[key] for key in ("corpus_version", "index_version")},
            reports=[
                {
                    "report_id": report_id,
                    "source_ids": sorted(
                        s["source_id"]
                        for s in retriever.corpus["sources"]
                        if s["report_id"] == report_id
                    ),
                    "chunk_count": sum(
                        c["report_id"] == report_id for c in retriever.corpus["chunks"]
                    ),
                }
                for report_id in sorted(retriever.report_ids)
            ],
        )

    def execute(body, run_id, deadline, cancelled):
        client = None
        try:
            if provider_factory is None:
                client = create_client()
                provider = GeminiProvider(client, journal)
            else:
                provider = provider_factory(journal)
            retriever = copy(app.state.retriever)
            retriever.provider = provider
            retriever.query_cache = EmbeddingCache(root / "data/local/query-embeddings.sqlite")
            retriever.pacer = EmbeddingPacer(journal)
            return analyze(
                body.question,
                retriever,
                provider,
                report_ids=body.report_ids,
                journal=journal,
                run_id=run_id,
                deadline=deadline,
                cancelled=cancelled,
            )
        finally:
            try:
                if client is not None:
                    client.close()
            finally:
                active.release()

    @app.post(
        "/analyses",
        response_model=AnalysisResponse,
        responses={
            **errors,
            409: {"model": AnalysisResponse | APIError},
            500: {"model": AnalysisResponse | APIError},
            502: {"model": AnalysisResponse},
            504: {"model": AnalysisResponse | APIError},
        },
    )
    async def post_analysis(body: AnalysisRequest, response: Response):
        retriever = app.state.retriever
        if retriever is None:
            return error_response(
                "index_unavailable", "Prepare and build the corpus before analysis.", 503
            )
        try:
            retriever.validate_request(
                body.question, "semantic", CONFIGURATION["k"], body.report_ids
            )
        except ValueError:
            return error_response(
                "invalid_scope", "Scope must contain known IDs from /reports.", 422
            )
        if provider_factory is None and not os.environ.get("GEMINI_API_KEY", "").strip():
            return error_response(
                "provider_not_configured",
                "Configure GEMINI_API_KEY in the server environment.",
                503,
            )
        # ponytail: one active analysis per process; run one Uvicorn worker, without reload.
        if not active.acquire(blocking=False):
            return error_response(
                "analysis_in_progress", "Wait for the active analysis to finish.", 409
            )
        run_id, cancelled = str(uuid4()), Event()
        deadline = monotonic() + CONFIGURATION["deadline_seconds"]
        task = asyncio.create_task(asyncio.to_thread(execute, body, run_id, deadline, cancelled))
        tasks[task] = cancelled

        def finished(done):
            tasks.pop(done, None)
            if not done.cancelled():
                done.exception()  # Consume late errors after an HTTP timeout/disconnect.

        task.add_done_callback(finished)
        try:
            record = await asyncio.wait_for(
                asyncio.shield(task), timeout=max(0, deadline - monotonic())
            )
            response.status_code = result_status(record)
            return public_result(record)
        except TimeoutError:
            cancelled.set()
            return error_response(
                "deadline_reached",
                "Analysis exceeded its deadline; lookup may show finalization in progress.",
                504,
                run_id,
            )
        except asyncio.CancelledError:
            cancelled.set()
            raise
        except OSError, sqlite3.Error:
            return error_response(
                "recording_unavailable",
                "Storage failed; a durable result cannot be guaranteed.",
                503,
                run_id,
            )
        except Exception:
            return error_response(
                "analysis_failed",
                "Analysis could not complete; inspect local diagnostics.",
                503,
                run_id,
            )

    @app.get(
        "/analyses/{run_id}",
        response_model=AnalysisResponse,
        responses={**errors, 404: {"model": APIError}},
    )
    def get_analysis(run_id: UUID):
        try:
            record = read_analysis(journal, str(run_id))
        except OSError, sqlite3.Error, ValueError:
            return error_response(
                "recording_unavailable", "Saved results cannot be read.", 503, str(run_id)
            )
        if record is None:
            return error_response(
                "analysis_not_found", "No saved analysis has this run ID.", 404, str(run_id)
            )
        return public_result(record)

    return app


app = create_app()
