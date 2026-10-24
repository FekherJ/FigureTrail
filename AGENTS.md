# FigureTrail — Engineering instructions

## References and scope

- Read [README](README.md), [architecture](docs/architecture/ARCHITECTURE_PROJET_IA.md), [engineering standards](docs/architecture/AI_PROJECT_BLUEPRINT.md) and [backlog](docs/Backlog/BACKLOG_PROJET_IA.md) before changes.
- Keep the existing `docs/architecture/`, `docs/Backlog/` and `docs/verification/` names and case. Use repository-relative runtime paths.
- Preserve existing work. Add modules, dependencies and services only when required by the current issue. The target directory tree is not a scaffolding checklist.
- Document product behaviour, contracts, decisions, verification evidence and operational limits in an impersonal, technical style. Distinguish implemented capabilities from design targets.
- Follow B01–B13 dependencies and priorities: LLM/RAG, API/architecture and evaluations first; bounded tools, security and observability next.

## Current baseline

- B01: ten development cases verified against supplied FinQA text/tables. See [data verification](docs/verification/B01_VERIFICATION_DONNEES.md). These checks do not establish model or retrieval performance.
- B02: local environment and `/health` verified. See [runtime verification](docs/verification/B02_ENVIRONNEMENT.md). Git remote `origin` is configured; issue-board status is tracked separately in the backlog.
- B03 is the next technical issue. No provider or model is configured. Do not make paid calls before provider capabilities, dated prices, cost limits and credentials are configured for that issue.

## Development and verification

- Use Python 3.14.5 and the project `.venv/`. Manage dependencies in `pyproject.toml` and preserve exact resolutions in `uv.lock`; use locked installs. Follow README commands with ordinary `git` and `uv` executables.
- Prefer standard-library functionality and small readable functions. Keep one local Python application; introduce abstractions only for a demonstrated requirement.
- Run checks proportionate to the change. Preserve executable checks for data separation, numeric conventions and trust boundaries. Do not rewrite numerical fixtures or measured results to make a check pass.
- Ruff lint covers the codebase; formatting is applied to the API and environment-check files. Avoid unrelated reformatting of verified reference tooling.
- The offline FinQA verifier uses assertions and rejects `-O`. Runtime API/provider/domain validation must use explicit validation and exceptions.
- Record actual commands, results, limitations and relevant versions. Keep failures in evaluation denominators and distinguish simulated from live model calls.
- Keep shared Git history intact. Leave changes reviewable and keep generated data, environments, credentials and execution traces out of commits.

## Data and trust boundaries

- Raw FinQA contains annotations. It is preparation input only, never application inference input.
- Source-only exports allow exactly `filename`, `pre_text`, `post_text`, `table` and `table_ori`. Preserve complete context, numbers, headers, units and periods.
- `evals/` and `docs/verification/` contain reference answers and evidence coordinates. Exclude both from inference ingestion, corpus construction and model context.
- The evaluator forwards only the question and explicit user scope to the shared analysis service. Never derive retrieval filters or supplied evidence from gold annotations.
- Validate stable cell/source IDs and resolve operands from source data. Calculate approved operations using `Decimal`; never execute generated Python, SQL or `eval`.
- Preserve source attribution, licence notices and provenance. Record and resolve table-normalisation conflicts before indexing; retain report groups when splitting evaluation cases.

## Operational limits

- Bind the service to localhost for the current release scope. No unrestricted URL/file ingestion, shell tools, arbitrary PDF/OCR pipeline or distributed deployment is required.
- Use a single hosted provider module. Apply deadlines, output-token bounds, retry limits, usage accounting and spending checks to every generation and embedding call.
- Keep cumulative hosted-AI spending strictly below €30. Preparation, evaluations, errors and retries count toward this limit. Local estimates are not a guaranteed provider billing cap.
- Introduce the agent only after the fixed baseline is measured. Initial ceiling: four generation calls and six tool calls, including at most two searches; enforce limits in code.
- Minimise provider payloads, redact secrets from traces and escape displayed source content. Guardrails supplement explicit permissions and boundary validation.
