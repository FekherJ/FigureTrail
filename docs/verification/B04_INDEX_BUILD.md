# B04 SQLite and embedding index verification

**25 October 2026. Complete source/index/vector bundle verified. B04 is complete; B05 is next.**

## Result

| Artifact or check | Observed result |
|---|---|
| Source contexts / report groups | 20 / 20 |
| Original source cells | 243; all 20 reviewed B01 operands preserved |
| SQLite chunks / FTS5 rows / matrix rows | 186 / 186 / 186 |
| Embeddings | `gemini-embedding-2`, 768 dimensions, float32 |
| Distinct cached inputs / duplicate rows reused | 184 / 2 |
| Matrix dimensions | 186 × 768 |
| Finite vectors / norm range | All finite; 0.999999424–1.000000576 |
| Provider requests / provider errors | 185 / 0 |
| Embedding request median / p95 | 0.412 s / 0.508 s |
| Cached rebuild | Same index version, zero requests, 186 cache hits; 0.394 s internal build time |
| Offline tests | 20 passed |

Corpus version: `32a94d8310f88e3987e833044c6131c808e4ac7da7391270aec098e59f062887`. Index version: `c0a8c69496f03a95e2049096228afaaec2f410547d14a384bc34b6e78f1225fb`. The ignored bundle under `data/corpus/indexes/<index_version>/` contains `corpus.sqlite`, `vectors.npy` and `manifest.json`. The [exact results](B04_INDEX_BUILD_RESULTS.json) record file/code/mapping hashes, timings and both live runs. The [earlier preparation snapshot](B04_CORPUS_PREPARATION.md) retains its original measurements; prepared data bytes are unchanged. Current-version pointers make the intended prepared artifact and index explicit.

## Requests, interruption and recovery

The initial campaign needed 184 distinct inputs for 186 chunks. Its first run completed 79 provider responses, but a Windows file-lock conflict interrupted a progress-file replacement. Reading that file during the build exposed the race. Seventy-eight vectors were already cached; the last returned vector had not yet been cached. All 79 requests remain in the provider journal.

The fix adds a bounded file-replacement retry (five attempts, at most 0.5 s of explicit backoff) and caches each returned vector before progress-file I/O. SDK/network retries remain disabled. Regression tests simulate a sharing violation and a persistent progress-save failure, proving that a returned vector survives for a later run. The resumed build reused the saved entries and made 106 requests for the remaining inputs. Total: **185 provider requests**, including the one response lost before the recording-order fix. The interruption and extra request are retained, not removed from counts.

The resumed live build took 305.485 s, including 256.708 s of deliberate pacing and local publication checks. The earlier interrupted run had its own pacing waits; the repair interval is not an end-to-end benchmark. A cached rebuild with an empty process API-key variable made zero requests and reproduced the exact same index in 0.394 s internally, excluding Python/SDK startup. This is index-build evidence, not interactive RAG latency.

All 185 embedding token-usage counters remain unknown because the Developer API response does not report them through this SDK path. Their EUR 0.01 reservations are retained. The cumulative local journal allowance is **EUR 1.9297150**, including earlier work, not a provider invoice. Actual charges remain unknown. The project was observed on the free tier; no billing settings changed. Current published text-embedding Standard pricing is USD 0.20/million input tokens, with free-tier access. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).

## Data, formatting and rate controls

Indexing reads only the validated prepared corpus. References, raw QA fields and normalization diagnostics are not ingested. Original source values, cell IDs and parent text are retained; all twenty reference operand values were compared separately after index construction.

Each embedding request contains exactly one formatted chunk: `title: none | text: ...`. The expected query prefix is `task: search result | query: ...`; it is recorded in the index configuration. This follows [Google's embedding guidance](https://ai.google.dev/gemini-api/docs/embeddings); multi-input aggregation is avoided. Requested model, dimensions, dtype and formatting participate in cache keys and index compatibility checks.

The single-builder limiter uses at most 80 requests and 24,000 conservative input allowances per rolling minute, seeded from recent journaled embedding attempts. UTF-8 byte count plus 64 is a pacing proxy, not measured tokens or a quota guarantee. Individual inputs must fit the 8,192 allowance ceiling. Observed account limits were 100 RPM / 30,000 input TPM / 1,000 RPD. Other account activity can affect capacity; a provider error stops the build and preserves the cache. No automatic network retry is used. [Observed account limits](B03_ACCOUNT_LIMITS.md).

## Integrity and reproducibility

The SQLite database holds source-only sources, cells, chunks and FTS5 text. The vector matrix uses the same chunk order. The manifest identifies the corpus version, model/configuration, exact row-to-chunk/input mapping, vector hashes, provider call/run IDs and file hashes. Duplicate text can reuse a vector while retaining separate source provenance.

Loading uses read-only SQLite and NumPy `allow_pickle=False`. It checks schema allowlists, SQLite integrity/foreign keys, regenerated source/cell/chunk records, FTS text/row alignment, matrix dtype/dimensions/finiteness/norms, per-row hashes and corpus/model compatibility. Tamper tests recompute file/manifest hashes before checking swapped vectors, NaN, wrong shape, mismatched FTS content, extra tables and wrong model configuration. Hashes establish consistency, not authenticity against a party that can rewrite all artifacts.

New bundles are staged inside the resolved index directory and published only after validation. Existing versions and the separate provider journal are preserved. Cached rebuilds require no key; missing vectors require explicit `--live`. The API still exposes only its HTTP foundation and reports `corpus_version: null`; it does not yet load or search this bundle.

```powershell
uv run --locked python -B -X utf8 -m scripts.prepare_corpus
uv run --locked python -B -X utf8 -m scripts.build_index --live
uv run --locked python -B -X utf8 -m scripts.build_index
uv run --locked python -B -X utf8 -m scripts.build_index --check
```

The first command prepares/discovers the source artifact. The second requests only missing vectors. The third rebuilds from cache without hosted requests; it refuses if vectors are missing. The fourth verifies the published bundle with no model calls. Do not run concurrent builders or reset the provider journal.

## Scope and next work

B04's four items are verified. 36 protected source/configuration/reference/result artifacts are unchanged, and all six earlier journal rows are preserved. A native FTS `canada` query confirms a usable inverted index; its hit count is a smoke check, not a relevance score. B05 must implement and measure lexical/semantic retrieval under explicit scope, without gold-selected filters. End-to-end calculation, analysis routes, UI and the bounded agent remain planned.
