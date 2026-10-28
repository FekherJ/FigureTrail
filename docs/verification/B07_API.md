# B07 — Documented local analysis API

**Verified 28 October 2026.** Base commit: `9e9bc95`; B07 changes are local pending the user's commit/push.

## Scope and implementation

The HTTP layer reuses the B06 service and calculator. It does not add a second inference workflow, frontend or agent. Existing development results retain their original versions and failures.

| File | Responsibility |
|---|---|
| [main.py](../../app/main.py) | Local request checks, startup, routes, single-analysis slot and HTTP deadline |
| [schemas.py](../../app/schemas.py) | Strict request schema and typed public reports, evidence, calculations and errors |
| [service.py](../../app/service.py) | Shared analysis, supplied run ID, stage cancellation checks and read-only result lookup |
| [retrieval.py](../../app/retrieval.py) | Existing search with remaining deadline passed to query embeddings |
| [embeddings.py](../../app/embeddings.py) | Existing cache and deadline-aware pacing |
| [llm.py](../../app/llm.py) | Budget reservations, sanitized errors and bounded SDK requests |
| [test_api.py](../../tests/test_api.py) | 17 API, lifecycle, security and deadline tests with simulated SDK responses |

Startup validates and loads the current source-only corpus/index once. With neither pointer present, `/health` and documentation remain available and analysis/report routes return 503. Partial or corrupt bundles fail startup. Restart after publishing a new corpus/index; previous saved results keep their recorded versions.

## Routes and contracts

| Route | Behavior |
|---|---|
| `GET /health` | Process availability and loaded corpus version; no AI request |
| `GET /reports` | Versioned report IDs, source IDs and chunk counts; no annotations or invented company labels |
| `POST /analyses` | Fixed semantic k=5 analysis; one search, at most one generation and at most one missing query embedding |
| `GET /analyses/{run_id}` | Read saved public result without provider initialization, model calls or journal writes |
| `GET /docs`, `/openapi.json` | Current generated API contract; Swagger browser assets may need internet access |

Accepted JSON has `question` (1–2000 characters, nonblank), optional `report_ids` (1–40 known IDs, or `null` for the full corpus) and `mode: "fixed"`. Unknown fields, types, report IDs and agent mode are rejected before provider initialization. Clients cannot choose paths, URLs, models, prompts or retrieval settings.

Public results include run ID, state, question/scope, evidence chunks/cell IDs, structured selection, validated calculation, source operands, timestamps, versions and safe call summaries. Decimal values are strings. Unreported token counters remain `null`; cost allowances are not confirmed charges. Internal SDK metadata, raw exceptions and credential values are excluded from the public projection.

After assigning an execution ID, error responses preserve it. Initial persistence happens before inference. If storage/setup fails, a response can contain an ID without a durable result; the response explicitly states that storage cannot be guaranteed. A missing or unreadable database must never trigger a replacement model call.

## HTTP outcomes

| HTTP | Meaning |
|---|---|
| 200 | Completed `success`, `insufficient_evidence` or `unsupported_request`; saved lookup also returns 200 for any recorded state |
| 400 / 403 | Invalid local Host / foreign or null Origin |
| 409 | Another analysis is still active, or an accepted execution was blocked by the budget |
| 413 / 415 | JSON body above 32,768 bytes / missing or unsupported content type |
| 422 | Invalid JSON, question, scope, mode, extra field or UUID |
| 404 | Valid UUID with no saved analysis |
| 500 | Unexpected internal analysis failure |
| 502 | Provider failure, invalid structured model output or invalid model-selected cells |
| 503 | Missing index/key or unavailable storage/setup |
| 504 | Analysis deadline or provider transport/HTTP 504 timeout |

Accepted completed executions return the typed analysis response even on 409/500/502/504. Request/preflight failures and an HTTP timeout before worker finalization return `APIError`: `status`, `error_code`, safe `message`, optional `run_id`. Concurrency errors create no execution. Validation errors omit raw request bodies and exception details. OpenAPI describes both result/error forms.

## Local operating limits

Run one Uvicorn worker bound to `127.0.0.1`, without reload. Host accepts `127.0.0.1` or `localhost`; browser Origin, when supplied, must exactly match scheme/host/port. Requests without Origin support CLI clients. Analysis requires JSON; the body limit also applies without Content-Length. There is no permissive CORS configuration, arbitrary ingestion or public-deployment authentication.

The HTTP analysis wait is bounded at 60 seconds after validated admission. Pacing and SDK calls receive the remaining deadline. SDK transport timeouts are at most 20 seconds, generation remains capped at 1000 output tokens and automatic retries remain disabled. A deadline reached during budget reservation prevents network access. Known pre-network deadline blocks release their unused reservation; unknown usage after a network attempt stays reserved.

Python cannot forcibly kill a running thread or recall an already submitted hosted request. After HTTP timeout, the worker retains the only analysis slot until it exits. Stage checks discard late numerical output, and lookup can temporarily show `started` before the final `blocked` state. Shutdown signals active work and waits for it to finish. A process crash can leave a started execution; automatic recovery/reconciliation is outside this milestone. These controls do not prove a strict remote-execution kill or solve the existing provider latency/reliability limits.

## Reproduce

After preparing/building the corpus and configuring the key in the server environment, run from the repository root:

```powershell
uv run --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In a second terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/reports
$body = @{
    question = "In Devon's estimated 2008 production table, what percentage of total production in MMBoe comes from Canada?"
    report_ids = @('DVN/2007')
    mode = 'fixed'
} | ConvertTo-Json
$analysis = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analyses -ContentType 'application/json' -Body $body
$analysis.calculation
Invoke-RestMethod "http://127.0.0.1:8000/analyses/$($analysis.run_id)"
```

POST is the explicit request to run hosted inference and consumes quota; it does not have a CLI `--live` flag. GET and server startup make no AI calls. A rerun creates a new ID; identical query embeddings are reused. A successful calculation can show `24.69 %`; actual live outcomes remain subject to retrieval, model selection and provider availability. The POST example above was not sent to a live model during B07 verification.

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check app tests/test_api.py
uv run --locked python -B -X utf8 -m unittest discover -s tests -v
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m scripts.prepare_corpus --check
uv run --locked python -B -X utf8 -m scripts.build_index --check
```

## Observed verification

All **51 offline tests passed in 6.855 seconds**, including the existing 34 and 17 new API tests. The tests cover success, read-only saved lookup, cached question reuse, abstentions, invalid requests, malformed JSON, unknown UUIDs, local Host/origin/content type/body limits, budget blocks, invalid model output/cells, sanitized 429/504/transport failures, missing key/index, corrupt storage, concurrent requests and late worker completion. No live SDK request was made.

One automated test starts Uvicorn on an ephemeral loopback TCP port, sends real HTTP health/report/analysis/lookup requests with simulated SDK generation/embedding responses, verifies 24.69%, and shuts down the server. Its timing does not measure hosted model latency.

Separate checks against the actual local project loaded all 20 report groups and read all 14 existing B06 analyses through the API: 7 successes, 4 failures, 2 insufficient-evidence states and 1 unsupported request. Values/states matched stored records; no SDK client was created. All 215 provider-call records and all 14 analysis records are unchanged. Sources, corpus/index bundles, caches, prior evidence, lockfile and private files retain their baseline hashes. The local allowance remains EUR 6.1633250; actual spending is unknown. No dependencies, billing settings, staging, commit or push changed.

The installed Starlette emits an `httpx` TestClient deprecation warning. The locked combination passes; dependency migration is separate maintenance work. The warning is not suppressed. Existing B06 provider 504s and 15–19-second follow-up latency remain unresolved. Wider answer-quality and latency evaluation belongs to B08.

See [machine-readable checks](B07_API_RESULTS.json) and the [implementation log](IMPLEMENTATION_LOG.md). Historical B01–B06 reports retain their dated counts and limitations.

References checked for this implementation: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [response models](https://fastapi.tiangolo.com/tutorial/response-model/) and [Python tasks, shielding and timeouts](https://docs.python.org/3.14/library/asyncio-task.html). Embedding timeout support was inspected in the installed Google GenAI 2.33.0 Pydantic SDK schema.
