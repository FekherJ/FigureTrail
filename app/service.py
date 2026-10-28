"""One retrieval, at most one generation, validated source calculation and a saved result."""

from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from time import monotonic, perf_counter
from uuid import uuid4

from app.calculator import EvidenceError, VERSION, calculate
from app.corpus import digest
from app.llm import JOURNAL, ProviderError
from app.schemas import CellSelection

ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION = {
    "version": "fixed-analysis-v2",
    "payload": "source-local-exact-line-dedup-v1",
    "k": 5,
    "generation_calls": 1,
    "max_context_characters": 20000,
    "deadline_seconds": 60,
    "calculator_version": VERSION,
}


def save_analysis(journal, record):
    """Save the current state of an execution, updating the same row at each stage.

    Args:
        journal: Path to runs.sqlite, not an open database connection.
        record: Execution dictionary containing run_id, progress, result and errors.

    Returns:
        None. Storage failures propagate so the caller cannot claim a saved result.
    """
    journal.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(journal)) as database, database:
        database.execute(
            "CREATE TABLE IF NOT EXISTS analyses (run_id TEXT PRIMARY KEY, record_json TEXT NOT NULL)"
        )
        database.execute(
            "INSERT INTO analyses VALUES (?, ?) ON CONFLICT(run_id) DO UPDATE SET record_json=excluded.record_json",
            (record["run_id"], json.dumps(record)),
        )


def read_analysis(journal, run_id):
    """Read a saved execution without creating files or calling Gemini.

    Args:
        journal: Path to the existing runs.sqlite database.
        run_id: String ID of the execution to look up.

    Returns:
        The saved dictionary, or None if the database/table/run is absent.
        Unreadable or corrupt storage raises an error rather than looking absent.
    """
    if not journal.exists():
        return None
    uri = journal.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as database:
        if not database.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='analyses'"
        ).fetchone():
            return None
        row = database.execute(
            "SELECT record_json FROM analyses WHERE run_id=?", (run_id,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def model_input(question, hits, cells):
    # RAG (retrieval-augmented generation) adds retrieved source excerpts to the prompt.
    # The model uses this context for the request; it is not retrained on these documents.
    """Build the JSON context supplied to the model for evidence selection.

    Args:
        question: The user's numerical question.
        hits: Ranked search results, including excerpt text and candidate cell IDs.
        cells: Original corpus cell records used to look up values and labels.

    Returns:
        A JSON string containing the question, excerpts and referenced source cells.
        Repeated lines are reduced; oversized context raises EvidenceError.
    """
    by_id = {cell["cell_id"]: cell for cell in cells}
    chunks, seen_by_source = [], {}
    for hit in hits:
        seen = seen_by_source.setdefault(hit["source_id"], set())
        lines = []
        # Repeated table context stays available once per source, with every candidate cell.
        for line in hit["text"].splitlines():
            if line not in seen:
                lines.append(line)
                seen.add(line)
        chunks.append(
            {
                **{key: hit[key] for key in ("chunk_id", "source_id", "report_id")},
                "text": "\n".join(lines),
                "cells": [
                    {
                        key: by_id[cell_id][key]
                        for key in ("cell_id", "source_value", "row_label", "column_header")
                    }
                    for cell_id in hit["cell_ids"]
                ],
            }
        )
    text = json.dumps({"question": question, "chunks": chunks}, ensure_ascii=False)
    if len(text) > CONFIGURATION["max_context_characters"]:
        raise EvidenceError("context_too_large")
    return text


def analyze(
    question,
    retriever,
    provider,
    *,
    method="semantic",
    report_ids=None,
    journal=JOURNAL,
    clock=monotonic,
    run_id=None,
    deadline=None,
    cancelled=None,
):
    # Shared workflow for HTTP, CLI and evaluations: retrieve -> select -> check -> calculate.
    """Run one fixed workflow and return its saved outcome, including non-answers.

    Args:
        question: User question, including the measure and periods to compare.
        retriever: Loaded Retriever object holding the validated corpus and search index.
        provider: Shared Gemini wrapper for generation; None blocks generation.
        method: "semantic" for vector similarity or "lexical" for word matching.
        report_ids: Explicit report scope; None searches the full corpus.
        journal: Path to the shared SQLite execution/provider journal.
        clock: Time-reading function (monotonic by default); tests can supply a fake clock.
        run_id: Caller-supplied execution ID, or None to generate a new one.
        deadline: Stop timestamp such as clock() + 60, not a duration; None sets 60s.
        cancelled: Optional thread-safe Event; setting it asks running stages to stop.

    Returns:
        A dictionary with run_id, status, retrieved evidence, plan, calculation and
        error_code. Domain/provider failures become recorded outcomes; invalid
        preflight input and storage failures can raise before a final result exists.
    """
    scope = retriever.validate_request(question, method, CONFIGURATION["k"], report_ids)
    started = perf_counter()
    deadline = clock() + CONFIGURATION["deadline_seconds"] if deadline is None else deadline
    instruction = (ROOT / "prompts/analysis_selection.md").read_text(encoding="utf-8")
    record = {
        "run_id": run_id or str(uuid4()),
        "status": "started",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "fixed",
        "question": question,
        "report_ids": scope,
        "retrieval_method": method,
        "corpus_version": retriever.manifest["corpus_version"],
        "index_version": retriever.manifest["index_version"],
        "configuration": CONFIGURATION,
        "configuration_sha256": digest(CONFIGURATION),
        "prompt_version": "analysis-selection-v1",
        "prompt_sha256": sha256(instruction.encode()).hexdigest(),
        # Hash file bytes to identify the code used; even comment edits change this fingerprint.
        "code_sha256": sha256(
            b"".join(
                (ROOT / name).read_bytes()
                for name in (
                    "app/service.py",
                    "app/calculator.py",
                    "app/retrieval.py",
                    "app/schemas.py",
                    "app/llm.py",
                )
            )
        ).hexdigest(),
        "retrieval": None,
        "selection": None,
        "call": None,
        "calculation": None,
        "error_code": None,
    }
    # Persist before any paid work; journal failures stop further requests.
    save_analysis(journal, record)
    try:
        if cancelled is not None and cancelled.is_set():
            raise EvidenceError("deadline_reached", "blocked")
        record["retrieval"] = retriever.search(
            question,
            method=method,
            k=CONFIGURATION["k"],
            report_ids=scope,
            run_id=record["run_id"],
            deadline=deadline,
            cancelled=cancelled,
        )
        save_analysis(journal, record)
        if clock() >= deadline or (cancelled is not None and cancelled.is_set()):
            raise EvidenceError("deadline_reached", "blocked")
        hits = record["retrieval"]["hits"]
        if not any(hit["cell_ids"] for hit in hits):
            raise EvidenceError("no_numeric_candidates")
        payload = model_input(question, hits, retriever.corpus["cells"])
        if provider is None:
            raise EvidenceError("live_generation_not_enabled", "blocked")
        # Gemini proposes an operation and cell IDs. calculate() reads the source values
        # and does the arithmetic; model-generated numbers are never used as operands.
        plan, call = provider.generate_json(
            payload,
            CellSelection,
            run_id=record["run_id"],
            instruction=instruction,
            deadline=deadline,
            cancelled=cancelled,
            metadata={
                "purpose": "fixed_analysis",
                "prompt_version": record["prompt_version"],
                "configuration_sha256": record["configuration_sha256"],
                "code_sha256": record["code_sha256"],
                "corpus_version": record["corpus_version"],
                "index_version": record["index_version"],
            },
        )
        record.update(selection=plan.model_dump(), call=call)
        save_analysis(journal, record)
        if clock() >= deadline or (cancelled is not None and cancelled.is_set()):
            raise EvidenceError("deadline_reached", "blocked")
        if plan.status != "ready":
            record.update(status=plan.status, error_code="model_abstention")
        else:
            record["calculation"] = calculate(plan, question, retriever.corpus["cells"], hits)
            record["status"] = "success"
    except TimeoutError:
        record.update(status="blocked", error_code="deadline_reached")
    except EvidenceError as error:
        record.update(status=error.status, error_code=error.code)
    except ProviderError as error:
        record.update(
            status="blocked" if error.record["status"] == "blocked" else "failed",
            error_code=str(error),
            call=error.record,
        )
    except OSError, sqlite3.Error:
        # Recording errors must remain visible to the caller, never look like a saved result.
        raise
    except ValueError:
        record.update(status="failed", error_code="invalid_analysis_input_or_output")
    except Exception:
        record.update(status="failed", error_code="internal_analysis_error")
    if record["status"] == "success" and (
        clock() >= deadline or (cancelled is not None and cancelled.is_set())
    ):
        record.update(status="blocked", error_code="deadline_reached", calculation=None)
    record["duration_seconds"] = round(perf_counter() - started, 6)
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    save_analysis(journal, record)
    return record
