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

## 12. Architecture walkthrough and contribution guidance - 25 October 2026

Reviewed the README, architecture, blueprint, backlog, HTTP entry point, dependency configuration and contributor instructions after a request to clarify the project and development workflow.

- The backend foundation is `app/`; only `/health` is exposed today. The provider/source-case experiments run through scripts and are not yet integrated into an analysis endpoint.
- The target frontend is one HTML/CSS/JavaScript page served by FastAPI in B09. The analysis service, retrieval, calculator and corpus access will be added with their working features. The current flat modules express responsibilities without requiring separate deployments or empty controller/service/repository directories.
- `.venv/` isolates Python dependencies. A `.env` file is a separate configuration convention and is not currently loaded. The provider reads `GEMINI_API_KEY` from the process environment; no credential value was read or displayed during this review.
- PowerShell is the current Windows shell. It is independent of the Python virtual environment and application architecture. A Unix shell is optional and is not required for the current verified setup.
- Added a communication section to `AGENTS.md`: explain each step's purpose and place in the architecture, unfamiliar commands, implemented versus planned behavior, verification and the next step.

Repository checks used ordinary Git operations:

```powershell
git status --short
git log -1 --format='%H %s'
```

Before these documentation edits, the working tree was clean at `f3be9ea2fbac4f8395689e07d276d5ee1e40b0ca` (`feat: add Gemini source-selection pilot and usage tracking`). The sandbox initially could not access the installed Git executable; the read succeeded with the permitted execution context. This was an assistant execution constraint, not a change to project commands. The temporary PowerShell documentation patch was blocked by the machine's script execution policy before it changed files. A Python helper applied the reviewed text instead; no execution policy was changed. The final documentation diff was checked with `git diff --check` and reviewed for scope.

No runtime code, dependencies, data, model settings or backlog status changed. No live model request, billing change, commit or push was made. Next technical work remains the two B03 checks: actual account quotas and bounded tool-call compatibility.

## 13. README consistency review - 25 October 2026

Compared the README with the current HTTP entry point, shared Gemini module, provider/source-case scripts, dependency configuration, architecture and backlog.

The existing measurements, model configuration, setup commands and B03 status were consistent with the implementation. Updated the README to show the planned frontend explicitly, explain the target workflow and current script/API boundary, distinguish `.venv` from `.env`, describe PowerShell and command flags, include `prompts/` and the provider module in the repository overview, and identify the remaining B03 work before B04.

Verification: all local README links resolve with matching case, existing command targets and the implemented `/health` contract were checked against code, and `git diff --check` passed. This review did not repeat runtime tests or live model calls; existing measurement dates and scope remain unchanged. No application code, dependency, data, credentials or backlog state changed. Earlier AGENTS/log edits were preserved; no commit or push was made.

Git commands used for this review:

```powershell
git status --short
git diff --stat
git diff --check
git diff -- README.md
```

## 14. Focused code comments - 25 October 2026

Added comments only around non-obvious decisions in `app/llm.py` and `app/schemas.py`: one-attempt SDK calls, atomic allowance reservations, safe error metadata, local output validation, explicit tool control, normalized embeddings, source-only fields, original-table coordinates and source-derived operands. Existing explanations in the pilot/data scripts were retained; self-explanatory health code was left unchanged. AGENTS now records the preference for sparse comments that explain decisions and boundaries.

A temporary standard-library review helper compared the Python syntax trees and all non-comment tokens before and after the edits. Both were identical in both modules. Ruff lint, formatting and Git whitespace checks passed:

```powershell
uv run --locked --offline ruff check app/llm.py app/schemas.py
uv run --locked --offline ruff format --check app/llm.py app/schemas.py
git diff --check
git diff -- app/llm.py app/schemas.py
```

The three-file pilot fingerprint changed from `668d9ca89a4fabae1139494140c8325198935c32df104dcff63599dc34a4aff2` to `8118671e0047a3ad583d855782fd373fbcafd77f613bca0891b6af7e1ed4ebad` because comments change source bytes. The original fingerprint matches the historical measured requests. Their JSON snapshot remains byte-for-byte unchanged; the pilot report now identifies the historical revision (`f3be9ea`) explicitly. No model measurements were repeated or relabeled as current.

No executable statements, contracts, dependencies, prompts or data changed. Existing README/AGENTS/log changes were preserved. No runtime test campaign, live provider request, commit or push was made. Next technical work remains the B03 quota and tool-call checks.

## 15. Account quota evidence - 25 October 2026

Transcribed the user-supplied Google AI Studio screenshot into `B03_ACCOUNT_LIMITS.md`. Project label: FigureTrail; displayed tier: free; reporting period: 28 days. The screenshot has no visible capture timestamp; the observation date records its receipt.

- Generation: 15 RPM, 250,000 input TPM, 500 RPD.
- Embedding: 100 RPM, 30,000 input TPM, 1,000 RPD.
- Values before each slash are peaks over the selected period, not remaining quota or today's usage.

Updated current local status in README, AGENTS, architecture, provider decision, backlog and verification notes. B03 now has six completed checklist items and one remaining: a bounded model-selected tool call with validated arguments. B03 remains open. The last GitHub alignment still had five completed tasks; no remote issue or board update was made during this screenshot review. A push does not automatically synchronize issue bodies.

Historical connection/pilot JSON snapshots and all current Python code, evaluation fixtures and prompts were preserved. The displayed free tier was observed later than those requests and does not establish their actual charges. No new runtime quota enforcement was implemented and no model request, billing change, commit or push was made.

Verified the local checklist count, local documentation links, protected artifact hashes and `git diff --check`. Review commands included:

```powershell
git status --short
git diff --check
git diff --stat
```

Next: verify one bounded native tool call through the shared provider module; the full B10 agent remains outside this compatibility check.

## 16. B03 native tool check and completion - 25 October 2026

Purpose: verify native function calling and validated execution before corpus/retrieval implementation. This is a single-request compatibility check, not the B10 agent.

Implemented:

- `app/llm.py`: shared bounded generation configuration, plus `request_tool` for exactly one native call to the configured function. The existing reservation/journal path is reused; AUTO mode exposes one function, and automatic SDK tool execution stays disabled.
- `app/schemas.py`: strict `EvidenceRead` arguments and a shared source-bound numeric-cell reader. Existing cell selection delegates to that reader; original values and coordinates are preserved.
- `scripts/check_tool_call.py` and `prompts/tool_call_check.md`: explicit live opt-in, one allowed `read_evidence` function, one model request and at most one local read, saved metadata and post-run reference comparison. No dynamic dispatch, calculation, retrieval or tool-result continuation.
- `tests/test_tool_call.py`: eleven simulated response/execution cases and one simulated quota failure. Existing data, budget, credential and source checks remain intact.

Offline commands:

```powershell
uv run --locked --offline ruff format app/llm.py app/schemas.py scripts/check_tool_call.py tests/test_tool_call.py
uv run --locked --offline ruff check .
uv run --locked --offline ruff format --check app scripts/check_environment.py scripts/check_provider.py scripts/run_source_case.py scripts/check_tool_call.py tests/test_provider_connection.py tests/test_source_case.py tests/test_tool_call.py
uv run --locked --offline python -B -X utf8 -m unittest discover -s tests -v
```

The first test run failed: the test expected `parametersJsonSchema`, while SDK 2.33.0 emits `parameters_json_schema`. A temporary fake-response inspection confirmed the actual SDK request. Correcting the test field name resolved the failures without changing provider behavior or relaxing validation. All nine tests and Ruff checks passed before the live call. These tests used fake credentials and an intercepted HTTP transport; no model requests occurred.

Actual live command, with the already configured user-level credential read only into the process environment:

```powershell
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
uv run --locked --offline python -B -X utf8 -m scripts.check_tool_call --live
```

Observed run `4003b7f3-68ff-4330-9652-2a3e733ee4d5`: one generation request, one native `read_evidence` call and one validated local read. The model selected `DVN/2007/page_58.pdf#table[3][4]` and `DVN/2007/page_58.pdf#table[5][4]`; Python returned original values 60 and 243. The cell set matched the reviewed reference, loaded only after execution. Model duration: 1.302 s; local check duration: 1.337 s, excluding client setup and post-run scoring. Usage: 2,250 input, 62 output, 2,312 total tokens; thoughts unknown. Paid-equivalent upper estimate: USD 0.00578; call allowance: EUR 0.01156. The six-row local journal totals EUR 0.0797150 in allowances, not actual charges. No billing settings changed and no additional live request was needed.

Evidence: `B03_TOOL_CALL.md` and `B03_TOOL_CALL_RESULTS.json`. The measured code/prompt fingerprints match the final files. Earlier connection/source-case result snapshots, all ten source exports, evaluation references, the health module and existing prompt were preserved (26 protected artifacts). Unknown charges remain unknown. The free-tier account observation is recorded separately.

Final offline commands:

```powershell
uv run --locked --offline python -B -X utf8 -m scripts.check_tool_call
uv run --locked --offline python -B -X utf8 scripts/inspect_finqa.py --case all --check
git diff --check
```

The first command intentionally returned exit code 2: without `--live`, the command refuses before creating a client. All ten reference cases passed. Local documentation checks validated 128 links and their case; no additional model calls occurred.

Updated README, AGENTS, architecture/blueprint, provider decision, local backlog and current verification notes. B03 has seven completed checklist items. The existing GitHub issue was patched with the reviewed completion body and `state: closed`, `state_reason: completed`; its existing board card was set to Done. Commands used the already authenticated GitHub CLI:

```powershell
gh issue view 3 --repo FekherJ/FigureTrail --json number,title,state,body,url
gh project item-list 2 --owner FekherJ --format json
gh project field-list 2 --owner FekherJ --format json
gh api --method PATCH repos/FekherJ/FigureTrail/issues/3 --input prepared-b03-completion.json
gh project item-edit --id PVTI_lAHOBWzpAs4BolTFzhDR8IE --project-id PVT_kwHOBWzpAs4BolTF --field-id $statusField.id --single-select-option-id $doneOption.id
gh api repos/FekherJ/FigureTrail/issues/3
gh project item-list 2 --owner FekherJ --format json
```

The prepared payload filename represents a temporary task-local file, not a setup input. `$statusField` and `$doneOption` were resolved from the current field listing. Readback confirmed the exact reviewed issue body, seven checked tasks, closed/completed and Done. All thirteen item identities and the other twelve board items were preserved. B04–B06 remain Ready; B04 has not started. The issue body identifies evidence paths awaiting publication; no unavailable main-branch links were presented as live. This is a one-time update, not recurring Markdown synchronization.

No dependency changes, commit or push were made. Next: B04, preparing a versioned annotation-free corpus with original cell IDs, table context, normalization-conflict handling and paced embedding preparation.

## 17. B04 offline corpus preparation - 25 October 2026

Purpose: prepare source-only data for RAG before indexing or embeddings. The starting Git checkpoint was `062b3e08bfc51f721faae4cd4db27c71b46015f2` with a clean working tree. This step made no model requests and did not alter the provider journal.

Added `app/corpus.py`, `scripts/prepare_corpus.py`, `tests/test_corpus.py` and `data/finqa-corpus-selection.json`. The source selection pins twenty filenames and the existing raw-file SHA-256. Preparation reads the raw dataset and that source-only selection; it does not load evals, verification reports or gold evidence. A separate post-build check uses references only to verify preservation of twenty B01 operands.

Selection includes the ten reviewed contexts, two prior distractors and eight additional contexts from distinct report groups. Additional candidates were ordered by a filename hash and checked against the existing shape contract. AES/2017/page_157 was excluded after its ragged multi-row original header failed validation; RE/2017/page_159 was excluded for an unsupported shape. Both exclusions are recorded. No padding, flattening or guessed coordinates were introduced. An early diagnostic invocation also clipped stdout and caused a broken-pipe exit; rerunning the audit with a bounded summary succeeded. These audits sent no network/model requests.

Transformation uses the original table in both prepared table fields. QA/retrieval annotations are dropped before source validation. Sources/cells/chunks have stable original identifiers; full parent context is retained, and row chunks include headers plus adjacent pre/post text. Numeric parsing retains original strings and recognizes conservative decimal/comma formats and an explicit leading dollar sign. Unknown forms remain null; missing dashes never become zero. No currency, unit or period metadata is guessed.

Initial preparation was reproducible, but post-build operand checking found dollar-prefixed original cells that the first numeric parser left unknown. Explicit leading-dollar parsing and focused format cases were added, then all tests and preparation were rerun. The final artifact preserves all twenty reviewed operands. Historical B01 source/reference files were not changed to fit the transformation. The first development artifact remains an ignored intermediate; the final version below is the verified preparation result.

Actual offline commands:

```powershell
uv run --locked --offline ruff format app/corpus.py scripts/prepare_corpus.py tests/test_corpus.py
uv run --locked --offline ruff check .
uv run --locked --offline python -B -X utf8 -m unittest discover -s tests -v
uv run --locked --offline python -B -X utf8 -m scripts.prepare_corpus
uv run --locked --offline python -B -X utf8 -m scripts.prepare_corpus --check
uv run --locked --offline ruff format --check app scripts/check_environment.py scripts/check_provider.py scripts/run_source_case.py scripts/check_tool_call.py scripts/prepare_corpus.py tests/test_provider_connection.py tests/test_source_case.py tests/test_tool_call.py tests/test_corpus.py
git diff --check
```

Final result: twenty source contexts/report groups, 243 original cells and 186 chunks. Sixty-four selected raw entries collapse to twenty sources, removing 44 repeated question copies. The 179 recorded original/normalized differences include 104 formatting, 33 text, 34 label and eight numeric conflicts. All eight numeric conflicts are normalized 2014 values replacing original dashes; preparation retains those dashes and null numeric values. The longest chunk is 2,048 characters, below the 6,000-character ceiling. The Canada row retains the 2008/MMBoe context despite its 2007 report path.

Corpus version: `32a94d8310f88e3987e833044c6131c808e4ac7da7391270aec098e59f062887`. The generated JSON is ignored under `data/corpus/prepared/`; the detailed transformation audit is separate under `data/local/corpus-preparation/`. Source contracts, fingerprints, regenerated cell/chunk records and counts are validated on load. Atomic same-directory writes reuse valid outputs and reject inconsistent existing artifacts. Check mode reproduces the expected artifact without writing. This is an intermediate preparation artifact; it is not a complete SQLite/vector bundle and is not loaded by the server.

All fourteen offline tests pass. New corpus checks cover field isolation, question/context deduplication, original values/IDs, period/unit context, supported/unknown numeric formats, reproducibility, tampering, wrong raw hashes, missing/ambiguous sources, ragged tables, oversized content and unexpected annotation fields even after fingerprint recomputation. Ruff lint and fourteen selected-file format checks pass. Post-build validation preserved all twenty B01 operands, verified 139 local links and their case, and confirmed 45 protected artifacts unchanged, including existing Python code, prompts, raw data, source exports, evaluation fixtures, historical results, dependencies, license and `runs.sqlite`.

Evidence: `B04_CORPUS_PREPARATION.md` and `B04_CORPUS_PREPARATION_RESULTS.json`. README, contributor instructions, architecture/blueprint, provenance and local backlog reflect the prepared state. The B04 checklist has two completed tasks and two remaining; SQLite/FTS5, embeddings, vector/chunk mappings and final corpus/index/vector alignment remain pending.

Updated the existing GitHub issue #4 body, kept it open, and moved its existing card to In progress. Commands used the authenticated CLI:

```powershell
gh issue view 4 --repo FekherJ/FigureTrail --json number,title,state,body,url
gh project item-list 2 --owner FekherJ --format json
gh project field-list 2 --owner FekherJ --format json
gh api --method PATCH repos/FekherJ/FigureTrail/issues/4 --input prepared-b04-progress.json
gh project item-edit --id PVTI_lAHOBWzpAs4BolTFzhDR8J8 --project-id PVT_kwHOBWzpAs4BolTF --field-id $statusField.id --single-select-option-id $inProgressOption.id
gh api repos/FekherJ/FigureTrail/issues/4
gh project item-list 2 --owner FekherJ --format json
```

The payload was a temporary reviewed body; status-field/option IDs were resolved from the current field listing. Readback confirmed the exact body and two checked/two pending tasks, thirteen preserved identities and twelve unchanged other board items. New evidence paths are identified as awaiting publication. This is a one-time update; pushes do not synchronize issue bodies automatically.

No dependency changes, live model calls, billing changes, commit or push were made. Next: continue B04 with SQLite/FTS5 and paced, cached document embeddings, then verify the complete index bundle before B05 retrieval measurements.

## 18. B04 SQLite and document embeddings - 25 October 2026

The user authorized the next B04 step, followed by documentation updates, and explicitly kept the Git commit for themselves. No assistant commit or push is authorized for this step.

Implemented a content-addressed SQLite embedding cache in `app/embeddings.py`, conservative single-builder pacing, and `app/storage.py` for a source-only SQLite/FTS5 database, float32 vector matrix and hashed index manifest. Added `scripts/build_index.py` and offline checks in `tests/test_index.py`. Prepared-corpus writes now maintain a validated current-version pointer; the corpus data/version remain unchanged. The provider embedding method accepts caller format metadata and records a byte-based input allowance, while preserving actual unknown usage and the existing budget journal.

Document formatting follows the current Google guidance: `title: none | text: ...`; expected query formatting is recorded separately as `task: search result | query: ...`. Each provider request contains one input. Identical formatted inputs share a cached vector. The SDK validates 768 finite, unit-length values before caching; loading checks the cache fingerprint and provenance. The index records row IDs, input keys, vector hashes and provider call/run IDs, and rejects mismatched files, shapes, row mappings, FTS records, schemas and corpus/model configuration. SQLite is opened read-only for validation; NumPy loading disables pickle.

All eighteen offline tests passed before the live campaign. Simulated checks include cached rebuilds without a provider, partial-failure resume, cache corruption, vector row swaps, wrong dimensions, NaN, mismatched FTS data, unexpected tables/model configuration and pacing/restart history. Pacing uses monotonic time, seeds recent embedding attempts from the journal and waits in at most one-second increments. It limits this builder to 80 requests and 24,000 byte-based input allowances per rolling minute. UTF-8 bytes plus 64 is a conservative pacing proxy, not measured tokens or a provider quota guarantee. Run one builder at a time; untracked account use can still affect provider quotas.

The campaign plan has 186 chunks and 184 unique formatted inputs, reserving at most EUR 1.84 for missing vectors against a starting local allowance of EUR 0.0797150. Input pacing allowances sum to 221,641; the maximum individual allowance is 2,132. The observed project limits remain 100 embedding RPM, 30,000 input TPM and 1,000 RPD. Actual usage/billing are not inferred from these planning values. Current published text-embedding prices were checked on 25 October: free tier available, paid Standard USD 0.20 per million input tokens; no billing settings changed.

Commands used before and to start the live campaign:

```powershell
uv run --locked --offline ruff format app/corpus.py app/llm.py app/embeddings.py app/storage.py scripts/prepare_corpus.py scripts/build_index.py tests/test_index.py
uv run --locked --offline ruff check .
uv run --locked --offline python -B -X utf8 -m unittest discover -s tests -v
uv run --locked --offline python -B -X utf8 -m scripts.prepare_corpus
uv run --locked --offline python -B -X utf8 -m scripts.prepare_corpus --check
uv run --locked --offline python -B -X utf8 -m scripts.build_index
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
uv run --locked --offline python -B -X utf8 -m scripts.build_index --live
```

The no-live command intentionally returned exit code 1 with 184 missing inputs and sent no requests. The live build uses run ID `052d922e-3717-4cd2-b8ef-0bee10d730ca`; its current authoritative progress/result is in `data/local/index-builds/052d922e-3717-4cd2-b8ef-0bee10d730ca.json`. Successful vectors are committed to `data/local/embeddings.sqlite` after each request; the existing provider journal is never reset. A provider failure stops the build and preserves completed vectors and all failed-call records. The completed result and final verification are recorded below after this campaign finishes. B04 remains open while the build is running.

### Completed build, recovery and handoff

The initial run stopped after 79 successful embedding responses because a Windows sharing violation prevented replacement of the progress JSON. Reading that file during the running build exposed the conflict. Seventy-eight vectors were already cached; one returned vector had not been saved because progress was written first. The provider journal retained all 79 requests. There were no provider errors.

The repair caches a returned vector before progress I/O and retries only local `PermissionError` replacements, five attempts with at most 0.5 seconds of explicit backoff. Network/SDK retries remain disabled. Two regression tests cover transient sharing violations and preservation of a vector when progress saving permanently fails. The full offline suite then passed all twenty tests; Ruff lint passed. No protected fixture or earlier measured result was rewritten.

The resumed live run `02469126-9545-4bd6-887d-16e5883e7889` reused 80 chunk rows and requested the remaining 106 inputs. It passed in 305.485 seconds, including 256.708 seconds of deliberate pacing. Across both live runs there were 185 provider requests for 184 distinct cached inputs, retaining the one response lost before the fix. Two duplicated inputs reuse vectors, so the final matrix has 186 rows at 768 dimensions. This is preparation evidence, not interactive retrieval latency or answer accuracy.

The cache-only run `fa5acab5-3ae3-40ea-9ad3-30c8dfae80e2`, with an empty process API-key variable, passed with 186 cache-hit rows and zero model requests in 0.394 seconds internally. It reproduced index `c0a8c69496f03a95e2049096228afaaec2f410547d14a384bc34b6e78f1225fb`. Its code fingerprint and the resumed run match the final implementation. Complete index checking and prepared-corpus checking passed without requests. The intermediate preparation check's `indexes_ready: false` describes that JSON artifact; the separate index command validates the complete bundle.

Project commands for reproducing the verified repair/build checks are below. An activated project environment or the README's locked `uv run` prefix resolves the same Python/dependencies; the process-only empty key does not remove the saved user variable.

```powershell
uv run --locked --offline ruff check .
uv run --locked --offline python -B -X utf8 -m unittest discover -s tests -v
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
uv run --locked --offline python -B -X utf8 -m scripts.build_index --live
$env:GEMINI_API_KEY = ''
uv run --locked --offline python -B -X utf8 -m scripts.build_index
uv run --locked --offline python -B -X utf8 -m scripts.build_index --check
uv run --locked --offline python -B -X utf8 -m scripts.prepare_corpus --check
```

All 185 new embedding usage counters are unknown and retain EUR 0.01 reservations. The journal now has 191 rows; all six earlier records are unchanged. Its cumulative local allowance is EUR 1.9297150, not an invoice. Actual charges remain unknown; no billing settings changed. The 36 protected source/configuration/reference/result artifacts are unchanged. All twenty B01 operand values remain present in the validated index. Exact file/code/mapping hashes, timing denominators and run IDs are in [the build evidence](B04_INDEX_BUILD.md) and its JSON result.

README, AGENTS, architecture, blueprint and the local backlog now distinguish the verified index from planned retrieval and analysis. The earlier corpus-preparation report is explicitly historical and its original JSON remains unchanged. The API still exposes only the HTTP foundation and has not loaded the bundle; `/health` retains `corpus_version: null`.

Updated the existing B04 issue and card using the authenticated CLI, with readback:

```powershell
gh project field-list 2 --owner FekherJ --format json
gh api repos/FekherJ/FigureTrail/issues/4
gh project item-list 2 --owner FekherJ --format json
gh api --method PATCH repos/FekherJ/FigureTrail/issues/4 --input prepared-b04-completion.json
gh project item-edit --id PVTI_lAHOBWzpAs4BolTFzhDR8J8 --project-id PVT_kwHOBWzpAs4BolTF --field-id $statusField.id --single-select-option-id $doneOption.id
gh api repos/FekherJ/FigureTrail/issues/4
gh project item-list 2 --owner FekherJ --format json
```

The payload name represents the reviewed temporary JSON, not a repository setup input; the Status/Done IDs came from the field listing. Readback confirmed the exact body, four completed tasks, closed/completed and Done. All thirteen identities and the other twelve board items are unchanged. B05–B06 remain Ready, B07–B13 Backlog. The issue explicitly says code/evidence await the user's commit/push. This is a one-time update; pushing Markdown does not synchronize GitHub issue bodies.

No dependency changes, commit, staging or push were made. B04 is complete. Next: B05, measured lexical and semantic retrieval under explicit user scope, without gold-derived filters.

Final documentation validation: 147 local Markdown links and their exact case passed.

Final handoff commands also passed:

```powershell
uv run --locked --offline ruff format --check app scripts/check_environment.py scripts/check_provider.py scripts/run_source_case.py scripts/check_tool_call.py scripts/prepare_corpus.py scripts/build_index.py tests/test_provider_connection.py tests/test_source_case.py tests/test_tool_call.py tests/test_corpus.py tests/test_index.py
git diff --check
git diff --cached --name-only
git rev-parse --short HEAD
git check-ignore data/local/runs.sqlite data/local/embeddings.sqlite data/corpus/current.json data/corpus/indexes/current.json data/raw/finqa-dev.json .venv .env
rg -l 'AIza[0-9A-Za-z_-]{30,}' app scripts tests docs README.md AGENTS.md
```

Ruff confirmed eighteen files already formatted. The diff has no whitespace errors, the staged-file list is empty and HEAD remains `062b3e0`. All seven generated/configuration paths above are ignored. The credential-pattern scan returned no matching files (ripgrep exit 1 means no matches); this is a narrow pattern check rather than proof that arbitrary secrets cannot exist. No further model requests were made during documentation/handoff checks.

## 19. Repository publishing and ignore review - 25 October 2026

Reviewed the existing ignore rules and all 67 tracked text files. The starting tree was clean at `9d4ff94`. Architecture, backlog, curated verification results and AGENTS.md remain shared engineering material. The personal explanatory PDF was created outside this repository and is not tracked. No tracked file required removal, and AGENTS.md itself was not changed.

Added narrow rules for root `private/`, `output/`, `outputs/`, `tmp/` and `work/` directories, `*.local.md` notes and the personal PDF's exact filename at any depth. Existing rules for environment files, credentials, Python caches, downloaded/generated data, database files, raw traces and editor files remain intact. No blanket `docs/`, Markdown or PDF exclusion was introduced; intentionally published technical PDF assets can still be tracked elsewhere. README documents the sharing convention.

Verified 26 excluded examples and 21 retained examples using Git's own matching engine with `--no-index -z --stdin`; the examples were path strings, not new files. The initial task-local matching check used newline-delimited stdin, which Windows translated into CRLF and Git treated as different filenames. Switching the check to NUL delimiters corrected that verification issue without changing the ignore policy. Confirmed that no already-tracked file matches the new exclusions. Environment examples, source code, prompts, tests, provenance/license, reference fixtures, engineering documents and a potential CI workflow remain eligible for sharing. Checked credential signatures and personal career/client identifiers across current tracked text; no matches were found in that narrow scan. This is a current-tree review, not an exhaustive secret scanner or a rewrite of repository history.

Commands used for inspection and verification:

```powershell
git status --short
git ls-files
git log -1 --format='%h %s'
git check-ignore --no-index -z --stdin
git ls-files --cached --ignored --exclude-standard
git diff --check
git diff --cached --name-only
```

The matching command received the reviewed included/excluded paths on stdin. Adding a path to .gitignore does not remove an already-tracked file or erase previously published versions. No index removal or history rewrite was needed. No application code, data, fixtures, dependency or historical result changed; no model requests, staging, commit or push were performed. B05 remains the next technical item. A software test-suite rerun was unnecessary for this ignore/documentation-only change; the relevant checks exercise actual Git behavior.

## 20. B05 — Measured evidence retrieval — 26 October 2026

Implemented shared lexical/semantic retrieval in `app/retrieval.py`, inspection in `scripts/search.py`, the question-only `evals/queries/finqa-b05.json` fixture and `evals/retrieval.py`. Reused SQLite FTS5/BM25, the validated B04 index, NumPy cosine search, embedding cache/pacer and shared Gemini provider journal. No dependency, prompt, HTTP route, calculator or agent was added. The query cache is separate from document embeddings.

Fixed primary k=5 and secondary k=1/3/5 before measurement. All ten questions have null scope and search all twenty contexts/186 chunks. The evaluator retrieves and saves candidates before reading references. Only explicit report scope filters search; scope precedes top-k. Literal quoted FTS terms and parameterized read-only SQL prevent questions supplying query operators/SQL. Semantic search uses Google's documented retrieval query prefix and the existing 768-dimension model configuration.

Actual project commands, using the existing locked environment (the tool runner resolved executable paths; ordinary executable names are shown):

```powershell
uv run --locked --offline ruff format app/retrieval.py scripts/search.py evals/retrieval.py tests/test_retrieval.py
uv run --locked --offline ruff check .
uv run --locked --offline python -B -X utf8 -m unittest discover -s tests -v
uv run --locked --offline python -B -X utf8 -m evals.retrieval
uv run --locked --offline python -B -X utf8 -m scripts.search "In Devon's estimated 2008 production table, what percentage of total production in MMBoe comes from Canada?" --k 3
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')
uv run --locked --offline python -B -X utf8 -m evals.retrieval --mode compare --live
$env:GEMINI_API_KEY = ''
uv run --locked --offline python -B -X utf8 -m evals.retrieval --mode compare
```

`--offline` controls uv dependency resolution; `--live` independently permits application API requests. The API key was loaded without printing its value. Ruff formatted four new files; lint passed. All 26 tests passed on the first B05 test run, including six new retrieval tests with simulated vectors. These test boundaries and ranking/scoring mechanics, not hosted-model accuracy.

The lexical-only run recovered 19/20 cells and complete proofs for 9/10 questions at k=5. The live comparison made exactly ten successful query-embedding calls and no generation/document-embedding calls. Semantic recovered 20/20 cells and complete proofs for 10/10. Lexical did better at k=3: 8/10 complete proofs versus 7/10. Median totals in the live comparison were 0.003737 s lexical and 0.423049 s semantic. The no-key replay reproduced every hit, score and evidence metric with ten query-cache hits and zero new journal records; cached semantic median was 0.001247 s. This is one small development campaign, not end-to-end answer accuracy or a reserved benchmark.

Reviewed C03 (after 2014 versus Thereafter: lexical required row at rank seven) and C08 (semantic favors related margins/adjusted profit before reported profit at rank four). Additional k=20 inspection reused the same cached vectors after primary measurement; it did not change metrics or tune ranking. Selected semantic k=5 provisionally for B06 while keeping the local lexical baseline and explicit CLI method switch.

The journal grew from 191 to 201 rows; all previous JSON records remain unchanged. Ten €0.01 reservations increased cumulative local allowance to €2.0297150. Usage/actual charges remain unknown where unreported. No retries, generation requests, document re-embedding or billing change occurred. All 86 baseline files were unchanged before documentation edits, including raw data, source/reference fixtures, document cache, immutable bundles and lockfile. A task-local audit initially lacked permission to read a protected generated manifest; rerunning that read with sandbox escalation succeeded. This was an inspection issue, not a model/data failure.

Added `B05_RETRIEVAL.md` and `B05_RETRIEVAL_RESULTS.json`; updated README, AGENTS, architecture, blueprint and backlog. Historical verification JSON and reference values are preserved. The prior .gitignore/README/log changes are retained. The personal PDF remains under ignored `private/`. B06 is next: one retrieval, one structured generation, validated source cells and Decimal calculation. The API still exposes only health with no loaded corpus. No staging, commit or push was performed; the user retains those actions.

### B05 final handoff

Final lint passed and Ruff confirmed 22 files already formatted. One verification invocation was initially launched from the conversation workspace rather than the repository, so uv could not locate the project Ruff executable; rerunning from FigureTrail passed. This changed no application code or dependency. Git inspection also required sandbox escalation to access the installed executable; the escalated check succeeded.

Verified 159 local Markdown links, exact filename case, ignored query cache/traces/private PDF, and the PDF's unchanged hash. Exactly six baseline engineering documents changed for B05; the other 80 protected baseline files, including .gitignore's preexisting update, remain byte-for-byte unchanged. Seven new implementation/fixture/evidence files are present. The credential-pattern check found no matches in current tracked/new text; this is not an exhaustive secret-history scan. HEAD remains `9d4ff94` and the staging area is empty.

Updated the existing B05 issue and board item only, then read both back:

```powershell
gh api repos/FekherJ/FigureTrail/issues/5
gh project item-list 2 --owner FekherJ --format json
gh project field-list 2 --owner FekherJ --format json
gh api --method PATCH repos/FekherJ/FigureTrail/issues/5 --input <reviewed-payload.json>
gh project item-edit --id <existing-B05-item> --project-id <existing-project> --field-id <Status-field> --single-select-option-id <Done-option>
git diff --check
git diff --cached --name-only
git status --short
```

The payload contained the four completed tasks, actual measurements/limits and closed/completed state. Field/option/item IDs came from the current project listing. Readback confirms the exact issue body and Done status, all thirteen item identities and twelve unchanged other cards. B06 remains Ready. The issue explicitly distinguishes verified local work from files awaiting the user's commit/push. No comments, duplicate issues, staging, commit or push were created.
