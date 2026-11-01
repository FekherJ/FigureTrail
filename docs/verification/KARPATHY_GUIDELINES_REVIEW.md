# Coding principles and project review

**Reviewed: 1 November 2026. Scope: the current local B07 implementation, based on FigureTrail commit `2f09352754b9ac9668267a9167ae2103d513809b`, including existing local instructions and verification-log edits.**

The project largely follows the reviewed principles. Its current architecture does not warrant a rewrite. The original audit identified four bounded findings: one reproduced evaluator-control issue, an execution-provenance gap, contradictory documentation, and two unclosed CLI SDK clients. Passing the existing checks does not certify every behavior or live-model result.

**Follow-up, 1 November 2026:** F01 is resolved in `evals/retrieval.py`. Filesystem/SQLite errors now stop the campaign, with remaining query/method entries recorded as blocked and retained in scoring denominators. Three new regression tests pass; the full suite has 54 passing offline tests. The audit baseline, original reproduction and machine-readable audit results below remain historical evidence. F02–F04 were still open at that follow-up. See the [implementation log](IMPLEMENTATION_LOG.md) for the fix and verification.

**Cleanup follow-up, 1 November 2026:** F03 and F04 are now resolved. The two CLI paths explicitly close their clients, with success/setup/provider/storage failure tests and lexical/cache-only checks. Backlog/integration statements reflect B07 completion and B08 next; CI is explicitly planned. All 58 offline tests pass. F02 (complete execution identity) remains open. Original audit measurements and JSON evidence are preserved.

## Source and adoption

The [upstream repository](https://github.com/multica-ai/andrej-karpathy-skills/tree/2c606141936f1eeef17fa3043a72095b4765b9c2) contains **one skill**, [karpathy-guidelines](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/skills/karpathy-guidelines/SKILL.md), with four principles. The [CLAUDE.md version](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/CLAUDE.md) expresses the same principles. This is guidance maintained by multica-ai and inspired by Karpathy's observations, not a formal AI engineering standard or certification.

All four are incorporated into [AGENTS.md](../../AGENTS.md): understand assumptions before coding; prefer the smallest adequate solution; keep edits scoped; and define verifiable outcomes. The adaptation preserves actual error handling, test seams, existing scope and proportionate verification. It does not install a global plugin or introduce application dependencies.

## Review coverage and evidence

Reviewed the ten application modules, nine command scripts, two evaluators, ten test modules, prompts, dependencies/lock setup, ignore rules, source/reference separation and current architecture/backlog/README claims. The tracked-file inventory covers 86 files, including curated evidence and attribution. Parsed all 31 tracked Python files and all tracked JSON. Checked local Markdown link targets; external links were not all revalidated. Private notes/PDFs were protected, not evaluated as public engineering claims. Environments, generated bundles and journals were excluded from code-review scope and checked for preservation.

Automated checks used the installed project environment, without dependency installation or live AI requests:

| Check | Observed result |
|---|---|
| Ruff lint | Pass across the repository |
| Documented Ruff formatting scope | Pass, 29 files |
| Offline unit/component suite | 51 tests pass, 15.426 s; includes local HTTP with simulated SDK responses |
| Environment check | Pass: dependency versions, SQLite FTS5 and NumPy |
| B01 existing-export verification | All ten cases pass without rewriting exports |
| Prepared-corpus reproducibility check | Pass: 20 sources, 186 chunks, 243 original cells |
| Current index check | Pass: aligned 186 × 768 matrix and validated SQLite/vector bundle |
| Tracked Markdown links | 184 local targets checked, none missing |
| Git whitespace check | Pass |
| Storage-error probe | Confirms retrieval evaluation advances after a simulated SQLite error |

Existing TestClient/httpx deprecation warnings remain visible. Checks do not measure live provider behavior, held-out accuracy or resistance to all attacks. No model availability or pricing claim was refreshed during this review.

## Findings, in action order

### F01 — Stop retrieval campaigns on storage errors

**Priority: medium. Confirmed with a simulated probe. Principle: goal-driven execution.**

In [evals/retrieval.py](../../evals/retrieval.py), `retrieve_cases()` catches `OSError` and `sqlite3.Error` with ordinary case failures, appends a failed result and proceeds to the next search. A two-question probe with a SQLite failure on the first search attempted **both** searches and returned statuses `failed`, `passed`.

An error from a shared-journal or query-cache write can therefore be treated as recoverable case failure while subsequent uncached questions remain eligible for live embedding calls. This does not prove an unrecorded real request occurred: the provider reserves before network access, and a persistent journal fault may block every attempt. It does prove the campaign does not abort when it can no longer establish normal storage operation. The analysis evaluator already stops after comparable recording failures.

**Smallest follow-up:** distinguish storage failures from ordinary per-case/provider failures; abort subsequent execution and retain remaining cases as blocked in the scoring denominator. Add a focused test asserting that a second search is not attempted after a storage failure, while ordinary failed cases still retain their documented treatment. Do this before another live retrieval campaign.

### F02 — Execution fingerprints omit behavior-affecting modules

**Priority: medium follow-up, aligned with B12. Confirmed by source inspection. Principles: explicit assumptions and verification.**

In [app/service.py](../../app/service.py), `analyze()` hashes five source files for `code_sha256`: service, calculator, retrieval, schemas and llm. It omits `app/embeddings.py`, `app/storage.py`, `app/corpus.py` and the API admission implementation. Existing corpus/index hashes identify data and build settings, but do not identify every runtime implementation. A change to pacing/cache behavior can leave the recorded code hash unchanged when the five listed files are untouched. `CONFIGURATION` also does not serialize the entire retrieval configuration.

This is an incomplete provenance claim, not an observed numerical error or a reason to rebuild the index now.

**Smallest follow-up:** document exactly what the current fingerprint covers; during B12, record a complete relevant code identity and effective runtime configuration. A commit ID alone is insufficient for dirty local files. Verify with a temporary fixture that changing a relevant dependency changes the execution identity while old records remain readable. Do not retroactively alter historical fingerprints.

### F03 — Current navigation and architecture contain stale claims

**Priority: low. Confirmed against current files. Principles: explicit assumptions and verifiable goals.**

- The final scope paragraph of [BACKLOG.md](../Backlog/BACKLOG.md) calls B05 the next technical step, while its current status table correctly identifies B08.
- Section 3 of [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) says end-to-end evaluation remains planned and that the bundle remains separate until integration, despite later sections documenting the B06 campaign and B07 integration.
- [AI_PROJECT_BLUEPRINT.md](../architecture/AI_PROJECT_BLUEPRINT.md) includes a CI workflow in its target tree and states that CI runs the checks. No tracked `.github/workflows/` file exists. The target tree is explicitly aspirational, so missing files alone are not a defect; the present-tense CI assertion needs a planned/implemented distinction.

**Smallest follow-up:** correct only these current-state statements. Preserve dated historical evidence and its original counts. Label CI as planned, or implement one credential-free workflow as a separately scoped task with explicit dataset/setup steps. Do not add every file shown in the target tree.

### F04 — Two CLI paths do not explicitly close SDK clients

**Priority: low. Confirmed by source inspection. Principle: scoped, straightforward resource ownership.**

[scripts/search.py](../../scripts/search.py) and the live branch of [evals/retrieval.py](../../evals/retrieval.py) construct `GeminiProvider(create_client())` without a context manager or matching `close()` in `finally`. The API and other commands demonstrate explicit client ownership and cleanup.

These are short-lived commands, so process exit limits practical impact. This is not evidence of an API client leak or a reason for a new provider framework.

**Smallest follow-up:** retain the SDK client locally and close it on both success and failure. Verify cleanup with a fake client and preserve cache-only operation without creating a client.

The audit itself applied no runtime fixes. Subsequent resolutions are identified in the dated follow-up above; the findings below describe the audit baseline.

## Assessment against all four principles

| Principle | Evidence of alignment | Qualification |
|---|---|---|
| Think before coding | Documented scope, report formats, budgets, explicit input schemas and disclosed provider failures | Correct F03; an artifact review cannot establish how every earlier decision was made |
| Simplicity first | One process/provider; flat modules; SQLite/FTS5 plus exact NumPy search; standard-library tests; no unused controller/repository framework or agent scaffolding | Keep justified boundaries; do not equate fewest lines with fewest failures |
| Surgical changes | Current app source matches the previously verified GitHub commit; private walkthroughs hold verbose teaching content | This review preserves existing local edits and makes no runtime refactor; it cannot certify every historical diff |
| Goal-driven execution | Reproducible preparation, source checks, simulated failure paths and separate retrieval/answer metrics | F01 is an uncovered path; final broader evaluation remains B08/B13 work |

Keep `GeminiProvider`: it owns accounting, SDK bounds, validation and safe error records rather than merely delegating. Keep `provider_factory`: tests use it to avoid live requests. Keep the shallow request copy of the retriever: it shares validated data while keeping per-request provider bindings separate. Keep source/index integrity checks: corruption and provenance mismatches are possible failures, not hypothetical branches to delete. Retain the B03 pilots as documented verification tools; do not merge their narrower parsing semantics with the production calculator solely to remove repeated-looking code.

The broadest remaining product-quality gap is already documented: ten development questions and targeted follow-ups do not establish independent accuracy or solved provider latency. Completing B08 measurements provides more value than adding layers, switching frameworks or deleting existing safeguards. The agent, UI, public authentication and distributed operations are planned/out of scope at this stage, not silently missing completed features.

## Reproduce the checks

Use the exact formatting command listed under **Run checks** in [README.md](../../README.md); it intentionally excludes historical B01 formatting. Other commands are:

```powershell
uv run --locked ruff check .
uv run --locked python -B -X utf8 -m unittest discover -s tests -v
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m scripts.prepare_corpus --check
uv run --locked python -B -X utf8 -m scripts.build_index --check
git diff --check
```

The source/export/corpus/index checks require the existing local prepared artifacts; see README for fresh-checkout setup. Machine-readable evidence accompanies this report in [KARPATHY_GUIDELINES_REVIEW_RESULTS.json](KARPATHY_GUIDELINES_REVIEW_RESULTS.json).
