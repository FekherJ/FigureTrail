# FinQA B01 data provenance

- Download and source review: 24 October 2026. English documentation update: 25 October 2026.
- Upstream: [czyssrs/FinQA](https://github.com/czyssrs/FinQA), accompanying **Chen et al., FinQA: A Dataset of Numerical Reasoning over Financial Data, EMNLP 2021**. [Paper](https://arxiv.org/abs/2109.00122).
- File: [dataset/dev.json](https://github.com/czyssrs/FinQA/blob/main/dataset/dev.json), 883 entries. Export only complete source contexts for the ten selected cases.
- Download URL: `https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/dev.json`.
- Git blob ID reported by GitHub: `970f239f591c782b17df420c0d343b780737f3da`.
- Downloaded SHA-256: `a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51`.
- Upstream `main` may change. The verifier rejects a different hash; review the source before updating the expected value.
- First detailed case: `DVN/2007/page_58.pdf-2`; `filename`: `DVN/2007/page_58.pdf`. This is a FinQA identifier, not a PDF stored here. The original PDF was not inspected.
- The repository publishes an MIT notice, copyright 2021 Zhiyu Chen. Retain the [complete notice](FINQA_LICENSE.txt), obtained from upstream [LICENSE](https://github.com/czyssrs/FinQA/blob/main/LICENSE), with relevant extracts. No complete financial-report PDF is redistributed here.

The raw file includes annotations and existing retrieval fields. It is ignored by Git and excluded from inference. Source exports allow only `filename`, `pre_text`, `post_text`, `table`, `table_ori`, retaining the whole context without gold-evidence filtering.

References in `evals/cases/` retain `question`, `answer`, `exe_ans`, `program`, `gold_inds`, case ID and the local `development` partition. The verifier never executes FinQA programs. This selection does not reserve final cases or measure retrieval quality.

## Second detailed case

`FBHS/2017/page_23.pdf-2`, context `FBHS/2017/page_23.pdf`, comes from the same download and notice. Exports: `data/samples/finqa-b01-growth-source.json` and `evals/cases/finqa-b01-growth-reference.json`. Only distributed text/tables were reviewed.

`FBHS/2017/page_23.pdf-1` shares the same source context. Deduplicate it before indexing and keep its questions in one report group when splitting evaluation cases. The two detailed examples come from different reports.

## Ten-case verification

Ten development contexts were checked through AI-assisted source review and deterministic calculation on 24 October 2026. See the [B01 report](../docs/verification/B01_DATA_VERIFICATION.md). The [review manifest](../evals/cases/finqa-b01-reviewed.json) records IDs, adapted questions, units, periods, cells, expected results and `exe_ans` conventions. All ten original reference exports remain unchanged.

The duplicate audit hashes source fields excluding `filename` and groups reports by company/year. Selected cases have ten distinct contexts and report groups. Three distractor candidates were identified at B01; their later preparation status is recorded below. Exact matches are recorded in [verification results](../docs/verification/B01_VERIFICATION_RESULTS.json). Exclude both `docs/verification/` and `evals/` from inference ingestion.

## B04 prepared corpus

The [source-only selection](finqa-corpus-selection.json) pins twenty filenames and the same raw-file hash. It includes the ten B01 contexts plus ten additional contexts from distinct report groups. Two prior distractors (LMT/2015/page_56 and UNP/2007/page_65) are included; AES/2017/page_157 is excluded because its original multi-row header does not fit the current rectangular coordinate model. RE/2017/page_159 was also excluded during additional-source selection for an unsupported table shape. No original table was flattened or padded.

The [B04 report](../docs/verification/B04_CORPUS_PREPARATION.md) records exact preparation, normalization policy and exclusions. Canonical inference tables retain original values in both table fields; original B01 exports remain unchanged. Normalization diagnostics and evaluation references are excluded from the prepared artifact. Preparation does not load evals or verification reports. All sources still come from FinQA's development file; no final evaluation split is established here.
