# B05 — Evidence retrieval verification

**Verified locally on 26 October 2026. B05 complete; B06 has not started.**

## Outcome and decision

Both retrievers search the same 20-context, 186-chunk corpus, including distractors. A chunk is a source excerpt: a text segment or a table row with its surrounding context. Search returns ranked excerpts with scores, source IDs and original cell IDs; it does not answer or calculate.

Use **semantic retrieval at k=5 provisionally for B06**: both required cells were found for 10/10 development questions, versus 9/10 with lexical retrieval. Keep lexical search as the free, local comparison baseline. The inspection CLI defaults to lexical; semantic mode is explicit. No automatic fallback is implemented.

This is development evidence, not a general RAG accuracy claim. The LLM has not yet selected cells from these retrieved candidates, and the runtime calculator is still planned.

## Measured comparison

`k` is the maximum number of returned chunks. Evidence recall is the fraction of required operand cell IDs recovered. Complete proof requires both cells in the union of those chunks. Each case requires two cells; there are 20 required cells overall. Duplicate cells do not increase recall. Failed retrievals receive zero evidence and remain in the denominator.

| Method | Recall@1 | Complete@1 | Recall@3 | Complete@3 | Recall@5 | Complete@5 |
|---|---:|---:|---:|---:|---:|---:|
| Lexical, FTS5/BM25 | 40% | 2/10 | 90% | 8/10 | 95% | 9/10 |
| Semantic, cosine | 35% | 2/10 | 80% | 7/10 | 100% | 10/10 |

There were zero technical retrieval failures in each method's ten trials. A technically successful search can still miss evidence; `status: passed` is not a quality threshold. Lexical retrieval performed better at k=3. Five candidates and the 1/3/5 reporting points were fixed before the first measurement; no ranking, chunking or query changes followed the results.

| Timing, one comparison campaign | Lexical median | Semantic median |
|---|---:|---:|
| Total search, first query-embedding pass | 0.003737 s | 0.423049 s |
| Ranking engine within that search | 0.003703 s | 0.000806 s |
| Total search, cached replay | 0.002488 s | 0.001247 s |

Index validation/loading is timed separately in the JSON. Semantic engine time excludes the query-embedding/cache step; total time includes it. Lexical engine time includes validation, query preparation and SQLite search. These are local single-campaign observations, not a throughput benchmark or service guarantee. Cached results require the same question and embedding configuration.

## Inputs and evaluation boundary

- Corpus: `32a94d8310f88e3987e833044c6131c808e4ac7da7391270aec098e59f062887`.
- Index: `c0a8c69496f03a95e2049096228afaaec2f410547d14a384bc34b6e78f1225fb`.
- Question-only fixture: [finqa-b05.json](../../evals/queries/finqa-b05.json), ten application questions copied from the reviewed development references before search. All have `report_ids: null`; all 186 chunks are eligible.
- [Evaluator](../../evals/retrieval.py) forwards only question and explicit scope as content/filter inputs, plus method/k/run bookkeeping. It persists candidates before loading references for scoring. Reference IDs never select a document. Question/reference correspondence is checked after retrieval.
- [Retriever](../../app/retrieval.py) uses the existing validated index loader and returns inspectable source text and cell IDs. Explicit report scope is validated and applied before top-k in both modes.

The curated questions include company and period wording. They are not unseen benchmark queries. Source PDFs were not inspected; these checks use supplied FinQA text and original tables. Required cell coverage does not validate units, periods, operand ordering, final calculation or abstention.

## Ranking and query handling

Lexical search converts up to 64 unique Unicode words into quoted literal terms joined with OR, removing a fixed generic stop-word list. It uses parameterized SQLite queries, read-only connections and FTS5 BM25. Lower BM25 scores are better in SQLite. User text cannot supply FTS operators or SQL. This follows [SQLite's BM25 score convention](https://sqlite.org/fts5.html#the_bm25_function), checked 26 October.

Semantic search embeds `task: search result | query: {question}` with `gemini-embedding-2` at 768 dimensions. Document inputs retain B04's `title: none | text: {content}` prefix. These follow [Google's retrieval formatting](https://ai.google.dev/gemini-api/docs/embeddings), checked 26 October. Existing cache checks validate configuration and vector integrity. Ranking normalizes document/query vectors in float64 and uses exact NumPy cosine similarity. Higher scores are better. Both methods break ties by corpus order. Scores from the two methods are not interchangeable or calibrated confidence values.

An exact scan is sufficient for 186 chunks; no vector service, approximate index, reranker or new dependency is needed. Semantic search can return neighbors even for an unrelated question; absence and safe abstention need later workflow checks.

## Difficult cases inspected

**C03 — PKG purchase commitments after 2014.** The required cells are `PKG/2009/page_65.pdf#table[6][1]` (Thereafter, 25,048) and `#table[7][1]` (Total, 44,572). Lexical search ranked the 2014 row first (-12.220313), Total second (-11.431406), and Thereafter seventh (-11.021674), outside the primary budget. The year token matches 2014 directly, while “after 2014” and “Thereafter” have no lexical synonym expansion. Several other rows tie at -11.021674 because they share table context; corpus order places Thereafter later. Semantic search ranked Thereafter third (0.760759) and Total fourth (0.751332). At k=5, recall is 1/2 for lexical and 2/2 for semantic. The rank-seven inspection used cache-only k=20 after measurement; it did not alter the primary result.

**C08 — Masco reported operating profit, 2017 to 2018.** Both required cells are in `MAS/2018/page_35.pdf#table-row[1]`: 1,211 and 1,194. Lexical search ranked that row first (-16.501158). Semantic search instead ranked narrative about profit margins first (0.746402), adjusted profit second (0.713025), and the required reported-profit row fourth (0.712075). At k=3, semantic retrieval recovers neither cell; k=5 recovers both. This shows why semantic similarity alone cannot distinguish reported profit from related margins or adjusted profit. B06 must validate the selected cells and calculation context.

Full ranked candidates, exact scores, missing IDs, per-case metrics, configuration/code/reference hashes and diagnostic rankings are retained in [B05_RETRIEVAL_RESULTS.json](B05_RETRIEVAL_RESULTS.json).

## Requests, costs and replay

The live campaign made exactly **10 query-embedding requests**, zero generation requests and zero document-embedding requests through `app/llm.py`. All ten succeeded with SDK retries disabled. The separate ignored `data/local/query-embeddings.sqlite` now has ten cached inputs; the B04 document cache is unchanged.

The shared journal grew from 191 to 201 rows; all previous record JSON values are unchanged. Ten €0.01 reservations increased the cumulative local allowance from €1.9297150 to **€2.0297150**, below the €25 local limit. Embedding token usage, paid-cost estimates and actual charges remain null where unreported. Google lists text embeddings free on the free tier and $0.20 per million text tokens on the standard paid tier, checked 26 October; see [official pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-embedding-2). No billing setting was changed; allowances are not confirmed expenses or a provider billing cap.

The cached comparison ran without a process API key. All ten semantic inputs were cache hits, with identical ranked hits/scores and evidence metrics; no journal rows were added. The 86-file protected baseline was unchanged before documentation updates, including the original references, raw data, B04 bundles/document cache and lockfile.

## Reproduce

Prepare the source corpus and build the index as documented in [README](../../README.md). Run local lexical search and its evaluation:

```powershell
uv run --locked python -B -X utf8 -m scripts.search "For PKG, what percentage of purchase commitments is due after 2014?" --k 5
uv run --locked python -B -X utf8 -m evals.retrieval
```

Configure `GEMINI_API_KEY` for missing query embeddings, then opt in once:

```powershell
uv run --locked python -B -X utf8 -m evals.retrieval --mode compare --live
uv run --locked python -B -X utf8 -m evals.retrieval --mode compare
```

The second command is cache-only and requires no key once all ten inputs are cached. Without `--live`, missing query embeddings fail before any SDK request. Search accepts `--method semantic`, `--live` and repeated `--report-id` options for explicit known report groups. An uncached rephrasing needs its own embedding. Local run reports are ignored under `evals/results/local/retrieval/`; provider requests remain in the shared journal.

Recorded runs: lexical `892f39fe-2436-416f-8b05-cf30e9094b2c`; live comparison `92967e42-d301-4ef8-b8c8-0da7b25acbe5`; cached comparison `de139387-f8cd-4b8f-ac47-328bab6df6f1`.

Ruff lint/format and **26 offline tests** passed. Six new tests cover literal query handling/read-only search, ranking/scope before top-k, cosine/prefix/cache reuse, validation before calls, evaluator separation and failure-aware evidence metrics. Their vectors are simulated; the ten-query comparison above uses the real hosted embedding model. No dependencies changed.

## Remaining work

B06 will connect retrieval to one structured generation, validate accessible source cells and calculate with Decimal. The HTTP API still exposes only `/health`, with `corpus_version: null`; it has not loaded the index. End-to-end numerical accuracy, reserved-case performance, agent behavior and complete analysis tracing remain unmeasured.
