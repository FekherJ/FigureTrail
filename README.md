# FigureTrail

Answer numerical questions about public reports with traceable evidence. Find the values, identify their units and periods, calculate a percentage ratio or change, and show the source cells behind the result.

The design combines retrieval, structured LLM selection and deterministic calculation with `Decimal`. The model selects evidence; source data and application code supply the operands and result.

## Project status

**Active development — status reviewed on 26 October 2026.**

| Component | Status |
|---|---|
| Data references | 10 FinQA cases verified: cells, units, periods, formulas and results |
| Prepared corpus | 20 contexts, 186 chunks and 243 original cells; offline preparation verified |
| Search bundle | SQLite/FTS5 plus an aligned 186 × 768 matrix; 184 distinct cached document embeddings |
| Reproducibility | Isolated Python environment, locked dependencies and repeatable checks |
| API | Working `/health` endpoint, Pydantic response contract and OpenAPI schema |
| Frontend | One HTML/CSS/JavaScript page planned for B09; no browser interface yet |
| Provider connection | Gemini SDK connection verified: one structured response and one 768-dimension embedding |
| Source-case pilot | Three matching operation/cell selections; 0.950 s median; one observed missing-period abstention |
| Native tool check | One validated `read_evidence` request and local execution; model request took 1.302 s |
| Retrieval | Lexical/semantic comparison measured on ten development questions; complete proof@5: 9/10 and 10/10 |
| Numerical analysis | Fixed CLI workflow with source validation, Decimal calculation and initial evaluation; provider latency/timeouts remain limitations |
| Tools and operations | Provider/analysis journals and local allowances implemented; bounded agent events and fuller observability planned |
| Delivery tracking | [Repository issues](https://github.com/FekherJ/FigureTrail/issues): B01–B06 completed; B07 analysis API is next |

Existing checks validate reference data, the HTTP foundation, a controlled LLM source-selection pilot and retrieval evidence coverage. Initial fixed-workflow evaluation is documented below, including provider failures. All ten questions are curated development cases; reserved-case performance remains unmeasured.

## How the application fits together

The target workflow is **question → retrieve report evidence → LLM selects cells and an operation → Python validates and calculates → result with sources**.

The backend lives in `app/` and runs as one local Python service. FastAPI handlers receive HTTP requests; corpus/index storage and retrieval already have shared modules. The shared analysis service now connects them to generation, validation and calculation. A browser page served by the same backend is planned for B09. Gemini runs remotely and is called by Python; its API key stays out of the browser.

Currently, the backend exposes only `/health`. The provider and source-selection checks run through command-line scripts using shared application modules. They are not yet connected to an analysis endpoint. Retrieval and fixed numerical analysis are available through the CLI; the analysis endpoint and browser interface remain planned. See the [architecture](docs/architecture/ARCHITECTURE.md) for the target design.

## Setup and run

Verified environment: **Windows, Python 3.14.5, uv 0.11.14**. Run commands from the repository root.

```powershell
python3.14.exe -m venv .venv --without-pip
uv sync --locked --no-build
uv run --locked python -B -X utf8 scripts/check_environment.py
uv run --locked python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`.venv/` isolates the project's Python interpreter and packages. It is separate from a `.env` configuration file; this project does not automatically load `.env` files. `uv run` uses the project environment without manual activation. In VS Code, select `.venv\Scripts\python.exe` as the interpreter.

`uv.lock` records resolved versions. `--locked` prevents implicit lockfile changes; `--no-build` uses prebuilt distributions. The first download requires internet access. The examples use PowerShell, the verified Windows shell; it launches the application and does not determine its architecture.

In the commands below, `python -m` runs a Python module, `-B` skips bytecode-cache files, and `-X utf8` selects UTF-8 text handling. `--live` is the provider scripts' explicit opt-in for real hosted requests; offline checks do not require it.

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

This explicit live command makes at most two model requests: a small JSON response and one text embedding. It uses a 20-second transport timeout, a 64-token generation ceiling and no automatic retries. The first failure stops the check. Without `--live`, it refuses to send requests. Local records go under the ignored `data/local/provider-checks/` directory. No billing settings are changed. [Observed free-tier quotas](docs/verification/B03_ACCOUNT_LIMITS.md) are recorded separately; actual charges remain unverified.

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

## Check a native tool call

The B03 compatibility command exposes one allowed `read_evidence` function for the supplied report:

```powershell
uv run --locked python -B -X utf8 -m scripts.check_tool_call --live
```

Gemini chooses cell IDs in a native function call. Python validates the name and arguments, then reads the original source values. The command makes at most one model request and one local read. It does not continue the conversation or run an agent loop. Observed: the correct Canada/total cells, values 60 and 243, and a 1.302-second model request. See the [verification and limits](docs/verification/B03_TOOL_CALL.md).

## Prepare the data

[FinQA](https://github.com/czyssrs/FinQA) supplies public text and tables with evaluation annotations. On a fresh checkout, download the raw file and generate separate exports:

```powershell
New-Item -ItemType Directory -Force -Path data/raw | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/dev.json' -OutFile data/raw/finqa-dev.json
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all
```

If the raw file already exists, keep it and run the export command. Its hash is checked before processing. A source change requires a provenance review.

Source exports contain only `filename`, `pre_text`, `post_text`, `table` and `table_ori`. Questions, answers, programs and annotated evidence remain in evaluation references. All ten cases are development cases. The original report PDFs have not been inspected.

## Prepare the corpus

The [pinned source selection](data/finqa-corpus-selection.json) includes the ten reviewed contexts and ten additional contexts. Build the source-only artifact and verify it without model requests:

```powershell
uv run --locked python -B -X utf8 -m scripts.prepare_corpus
uv run --locked python -B -X utf8 -m scripts.prepare_corpus --check
```

Verified output: 20 report contexts, 186 chunks and 243 cells. Original tables are authoritative; normalized dash-to-2014 conflicts are recorded separately and retain missing values. Chunks preserve headers and adjacent context, with links to full parent sources. Generated artifacts are ignored by Git. The completed SQLite/vector bundle is built in the next section; the service has not loaded it yet. See the [verification report](docs/verification/B04_CORPUS_PREPARATION.md).

## Build and verify the search bundle

After corpus preparation, configure `GEMINI_API_KEY` for the first live build:

```powershell
uv run --locked python -B -X utf8 -m scripts.build_index --live
uv run --locked python -B -X utf8 -m scripts.build_index --check
```

The builder embeds each distinct chunk input once, caches completed vectors and publishes SQLite/FTS5, a float32 matrix and a versioned manifest only after validation. The first build is paced and may take several minutes. Missing vectors require `--live`; `uv run --locked python -m scripts.build_index` rebuilds from cache without a key or hosted requests. Repeating `--live` also reuses existing vectors.

Verified: 186 aligned rows, 768 dimensions, 184 distinct inputs and a cached rebuild at 0.394 s internally with zero requests. A Windows progress-file interruption was fixed and resumed; its extra request is retained in the [build evidence](docs/verification/B04_INDEX_BUILD.md). Usage/charges remain unknown where unreported. Generated bundles, caches and journals are ignored by Git. Run one builder at a time and preserve `data/local/runs.sqlite`.

## Search and compare retrieval

After building the index, lexical search runs locally without a provider key:

```powershell
uv run --locked python -B -X utf8 -m scripts.search "What percentage of Devon production comes from Canada?" --k 5
uv run --locked python -B -X utf8 -m evals.retrieval
```

The CLI returns source excerpts, scores and cell IDs. Lexical search matches words using SQLite FTS5/BM25; semantic search compares a question embedding with the document vectors. Lower BM25 scores and higher cosine scores rank first. Repeated `--report-id` options apply explicit known report groups before top-k; otherwise the full corpus is searched.

For the ten-question semantic comparison, configure `GEMINI_API_KEY` and explicitly allow missing query embeddings once, then replay from cache:

```powershell
uv run --locked python -B -X utf8 -m evals.retrieval --mode compare --live
uv run --locked python -B -X utf8 -m evals.retrieval --mode compare
```

The first command plans at most ten missing query embeddings; document embeddings are reused. The second requires all query inputs cached and sends zero model requests. Add `--method semantic --live` to the search command for a new question; subsequent identical questions can omit `--live` and the key. Query vectors are cached separately in ignored `data/local/query-embeddings.sqlite`; all live calls retain the shared provider journal and allowance controls.

Measured on ten development questions over all 186 chunks: lexical recall@5 **95%**, complete proof **9/10**; semantic recall@5 **100%**, complete proof **10/10**, with a **0.423 s** median including live query embedding. Semantic at k=5 is the provisional B06 choice; lexical does better at k=3. Cached replay reproduced every ranking and score without requests. Complete proof means both operand cells are present, not that an answer is correct. See [comparison, difficult cases and limits](docs/verification/B05_RETRIEVAL.md) and [machine-readable evidence](docs/verification/B05_RETRIEVAL_RESULTS.json).

## Run a fixed analysis

The fixed workflow retrieves five candidate chunks, asks Gemini for two source cell IDs and an operation, validates source context, then calculates with Decimal. After the documented setup and cache creation, configure `GEMINI_API_KEY` and explicitly enable hosted requests:

```powershell
uv run --locked python -B -X utf8 -m scripts.analyze "In Devon's estimated 2008 production table, what percentage of total production in MMBoe comes from Canada?" --live
```

Each execution uses one retrieval and at most one generation; a new semantic question may also need an embedding. Use `--method lexical` for local word-based retrieval, or repeated `--report-id` options for explicit known report groups. Without `--live`, the command refuses requests. Results and evidence are saved in the `analyses` table of ignored `data/local/runs.sqlite`; provider requests retain the existing shared budget journal. Source cells, units/scales, explicit periods and positive denominators are checked. Unsupported or ambiguous context produces no numerical answer.

Current examples include **24.69%** for Canada's estimated production share and **−7.44%** for a signed revenue change. The initial ten-case campaign produced **5 correct answers, 1 conservative abstention and 4 provider HTTP 504s**; both negative checks returned the expected outcome. After removing exact duplicated source context, two bounded follow-ups succeeded in **15.1 s and 19.2 s**. These follow-ups do not replace the original failures or establish a full current-version score. Provider responsiveness and reliability remain limitations.

Run the initial evaluator explicitly with `uv run --locked python -B -X utf8 -m evals.analysis --live`; it plans at most twelve generations and requires the B05 query cache. Every rerun consumes quota and is recorded. See [workflow verification and supported formats](docs/verification/B06_FIXED_WORKFLOW.md) and [full measured evidence](docs/verification/B06_FIXED_WORKFLOW_RESULTS.json). The analysis API and browser interface remain planned.

## Run checks

After preparing the data:

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check app scripts/check_environment.py scripts/check_provider.py scripts/run_source_case.py scripts/check_tool_call.py scripts/prepare_corpus.py scripts/build_index.py tests/test_provider_connection.py tests/test_source_case.py tests/test_tool_call.py tests/test_corpus.py tests/test_index.py scripts/search.py evals/retrieval.py tests/test_retrieval.py scripts/analyze.py evals/analysis.py tests/test_analysis.py tests/test_analysis_evaluation.py
uv run --locked python -B -X utf8 scripts/inspect_finqa.py --case all --check
uv run --locked python -B -X utf8 -m unittest discover -s tests -v
```

Verified results: **10 valid cases and 3 passing negative tests**. The tests reject the wrong year, confusion between ratios and percentages, and answers leaked into source exports. The verifier rejects Python's `-O` mode because it disables assertions.

All **34 offline tests** pass. Fixed-analysis tests cover source arithmetic, units/periods/scales, accessible cells, outcomes, durable records and failure-aware scoring. Retrieval tests cover literal query handling, scope before top-k, cosine/cache behavior, invalid requests, evaluator separation and failure-aware metrics. Index checks cover cached rebuild/resume, file-lock recovery, pacing/restart history, cache corruption and mismatched SQLite/FTS/vector rows and configuration. Corpus checks cover source isolation, deduplication, original values/context, repeatable artifacts and rejection of inconsistent input/output. Native-tool tests also cover eleven response/execution cases and a simulated quota failure. The provider tests additionally simulate quota errors on both SDK endpoints and verify credential exclusion, retained unknown usage, source/plan boundaries, invented cells and a budget block before network access. Ruff checks lint across the codebase and formatting in the application, current preparation/provider/index/search/evaluation commands and their tests. FinQA verification also runs with the Python standard library alone. These checks are separate from live development retrieval/workflow evaluations and future reserved-case measurements.

## Repository layout

```text
app/                    HTTP, contracts, retrieval, fixed service, calculator, storage and Gemini
prompts/                Versioned model instructions
scripts/                Data preparation, search/analysis commands and provider checks
tests/                  Automated tests
evals/                  Question fixtures, separate references and retrieval/workflow evaluators
data/                   Pinned source selection, local sources, provenance and license notice
docs/architecture/      Design, contracts and technical decisions
docs/Backlog/           B01–B13 roadmap and reference cases
docs/verification/      Verification reports, results and limitations
```

Downloads, generated exports, execution records and `.venv/` are excluded from Git. Application modules are added with their first working feature.

Architecture, backlog, curated verification evidence and `AGENTS.md` are shared engineering documents. Keep personal notes and non-public documents in the ignored `private/` directory or `*.local.md` files. Generated document exports belong in ignored `output/` or `outputs/` directories; temporary work belongs in `tmp/` or `work/`. Ignore rules do not remove files already tracked by Git.

## Design principles

- **Evidence before calculation:** validate cell references, units and periods, then calculate deterministically.
- **Independent evaluation:** keep annotations and verification reports out of the inference corpus.
- **Measured comparisons:** compare lexical retrieval, semantic retrieval and a bounded agent under the same conditions.
- **Controlled execution:** enforce tool permissions and record call limits, costs, errors and versions.

Use clear, concise English for project documentation, diagrams, comments, diagnostics and GitHub issues. Preserve original source quotations and technical identifiers. Do not rewrite source evidence to improve its wording.

The B03 pilot uses Google's Gemini Developer API: `gemini-3.5-flash-lite` for generation and `gemini-embedding-2` for embeddings, starting on the free tier. See the [provider decision](docs/architecture/PROVIDER_SELECTION.md). Model access, SDK compatibility, the source-selection contract, one-case latency and the provider allowance journal are verified. [Free-tier project quotas](docs/verification/B03_ACCOUNT_LIMITS.md) are recorded from AI Studio. The [bounded native tool check](docs/verification/B03_TOOL_CALL.md) also passed. B03–B06 functionality is complete within documented limits; API integration and broader reliability checks remain planned.

## Next milestone

B01–B06 functionality is complete. Next, implement B07: report listing, analysis submission and saved-result lookup around the shared service. The browser interface and bounded agent follow later. Provider latency/timeouts and broader task quality still require measurement before release. The [backlog](docs/Backlog/BACKLOG.md) contains the acceptance criteria and dependencies.

## Documentation

- [Fixed workflow, domain limits and live results](docs/verification/B06_FIXED_WORKFLOW.md)
- [Retrieval comparison and difficult cases](docs/verification/B05_RETRIEVAL.md)
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
