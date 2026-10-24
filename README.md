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
| Retrieval and analysis | Indexed corpus, lexical/semantic retrieval and LLM analysis planned |
| Tools and operations | Bounded agent, analysis guardrails and execution records planned |
| Delivery tracking | B01–B13 tracked as [repository issues](https://github.com/FekherJ/FigureTrail/issues); B01 closed, B02 open for final review |

Existing checks validate the reference data and HTTP foundation. LLM/RAG performance will be measured after implementation; no model score is published yet.

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
uv run --locked ruff format --check app scripts/check_environment.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m unittest discover -s tests -p test_b01_verification.py -v
```

Verified results: **10 valid cases and 3 passing negative tests**. The tests reject the wrong year, confusion between ratios and percentages, and answers leaked into source exports. The verifier rejects Python's `-O` mode because it disables assertions.

Ruff checks lint across the codebase and formatting in the API foundation files. FinQA verification also runs with the Python standard library alone. These data checks are separate from future retrieval and answer evaluations.

## Repository layout

```text
app/                    Implemented API and application contracts
scripts/                Data preparation and environment checks
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

The next technical step is a hosted-provider integration with structured output, cost/latency measurement and initial execution records. Provider and model selection remain open.

## Documentation

- [Architecture and contracts](docs/architecture/ARCHITECTURE.md)
- [Engineering standards](docs/architecture/AI_PROJECT_BLUEPRINT.md) and [standards review](docs/verification/AI_PROJECT_BLUEPRINT_REVIEW.md)
- [Roadmap and acceptance criteria](docs/Backlog/BACKLOG.md)
- [Data verification](docs/verification/B01_DATA_VERIFICATION.md), [exact results](docs/verification/B01_VERIFICATION_RESULTS.json) and [environment verification](docs/verification/B02_ENVIRONMENT.md)
- [Repository review](docs/verification/STRUCTURE_REVIEW.md) and [contribution instructions](AGENTS.md)
- [FinQA provenance](data/FINQA_PROVENANCE.md) and [license notice](data/FINQA_LICENSE.txt)

The FinQA notice applies to the relevant data. A general license for FigureTrail code has not yet been selected.
