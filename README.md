# FigureTrail

Answer numerical questions about public reports with traceable evidence. Find the values, identify their units and periods, calculate a percentage ratio or change, and show the source cells behind the result.

The design combines retrieval, structured LLM selection and deterministic calculation with `Decimal`. The model selects evidence; source data and application code supply the operands and result.

## Project status

**Active development — status reviewed on 25 October 2026.**

| Component | Status |
|---|---|
| Data references | 10 FinQA cases verified: cells, units, periods, formulas and results |
| Reproducibility | Isolated Python environment, locked dependencies and repeatable checks |
| API | Working `/health` endpoint, Pydantic response contract and OpenAPI schema |
| Provider connection | Gemini SDK connection verified: one structured response and one 768-dimension embedding |
| Source-case pilot | Three matching operation/cell selections; 0.950 s median; one observed missing-period abstention |
| Retrieval and analysis | Indexed corpus, lexical/semantic retrieval and LLM analysis planned |
| Tools and operations | Provider call journal and local allowances implemented; bounded agent and complete analysis records planned |
| Delivery tracking | [Repository issues](https://github.com/FekherJ/FigureTrail/issues): B01–B02 completed; B03 In progress with quota/tool-call checks remaining |

Existing checks validate the reference data, HTTP foundation and one controlled LLM source-selection pilot. Broader task quality and RAG performance remain unmeasured; no benchmark accuracy score is published.

## Setup and run

Verified environment: **Windows, Python 3.14.5, uv 0.11.14**. Run commands from the repository root.

```powershell
python3.14.exe -m venv .venv --without-pip
uv sync --locked --no-build
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`uv.lock` records resolved versions. `--locked` prevents implicit lockfile changes; `--no-build` uses prebuilt distributions. The first download requires internet access. PowerShell environment activation is optional. In VS Code, select `.venv\Scripts\python.exe` as the interpreter.

In another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

```json
{"status":"ok","corpus_version":null}
```

The health endpoint confirms that the process responds. `corpus_version: null` means no corpus is loaded. The schema is available at `/openapi.json`, with interactive documentation at `/docs`. The server listens on `127.0.0.1`; press **Ctrl+C** to stop it. This foundation requires no provider key.

## Check the provider connection

Configure `GEMINI_API_KEY` in your local environment using [Google's key setup instructions](https://ai.google.dev/gemini-api/docs/api-key). Keep its value out of commands, Git and screenshots. The check reads this variable explicitly; `.env` files are not loaded automatically.

```powershell
uv run --locked python -B -X utf8 -m scripts.check_provider --live
```

This explicit live command makes at most two model requests: a small JSON response and one text embedding. It uses a 20-second transport timeout, a 64-token generation ceiling and no automatic retries. The first failure stops the check. Without `--live`, it refuses to send requests. Local records go under the ignored `data/local/provider-checks/` directory. No billing settings are changed; account quotas and charges must be checked separately.

On 25 October 2026, both checks passed: **1.015 seconds** for the structured response and **0.376 seconds** for the embedding. These are single-request connection measurements, not report-analysis or RAG benchmarks. See the [results and limitations](docs/verification/B03_PROVIDER_CONNECTION.md).

## Run the controlled source-case pilot

After preparing the source data below and configuring the key, these explicit live commands repeat the Canada-production case and check a missing-period variant:

```powershell
uv run --locked python -B -X utf8 -m scripts.run_source_case --live --repetitions 3
uv run --locked python -B -X utf8 -m scripts.run_source_case --live --scenario missing-period
```

Gemini proposes the operation and ordered cell IDs; Python validates and resolves source values. The original-table context is supplied directly, so this is a feasibility test before retrieval. The evaluator reads expected references after the requests. There is no runtime numerical calculation yet.

Observed: three matching selections of Canada 60 / total 243 MMBoe, with a **0.950-second median**, and one `insufficient_evidence` response for 2035. These results cover one development example and one negative variant. See the [pilot evidence](docs/verification/B03_SOURCE_CASE.md).

The shared provider module records calls in the ignored `data/local/runs.sqlite`. It reserves allowances before requests against a €25 local limit, retains unknown usage and disables automatic retries. Allowances are conservative estimates, not provider charges or a guaranteed billing cap. Full commands, decisions and troubleshooting are in the [implementation log](docs/verification/IMPLEMENTATION_LOG.md).

## Prepare the data

[FinQA](https://github.com/czyssrs/FinQA) supplies public text and tables with evaluation annotations. On a fresh checkout, download the raw file and generate separate exports:

```powershell
New-Item -ItemType Directory -Force -Path data/raw | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/dev.json' -OutFile data/raw/finqa-dev.json
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all
```

If the raw file already exists, keep it and run the export command. Its hash is checked before processing. A source change requires a provenance review.

Source exports contain only `filename`, `pre_text`, `post_text`, `table` and `table_ori`. Questions, answers, programs and annotated evidence remain in evaluation references. All ten cases are development cases. The original report PDFs have not been inspected.

## Run checks

After preparing the data:

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check app scripts/check_environment.py scripts/check_provider.py scripts/run_source_case.py tests/test_provider_connection.py tests/test_source_case.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m unittest discover -s tests -v
```

Verified results: **10 valid cases and 3 passing negative tests**. The tests reject the wrong year, confusion between ratios and percentages, and answers leaked into source exports. The verifier rejects Python's `-O` mode because it disables assertions.

All **seven offline tests** pass. The provider tests additionally simulate quota errors on both SDK endpoints and verify credential exclusion, retained unknown usage, source/plan boundaries, invented cells and a budget block before network access. Ruff checks lint across the codebase and formatting in the API and B03 files. FinQA verification also runs with the Python standard library alone. These checks are separate from future retrieval and answer evaluations.

## Repository layout

```text
app/                    Implemented API and application contracts
scripts/                Data preparation, environment and provider checks
tests/                  Automated tests
evals/cases/            References for evaluation only
data/                   Local sources, provenance and license notice
docs/architecture/      Design, contracts and technical decisions
docs/Backlog/           B01–B13 roadmap and reference cases
docs/verification/      Verification reports, results and limitations
```

Downloads, generated exports, execution records and `.venv/` are excluded from Git. Application modules are added with their first working feature.

## Design principles

- **Evidence before calculation:** validate cell references, units and periods, then calculate deterministically.
- **Independent evaluation:** keep annotations and verification reports out of the inference corpus.
- **Measured comparisons:** compare lexical retrieval, semantic retrieval and a bounded agent under the same conditions.
- **Controlled execution:** enforce tool permissions and record call limits, costs, errors and versions.

Use clear, concise English for project documentation, diagrams, comments, diagnostics and GitHub issues. Preserve original source quotations and technical identifiers. Do not rewrite source evidence to improve its wording.

The B03 pilot uses Google's Gemini Developer API: `gemini-3.5-flash-lite` for generation and `gemini-embedding-2` for embeddings, starting on the free tier. See the [provider decision](docs/architecture/PROVIDER_SELECTION.md). Model access, SDK compatibility, the source-selection contract, one-case latency and the provider allowance journal are verified. Numeric project quotas and tool-call compatibility remain pending. B03 is open.

## Documentation

- [Architecture and contracts](docs/architecture/ARCHITECTURE.md)
- [Hosted provider and model selection](docs/architecture/PROVIDER_SELECTION.md)
- [Provider connection verification](docs/verification/B03_PROVIDER_CONNECTION.md)
- [Source-case verification](docs/verification/B03_SOURCE_CASE.md) and [implementation log with commands](docs/verification/IMPLEMENTATION_LOG.md)
- [Engineering standards](docs/architecture/AI_PROJECT_BLUEPRINT.md) and [standards review](docs/verification/AI_PROJECT_BLUEPRINT_REVIEW.md)
- [Roadmap and acceptance criteria](docs/Backlog/BACKLOG.md)
- [Data verification](docs/verification/B01_DATA_VERIFICATION.md), [exact results](docs/verification/B01_VERIFICATION_RESULTS.json) and [environment verification](docs/verification/B02_ENVIRONMENT.md)
- [Repository review](docs/verification/STRUCTURE_REVIEW.md) and [contribution instructions](AGENTS.md)
- [FinQA provenance](data/FINQA_PROVENANCE.md) and [license notice](data/FINQA_LICENSE.txt)

The FinQA notice applies to the relevant data. A general license for FigureTrail code has not yet been selected.
