# Fixed-workflow evaluation comparison

**Verified: 9 November 2026. B08 development baseline.**

The existing evaluator now plans and runs either fixed lexical or fixed semantic analysis through the same `app/service.py:analyze()` used by the API. Saved matched reports can be compared offline. No agent framework, external judge or new dependency is required.

## Protocol and results

Each variant runs the same ten reviewed development questions and two negative questions over the unchanged 20-context/186-chunk corpus at k=5. Report scope comes only from the query fixture, currently null/full corpus. The evaluator forwards only question and explicit scope to the service; expected answers/cells are read after every planned execution outcome exists. Both positives and negatives use the selected retrieval method. This differs from the original B06 evaluator, whose negative cases always used lexical search.

The `analysis-evaluation-v2` policy is recorded before requests: complete retrieved proof, ordered source cells, operation, finite value within each reference's absolute percentage-point tolerance (currently 0.000005), and known unit/scale/year checks are required for a correct answer. Source dates and financial interpretations remain subject to runtime guards and reviewed-cell identity; the new year metric is not a universal period-understanding test. Negative success requires the exact expected status and no calculation. Wrong answers, abstentions, technical failures and unattempted blocks remain in their respective denominators. No release-quality accuracy threshold is inferred from this small sample.

| Protocol / variant | Correct positives | Complete proof@5 | Correct negatives | Provider failures across 12 cases |
|---|---:|---:|---:|---:|
| Initial, lexical | 8/10 | 9/10 | 2/2 | 0 |
| Initial, semantic | 5/10 | 10/10 | 0/2 | 1 HTTP 503 + 5 HTTP 429 |
| Paced, lexical | 8/10 | 9/10 | 2/2 | 0 |
| Paced, semantic | 6/10 | 10/10 | 1/2 | 3 HTTP 503 |

The first batches were launched too close together without generation pacing. This was an execution error: embedding pacing alone did not protect the generation quota. Every original request/result is retained. Added journal-based generation pacing at 12 RPM, leaving headroom below the account's [observed 15 RPM quota](B03_ACCOUNT_LIMITS.md), and stop-on-429 behavior that blocks remaining cases without retries. Offline tests cover both safeguards before the new matched pair. Pacing is for one sequential evaluator campaign; it does not coordinate simultaneous processes or guarantee a current provider quota. No 429 occurred in the paced pair; 503 failures remain. Do not describe provider reliability as solved.

The initial and paced pairs have different evaluator hashes/protocols and are preserved separately. The offline comparator accepts matched inputs only: same cases/references, corpus/index, prompt, application identity, effective settings other than retrieval method, scoring policy, evaluator hash and pacing policy. It rejects mixing these protocols.

## Matched paced measurements

| Metric | Lexical | Semantic |
|---|---:|---:|
| Correct answers | 8/10 | 6/10 |
| Positive abstentions | 2 | 2 |
| Positive technical failures | 0 | 2 |
| Mean source-cell recall@5 | 95% | 100% |
| Median positive attempt, seconds | 1.109 | 1.602 |
| p95 positive attempt, seconds | 2.734 | 3.129 |
| Whole campaign, seconds | 15.360 | 40.790 |
| Generation pacing wait, seconds | 0.000 | 13.461 |

Attempt latency includes failed positive requests and excludes campaign pacing; p95 uses nearest rank and therefore equals the maximum with ten samples. Whole-campaign time includes waiting. Query embeddings were warm in the paced pair. Initial semantic preparation made two missing negative-query embeddings. These are single-pass development observations, not general responsiveness guarantees or proof of improvement over dated B06 timings.

Semantic retrieval improved proof coverage but did not improve end-to-end answers in this sample: the measured accuracy difference is -20 percentage points. Provider failures and unit-context limitations account for the observed gap; a sequential run with ten questions cannot establish a generally superior retriever. Keep lexical as a measured comparison; the existing semantic API default is unchanged and remains provisional. Do not cherry-pick successful semantic retries into the baseline.

## Detailed error analysis: C07

Question: percentage change in Lockheed Martin Space Systems operating profit from 2010 to 2011. Both retrievers returned complete proof and both model plans selected the reviewed cells:

- `LMT/2012/page_47.pdf#table[2][2]`: `1,063`, Operating profit, 2011.
- `LMT/2012/page_47.pdf#table[2][3]`: `1,030`, Operating profit, 2010.

The shared calculator returned `insufficient_evidence` / `ambiguous_unit` and no calculation because its supported unit-context extraction could not establish a unique unit. This is a domain-coverage limit after successful retrieval/selection, not an arithmetic error. The benchmark counts it as a missed positive. Do not assume dollars from company identity or use the reference unit as inference input. A future parser extension needs explicit source support and regression cases for nearby conflicting units/scales.

C06 supplies a separate reliability diagnostic: lexical succeeded and semantic received HTTP 503 even though their generation payload hashes match. This supports treating that failure as provider-related; it does not show semantic evidence was worse.

## Budget, provenance and preservation

This step made **48 generation requests and two query-embedding requests** across four twelve-case campaigns. All use the shared journal, one SDK attempt and configured limits. The local cumulative allowance is **EUR 15.5512000**, below the EUR25 local ceiling; it is conservative accounting, not confirmed spending. Failed requests with unknown usage keep their allowances. Known paid-cost estimates are partial upper estimates at the recorded prices; unknown total usage/cost and actual billing remain null. Cached historical embedding calls are not counted as new calls. No billing setting or allowance was reset. A further full campaign currently fails the worst-case allowance preflight; do not bypass it.

Original rows are preserved: 215 calls, 14 analyses and ten query embeddings. Current totals are 265 calls, 62 analyses and twelve query embeddings. Earlier raw reports, source/reference bytes, corpus/index/document-cache data and private materials remain intact. Full new reports are ignored local artifacts; [curated structured evidence](B08_WORKFLOW_EVALUATION_RESULTS.json) contains all four summaries, per-case outcomes, input identities, file hashes and the matched comparison.

## Reproduce

No model requests; read-only allowance plans:

```powershell
uv run --locked python -B -X utf8 -m evals.analysis --method lexical
uv run --locked python -B -X utf8 -m evals.analysis --method semantic
```

Explicit live operations, only when the printed worst-case plan fits the remaining allowance:

```powershell
uv run --locked python -B -X utf8 -m evals.analysis --method lexical --live
uv run --locked python -B -X utf8 -m evals.analysis --method semantic --live
```

Compare the existing paced reports without requests:

```powershell
uv run --locked python -B -X utf8 -m evals.analysis --compare-results evals/results/local/analysis/b4afb150-a07c-4643-b8a0-7edcd946a52b.json evals/results/local/analysis/947b3082-84ea-4483-9ce1-cf6c60b3bacd.json
```

The campaign command returns nonzero for technical failures/blocked cases; a zero exit code is not a claim that every answer was correct. Reference/case-identity errors fail scoring. Storage errors stop later analyses; report-write failures propagate before another call. SDK clients close on normal completion and setup/processing failures. Existing historical results are not rescored or migrated.

## Verification and remaining scope

All **72 offline tests pass in 13.702 s**, plus lint, 30-file formatting, ten-case data verification, corpus/index checks and key-free plans. Added ten evaluator tests beyond the original scoring test: false-positive scoring, nonfinite answers, negative identity, read-only plan/budget counts, source/reference separation, cleanup, mismatched comparisons, unknown usage/cost, storage stopping, quota stopping and pacing history. These use simulated providers and temporary journals; live results are reported separately above. The existing TestClient/httpx warning remains visible.

The preceding identity commit's [GitHub run](https://github.com/FekherJ/FigureTrail/actions/runs/42684643190) passes all 62 tests in 7.280 s. The new 72-test evaluator changes are locally verified and await user commit/push.

B08's initial development comparison is complete at the actual scope of ten positive and two negative cases. The optional 20-development/10-reserved expansion was not delivered; reserved-case performance is unmeasured. Prepare/review a report-disjoint reserved set before B13 final trials and never use it to tune variants. B09's evidence UI is the next planned feature; model-selected agent behavior remains B10. Source-format coverage and 503 reliability remain explicit limits.
