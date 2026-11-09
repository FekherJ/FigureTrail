# Fixed-workflow execution identity

**Verified locally: 9 November 2026. Audit F02 / B08 preparation.**

New analysis records identify the implementation and effective settings used for a fixed-workflow attempt. This prepares repeatable evaluation comparisons; it does not establish answer accuracy or complete B08/B12.

## Scope and format

`app/service.py:execution_identity(method, report_ids)` runs before retrieval/generation and returns:

- `identity_version`: `fixed-execution-v1`.
- `code_files`: relative-name-to-SHA-256 map covering all top-level `app/*.py` files (currently ten) plus `pyproject.toml`, `uv.lock` and `.python-version` (13 files total).
- `code_sha256`: canonical digest of that map. Paths distinguish file identities; byte changes, added application modules and dependency-file changes alter it.
- `configuration`: an owned JSON snapshot of the fixed settings, retrieval settings/method/explicit scope, embedding formats/model/dimensions, pacing allowances, provider request settings/model IDs/local EUR limit and Python/SQLite/installed-package versions.
- `configuration_sha256`: canonical digest of that snapshot. Different settings/runtime versions deliberately produce a different identity even if source files are unchanged.

Prompt bytes, prepared corpus and index retain their separate identities. `PROVIDER_CONFIG` in `app/llm.py` supplies shared request settings; the recorded output-token ceiling is passed explicitly by the service. Lexical term truncation reads the same setting that is recorded. Default timeout/retry/thinking/tool settings, model IDs, arithmetic, scope, call ceilings and local budget are unchanged. Per-call metadata retains realized transport timeout and usage where available; the configuration records the configured timeout ceiling.

Records without `identity_version`/`code_files` retain their historical five-module concatenated code hash and flat configuration. Do not compare their hash strings as if they used the new format. No migration, historical rewrite, index rebuild or public API/schema change is required. The existing API returns code/configuration hashes; full manifests/settings remain in internal records and CLI output.

The source identity covers on-disk files, not already imported Python bytecode. Restart after code/dependency edits and avoid edits during campaigns. It is provenance evidence, not attestation of an entire machine or a guarantee of deterministic provider output. Top-level application files are the current flat-layout boundary; revise it if runtime code moves into subpackages. Installed-package metadata includes package names/versions, never environment-variable values or filesystem locations. Returned model versions remain per-call evidence; aliases may change upstream.

## Regression evidence

Added four offline checks in `tests/test_analysis.py`, using temporary source copies, journals and simulated providers:

1. File/dependency changes: omitted runtime modules, API code, package initialization, dependency specification/lock/Python pin and a new top-level application module change the recorded code identity. Repeated unchanged runs retain the same hashes.
2. Effective settings: changes to k, lexical term cap, query formatting, token/timeout ceilings, retrieval mode, generation model, pacing and Python version change the configuration hash. Captured values remain owned after global settings change; a test key is excluded. Token/term-cap changes reach the actual call/search settings.
3. Compatibility: a legacy-shaped record loads unchanged, validates through the public-result projection and leaves SQLite bytes unchanged.
4. Missing dependency input: absence of `uv.lock` fails before search, generation or journal creation.

Before implementation, the corrected fixtures produced two missing-identity/settings errors and one missing-lock rejection failure; legacy lookup already passed. The initial compatibility fixture needed API rank/score/call fields before its baseline check could be meaningful. After implementation, all four checks pass.

Full local verification: **62 offline tests pass in 13.001 s**, Ruff lint and 30-file formatting pass; environment, ten source cases, prepared corpus and current index checks pass. The existing TestClient/httpx deprecation warning remains visible. All **14 existing historical analyses** pass read-only lookup/public projection; journal bytes are unchanged. Provider requests are simulated; no live inference ran. Existing hosted CI evidence remains the earlier 58-test baseline until the user publishes these changes.

Commands, through the installed project environment:

```powershell
uv run --locked python -B -X utf8 -m unittest discover -s tests -p test_analysis.py -k identity -v
uv run --locked ruff check .
uv run --locked python -B -X utf8 -m unittest discover -s tests -v
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m scripts.prepare_corpus --check
uv run --locked python -B -X utf8 -m scripts.build_index --check
git diff --check
```

The exact formatting scope is the command in [README](../../README.md). [Structured results](B08_EXECUTION_IDENTITY_RESULTS.json) retain the observed counts. Historical audit/CI/measurement reports are preserved. The next implementation task is the broader B08 evaluation comparison, not a new agent or framework.


## Hosted follow-up, 9 November 2026

The user published identity commit `b9cd10942217418380c72ceb76de251f0d82f296`. [GitHub run 42684643190](https://github.com/FekherJ/FigureTrail/actions/runs/42684643190) passes all 62 tests in 7.280 s; every job step succeeds. This confirms the earlier identity baseline. The subsequent B08 evaluator has separate local 72-test/live-comparison evidence and awaits its own publication.

The subsequent [B08 development comparison](B08_WORKFLOW_EVALUATION.md) is now complete at its declared ten-positive/two-negative scope. B09 is next; provider reliability and reserved-case validation remain open.
