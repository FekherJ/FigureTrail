# FigureTrail backlog

**Version 1.1 — implementation roadmap dated 24 October 2026; English edition, 25 October 2026 — Fekher Jarrar.**

This backlog implements the [architecture](../architecture/ARCHITECTURE.md). B01–B13 are stable work-item IDs. They are now linked to [repository issues](https://github.com/FekherJ/FigureTrail/issues) and [Project 2](https://github.com/users/FekherJ/projects/2), verified on 25 October 2026. Their current GitHub issue numbers are 1–13; the Bxx IDs remain the roadmap identifiers.

The target is a local application that retrieves cells from public reports, calculates a percentage change or ratio, and shows the result, formula and evidence. A hosted LLM, measured RAG and an API form the core. A bounded agent, guardrails and execution records extend the fixed workflow.

## 1. GitHub tracking

Track work in the existing board and keep one issue in progress. Each Bxx section defines an issue; retain its checklist and dependencies in the issue body. The following issue/board states were read back and verified on 25 October 2026:

| Work items | Issue state | Board status |
|---|---|---|
| B01–B03 | Closed | Done |
| B04–B06 | Open | Ready |
| B07–B13 | Open | Backlog |

B03's seven checklist items are verified, including the account-limit observation and one native tool call with validated arguments and original source values. B01–B03 are complete; B04 is the next work item. The B03 issue body and Done status are aligned with this completion review. B04–B06 retain their existing planning status; completion still follows the dependencies below. All thirteen issues and board-item identities were preserved. This was a one-time alignment; pushing Markdown does not automatically synchronize issue bodies or board fields.

Record priority (`P0`/`P1`), milestone and estimated hours. Optional labels are `data`, `llm`, `rag`, `api`, `evals`, `agents`, `security`, `observability` and `docs`. These values are currently documented in issue descriptions; importing them did not create labels or GitHub milestones.

Close an issue only after verifying its criteria and saving or linking evidence. Distinguish simulated from live model calls. Documentation alone does not establish an implemented feature.

## 2. Delivery plan and validation allowance

Initial estimates total **31 hours of implementation and verification**, plus five hours for integration, diagnosis and fixes: **36 hours**, including documentation and issue tracking. These are provisional estimates, not a delivery commitment.

Re-estimate after B01 and B03. If necessary, reduce corpus size, question types or UI polish while preserving P0 and a limited demonstration of each P1 capability. Document unfinished work rather than marking it complete.

| ID | Priority | Deliverable | Completion dependencies | Estimate | Milestone |
|---|---|---|---|---:|---|
| B01 | P0 | Ten verified cases and data scope | None | 2 h | J1 |
| B02 | P0 | Environment and minimal HTTP foundation | B01 | 2 h | J1 |
| B03 | P0 | First hosted call, output contract and traces | B02 | 2 h | J1 |
| B04 | P0 | Corpus/index without annotations | B01, B02, B03 | 2 h | J2 |
| B05 | P0 | Measured lexical and semantic retrieval | B04 | 3 h | J2 |
| B06 | P0 | Fixed workflow and verifiable calculation | B03, B05 | 3 h | J2 |
| B07 | P0 | Documented API and consistent errors | B06 | 2 h | J2 |
| B08 | P0 | Evaluator and measured improvement | B01, B05, B06 | 3 h | J3 |
| B09 | P0 | Evidence-focused UI | B07 | 2 h | J3 |
| B10 | P1 | Bounded agent with structured tool calls | B07, B08 | 3 h | J4 |
| B11 | P1 | Guardrail and negative-test campaign | B09, B10 | 2 h | J4 |
| B12 | P1 | Complete execution records and versions | B07, B10 | 2 h | J4 |
| B13 | P0 | Final validation and reproducible release | B08, B09, B10, B11, B12 | 3 h | J5 |
| Reserve | — | Integration, diagnosis and fixes | As needed | 5 h | All |
| **Total** | | | | **36 h** | |

Dependencies govern completion, not when work can begin. Evaluations and traces start early: B08 formalizes initial checks, and B12 extends B03's records. API/UI work can start before those issues are ready to close.

Milestones describe outcomes, not fixed calendar weeks. Keep the existing J1–J5 identifiers:

- **J1 — Feasibility:** verifiable data and a suitable hosted LLM.
- **J2 — P0 workflow:** retrieval → LLM → calculation → API, with initial evaluated results.
- **J3 — Visible quality:** measured comparison and evidence UI.
- **J4 — P1 demonstrated:** bounded agent, guardrails and observability.
- **J5 — Release:** frozen versions, final trials, limits and reproducibility.

Suggested order: B01 → B02 → B03 → B04 → B05 → B06 → B07 → B08 → B09 → B10 → B11 → B12 → B13. Validate J1 before completing the P0 workflow, and revisit estimates after B03.

Validation allowance: **€20 API usage plus €5 reserve**, within a cumulative ceiling strictly below €30. The [provider decision](../architecture/PROVIDER_SELECTION.md) starts with the Gemini free tier; no paid billing has been enabled by the project. Count pilots, embeddings, evaluations and failed calls. Estimate a campaign before running it and reduce repetitions if necessary. Verify actual API access, dated prices and any later billing separately.

### Apply standards incrementally

The [engineering blueprint](../architecture/AI_PROJECT_BLUEPRINT.md) adds standards, not mandatory tickets, hours or technologies. Inspect the current state and correct gaps relevant to the current milestone. Do not create the target tree in advance.

| Step | Checks to apply |
|---|---|
| B02 | Current structure, Git exclusions, reproducible environment and `/health`. Keep uv/Ruff and the flat `app/` layout. |
| B03 | LLM contract, validation, bounded calls, errors, cost and first traces. |
| B04–B08 | Provenance, annotation-free corpus, index consistency, retrieval, calculation and shared-service evaluations. |
| B09–B12 | Safe evidence display, bounded tools, negative cases and complete traces. |
| B13 | Checks without secrets, reproducible demo and measured results/limits. |

B01 and the B02 foundation are verified, including the final B02 review on 25 October. GitHub import is complete. B03 is complete, including source selection and a native tool check; retrieval and the complete analysis workflow remain planned.

## 3. Work items

### B01 — Verify ten questions, their evidence and the data scope

**Priority: P0 · Labels: data, evals · Milestone: J1 · Estimate: 2 h · Dependencies: none**

Objective: establish two-cell numerical references with explicit context, without OCR or implicit financial reconstruction.

- [x] Inspect a small FinQA sample and select ten understandable percentage-change/ratio questions with positive denominators.
- [x] Record each question, context, cells, units, periods, formula, expected result and provenance; recalculate and check source evidence.
- [x] Audit duplicate contexts and identify distractor documents for retrieval.
- [x] Review attribution/license requirements and record scope and exclusions.

**Acceptance criteria:** ten reviewed cases with identifiable evidence and no implicit calculation convention. Preserve actual examples and numbers. Separate source exports from annotations. If the subset is unsuitable, record blockers and narrow calculation types before B04.

**Evidence:** feasibility report and annotated development references, counting only cases actually checked.

**Design note:** evaluate retrieval relevance, cell selection and numerical accuracy separately.

**Verified status:** data feasibility completed on 24 October 2026; [issue #1](https://github.com/FekherJ/FigureTrail/issues/1) closed on 25 October. Ten cases, ten distinct contexts/report groups, explicit conventions, duplicate audit, three distractor candidates and retained license notice. Ten checks and three negative tests passed without model calls. See [report and limits](../verification/B01_DATA_VERIFICATION.md). J1 still requires B03.

### B02 — Establish the environment and HTTP foundation

**Priority: P0 · Labels: api, data · Milestone: J1 · Estimate: 2 h · Dependencies: B01**

Objective: create a reproducible environment and a verifiable HTTP foundation.

- [x] Review architecture/backlog, inspect the structure and initialize local Git.
- [x] Configure the GitHub remote and tracking for `main`.
- [x] Create the project board and implementation issues; import/membership verified on 25 October 2026.
- [x] Install FastAPI/Pydantic/Uvicorn and NumPy in an isolated Python environment; verify SQLite FTS5 on Windows.
- [x] Add non-secret configuration, Git exclusions and startup instructions; lock tested versions.
- [x] Load a case with sources separate from references and start `/health` without AI calls.

**Acceptance criteria:** documented environment/startup, readable sample and no tracked key. FTS5 works or a minimal alternative is documented. Do not build a custom SQL/search engine.

**Evidence:** initial commit, Windows instructions and sample output. Empty modules for future architecture components are not required.

**Design note:** configuration, inference sources and evaluation references have separate responsibilities.

**Verified status:** final review completed on 25 October: published foundation commit `d5c26ca`, current dependency/FTS5/NumPy checks and in-process `/health`/OpenAPI contracts confirmed. The original live HTTP results remain in the [B02 report](../verification/B02_ENVIRONMENT.md). [Issue #2](https://github.com/FekherJ/FigureTrail/issues/2) is closed as completed and its board item is Done; both were read back. B03 is the active item; its source-case pilot exists, while retrieval and the complete analysis workflow remain planned.

### B03 — Verify a hosted LLM, its output contract and cost

**Priority: P0 · Labels: llm, observability, security · Milestone: J1 · Estimate: 2 h · Dependencies: B02**

Objective: rule out unsuitable latency/access early and make a controlled real model call.

**Progress recorded on 25 October 2026:** Gemini Developer API, `gemini-3.5-flash-lite` and `gemini-embedding-2`; SDK 2.33.0. The [connection check](../verification/B03_PROVIDER_CONNECTION.md) and [source-case pilot](../verification/B03_SOURCE_CASE.md) passed. Three source selections matched reviewed cells at a 0.950 s median; one missing-period request abstained. Shared calls, SQLite records, local allowance checks and simulated failures are implemented. The [account-limit screenshot](../verification/B03_ACCOUNT_LIMITS.md) records the free tier and model-specific quotas. The [native tool check](../verification/B03_TOOL_CALL.md) passed: one request, one local read, the reviewed Canada/total cells and a 1.302 s model duration. B03 is complete. See the [implementation log](../verification/IMPLEMENTATION_LOG.md) for commands and scope limits.

- [x] Select generation and embedding models from documented capabilities and dated prices.
- [x] Verify model access, structured generation and a normalized 768-dimension text embedding.
- [x] Record the project's actual model-specific RPM, TPM and daily quotas, with the observation date and tier.
- [x] Verify a bounded model-selected tool call with validated arguments; the B10 agent is not required for this compatibility check.
- [x] Call the model on a source case: request an operation and cell references, or abstention; validate the schema in Python.
- [x] Centralize calls in one module without a multi-provider layer. Disable hidden retries; enforce output bounds, timeouts and usage tracking.
- [x] Create a `run_id`; record model, prompt version, duration, tokens, estimated cost and errors. Test a simulated failure without fees.

**Acceptance criteria:** inspect a real result; never use a freely generated number as an operand. Measure latency/cost and compare with a written limit before proceeding. Preserve unknown usage and explicit errors. Keep keys out of the browser and traces.

**Evidence:** sanitized trace, model configuration and dated cost/latency decision. Do not claim performance before measurement.

**Design note:** schema validity does not establish cell relevance or answer accuracy.

### B04 — Prepare a versioned corpus without answer leakage

**Priority: P0 · Labels: data, rag, security · Milestone: J2 · Estimate: 2 h · Dependencies: B01, B02, B03**

Objective: transform public text/tables into retrievable evidence.

- [ ] Prepare a small corpus with distractors; deduplicate, assign `report_id`, `source_id` and `cell_id`, and retain original numbers.
- [ ] Build text/table-row chunks preserving labels, headers, periods, units and context. Do not invent missing company or unit metadata.
- [ ] Create SQLite/FTS5 and corpus embeddings; store vectors, chunk mappings and a version/hash manifest.
- [ ] Physically separate references; check annotation leakage and corpus/index/vector alignment.

**Acceptance criteria:** repeatable preparation, no answers/programs/gold evidence in inference artifacts, and valid source resolution for every ID. Reject inconsistent indexes at load time. Preserve traces during rebuilds.

**Evidence:** preparation command, manifest, check results and an example sanitized only if needed. Include only permitted public sources.

**Design note:** chunking keeps numbers together with labels, periods and units.

### B05 — Build and measure evidence retrieval

**Priority: P0 · Labels: rag, evals · Milestone: J2 · Estimate: 3 h · Dependencies: B04**

Objective: retrieve useful evidence from multiple contexts rather than preselecting the answer document.

- [ ] Implement FTS5/BM25 and inspect top chunks, scores and cells.
- [ ] Add question embeddings, normalized vectors and NumPy cosine search; apply explicit scope before final candidate selection.
- [ ] Measure evidence recall and complete-proof retrieval on the ten development cases; inspect at least two failures or difficult cases.
- [ ] Compare lexical/semantic retrieval with the same corpus and questions; document the provisional choice.

**Acceptance criteria:** search includes distractors. Gold document IDs never become hidden filters. Only explicit user scope constrains retrieval. References are used only for scoring. Retain inspectable scores and sources.

**Evidence:** comparison table and retrieved/missed evidence examples, with corpus version and `k`.

**Design note:** similarity ranks candidates; reference-based evaluation measures relevance.

### B06 — Assemble the fixed workflow and verifiable calculation

**Priority: P0 · Labels: llm, rag, security · Milestone: J2 · Estimate: 3 h · Dependencies: B03, B05**

Objective: question → retrieval → structured LLM selection → calculation in code → evidence.

- [ ] Build the fixed service with one search and at most one generation call, using retrieved chunks only.
- [ ] Validate the operation and accessible cell references; read source numbers and calculate with `Decimal`.
- [ ] Enforce formulas, units, periods, scales and denominator checks. Build displayed evidence from source data.
- [ ] Handle success, insufficient evidence, unsupported requests, blocked work and failures; record initial evaluated results.

**Acceptance criteria:** controlled cases calculate correctly without executing `eval`, generated code or generated SQL. Unknown IDs, ambiguous units, zero denominators and invalid outputs cannot become successes. Test formulas, invalid references and incomplete evidence. These checks alone do not establish an overall model score.

**Evidence:** a real complete execution and repeatable checks; include a result with formula/two source cells and a result without a numerical answer.

**Design note:** the model selects operation/cells; code validates the data and calculates.

### B07 — Expose a documented API with explicit contracts and errors

**Priority: P0 · Labels: api, security · Milestone: J2 · Estimate: 2 h · Dependencies: B06**

Objective: make the service usable and testable independently of the UI.

- [ ] Expose `/reports`, `POST /analyses` and `GET /analyses/{run_id}`; retain `/health` and OpenAPI.
- [ ] Define request/result schemas and error codes; preserve `run_id` after execution creation, including failures.
- [ ] Validate question size, scope and mode; allow one active analysis and enforce a deadline.
- [ ] Check local binding, origin and JSON requirements. Verify success, invalid input, unknown execution and simulated provider failure.

**Acceptance criteria:** consistent `/docs` contract, stored-result lookup without AI calls, and technical errors distinct from domain outcomes. No exposed keys, permissive CORS or unrestricted paths. Invalid input must not trigger paid calls.

**Evidence:** request/response examples and targeted HTTP contract checks.

**Design note:** insufficient evidence is a domain outcome, distinct from a technical failure.

### B08 — Formalize evaluations and measure an improvement

**Priority: P0 · Labels: evals, rag · Milestone: J3 · Estimate: 3 h · Dependencies: B01, B05, B06**

Objective: measure strengths/failures and avoid a demonstration based only on selected successes.

- [ ] Build the evaluator around the API's shared service. Only the evaluator loads expected answers/evidence, separately from analysis.
- [ ] If feasible, extend to 20 development cases and 10 reserved cases split by report group; report actual counts if preparation takes longer.
- [ ] Define tolerances, percentage conventions, retrieval/accuracy/unit/abstention metrics, evidence review, latency/cost and error categories.
- [ ] Compare retrieval variants within the fixed workflow; fix an observed weakness and remeasure development cases.

**Acceptance criteria:** repeatable command, published versions/counts and retained failures. Reserved cases do not tune variants. Do not derive document filters from answers. Measure an improvement or explain the lack of gain. Evaluate beyond JSON validity.

**Evidence:** before/after reports, scoring rules and at least one detailed error analysis. Record numerical thresholds and their rationale before final trials.

**Design note:** calculation, retrieval and end-to-end checks use distinct metrics.

### B09 — Build an interface that shows the evidence

**Priority: P0 · Labels: api, docs · Milestone: J3 · Estimate: 2 h · Dependencies: B07**

Objective: provide a quickly understandable analysis result.

- [ ] Serve one page from FastAPI with question, scope, submit action, waiting state and result.
- [ ] Show original values, units/periods, formula, result and readable evidence with table headers.
- [ ] Clearly display unresolved cases and errors; support execution lookup and technical details.
- [ ] Escape source content and check the browser flow, including text containing HTML tags.

**Acceptance criteria:** a reader can understand the purpose and trace the calculation to sources. The browser calls the application API without a provider key. One page is sufficient; no conversation state or graphical redesign is required.

**Evidence:** screenshots or a short sequence showing a sourced success and insufficient evidence.

**Design note:** every result remains traceable to source values and formula.

### B10 — Add a bounded agent with structured tool calls

**Priority: P1 · Labels: agents, llm, evals · Milestone: J4 · Estimate: 3 h · Dependencies: B07, B08**

Objective: implement bounded model-selected tools and measure their contribution against the fixed workflow.

- [ ] Define `search_evidence`, `read_evidence` and `calculate` with structured parameters backed by existing functions.
- [ ] Let the model choose tools/next actions; enforce immutable scope, four generation calls and six tool calls, including at most two searches.
- [ ] Stop after valid calculation, abstention or a limit. Reject unknown tools, inaccessible cells and numerical final text without a validated calculation.
- [ ] Compare quality, errors, tools, latency and cost using the same development cases and retriever as the fixed workflow.

**Acceptance criteria:** at least one real trace contains multiple model-selected tool decisions. Share validations with the fixed workflow. Test enforced limits, including simulated model attempts to exceed them. No agent framework or multi-agent system is required.

**Evidence:** sanitized trace, comparison table and justified default mode. Report actual findings; retain fixed mode if it performs better for the requirements.

**Design note:** the agent selects actions; code enforces permissions and ceilings.

### B11 — Test injections, permissions and impossible requests

**Priority: P1 · Labels: security, evals · Milestone: J4 · Estimate: 2 h · Dependencies: B09, B10**

Objective: test existing guardrails throughout the system rather than introducing them only at the end.

- [ ] Prepare about ten robustness cases: hostile source instructions, out-of-scope access, unknown tools, invented cells, invalid formats, call limits and hostile HTML.
- [ ] Add/review genuinely missing-evidence cases with identified corpus variants and duplicate checks.
- [ ] Exercise permission/error paths with simulated responses, then run a few live injection cases within budget.
- [ ] Fix observed permission bypasses and document remaining limitations.

**Acceptance criteria:** no observed forbidden action counts as success. Reject unsupported results, stop loops at limits and keep source HTML inactive. Distinguish deterministic application checks, model behavior and untested cases. Do not equate zero observed violations with a general security guarantee.

**Evidence:** attacks/cases, expected and observed outcomes, fixes and remaining work.

**Design note:** model instructions do not replace code-enforced permissions.

### B12 — Make executions inspectable and versioned

**Priority: P1 · Labels: observability, data · Milestone: J4 · Estimate: 2 h · Dependencies: B07, B10**

Objective: extend B03 traces to diagnose quality, cost and failures.

- [ ] Correlate events, retrieval, tools and AI calls by `run_id`; record code/prompt/corpus/index/configuration versions and requested/returned model IDs where available.
- [ ] Consolidate durations, tokens and dated cost estimates, including failures; preserve `null` for unknown usage.
- [ ] Export JSON/CSV or provide a SQL query; show useful execution details in the UI.
- [ ] Change a test corpus version and verify that old results remain readable, identified as old and explicitly rerunnable.

**Acceptance criteria:** an execution ID resolves sources, settings, tools, results and errors without secrets or private chain of thought. Corpus rebuilds preserve traces. Critical recording failures stop further untracked paid calls.

**Evidence:** diagnosed failure, export and corpus-version change demonstration. Local observability requires no subscription.

**Design note:** distinguish retrieval, cell selection, calculation and provider errors.

### B13 — Run final trials and deliver a reproducible release

**Priority: P0 · Labels: evals, docs · Milestone: J5 · Estimate: 3 h · Dependencies: B08, B09, B10, B11, B12**

Objective: release a reproducible version with measured results and documented technical decisions.

- [ ] Freeze code, prompts, corpus, models/configuration and scoring rules; estimate the final campaign before running it.
- [ ] Run fixed variants and the agent on reserved cases; publish actual counts, scores, failures, latency and cost.
- [ ] Verify startup in a fresh Python environment; document downloads, configuration and commands without secrets. Clearly identify any simulated offline checks.
- [ ] Align README/diagrams with the code. Record a short demo: sourced success, difficult case/improvement and missing evidence. Document limits, trade-offs and error-driven next steps.

**Acceptance criteria:** another person can follow setup and understand measurements; real RAG/API/evaluation/tool code is present. Published results match recorded executions and verified deployment scope. If time/budget prevents a comparison, disclose it and report only completed measurements.

**Evidence:** release version, README, measurement report, request/response example, sanitized traces and video or demonstration script. Record incremental spending and limits of reconciliation with provider billing.

**Design note:** release documentation covers trust boundaries, errors, comparisons and quality/cost/latency trade-offs.

## 4. Coverage

| Priority | Capability | Issues | Final evidence |
|---|---|---|---|
| P0 | LLM and structured output | B03, B06 | Live call, validated cell selection and explicit errors. |
| P0 | RAG | B04, B05, B06, B08 | Multi-source retrieval, evidence and retriever comparison. |
| P0 | APIs and architecture | B02, B07, B09 | OpenAPI, shared evaluation service and API demonstration. |
| P0 | AI evaluations | B01, B08, B13 | Separate references, reserved cases, metrics and error analysis. |
| P1 | Agents and tool calling | B10 | Real model-selected tools compared with the fixed workflow. |
| P1 | Security and guardrails | B03, B06, B07, B11 | Code checks, negative tests and stated limitations. |
| P1 | LLMOps and observability | B03, B12, B13 | Versions, traces, cost/latency, diagnosis and reproduction. |
| Additional | Data pipeline and SQL | B01, B04, B12 | Repeatable preparation, SQLite, manifests and exports. |

## 5. Scope limits

Exclude arbitrary PDF/OCR ingestion, user-supplied URL downloads, slow local models, fine-tuning, multi-agent systems, multiple providers, SSO, distributed cloud deployment, full dashboards and systematic LLM judging from this cycle.

Add an extension only to address an observed weakness, and replace another task within the available allowance. The next technical step is **B04**: indexed corpus construction before retrieval and the complete analysis workflow.
