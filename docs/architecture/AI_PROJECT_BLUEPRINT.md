# AI Project Blueprint — FigureTrail

**Reviewed 24 October 2026. Proposed target; build incrementally.**

Purpose: answer numerical questions from public reports with traceable evidence. Scope: one local Python service, a bounded report corpus, deterministic calculations and measured retrieval/model variants. Data references, the HTTP health contract, provider access and a bounded native tool call are verified; retrieval and full analysis capabilities follow the implementation roadmap.

## 1. Repository responsibilities

```text
figuretrail/
├── app/                         # single Python application
│   ├── __init__.py
│   ├── main.py                  # FastAPI routes; serves UI
│   ├── schemas.py               # request, plan, tool, result contracts
│   ├── service.py               # fixed workflow; shared validation/limits
│   ├── retrieval.py             # search, scope, evidence/cell lookup
│   ├── calculator.py            # permitted Decimal operations
│   ├── llm.py                   # one provider SDK; bounded calls
│   ├── storage.py               # corpus reads; execution records
│   ├── agent.py                 # P1 bounded tool-selection loop
│   └── static/                  # minimal HTML/CSS/JavaScript
├── prompts/                     # versioned task prompts
├── scripts/                     # preparation and B01 checks
├── tests/                       # deterministic and component tests
├── evals/
│   ├── cases/                   # references; evaluator only
│   ├── run.py                   # invokes the application service
│   └── results/                 # selected, sanitized experiment artifacts
├── data/                        # ignore generated/private subdirectories
│   ├── raw/                     # original download, including annotations
│   ├── samples/                 # source-only development exports
│   ├── corpus/                  # versioned corpus/index bundles
│   └── local/                   # executions and caches
├── docs/
│   ├── architecture/
│   ├── Backlog/
│   └── verification/
├── .github/workflows/ci.yml     # credential-free checks
├── pyproject.toml               # dependencies and tool configuration
├── uv.lock                     # resolved dependencies
├── .python-version             # tested interpreter
├── .env.example                # variable names; no secrets
├── README.md
├── AGENTS.md
├── .gitignore
└── .editorconfig
```

Preserve existing files, including data attribution/license. Create modules with working behavior, not empty placeholders. The flat `app/` layout fits the current design; `src/figuretrail/` is an alternative requiring packaging/install configuration. [PyPA](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)

## 2. Runtime architecture

**Question → retrieval → LLM cell-selection plan → validation → Decimal calculation → evidence-backed result.**

Use FastAPI/Pydantic, SQLite FTS5/BM25, then compare hosted embeddings with local NumPy cosine search. One provider and one process suffice initially; verify FTS5 availability. [SQLite](https://sqlite.org/fts5.html)

The LLM selects an allowed operation and cell IDs. Code resolves source values, checks scope/units/periods and positive denominators, then calculates. Schema conformity does not establish factual correctness. [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

API, UI and evaluator share the analysis service. Expose `/health`, `/reports`, `POST /analyses`, and execution lookup. Return explicit `success`, `insufficient_evidence`, `unsupported_request`, `blocked` or `failed` states.

Add P1 tool calling through `search_evidence`, `read_evidence`, `calculate`, reusing the fixed workflow's functions. Compare outcomes before choosing a default. [Anthropic](https://www.anthropic.com/research/building-effective-agents)

## 3. Data and prompt boundaries

Preserve table headers, units, periods, original numbers and stable document/segment/cell IDs. Record provenance, hashes, parsing/chunking versions and embedding model/dimension; reject mismatched index bundles. Resolve known dash/`2014` conflicts before indexing.

Allowlist corpus fields; exclude raw annotations, reference files and verification reports from ingestion. The evaluator forwards questions and explicit user scope, never gold-selected evidence or document filters. Deduplicate contexts; split by report. [FinQA repository](https://github.com/czyssrs/FinQA)

Version substantive prompts and record their hashes. Keep trusted instructions separate from untrusted source content; file placement or template syntax provides no injection guarantee.

## 4. Reproducible development

Use uv with committed `pyproject.toml`/`uv.lock`, tested Python, and locked CI installs. Retain B01's dependency-free commands. [uv](https://docs.astral.sh/uv/concepts/projects/layout/)

Use Ruff lint/format checks; add type checking where useful. Ruff does not replace a type checker. [Ruff](https://docs.astral.sh/ruff/faq/)

Validate API/model boundaries with Pydantic, plus explicit domain checks. Keep settings centralized, secrets in environment variables, and long-lived database transactions away from network calls.

## 5. Evaluation and release evidence

Separate development, reserved and adversarial cases; include absent evidence, ambiguity and injection. Define tolerances and acceptance thresholds before final measurement. Public examples may have appeared in model training.

Compare **fixed lexical → fixed semantic → bounded agent**, changing one dimension at a time. Measure evidence recall@k, complete-proof retrieval, correct cells/units/periods, numerical accuracy, justified/unjustified abstention, errors, latency and cost. Keep failures in denominators; publish sample counts and variability.

Use deterministic reference checks first. Judge-based faithfulness scores are supplementary estimates, calibrated against reviewed examples; they do not prevent hallucinations. [Evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [Ragas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)

## 6. Safety, operations and delivery

Treat questions, retrieved text and tool outputs as untrusted. Enforce tool allowlists, immutable scope and validated arguments in code; expose no shell, arbitrary URL, filesystem or generated-code execution. Escape displayed source text. Filters are supplementary. Minimize submitted data; redact sensitive fields if introduced. [OWASP](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

Bound every model/embedding call centrally: deadline, output tokens, retries, tool steps and conservative spending checks. Agent ceiling: four generation calls and six tool calls. Disable hidden SDK retries initially. Local cost estimates alone cannot guarantee a billing cap.

Record `run_id`, versions, retrieved ranks, tool events, state/errors, durations, tokens and estimated cost in SQLite. Unknown usage stays unknown; redact secrets. OpenTelemetry is optional later.

CI runs formatting, tests and leakage/contract checks without live LLM credentials. Run paid comparisons explicitly within budget; protect secrets from untrusted PRs. [GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use). `.gitignore` is not access control. [Git](https://git-scm.com/docs/gitignore)

Publish a reproducible demo, measured comparisons, representative failures and one trace explaining an answer. Add cloud deployment, orchestration frameworks or distributed databases only for a demonstrated requirement.
