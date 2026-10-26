# B06 — Fixed workflow verification

**Functionality verified on 26 October 2026. Initial latency/reliability limitations remain open.**

## Implemented behavior

The shared [analysis service](../../app/service.py) executes one retrieval, at most one structured generation, source validation and a [Decimal calculation](../../app/calculator.py). The model selects only an operation and two listed cell IDs. Code reads source values and produces the formula, operands, percentage, display value and evidence. No generated code, SQL, free-form numerical operands or model-generated answer is executed.

The CLI uses the same service as the initial evaluator. Semantic retrieval at k=5 is the default; explicit report scope precedes retrieval. The complete twenty-context/186-chunk corpus is used in all measured trials. The API remains health-only: this is a working command-line workflow, not the B07 analysis API or B09 interface.

## Initial campaign, retained without replacement

The first configuration, `fixed-analysis-v1`, ran ten development questions plus two negative checks. Its ten answerable cases produced **5 correct answers, 1 conservative abstention and 4 provider HTTP 504 failures**. All five returned answers had the reviewed operation, ordered cell IDs and numerical value within the B01 tolerance. The median across all ten executions, including failures, was **18.175062 seconds**.

| Case | Outcome | Result or reason | Total seconds |
|---|---|---|---:|
| C01 | failed | provider_http_504 | 19.398 |
| C02 | failed | provider_http_504 | 19.552 |
| C03 | failed | provider_http_504 | 19.241 |
| C04 | success | 14.34 % | 16.192 |
| C05 | success | 35.84 % | 12.855 |
| C06 | success | 4.39 % | 15.730 |
| C07 | insufficient_evidence | ambiguous_unit | 18.452 |
| C08 | success | 1.42 % | 17.899 |
| C09 | success | 5.50 % | 16.834 |
| C10 | failed | provider_http_504 | 19.552 |
| N01 | insufficient_evidence | model_abstention | 18.110 |
| N02 | unsupported_request | model_abstention | 17.461 |

The missing-2035-period and unsupported-CAGR checks returned their expected non-answer states: **2/2**. These are two observed checks, not a general abstention or prompt-injection score. Schema validation, reference integrity and correct arithmetic cannot alone establish semantic correctness.

The C07 abstention was enforced by code: the selected operating-profit cells have no dollar marker, while their supplied header/context establishes only “in millions.” The validator does not infer a currency from unrelated rows. The unreturned C03 schedule also exceeds the current period/currency rules; its observed outcome in this campaign remains a provider timeout, not a retroactively assigned domain abstention.

## Bounded follow-up and current version

Inspection found repeated table context in the five retrieved row chunks. `fixed-analysis-v2` removes exact repeated text lines **within each source** from the model payload, while retaining every candidate cell, source ID and unique source line. Original retrieval results remain unchanged for validation and traces. No parent source, gold evidence or additional cells are added. Decimal context is now constructed explicitly at 28 significant digits with internal ROUND_HALF_EVEN and separate two-decimal ROUND_HALF_UP display rounding.

Two explicitly bounded follow-up executions used the current code:

| Case | Original → compact payload characters | Correct result | Total seconds |
|---|---:|---:|---:|
| C01, Canada production share | 6,965 → 4,313 | 24.69% | 15.122317 |
| C10, signed net-revenue change | 10,064 → 3,640 | −7.44% | 19.213437 |

Both completed with the reviewed cells and correct values. C01 resolves Canada 60 and Total 243 MMBoe, estimated 2008, and calculates `100 * 60 / 243`. C10 resolves 2016 revenue 1,542 and 2015 revenue 1,666, then calculates `100 * (1542 - 1666) / 1666`. Its negative sign is preserved.

These two follow-ups do not replace the initial failures or establish a new ten-case score. The full twelve-case campaign has not been repeated on v2. Provider variability and the small sample prevent attributing a reliability improvement to compaction. **15–19 seconds remains slow for an interactive demonstration.** Investigate latency and 504s before making a responsiveness claim; B08 will broaden workflow comparisons.

## Explicit domain boundaries

- Exactly two listed cells from one source table. Cross-source calculations are unsupported. Unknown/unretrieved IDs fail; missing or unsupported numeric text produces no answer.
- Original source strings are parsed conservatively; a dash remains missing. Parenthesized negatives, percentages as operands, currency conversion and implicit totals are outside this initial parser.
- Recognized physical headers include MMBoe, MMBbls, Bcf and square feet. Dollar units require a marker on the selected value or an explicit dollar header/near-table statement. `$` is not relabeled as a specific national currency. Scales must agree; code never silently converts them.
- Periods come from a single year/date in a column or row, a direct production-estimate statement, or an explicit “as of” date in retrieved context. The question must state matching years; explicit dates and actual-versus-estimate wording are checked. Missing/ambiguous periods are refused. Complex schedules such as Thereafter/Total are not reconstructed.
- Ratio operands require the same period context. Change operands require the same normalized metric label and chronological new/old years. Denominators and old values must be strictly positive.

These are bounded source-format checks, not a universal financial-document interpreter. The model still determines relevance, requested operation and scope within the question; reserved-case and adversarial performance remain unmeasured.

## Outcomes, records and limits

Results distinguish `success`, `insufficient_evidence`, `unsupported_request`, `blocked` and `failed`. Every accepted execution gets a run ID. A new `analyses` table in ignored `data/local/runs.sqlite` saves initial state, retrieved candidates, structured selection, source evidence, versions, result/errors and duration. SDK requests continue through `app/llm.py` and its existing `calls` table. Network calls occur outside database transactions. Recording failures propagate and stop further paid work; no failed trace is presented as a saved success.

The workflow checks a 60-second deadline and passes remaining time to generation, whose transport limit is at most 20 seconds. Cached semantic inputs require no embedding request. New CLI questions may need one embedding; pacing/transport can consume time before the post-retrieval deadline check. Strict wall-clock cancellation across that stage remains unverified. There are no automatic network retries or fallback models.

Across the initial and follow-up campaigns: **14 generation requests, 0 embedding requests, 10 successful provider responses and 4 HTTP 504s**. “Successful provider response” includes model abstentions; it is distinct from an answered question. Four failed calls have unknown usage and retain their €1 reservations. The journal grows from 201 to 215 rows, with all prior JSON records intact. Fourteen analyses are saved; their records contain no evaluator answers. The cumulative local allowance is **€6.1633250**, starting at €2.0297150. This is conservative accounting, not confirmed spending. Actual charges remain unknown, and billing was not changed.

Prices were rechecked on 26 October: Gemini 3.5 Flash-Lite standard paid input $0.30/million tokens and output $2.50/million, with free-tier availability listed. The existing provider uses a conservative all-tokens-at-output-rate upper estimate plus its planning buffer. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite). Structured outputs still require semantic validation: [Google guidance](https://ai.google.dev/gemini-api/docs/structured-output). Decimal arithmetic and context/rounding follow [Python 3.14 documentation](https://docs.python.org/3.14/library/decimal.html).

## Reproduce and inspect

After README setup, source preparation and B04/B05 cache creation, configure the local key and explicitly permit hosted requests:

```powershell
uv run --locked python -B -X utf8 -m scripts.analyze "In Devon's estimated 2008 production table, what percentage of total production in MMBoe comes from Canada?" --live
uv run --locked python -B -X utf8 -m evals.analysis --live
```

The first command permits one generation and, only if missing, a query embedding. `--method lexical` avoids the embedding; repeated `--report-id` options constrain known reports explicitly. Omitting `--live` refuses requests. The evaluator plans at most twelve generations and requires B05's cached questions; it uses semantic retrieval on the ten development cases and lexical retrieval on the two negative checks. Every explicit rerun counts against the same cumulative journal; it is not a cache-only replay.

Only the evaluator opens reference answers, after executions finish. Failed/abstaining answerable cases remain in its ten-case denominator. Scores require the correct operation, ordered cells and value tolerance. Reports are ignored under `evals/results/local/analysis/`. The initial campaign ID is `e3649473-c2ea-42f2-a965-a04a18cf0cf9`; the two follow-up execution IDs and full evidence are in [B06_FIXED_WORKFLOW_RESULTS.json](B06_FIXED_WORKFLOW_RESULTS.json). Results retain code, prompt, corpus, index and configuration fingerprints.

All **34 offline tests** and Ruff lint/format pass. Eight new tests cover arithmetic, context boundaries, accessible evidence, outcomes, one-call orchestration, recording/deadline stops and failure-aware scoring. A test-owned SQLite connection initially prevented Windows cleanup, and a scale fixture lacked period context; both fixtures were corrected without weakening runtime checks. No dependency changed. All 95 protected baseline files were unchanged before current-document updates, including references, prior measured JSON, raw data, both embedding caches, index bundles, lockfile and the private explanatory PDF.

B06 functionality is verified within these limits. B07 is next: expose the shared service through documented analysis/report/lookup endpoints. Reliability work and broader evaluation remain necessary before a release claim.
