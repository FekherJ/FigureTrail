"""A serial native-tool loop; scope, evidence permissions and limits belong to code."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
from time import monotonic, perf_counter
from uuid import uuid4

from google.genai import types
from pydantic import ValidationError

from app.calculator import EvidenceError, calculate
from app.corpus import digest
from app.llm import GENERATION_RPM, JOURNAL, ProviderError, wait_for_generation_slot
from app.schemas import AgentCalculation, AgentRead, AgentSearch, CellSelection
from app.service import CONFIGURATION, ROOT, execution_identity, model_input, save_analysis

AGENT_CONFIG = {
    "version": "bounded-agent-v1",
    "max_generation_calls": 4,
    "max_tool_calls": 6,
    "max_searches": 2,
    "max_history_characters": 22000,
    "tool_policy": "retrieved-chunks-then-read-cells-v1",
    "generation_rpm": GENERATION_RPM,
}
TOOLS = {
    "search_evidence": (
        AgentSearch,
        "Search the permitted reports. Returns chunk IDs and brief previews. Read selected chunks before calculating.",
    ),
    "read_evidence": (
        AgentRead,
        "Read previously retrieved chunk IDs, returning source context and original cell IDs/values. No paths or URLs.",
    ),
    "calculate": (
        AgentCalculation,
        "Calculate ratio_percent (numerator, denominator) or percent_change (new, old) using two previously read cell IDs. Python validates and calculates.",
    ),
}


def run_agent(
    question,
    retriever,
    provider,
    *,
    method="semantic",
    report_ids=None,
    journal=JOURNAL,
    run_id=None,
    deadline=None,
    cancelled=None,
    clock=monotonic,
):
    """Execute up to four model turns with serial, permission-checked tools.

    Args:
        question: User question; never replaced by a model's rewritten search query.
        retriever: Loaded index and request-local provider/cache bindings.
        provider: Shared Gemini wrapper; None blocks hosted work.
        method: Fixed retrieval method used by every search in this execution.
        report_ids: Explicit user scope, validated once and immutable during the loop.
        journal: Shared provider/analysis journal path.
        run_id: Optional caller-assigned UUID.
        deadline: Absolute stop time; None uses the fixed workflow's 60-second limit.
        cancelled: Optional cooperative stop Event; remote calls cannot be recalled.
        clock: Monotonic time function, replaceable for deterministic deadline tests.

    Returns:
        Saved analysis with sanitized calls/tool events, or an explicit non-answer.
        Storage failures propagate before further model work. Raw SDK content and
        opaque thought signatures stay in memory only for the next native turn.
    """
    scope = retriever.validate_request(question, method, CONFIGURATION["k"], report_ids)
    # A tuple cannot be widened by a model-supplied query or mutable request argument.
    scope = tuple(scope) if scope is not None else None
    started = perf_counter()
    deadline = clock() + CONFIGURATION["deadline_seconds"] if deadline is None else deadline
    instruction = (ROOT / "prompts/agent.md").read_text(encoding="utf-8")
    identity = execution_identity(method, list(scope) if scope is not None else None)
    identity["configuration"].update(
        version=AGENT_CONFIG["version"],
        payload="native-content-history-v1",
        generation_calls=AGENT_CONFIG["max_generation_calls"],
    )
    identity["configuration"]["agent"] = dict(AGENT_CONFIG)
    identity["configuration_sha256"] = digest(identity["configuration"])
    identity["identity_version"] = "agent-execution-v1"
    limits = identity["configuration"]["agent"]
    record = {
        "run_id": run_id or str(uuid4()),
        "status": "started",
        "mode": "agent",
        "question": question,
        "report_ids": list(scope) if scope is not None else None,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrieval_method": method,
        "corpus_version": retriever.manifest["corpus_version"],
        "index_version": retriever.manifest["index_version"],
        **identity,
        "prompt_version": "bounded-agent-v1",
        "prompt_sha256": sha256(instruction.encode()).hexdigest(),
        "retrieval": {"hits": [], "query_embedding": None},
        "searches": [],
        "selection": None,
        "calculation": None,
        "call": None,
        "calls": [],
        "tool_events": [],
        "error_code": None,
        "generation_wait_seconds": 0.0,
    }
    messages = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=json.dumps(
                        {
                            "question": question,
                            "report_ids": record["report_ids"],
                            "limits": limits,
                        }
                    )
                )
            ],
        )
    ]
    retrieved, read = {}, {}

    def check_deadline():
        if clock() >= deadline or (cancelled is not None and cancelled.is_set()):
            raise EvidenceError("deadline_reached", "blocked")

    save_analysis(journal, record)
    try:
        if provider is None:
            raise EvidenceError("live_generation_not_enabled", "blocked")
        for turn in range(1, limits["max_generation_calls"] + 1):
            check_deadline()
            if len(record["tool_events"]) >= limits["max_tool_calls"]:
                raise EvidenceError("tool_limit", "blocked")
            history = json.dumps(
                [item.model_dump(mode="json", exclude_none=True) for item in messages]
            )
            if len(history) > limits["max_history_characters"]:
                raise EvidenceError("context_too_large", "blocked")
            record["generation_wait_seconds"] += wait_for_generation_slot(
                journal,
                deadline=deadline,
                cancelled=cancelled,
            )
            action, content, call = provider.agent_turn(
                messages,
                TOOLS,
                run_id=record["run_id"],
                instruction=instruction,
                deadline=deadline,
                cancelled=cancelled,
                metadata={
                    "purpose": "bounded_agent",
                    "turn": turn,
                    "configuration_sha256": record["configuration_sha256"],
                    "code_sha256": record["code_sha256"],
                    "prompt_sha256": record["prompt_sha256"],
                    "corpus_version": record["corpus_version"],
                    "index_version": record["index_version"],
                },
            )
            record["calls"].append(call)
            record["call"] = call
            save_analysis(journal, record)
            check_deadline()
            if action["type"] == "abstention":
                record.update(status=action["status"], error_code="model_abstention")
                break
            name, arguments = action["name"], action["arguments"]
            event = {
                "step": len(record["tool_events"]) + 1,
                "name": name,
                "arguments": arguments,
                "status": "started",
                "error_code": None,
            }
            record["tool_events"].append(event)
            save_analysis(journal, record)
            tool_started = perf_counter()
            try:
                if name not in TOOLS:
                    raise EvidenceError("unknown_tool", "failed")
                params = TOOLS[name][0].model_validate(arguments)
                check_deadline()
                if name == "search_evidence":
                    if len(record["searches"]) >= limits["max_searches"]:
                        raise EvidenceError("search_limit", "blocked")
                    result = retriever.search(
                        params.query,
                        method=method,
                        k=CONFIGURATION["k"],
                        report_ids=list(scope) if scope is not None else None,
                        run_id=record["run_id"],
                        deadline=deadline,
                        cancelled=cancelled,
                    )
                    record["searches"].append(result)
                    embedding_call = (result.get("query_embedding") or {}).get("call")
                    if embedding_call:
                        record["calls"].append(embedding_call)
                    for hit in result["hits"]:
                        retrieved[hit["chunk_id"]] = hit
                    record["retrieval"]["hits"] = list(retrieved.values())
                    output = {
                        "hits": [
                            {
                                key: hit[key]
                                for key in ("chunk_id", "source_id", "report_id", "rank", "score")
                            }
                            | {"preview": hit["text"][:200]}
                            for hit in result["hits"]
                        ]
                    }
                elif name == "read_evidence":
                    if any(key not in retrieved for key in params.chunk_ids):
                        raise EvidenceError("evidence_not_retrieved", "failed")
                    chunks = [retrieved[key] for key in params.chunk_ids]
                    output = json.loads(model_input(question, chunks, retriever.corpus["cells"]))
                    read.update({chunk["chunk_id"]: chunk for chunk in chunks})
                else:
                    selection = CellSelection(status="ready", **params.model_dump())
                    # Only explicitly read chunks grant permission to use their cells.
                    calculation = calculate(
                        selection, question, retriever.corpus["cells"], list(read.values())
                    )
                    check_deadline()
                    record.update(
                        selection=selection.model_dump(), calculation=calculation, status="success"
                    )
                    output = {"status": "success", "calculation": calculation}
                event.update(status="executed", result=output)
            except ValidationError:
                event.update(status="rejected", error_code="invalid_tool_arguments")
            except EvidenceError as error:
                event.update(status="rejected", error_code=error.code)
                if error.status == "blocked":
                    raise
            event["duration_seconds"] = round(perf_counter() - tool_started, 6)
            save_analysis(journal, record)
            if record["status"] == "success":
                break  # The validated code result is final; no extra model call.
            check_deadline()
            # Keep the full model Content in memory: native signatures must survive turns.
            messages.extend(
                [
                    content,
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=name,
                                    id=action.get("provider_call_id"),
                                    response=event.get("result")
                                    or {"error_code": event["error_code"]},
                                )
                            )
                        ],
                    ),
                ]
            )
        else:
            raise EvidenceError("generation_limit", "blocked")
    except TimeoutError:
        record.update(status="blocked", error_code="deadline_reached")
    except EvidenceError as error:
        record.update(status=error.status, error_code=error.code)
    except ProviderError as error:
        record["calls"].append(error.record)
        record.update(
            status="blocked" if error.record["status"] == "blocked" else "failed",
            error_code=str(error),
            call=error.record,
        )
    except OSError, sqlite3.Error:
        raise
    except ValueError:
        record.update(status="failed", error_code="invalid_agent_input_or_output")
    except Exception:
        record.update(status="failed", error_code="internal_analysis_error")
    if record["status"] == "success":
        try:
            check_deadline()
        except EvidenceError:
            record.update(status="blocked", error_code="deadline_reached", calculation=None)
    if record["tool_events"] and record["tool_events"][-1]["status"] == "started":
        record["tool_events"][-1].update(status="failed", error_code=record["error_code"])
    record.update(
        duration_seconds=round(perf_counter() - started, 6),
        finished_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    save_analysis(journal, record)
    return record
