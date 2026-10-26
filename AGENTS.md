# FigureTrail — Engineering instructions

## References and scope

- Read [README](README.md), [architecture](docs/architecture/ARCHITECTURE.md), [engineering standards](docs/architecture/AI_PROJECT_BLUEPRINT.md) and [backlog](docs/Backlog/BACKLOG.md) before changes.
- Keep the existing `docs/architecture/`, `docs/Backlog/` and `docs/verification/` names and case. Use repository-relative runtime paths.
- Preserve existing work. Add modules, dependencies and services only when required by the current issue. The target directory tree is not a scaffolding checklist.
- Write project documentation, diagrams, comments, diagnostic messages and GitHub issues in clear, concise US English. Use English document filenames. Preserve original source quotations, legal notices and technical identifiers.
- Document product behavior, contracts, decisions, verification evidence and operational limits in an impersonal, technical style. Distinguish implemented capabilities from design targets.
- Follow B01–B13 dependencies and priorities: LLM/RAG, API/architecture and evaluations first; bounded tools, security and observability next.

## Communication and handoff

- Before each implementation step, explain the active backlog item, its purpose, the affected components and how the result will be verified in plain English.
- Explain unfamiliar tools and commands briefly before using them. Prefer the standard README commands; explain additional flags when needed. Distinguish shell syntax, the Python virtual environment and configuration variables.
- Distinguish working application features, isolated experiments and planned components. Relate implementation choices to the documented architecture without creating unused layers or folders.
- Close each meaningful step with what changed, the observed result, relevant limits and one next step. Explain a transition to another backlog item before starting it.

## Current baseline

- B01: ten development cases verified against supplied FinQA text/tables. See [data verification](docs/verification/B01_DATA_VERIFICATION.md). These checks do not establish model or retrieval performance.
- B02: environment, `/health`, published foundation and GitHub setup verified; final review completed on 25 October. Issue #2 is closed/completed and its board item is Done. See [runtime verification](docs/verification/B02_ENVIRONMENT.md) and the current status table in the backlog.
- B03 is complete: it uses Gemini Developer API, `gemini-3.5-flash-lite` and `gemini-embedding-2`, starting free. SDK 2.33.0, the connection check and [source-case pilot](docs/verification/B03_SOURCE_CASE.md) are verified: three matching selections at a 0.950 s median and one missing-period abstention. Shared SDK calls and local allowances live in `app/llm.py`; the B06 calculator and fixed service are now verified within documented source-format limits. [Free-tier account quotas](docs/verification/B03_ACCOUNT_LIMITS.md) were recorded from the supplied AI Studio screenshot on 25 October; the [native tool check](docs/verification/B03_TOOL_CALL.md) passed with one request, one validated local read and a 1.302 s model duration. B04 is complete. Do not make paid calls before dated prices, cost limits and credentials are configured for that issue.

- B04 is complete: [index verification](docs/verification/B04_INDEX_BUILD.md) confirms 20 contexts, 186 chunks, 243 original cells, SQLite/FTS5 and an aligned 186 × 768 matrix. There are 184 distinct cached inputs. B05 retrieval is complete; the API has not loaded the index. The earlier preparation report is a historical intermediate snapshot.

- B05 is complete: [retrieval verification](docs/verification/B05_RETRIEVAL.md) measures lexical recall@5 95% / complete proof 9/10 and semantic recall@5 100% / complete proof 10/10 on ten development questions. All 186 chunks are eligible; references are read only after candidates are retrieved. Semantic k=5 is the B06 default; the search CLI defaults to local lexical search. Twenty-six tests passed at the B05 snapshot; the current suite has 34. The cached replay made zero requests. B06 functionality is now complete; B07 analysis API is next.

- B06 is implemented: `app/service.py`, `app/calculator.py`, `prompts/analysis_selection.md` and `scripts/analyze.py`. [Verification](docs/verification/B06_FIXED_WORKFLOW.md) retains the initial 5/10 correct answers, one abstention and four 504s; two v2 follow-ups succeeded at 15.1/19.2 s. Do not describe provider latency/reliability as solved. All 34 offline tests pass. B07 API integration is next.

## Development and verification

- Use Python 3.14.5 and the project `.venv/`. Manage dependencies in `pyproject.toml` and preserve exact resolutions in `uv.lock`; use locked installs. Follow README commands with ordinary `git` and `uv` executables.
- Prefer standard-library functionality and small readable functions. Keep one local Python application; introduce abstractions only for a demonstrated requirement.
- Use comments sparingly to explain non-obvious decisions, constraints and trust boundaries. Do not narrate self-explanatory code or comment every line.
- Run checks proportionate to the change. Preserve executable checks for data separation, numeric conventions and trust boundaries. Do not rewrite numerical fixtures or measured results to make a check pass.
- Ruff lint covers the codebase; formatting covers `app/`, environment/provider/source-case/tool/corpus/index/search/analysis/evaluation commands and their tests. Avoid unrelated reformatting of verified reference tooling.
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
- Prepared inference tables use original values in both `table` and `table_ori`; keep normalization audits outside inference artifacts. Load prepared JSON through its fingerprint/schema/cell/chunk checks and build indexes only from that source-only artifact.
- Preserve source attribution, license notices and provenance. Record and resolve table-normalization conflicts before indexing; retain report groups when splitting evaluation cases.

## Operational limits

- Bind the service to localhost for the current release scope. No unrestricted URL/file ingestion, shell tools, arbitrary PDF/OCR pipeline or distributed deployment is required.
- Use `app/llm.py` for every SDK request; all provider, source-case and native-tool commands share it. It records calls in `data/local/runs.sqlite`, reserves allowances against a €25 local limit and retains unknown usage. Do not bypass or reset that journal. Keep actual billing unknown unless verified. Apply deadlines, output-token bounds, retry limits and usage accounting to every request; strict wall-clock cancellation still needs validation.
- Keep cumulative hosted-AI spending strictly below €30. Preparation, evaluations, errors and retries count toward this limit. Local estimates are not a guaranteed provider billing cap.
- Build indexes from the validated prepared artifact. Use the current-version pointers and `app/storage.py` loader; reject corpus/model/file/row mismatches. Reuse the content-addressed embedding cache; missing vectors require `--live`, and cache-only builds/checks must make no model requests. Run one builder at a time.
- Pacing uses 80 RPM and a 24,000/minute byte-based allowance proxy; actual embedding usage remains unknown. Local file-write retries are bounded and separate from disabled SDK/network retries. Preserve returned vectors before progress-record updates.
- Retrieval uses `app/retrieval.py` and the validated index loader. Keep explicit scope before top-k and references out of search inputs. Query embeddings use `data/local/query-embeddings.sqlite`; document cache/bundles remain immutable. The CLI/evaluator require `--live` for missing query vectors. Retain failures in evidence metrics and distinguish retrieval coverage from answer correctness.
- Fixed analysis makes one search and at most one generation. Preserve the same shared service for CLI/API/evaluations; keep reference loading in evaluators after execution. Save accepted runs in the journal's `analyses` table without overwriting `calls`. Unknown cells fail; unknown units, scales or periods cannot become numerical successes. Keep the current conservative source-format policy explicit, and preserve baseline failures when comparing variants.
- Introduce the agent only after the fixed baseline is measured. Initial ceiling: four generation calls and six tool calls, including at most two searches; enforce limits in code.
- Minimize provider payloads, redact secrets from traces and escape displayed source content. Guardrails supplement explicit permissions and boundary validation.
