# B04 corpus preparation verification

**25 October 2026. Historical offline-preparation snapshot: no model requests in this phase. B04 was subsequently completed; see the index-build report below.**

## Prepared output

| Item | Verified result |
|---|---:|
| Source contexts / report groups | 20 / 20 |
| Original data cells | 243 |
| Chunks | 186 |
| Selected raw entries | 64 |
| Repeated question copies collapsed | 44 |
| Recorded normalization differences | 179 |
| Numeric conflicts resolved using original cells | 8 |
| Reviewed B01 operand cells preserved | 20 / 20 |
| Offline tests passing | 14 |
| Model requests | 0 |

Corpus version: `32a94d8310f88e3987e833044c6131c808e4ac7da7391270aec098e59f062887`. The generated artifact is `data/corpus/prepared/32a94d8310f88e3987e833044c6131c808e4ac7da7391270aec098e59f062887.json`; the full normalization audit is stored separately under the ignored `data/local/corpus-preparation/` directory. The [exact verification results](B04_CORPUS_PREPARATION_RESULTS.json) record hashes, counts and conflict resolutions.

## Selection and provenance

The [source selection](../../data/finqa-corpus-selection.json) pins twenty filenames and the existing raw FinQA SHA-256. It includes all ten reviewed development contexts and ten additional contexts, with no per-question evidence filtering. Two previously identified distractors, `LMT/2015/page_56.pdf` and `UNP/2007/page_65.pdf`, are included. Remaining additions were selected deterministically by filename hash from distinct report groups, subject to the existing table-shape contract. Runtime preparation reads this source list and the pinned raw file, not reference answers or verification reports.

Two candidates were excluded explicitly: `AES/2017/page_157.pdf` and `RE/2017/page_159.pdf` have unsupported original/normalized table shapes. AES has a ragged, multi-row original header that does not align with the normalized table. The pipeline rejects these shapes rather than padding, flattening or inventing coordinates. This narrows the initial dataset; it is not a general PDF/table parser. The original PDFs were not reviewed. See the [FinQA provenance](../../data/FINQA_PROVENANCE.md) and retained [license](../../data/FINQA_LICENSE.txt).

## Transformation and boundaries

- Raw QA/retrieval fields are discarded through an explicit five-field allowlist before source validation. Repeated question entries collapse to one source; identical original contexts under different filenames also have a deterministic deduplication path.
- Original tables are authoritative. Both prepared `table` and `table_ori` contain the original values. The eight observed numeric conflicts were normalized `2014` values whose original cells are missing-value dashes. They remain dashes with `decimal_value: null`, never zero or 2014. Original strings, B01 files and historical measurements are unchanged.
- Source IDs remain filenames; report groups remain their company/year path groups. Cell IDs retain B03's zero-based `filename#table[row][column]` coordinates. No company, measurement period, unit or scale is inferred from a filename.
- Text chunks keep complete paragraphs, targeting 1,200 characters. Table-row chunks contain the original headers, row values, the last five pre-table paragraphs and first three post-table paragraphs. All parent text is retained in the source record and separate text chunks. This adjacency policy does not guarantee all semantic context appears in every row chunk; later retrieval/analysis must follow the parent reference where needed. The Canada row retains the 2008 production context and MMBoe units, despite the 2007 report path.
- Plain signed decimals, valid comma-grouped numbers and an explicit leading `$` are parsed conservatively. Parsing a visible dollar sign does not identify a currency or scale. Percentage signs, accounting parentheses and other unsupported forms retain their original text with an unknown decimal value. Full numerical/unit validation remains B06 work.
- The prepared artifact contains sources, cells, chunks and a versioned manifest. It excludes normalization diagnostics and evaluation references. Hashes, source contracts, exact regenerated cells/chunks and counts are validated on load. Unexpected annotation fields are rejected even if a fingerprint is recomputed. A hash is an integrity check, not an authenticity signature.
- Output is written to a temporary file and renamed within the resolved corpus directory. Existing valid versions are reused; inconsistent/corrupt existing versions are rejected rather than overwritten. `--check` verifies the existing artifact against fresh preparation without writing. The provider journal is untouched.

The longest observed chunk has 2048 characters, below the 6,000-character ceiling. There are no SQLite indexes, vectors, query embeddings or running-service corpus integration yet. `/health` still reports `corpus_version: null`.

## Reproduce

With the existing raw download and locked dependencies:

```powershell
uv run --locked python -B -X utf8 -m scripts.prepare_corpus
uv run --locked python -B -X utf8 -m scripts.prepare_corpus --check
```

Both commands produced the same corpus version and records. No evaluation file is loaded by the preparation command. A separate post-build verification compared all twenty B01 operand cells with the references; those references were not supplied to preparation or used to generate chunks.

All fourteen offline tests pass. New checks cover annotation exclusion, duplicate entries/contexts, original dash handling, preserved period/unit context, repeatable writes, tampering, wrong input hashes, missing/ambiguous sources, ragged tables, oversized content and unexpected annotation fields. Ruff lint passed. 45 protected input/code/prompt/reference/result/configuration artifacts, including `runs.sqlite`, are unchanged.

## Subsequent B04 completion

At this snapshot, source IDs and contextual chunks were complete while indexing remained pending. The subsequent [index build](B04_INDEX_BUILD.md) verified SQLite/FTS5, document vectors and the final mapping/manifest, completing B04. The original preparation JSON/code fingerprint and fourteen-test count remain historical; later pointer/file-write support changed the implementation without changing prepared data bytes. Prepared JSON remains an intermediate artifact rather than the complete search bundle.
