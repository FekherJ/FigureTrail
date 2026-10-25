# B02 environment and HTTP verification

**Local checks: 24 October 2026; rechecked on 25 October 2026. GitHub tracking verified: 25 October 2026.**

## Scope

The foundation includes FastAPI, the Pydantic `/health` contract, an isolated Python environment and verification commands. Data, references, tests and documentation retain separate responsibilities. Add analysis, retrieval and tools according to the roadmap.

`GET /health` returns HTTP 200 with `{"status":"ok","corpus_version":null}`. It reports process availability; no corpus is loaded. OpenAPI describes only `/health`. The application does not import preparation scripts or evaluation annotations.

## Verified versions

| Component | Version |
|---|---|
| CPython, Windows 64-bit | 3.14.5 |
| uv | 0.11.14 |
| FastAPI | 0.162.0 |
| Pydantic | 2.14.1 |
| Uvicorn | 0.54.0 |
| NumPy | 2.5.4 |
| SQLite, with FTS5 | 3.50.4 |
| Ruff | 0.17.2 |

`pyproject.toml` defines dependencies and code rules; `uv.lock` records resolved versions and distribution hashes. `package = false` reflects execution from the repository. Compatibility has been checked on Windows with Python 3.14.

Packages are installed from PyPI as prebuilt distributions in `.venv/`. Explicit Python environment creation requires neither PowerShell activation nor pip installation. `.gitattributes` preserves JSON bytes and normalizes other text to LF, keeping reference hashes reproducible across checkouts.

## Reproduce

From the root, with data prepared as described in [README](../../README.md):

```powershell
python3.14.exe -m venv .venv --without-pip
uv sync --locked --no-build
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked ruff check .
uv run --locked ruff format --check app scripts/check_environment.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m unittest discover -s tests -p test_b01_verification.py -v
uv run --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Call `Invoke-RestMethod http://127.0.0.1:8000/health` in another terminal. `/openapi.json` serves the schema; `/docs` provides interactive FastAPI documentation whose browser assets may require internet access. Stop the server with Ctrl+C.

## Observed results

- Environment synchronized with the lockfile; 16 packages installed with compatible dependencies.
- SQLite FTS5 creation, insertion and in-memory search passed; NumPy dot product matched expectations.
- Real HTTP check returned 200 and the expected health contract; OpenAPI was valid.
- Raw-data, evaluation-reference and unimplemented analysis routes returned 404.
- Ten B01 cases and three negative tests passed in the project environment.
- Ruff lint and formatting checks for the three foundation files passed.
- Git exclusions covered environments, caches, secrets and generated data; code, references and notices remained tracked.
- Checks required no model calls. The temporary verification server was stopped afterwards.

Health does not establish provider availability, retrieval quality or LLM answer accuracy. The [repository review](STRUCTURE_REVIEW.md) records documentation and link checks.

## GitHub tracking

On 25 October 2026, the thirteen B01–B13 repository issues were imported into [Project 2](https://github.com/users/FekherJ/projects/2). At import, live reads confirmed one issue and one board item per ID, matching descriptions, B01 closed/Done and B02–B13 open/Backlog. The import did not configure recurring Markdown synchronization.

## Final B02 review — 25 October 2026

The foundation is published in commit `d5c26ca`; a fresh GitHub read confirmed the full revision. `app/main.py` and `scripts/check_environment.py` are unchanged from that commit. Current dependency versions, SQLite FTS5 and the NumPy check passed again. An in-process ASGI check confirmed HTTP 200 with the expected `/health` body and the `/openapi.json` path contract; this did not start a network listener or call a model. Earlier real HTTP results above remain the evidence for local server startup.

B02's acceptance criteria are met. Issue #2 was closed as completed and its existing board item moved from In review to Done. B03 remains open and its board item is In progress. Reads confirmed thirteen issues/items, unchanged identities and preservation of the other eleven items, including the existing Ready statuses for B04–B06. See the [current backlog](../Backlog/BACKLOG.md) and [implementation log](IMPLEMENTATION_LOG.md). The provider/pilot code is still local and awaits the user's commit/push.

## Next step

B03 establishes provider access, structured cell-selection output, call limits, usage accounting and initial cost/latency measurements. After this foundation review, the [provider selection](../architecture/PROVIDER_SELECTION.md), key setup, [connection check](B03_PROVIDER_CONNECTION.md) and [source-case pilot](B03_SOURCE_CASE.md) were completed. The locked environment also includes Google GenAI SDK 2.33.0 and its dependencies. The original B02 package counts above describe the foundation snapshot. Numeric account quotas and tool-call compatibility remain pending in B03.

References: [uv layout/lockfile](https://docs.astral.sh/uv/concepts/projects/layout/), [locked synchronization](https://docs.astral.sh/uv/concepts/projects/sync/), [FastAPI/OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/), [Ruff](https://docs.astral.sh/ruff/configuration/), [SQLite FTS5](https://sqlite.org/fts5.html), [Git attributes](https://git-scm.com/docs/gitattributes).
