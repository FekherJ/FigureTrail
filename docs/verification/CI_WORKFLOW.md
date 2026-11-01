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

**Pending publication and hosted runs.** Local Ubuntu validation is not a GitHub-hosted result. No GitHub run ID or URL has yet been recorded for this workflow.

After publication, verify a green run on a fresh GitHub runner. Then, on a temporary validation branch, add a deliberately failing unittest and confirm the `Run offline tests` step and job fail. Remove that test and confirm the branch is green again. Record the commits/run URLs before marking hosted acceptance complete. The deliberately failing test must not be merged into the default branch.

Commits and pushes remain under the user's control unless separately authorized. B08 remains the next application implementation milestone.

## Sources

The setup follows [Astral's GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/) and [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax). Action pins were checked against the upstream repositories: [checkout](https://github.com/actions/checkout/commit/d23441a48e516b6c34aea4fa41551a30e30af803), [setup-uv](https://github.com/astral-sh/setup-uv/commit/bec219d24cd3e171d82865faccec33120bb574f4). The [FinQA provenance](../../data/FINQA_PROVENANCE.md) and reviewed manifest remain the source-data record.
