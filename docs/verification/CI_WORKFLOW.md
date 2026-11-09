# Continuous integration verification

**1 November 2026. Workflow: [ci.yml](../../.github/workflows/ci.yml).**

One Ubuntu 24.04 job checks pushes, pull requests and manual dispatches. It installs Python from `.python-version` and uv 0.11.14, then uses `uv sync --locked --no-build`. Actions are pinned to full commit IDs. Checkout does not persist credentials; job permissions are limited to reading repository contents. No dependency cache is restored or saved.

## Checks and data setup

The workflow downloads FinQA `dataset/dev.json` at commit `0f16e2867befa6840783e58be38c9efb9229d742`. Before writing data, it checks the SHA-256 against the existing reviewed-case manifest:

```text
a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51
```

It generates only ignored `data/samples/*-source.json` exports using the existing source-field allowlist. Committed references are read, not regenerated; this preserves their exact bytes across operating systems. The existing ten-case verifier runs in `--check` mode afterward.

The job then checks dependency/SQLite FTS5/NumPy availability, runs Ruff lint and the README's formatting scope, and executes the full offline unittest suite. The final step rejects changes to tracked files and whitespace errors. Model keys are empty and no `--live` inference command is present. Network access is required for tools, dependencies and public data; model responses in tests are simulated.

## Observed local validation

| Check | Result |
|---|---|
| actionlint 1.7.12 | Workflow syntax/expressions pass |
| Isolated Ubuntu 24.04 checkout | Fresh Python 3.14.5 and all 33 locked dependency distributions installed |
| Pinned data and exports | Hash matched; all ten cases passed |
| Environment | Python 3.14.5, SQLite 3.50.4, FTS5 and NumPy passed |
| Ruff | Lint passed; 30 files already formatted |
| Offline tests | 58 passed in 14.313 s |
| Windows regression | 58 tests passed in 9.946 s; lint/format pass |
| Tracked-file reproducibility | No tracked bytes changed by setup/checks |
| Intentional failure | Temporary test produced 59 tests, one intentional failure and exit code 1 |
| Hash-mismatch rejection | Wrong expected hash produced a nonzero exit before data/exports were written |

Validation executed the workflow's run blocks in an isolated Ubuntu 24.04 WSL checkout with its own environment/cache and empty model keys. It did not reuse the project's Windows virtual environment, existing data or provider journal. The temporary failing test was removed and is not part of the project. No failure is suppressed by `continue-on-error` or an always-successful wrapper.

The first Ubuntu test run exposed a timing-sensitive assumption: a 150 ms test deadline could expire during setup before simulated generation started. The two HTTP deadline tests now allow one second to reach their controlled SDK stage. Cancellation, blocked-result, slot-ownership and latency assertions remain. Production deadlines and application code are unchanged. The existing TestClient/httpx deprecation warning remains visible.

## GitHub-hosted acceptance

**Hosted success verified on 1 November 2026.** [CI run 41318662604](https://github.com/FekherJ/FigureTrail/actions/runs/41318662604), attempt 1, completed successfully for commit `d901156ba47e075c640b4d27231a376131a9109c` on `main`. The `checks` job used GitHub-hosted Ubuntu 24.04 and passed all 58 tests in 4.751 s; every job step succeeded, including fresh locked installation, data verification, lint, formatting and tracked-file checks. Logs show empty model-key variables. Job duration was 17 seconds; the workflow summary shows 20 seconds total. These are CI durations, not live-model latency measurements.

**Hosted intentional failure verified on 1 November 2026.** [CI run 41332322419](https://github.com/FekherJ/FigureTrail/actions/runs/41332322419), commit `95b596f15799adc601ca57ee94a477c716ed2736` on `ci/verify-failure`, failed specifically at `Run offline tests`. Setup, pinned data, environment, lint and formatting passed. Logs show 59 tests in 4.658 s, one intentional assertion failure (`Intentional hosted CI verification failure`) and exit code 1. The subsequent reproducibility step was skipped because the test step failed; this is expected failure propagation. Model keys were empty.

**Hosted restoration verified on 1 November 2026.** [CI run 41332673328](https://github.com/FekherJ/FigureTrail/actions/runs/41332673328), commit `16e7ae95f138b6d5efb29ac3794a9665c6ca784d` on `ci/verify-failure`, passed all 58 tests in 4.695 s after the user committed and pushed the probe removal. Every job step passed, including the tracked-file/whitespace check. The tracked validation-branch tree matches the original CI baseline. The main success, intentional test failure and restored success now complete hosted CI acceptance. Main contains no probe and no validation-branch merge is required. The existing local negative test remains separate evidence.

Commits and pushes remain under the user's control unless separately authorized. B08 remains the next application implementation milestone.

## Sources

The setup follows [Astral's GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/) and [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax). Action pins were checked against the upstream repositories: [checkout](https://github.com/actions/checkout/commit/d23441a48e516b6c34aea4fa41551a30e30af803), [setup-uv](https://github.com/astral-sh/setup-uv/commit/bec219d24cd3e171d82865faccec33120bb574f4). The [FinQA provenance](../../data/FINQA_PROVENANCE.md) and reviewed manifest remain the source-data record.
