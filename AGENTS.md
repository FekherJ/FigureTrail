# FigureTrail — Engineering instructions

## References and scope

- Read [README](README.md), [architecture](docs/architecture/ARCHITECTURE.md), [engineering standards](docs/architecture/AI_PROJECT_BLUEPRINT.md) and [backlog](docs/Backlog/BACKLOG.md) before changes.
- Keep the existing `docs/architecture/`, `docs/Backlog/` and `docs/verification/` names and case. Use repository-relative runtime paths.
- Preserve existing work. Add modules, dependencies and services only when required by the current issue. The target directory tree is not a scaffolding checklist.
- Write project documentation, diagrams, comments, diagnostic messages and GitHub issues in clear, concise US English. Use English document filenames. Preserve original source quotations, legal notices and technical identifiers.
- Document product behavior, contracts, decisions, verification evidence and operational limits in an impersonal, technical style. Distinguish implemented capabilities from design targets.
- Follow B01–B13 dependencies and priorities: LLM/RAG, API/architecture and evaluations first; bounded tools, security and observability next.

## Current baseline

- B01: ten development cases verified against supplied FinQA text/tables. See [data verification](docs/verification/B01_DATA_VERIFICATION.md). These checks do not establish model or retrieval performance.
- B02: environment, `/health`, published foundation and GitHub setup verified; final review completed on 25 October. Issue #2 is closed/completed and its board item is Done. See [runtime verification](docs/verification/B02_ENVIRONMENT.md) and the current status table in the backlog.
- B03 uses Gemini Developer API, `gemini-3.5-flash-lite` and `gemini-embedding-2`, starting free. SDK 2.33.0, the connection check and [source-case pilot](docs/verification/B03_SOURCE_CASE.md) are verified: three matching selections at a 0.950 s median and one missing-period abstention. Shared SDK calls and local allowances live in `app/llm.py`; no application calculator or retrieval exists yet. Numeric account quotas and tool-call compatibility remain pending. Do not make paid calls before dated prices, cost limits and credentials are configured for that issue.

## Development and verification

- Use Python 3.14.5 and the project `.venv/`. Manage dependencies in `pyproject.toml` and preserve exact resolutions in `uv.lock`; use locked installs. Follow README commands with ordinary `git` and `uv` executables.
- Prefer standard-library functionality and small readable functions. Keep one local Python application; introduce abstractions only for a demonstrated requirement.
- Run checks proportionate to the change. Preserve executable checks for data separation, numeric conventions and trust boundaries. Do not rewrite numerical fixtures or measured results to make a check pass.
- Ruff lint covers the codebase; formatting covers `app/`, environment/provider/source-case checks and B03 tests. Avoid unrelated reformatting of verified reference tooling.
- The offline FinQA verifier uses assertions and rejects `-O`. Runtime API/provider/domain validation must use explicit validation and exceptions.
- Record actual commands, results, limitations and relevant versions. Keep failures in evaluation denominators and distinguish simulated from live model calls.
- Maintain [IMPLEMENTATION_LOG.md](docs/verification/IMPLEMENTATION_LOG.md) after each meaningful step: purpose, changed files, actual commands, observed results, failures/fixes and next work. Keep secrets and private career information out of the log. Identify reconstructed history rather than inventing an exact transcript.
- Keep shared Git history intact. Leave changes reviewable and keep generated data, environments, credentials and execution traces out of commits.

## Data and trust boundaries

- Raw FinQA contains annotations. It is preparation input only, never application inference input.
- Source-only exports allow exactly `filename`, `pre_text`, `post_text`, `table` and `table_ori`. Preserve complete context, numbers, headers, units and periods.
- `evals/` and `docs/verification/` contain reference answers and evidence coordinates. Exclude both from inference ingestion, corpus construction and model context.
- The evaluator forwards only the question and explicit user scope to the shared analysis service. Never derive retrieval filters or supplied evidence from gold annotations.
- Validate stable cell/source IDs and resolve operands from source data. Calculate approved operations using `Decimal`; never execute generated Python, SQL or `eval`.
- B03 cell IDs use `filename#table[row][column]` with zero-based coordinates against `table_ori`. The source-case pilot uses the original table explicitly; preserve this meaning when preparing the corpus.
- Preserve source attribution, license notices and provenance. Record and resolve table-normalization conflicts before indexing; retain report groups when splitting evaluation cases.

## Operational limits

- Bind the service to localhost for the current release scope. No unrestricted URL/file ingestion, shell tools, arbitrary PDF/OCR pipeline or distributed deployment is required.
- Use `app/llm.py` for every SDK request; both B03 commands share it. It records calls in `data/local/runs.sqlite`, reserves allowances against a €25 local limit and retains unknown usage. Do not bypass or reset that journal. Keep actual billing unknown unless verified. Apply deadlines, output-token bounds, retry limits and usage accounting to every request; strict wall-clock cancellation still needs validation.
- Keep cumulative hosted-AI spending strictly below €30. Preparation, evaluations, errors and retries count toward this limit. Local estimates are not a guaranteed provider billing cap.
- Introduce the agent only after the fixed baseline is measured. Initial ceiling: four generation calls and six tool calls, including at most two searches; enforce limits in code.
- Minimize provider payloads, redact secrets from traces and escape displayed source content. Guardrails supplement explicit permissions and boundary validation.
