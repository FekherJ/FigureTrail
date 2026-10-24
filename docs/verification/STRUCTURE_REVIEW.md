# Repository structure and documentation review

**Baseline review: 24 October 2026. English-language review: 25 October 2026.**

## Responsibilities

The repository separates the application, preparation commands, tests, evaluation references and verification evidence. Keep the existing flat application layout and directory case. Add modules only with their first working feature.

| Location | Responsibility | Boundary |
|---|---|---|
| `app/` | API and application contracts | Health endpoint implemented; analysis service planned. |
| `scripts/` | Local preparation and verification | Repeatable commands with repository-relative runtime paths. |
| `tests/` | Automated checks | Failures and data boundaries. |
| `evals/cases/` | References and review manifest | Never loaded by the inference service. |
| `data/` | Local sources and provenance | Ignore generated/raw data; track notice and provenance. |
| `docs/architecture/` | Target design and contracts | Distinguish planned capabilities from implemented code. |
| `docs/Backlog/` | Roadmap and acceptance criteria | Preserve stable B01–B13 IDs. |
| `docs/verification/` | Evidence, measurements and limits | Exclude from inference ingestion. |

Verification reports belong under `docs/verification/`. Root configuration covers editing, Git exclusions and line endings. No packaging migration, new service or placeholder module is needed.

## Documentation standard

Use clear, concise US English for documentation, diagrams, authored metadata, comments, diagnostics and GitHub issues. Document purpose, behavior, contracts, evidence and limits. Preserve original source quotations, annotations, identifiers and legal notices exactly where they provide evidence.

README covers the service, implemented capabilities, setup and checks. Architecture/backlog describe decisions, dependencies and acceptance criteria. Verification reports state methods, reviewed data and measurement limits. Retain AI-assisted review provenance without implying independent human review or unverified capabilities.

French document filenames have been replaced with English equivalents, and local links updated. Directory names/case remain unchanged. The English editions preserve original review dates and distinguish later status updates.

## Baseline evidence

The 24 October review examined 47 project files outside Git metadata, environment and caches, adapted 18 files, and validated 40 local Markdown links. It recorded ten passing case checks, three negative tests, Ruff lint/format checks and unchanged numerical references/application logic. Those counts describe that review, not the current link inventory.

Raw data, source exports, original FinQA annotations, dependencies, lockfile and license notice remain reference artifacts. The review manifest and verifier contain translated descriptive text, so their hashes in the result snapshot must identify the translated files. Numeric results and source context hashes remain unchanged.

## Current scope and tracking

B01 data feasibility and the B02 local HTTP foundation are verified. Thirteen issues are attached to GitHub Project 2: B01 closed/Done; B02–B13 open/Backlog. B02 remains open for final review. Language edits do not change issue states or create recurring Markdown synchronization.

| Step | Remaining evidence |
|---|---|
| B03 | Provider/models, structured output, cost/latency and first traces. |
| B04–B08 | Annotation-free corpus/index, resolved table conflicts, retrieval and reserved-case evaluations. |
| B09–B12 | Evidence UI, bounded tools, security checks and observability. |
| B13 | Final validation, reproducibility and release documentation. |

See the [backlog](../Backlog/BACKLOG.md), [B01 report](B01_DATA_VERIFICATION.md), [exact results](B01_VERIFICATION_RESULTS.json) and [B02 report](B02_ENVIRONMENT.md). Language consistency does not establish LLM/RAG performance.

## English edition checks — 25 October 2026

- Ten source/reference checks and all three negative tests passed with the translated verifier.
- Ruff lint passed across the repository; the three API/environment foundation files passed formatting checks.
- All 46 local Markdown links resolved with exact path casing. Code fences were balanced, and no obsolete French document paths remained in authored files.
- Thirty preserved artifacts matched their baseline hashes, including raw/source data, original reference exports, dependency files, the license notice and unchanged application files.
- Computational reference fields and measured numerical results were unchanged. The result snapshot identifies the translated manifest and verifier hashes.
- Python edits were limited to reviewed comments, docstrings, help text and diagnostics, with the matching negative-test expectation updated.
- Live GitHub reads confirmed all thirteen translated titles/descriptions, with issue numbers, states, board item IDs and statuses preserved.
- No dependencies, model calls, feature scope, Git commits or repository push were introduced by this review. Issue translations are live; repository edits remain available for local review.

## Pre-commit verification — 25 October 2026

The README, implementation, dependency metadata and roadmap describe the same baseline: ten reviewed data cases and a working health API. LLM integration, indexed retrieval, the analysis API, UI and agent remain planned. B03 is the next technical step.

The review corrected two remaining US-spelling inconsistencies and changed the README's delivery-tracking link to public repository issues; the project board is private. Board visibility was not changed.

- `uv lock --check --offline` and `uv sync --locked --no-build --offline` passed without changing dependency files. The review used a temporary writable uv cache outside the repository.
- Environment, Ruff, ten data checks and three negative tests passed through the documented `uv run --locked` commands, with offline mode enabled for the review.
- A temporary localhost Uvicorn server returned the documented `/health` body, valid OpenAPI matching project version `0.1.0`, and HTTP 200 for `/docs`. Unimplemented analysis/UI routes and raw/reference-data paths returned 404. The server was stopped afterwards.
- The verifier rejected Python `-O` as documented. Reference hashes, numerical results and all 46 local documentation links remained valid.
- Current GitHub reads matched the thirteen English issue descriptions and board states. B02 remains open for final review; the language changes did not alter progress.
- The Git dry run included all six document renames. The 36 files that would exist in the resulting checkout excluded generated data, environments and local configuration. Recognized credential-pattern checks found no matches; all JSON candidates parsed.
- Git whitespace checks passed. The review did not stage, commit or push changes.
