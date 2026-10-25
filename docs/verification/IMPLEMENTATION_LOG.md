# Implementation and reproduction log

**Updated: 25 October 2026. Current step: B03 source-case pilot verified; quota and tool-call checks pending.**

This file records completed work, commands, decisions, observed results and the next handoff. Earlier milestones are summarized from saved verification reports; a complete historical shell transcript is not available. Current source files and linked evidence provide the implementation details. Append new verified steps here rather than inventing missing history.

Commands use PowerShell from the repository root. They contain no credential values. Commands marked **live** send provider requests; reading saved evidence and running offline tests do not. Reproduction commands use `uv run --locked`; the latest execution used the same environment directly through `.venv\Scripts\python.exe` and `.venv\Scripts\ruff.exe`.

## 1. Completed milestones

| Date | Work | Verified evidence |
|---|---|---|
| 24 October | B01: inspect FinQA, separate sources/references, review ten two-cell examples, record periods/units and duplicate contexts | [B01 report](B01_DATA_VERIFICATION.md); ten valid cases and three negative tests |
| 24 October | B02: isolated Python, locked dependencies, FastAPI health/OpenAPI, SQLite FTS5 and NumPy checks | [B02 report](B02_ENVIRONMENT.md) |
| 25 October | Standardize authored repository content and GitHub issues in clear US English; verify issue import | [Structure review](STRUCTURE_REVIEW.md); latest published foundation commit `d5c26ca` |
| 25 October | Select Gemini generation/embedding models using official capabilities, prices and limits | [Provider decision](../architecture/PROVIDER_SELECTION.md) |
| 25 October | Configure local key; install SDK; test structured generation and one embedding | [Connection report](B03_PROVIDER_CONNECTION.md) |
| 25 October | Centralize SDK requests, add selection contract/prompt, SQLite call journal and source-case runner | [Source-case report](B03_SOURCE_CASE.md) and [snapshot](B03_SOURCE_CASE_RESULTS.json) |

The current provider and source-case changes are local. No new commit/push or GitHub status change was made during these two implementation steps. The repository backlog is now [BACKLOG.md](../Backlog/BACKLOG.md); the old French filename is historical. Issue import does not provide recurring Markdown synchronization.

## 2. Inspect and restore the environment

Read [engineering instructions](../../AGENTS.md), [README](../../README.md), [architecture](../architecture/ARCHITECTURE.md), [standards](../architecture/AI_PROJECT_BLUEPRINT.md) and the backlog before editing.

```powershell
git status --short
git log -1 --format='%h %s'
uv sync --locked --no-build
uv run --locked python -B -X utf8 scripts/check_environment.py
```

For a fresh environment only, create it first if `.venv` is missing:

```powershell
python3.14.exe -m venv .venv --without-pip
```

Verified runtime: Windows, Python 3.14.5, uv 0.11.14 and Google GenAI SDK 2.33.0. The latest locked synchronization installed 33 packages; the lockfile includes 34 entries including the project. Existing application dependency versions were preserved.

Dependency-change history, **already completed; do not repeat for ordinary setup**:

```powershell
uv add google-genai --no-build --link-mode copy
uv lock --offline
uv sync --locked --offline --no-build --link-mode copy
```

The first SDK install without `--link-mode copy` failed because the execution sandbox blocked a Windows package launcher. uv rolled that dependency change back. The successful install ran outside that restricted sandbox. `pyproject.toml` was then bounded to `google-genai>=2.33,<3`; `httpx>=0.28,<1` was declared for offline transport tests. `uv lock --offline` recorded the final constraints. Use the committed lockfile on another machine; `--offline` requires cached packages.

An execution-only `UV_CACHE_DIR` override was used to work around sandbox cache permissions. It is not a project setting and is unnecessary on a normal working environment. No custom SDK, agent framework or additional service was introduced.

## 3. Prepare and verify the public data

If `data/raw/finqa-dev.json` is absent:

```powershell
New-Item -ItemType Directory -Force -Path data/raw | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/dev.json' -OutFile data/raw/finqa-dev.json
```

Preserve an existing raw file. Generate exports only if needed, then verify:

```powershell
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
```

Ten source exports and ten reference exports are separate. Source inputs allow only `filename`, `pre_text`, `post_text`, `table` and `table_ori`. Raw annotations and everything in `evals/` or verification reports stay out of model context. The raw-file hash, numerical conventions and reviewed operands are checked by the existing verifier. See [provenance](../../data/FINQA_PROVENANCE.md).

## 4. Configure the local key

Create a key in Google AI Studio as described in [Google's instructions](https://ai.google.dev/gemini-api/docs/api-key). Start without enabling paid billing. The key was created and configured before the connection tests; its value was never supplied in chat or committed.

For initial Windows configuration, run the first line by itself, paste the key at the hidden prompt, and press Enter:

```powershell
$figuretrailKey = Read-Host "Paste your Gemini API key" -AsSecureString
```

Then run:

```powershell
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', $figuretrailKey).Password
[Environment]::SetEnvironmentVariable('GEMINI_API_KEY', $env:GEMINI_API_KEY, 'User')
Remove-Variable figuretrailKey
-not [string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)
```

Expected: `True`, confirming presence only. It does not validate authentication. For an already saved key in an existing terminal that has not inherited it:

```powershell
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
```

The application explicitly reads `GEMINI_API_KEY`. No `.env` loader is installed. Do not display the key, paste it into a command, include it in an AI prompt or send a screenshot containing it.

## 5. Connection checks and the SDK retry decision

Two authenticated GET requests to Google's documented `/v1beta/models/{model}` endpoints confirmed both selected IDs. They made no generation/embedding requests. The generation metadata advertised `generateContent`; the embedding metadata advertised `embedContent`.

The first live command originally ran as:

```powershell
& '.venv\Scripts\python.exe' -B -X utf8 scripts/check_provider.py --live
```

Observed: one JSON response `{"status":"ready"}` in 1.015 s and one normalized 768-dimension text embedding in 0.376 s. These historical values remain in the connection snapshot.

After moving shared code into `app/llm.py`, use module execution so Python resolves application imports from the repository root:

```powershell
uv run --locked python -B -X utf8 -m scripts.check_provider --live
```

This is an optional **live** connection recheck, not needed to read the existing proof. The refactored version was exercised with offline responses; it was not rerun live during the source-case step.

An offline HTTP 429 test caught an unwanted repeat in the SDK's Interactions adapter: client initialization changed zero attempts to one, and that adapter interpreted the value as a retry count. The implementation uses the supported `generateContent`/`embedContent` paths with **one total attempt**. Offline tests verify one request per error on both paths. No private SDK internals are patched. Recheck this after SDK upgrades.

## 6. Source-case implementation

| File | Responsibility |
|---|---|
| [app/llm.py](../../app/llm.py) | SDK client, shared generation/embedding requests, limits, sanitized errors and cumulative SQLite allowances |
| [app/schemas.py](../../app/schemas.py) | Strict source/plan schemas, original-table IDs and numeric source resolution |
| [cell_selection.md](../../prompts/cell_selection.md) | Versioned instructions for an operation and ordered cell references or abstention |
| [run_source_case.py](../../scripts/run_source_case.py) | Controlled request, source-reference validation and separate post-call reference comparison |
| [check_provider.py](../../scripts/check_provider.py) | Two-request connection diagnostic using the shared module |
| [test_source_case.py](../../tests/test_source_case.py) | Source leakage, invalid states/IDs and a budget block before network access |
| [test_provider_connection.py](../../tests/test_provider_connection.py) | SDK quota failures, no retries, retained unknown usage and credential exclusion |

The source-case pipeline is:

1. Load the existing source-only JSON and validate its five fields and table shape.
2. Render the original table with stable zero-based IDs, preserving headers and all accompanying text. The known normalized dash/`2014` conflict is not rewritten.
3. Load the versioned instruction file. Keep question/source data separate from trusted instructions.
4. Reserve a local allowance and record the call before sending it.
5. Request a schema-bound `CellSelection`, at most 1,000 output tokens, minimal thinking, no automatic tool execution and no retries.
6. Validate the JSON and state-dependent fields. Resolve each selected ID within the supplied original table and require a finite decimal source value.
7. Read the reviewed expected operation and cells **after** the requests; compare outside inference.
8. Save sanitized call metadata and a local result summary, then publish a deliberate evidence snapshot.

`ready` means a proposed selection is available for validation. It is not the final analysis state `success`. The model never provides the numeric operands or result. Runtime calculation and complete unit/period checks remain B06 work.

## 7. Exact live source-case commands and observations

Executed on 25 October 2026 after the offline suite passed:

```powershell
& '.venv\Scripts\python.exe' -B -X utf8 -m scripts.run_source_case --live --repetitions 3
& '.venv\Scripts\python.exe' -B -X utf8 -m scripts.run_source_case --live --scenario missing-period
```

Equivalent locked reproduction commands, both **live**:

```powershell
uv run --locked python -B -X utf8 -m scripts.run_source_case --live --repetitions 3
uv run --locked python -B -X utf8 -m scripts.run_source_case --live --scenario missing-period
```

Observed:

- Canada question: all three runs selected `ratio_percent`, `table[3][4]` then `table[5][4]`. Python resolved 60 and 243 MMBoe from source cells.
- Generation times: 1.056, 0.950 and 0.876 s; median 0.950 s, meeting the written five-second pilot target.
- Missing-period question: `insufficient_evidence`, null operation and no cells in 0.961 s.
- Four live requests; all expected outcomes matched. This is one answerable development example repeated three times plus one negative variant. No benchmark accuracy, retrieval quality or generalization score is established.

No option without `--live` sends a request. The default source-case repetition count is one; the maximum is three. Each completed provider call has its own `run_id`/`call_id`. The runner records unexpected model/reference outcomes rather than replacing them with the reference answer.

## 8. Spending, traces and their limits

`data/local/runs.sqlite` records calls across commands. Each request reserves €1 for generation or €0.01 for an embedding against a €25 local allowance cap. Reservation is atomic and the transaction closes before network access. Unknown usage and interrupted calls retain their allowance. A blocked reservation sends no request and records the block.

The four source-case calls reported 9,631 total tokens. Pricing every token at the highest published generation rate gives a conservative paid equivalent of $0.0240775. The local accounting multiplies such estimates by a planning factor of €2/USD, not a verified exchange rate. The journal currently holds **€0.0681550** in allowances, including €0.02 assigned to earlier connection requests. These are not actual charges. Free-tier eligibility, tax, conversion and provider reporting require separate checks; no billing setting was changed.

The shared module records model/SDK versions, hashes, output, errors, duration, token counters and allowances. Unknown counters stay `null`. It excludes credentials, arbitrary exception messages, raw response bodies and private chain of thought. Input text is represented in the call journal by hashes; the public question appears in the pilot summary.

Transport timeout: 20 s. The source-case command supplies a 60 s deadline and remaining-time request bounds; these are not a guarantee of strict wall-clock cancellation across all transport stages. Full API failure handling and cancellation remain implementation work.

Generated traces remain ignored by Git. Do not delete or reset the journal to bypass the spending limit. Selected sanitized evidence lives in `docs/verification/`; reference answers and these reports are excluded from future corpus ingestion.

## 9. Offline verification and inspection

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check app scripts/check_environment.py scripts/check_provider.py scripts/run_source_case.py tests/test_provider_connection.py tests/test_source_case.py
uv run --locked python -B -X utf8 -m unittest discover -s tests -v
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
git diff --check
git status --short
```

The execution used the corresponding `.venv\Scripts\ruff.exe` and `.venv\Scripts\python.exe` commands. Seven offline tests passed before the live pilot. Tests include two SDK endpoint subcases plus the existing B01 guards. A Windows cleanup failure in the initial new test was corrected by explicitly closing SQLite connections; the test suite then passed.

After the pilot, Ruff lint and formatting of nine selected files passed, the lockfile check passed, and the provider test passed again with an additional unknown-usage allowance assertion. Documentation checks validated 98 local links with exact filename case. Code/prompt hashes matched the measured snapshots and all four model inputs were reconstructed from current source files. Twenty-two protected raw/source/reference/license artifacts matched their earlier hashes. Git whitespace checks passed; the journal and generated pilot summaries were confirmed ignored. No further live requests were used for these checks.

README, backlog, architecture, provider decision, contribution instructions and related verification documents were aligned with the implemented scope. Historical statements in the first B01 case and structure review were identified as earlier snapshots and given current B03 status, preserving their original numerical evidence.

The no-live safeguard was checked with this command; it exited with an explicit opt-in error before sending anything:

```powershell
& '.venv\Scripts\python.exe' -B -X utf8 -m scripts.run_source_case
```

Read the saved results without any API call:

```powershell
Get-Content -LiteralPath docs/verification/B03_SOURCE_CASE.md
Get-Content -LiteralPath docs/verification/B03_SOURCE_CASE_RESULTS.json
```

## 10. Continue with an AI coding assistant

The next assistant can use this handoff, together with the actual repository files:

> Read AGENTS.md, README.md, docs/architecture/ARCHITECTURE.md, docs/architecture/PROVIDER_SELECTION.md, docs/Backlog/BACKLOG.md and this implementation log. Inspect the current Git diff before editing. B03 has a verified provider connection, centralized SDK requests, a SQLite allowance journal, three matching source selections at a 0.95 s median and one observed missing-period abstention. Verify the remaining account quota and tool-call compatibility requirements without building the B10 agent early. Keep source/reference separation, explicit live opt-in, call limits, unknown usage, existing numerical fixtures and the sub-€30 project ceiling. Keep credentials private; read the configured key only in memory for authorized provider requests. Leave changes reviewable, preserve billing settings and keep B03 open until its remaining criteria have evidence. Add only what the current backlog item needs. Update this log with actual commands, results and failures after each meaningful step.

Next work: inspect actual project quotas, run a bounded tool-call compatibility check, complete remaining B03 verification and then build the annotation-free corpus in B04. The indexed corpus, retrieval comparison, numerical analysis service, UI, API analysis endpoints and bounded agent remain planned.

## 11. Backlog review and GitHub alignment — 25 October 2026

Requested scope: review/update the backlog; the user will commit and push. No application code, model configuration or data changed during this review, and no provider request was sent.

B02's saved evidence met all acceptance criteria. The published foundation revision `d5c26caaa74713aa472f90658981ab8e5f92c589` was confirmed on GitHub; the health/environment-check code was unchanged from it. Current dependency/FTS5/NumPy checks passed. An in-process ASGI check verified health and OpenAPI without opening a network listener. Its first inline invocation failed due to PowerShell quoting; rerunning it as a temporary Python script passed. A PowerShell-safe equivalent is:

```powershell
@'
import asyncio
import httpx
from app.main import app

async def check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        if health.status_code != 200 or health.json() != {"status": "ok", "corpus_version": None}:
            raise RuntimeError("Health contract failed")
        schema = await client.get("/openapi.json")
        if schema.status_code != 200 or set(schema.json()["paths"]) != {"/health"}:
            raise RuntimeError("OpenAPI contract failed")
        print("Health and OpenAPI checks passed")

asyncio.run(check())
'@ | uv run --locked python -B -X utf8 -
```

Read-only commands used for the review:

```powershell
git status --short
git log -1 --format='%H %s'
git diff HEAD -- app/main.py scripts/check_environment.py
uv run --locked python -B -X utf8 scripts/check_environment.py
gh api repos/FekherJ/FigureTrail/commits/main --jq .sha
gh issue list --repo FekherJ/FigureTrail --state all --limit 100 --json number,title,state,body
gh project item-list 2 --owner FekherJ --format json
gh project field-list 2 --owner FekherJ --format json
```

The GitHub integration had previously lacked write permission, so the review used the already authenticated `gh` connection. B02's prepared JSON patch included its reviewed body, `state: closed` and `state_reason: completed`; B03's prepared Markdown body was generated from its local backlog section, preserving the historical source link and keeping unpublished evidence paths as inline repository paths. The mutation record is below. The two payload filenames stand for task-local files, not repository files or commands to run during setup; recreate them from reviewed content if repeating this operation.

```powershell
gh api --method PATCH repos/FekherJ/FigureTrail/issues/2 --input prepared-b02-patch.json
gh issue edit 3 --repo FekherJ/FigureTrail --body-file prepared-b03-body.md
gh project item-edit --id PVTI_lAHOBWzpAs4BolTFzhDR8FA --project-id PVT_kwHOBWzpAs4BolTF --field-id PVTSSF_lAHOBWzpAs4BolTFzhnEubk --single-select-option-id 98236657
gh project item-edit --id PVTI_lAHOBWzpAs4BolTFzhDR8IE --project-id PVT_kwHOBWzpAs4BolTF --field-id PVTSSF_lAHOBWzpAs4BolTFzhnEubk --single-select-option-id 47fc9ee4
```

Result, confirmed by rereading issue bodies/states and board fields:

- B01 and B02: closed / Done. B02's final review was recorded in its issue and report.
- B03: open / In progress; five completed checklist items and two remaining: actual model-specific quotas, then a bounded tool-call compatibility check. The mixed access/quota/tools item was split to show partial completion accurately.
- B04–B06: open / Ready, preserving the board's existing planning choices.
- B07–B13: open / Backlog.
- All thirteen issue and board-item identities were retained; the other eleven issues/items were preserved. Local/GitHub B03 checklist text and check marks match after normalizing Windows line endings.

Local backlog, README, instructions and B02 status notes were aligned. Historical import snapshots retain their original observations. Issue changes are already live; provider/pilot files and these local documentation changes await the user's commit/push. This is a one-time synchronization; a push does not automatically update GitHub issue bodies or board status.

Final review checks: 100 local Markdown links validated, 22 protected artifacts unchanged, and the four measured source requests/code/prompt hashes still reconstructible. Git whitespace checks passed. No application code or model request was needed for the backlog alignment.
