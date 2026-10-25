# B03 controlled source-case verification

**25 October 2026. Four live generation requests: three repetitions of one ratio question and one missing-period question. Original source-case snapshot; B03 was subsequently completed.**

## Result

Gemini selected `ratio_percent` and the reviewed cells in all three repetitions:

| Role | Source cell | Value resolved by Python | Header |
|---|---|---:|---|
| Numerator | `DVN/2007/page_58.pdf#table[3][4]` | 60 | Total (MMBoe) |
| Denominator | `DVN/2007/page_58.pdf#table[5][4]` | 243 | Total (MMBoe) |

Generation durations were **1.056, 0.950 and 0.876 seconds**, with a **0.950-second median**, below the five-second pilot target. All three requests returned a valid schema and matched the independently reviewed operation and ordered cell references. These are repetitions of one development example, not three independent evaluation cases.

For “What percentage of total actual production in MMBoe came from Canada in 2035?”, the model returned `insufficient_evidence`, `operation: null` and an empty cell list in **0.961 seconds**. The supplied context describes estimates for 2008 and does not supply the requested 2035 production. This is one observed abstention within a controlled context, not a guarantee about other questions or a complete corpus.

See the [exact results](B03_SOURCE_CASE_RESULTS.json) and [implementation log with commands](IMPLEMENTATION_LOG.md).

## Implemented boundaries

- `app/llm.py` owns all SDK request paths, explicit key lookup, model IDs, request limits, token metadata and sanitized errors. Both commands use this module.
- `app/schemas.py` rejects annotation fields in source input and validates the output state, operation and two distinct cell IDs. Code resolves IDs only within the supplied original table and requires finite decimal source values.
- `prompts/cell_selection.md` is versioned and hashed. The model returns references, without a numerical answer or generated operands.
- The model request includes the original table, headers, cell IDs and full accompanying text. The evaluator reads expected operation/cell references only after the model requests. No answers, programs, gold coordinates or verification reports are sent.
- The pilot uses `table_ori` explicitly; it does not modify either source table. This avoids using the known normalized dash/`2014` conflict in this pilot. Corpus-wide conflict handling remains B04 work.

No retrieval occurs: the source document is deliberately supplied for this feasibility check. The application calculator, full unit/period validation, API analysis routes and agent remain unimplemented. Existing numeric IDs and valid JSON alone do not establish semantic correctness on other questions.

## Usage, spending and records

The four requests reported **9,631 total tokens**. Thought-token counters were absent and remain `null`. A conservative paid-equivalent upper estimate prices every reported token at $2.50/million: **$0.0240775**, rather than treating this as an actual charge. [Dated provider prices](https://ai.google.dev/gemini-api/docs/pricing).

The local SQLite journal contains four call records plus a **€0.02 opening allowance** for the two earlier connection requests. The combined local allowance is **€0.0681550**, not provider-billed spending. Actual charges and the account's billing tier were unverified at the time of these requests; billing settings were not changed. A later [AI Studio screenshot](B03_ACCOUNT_LIMITS.md) shows the free tier and project quotas, without changing this historical snapshot.

Before each request, the journal atomically reserves €1 for generation or €0.01 for a text embedding against a **€25 local limit**. The generation reservation covers the published model token ceilings at the dated rates with a planning buffer of €2/USD. This factor is a conservative assumption, not a market exchange rate. Known usage can reduce an allowance; unavailable usage retains the reservation. Rows marked `started` after interruption also retain it. Recording failure prevents further untracked requests. Local limits cannot guarantee provider billing, tax or currency conversion.

Records include `run_id`, `call_id`, requested/returned model, SDK version, prompt/code/source/input hashes, duration, usage, dated estimate, allowance and outcome. The local database is `data/local/runs.sqlite`; generated pilot summaries are under `data/local/source-case-pilots/`. These paths are ignored by Git. The published snapshot contains public questions and sanitized metadata, with no key, raw exceptions or private chain of thought.

## Verification and remaining work

Offline checks cover annotation leakage, invalid outcome combinations, invented cell IDs, one request per simulated quota failure, retained unknown-usage allowances and a budget block before any network call. Seven tests pass, including the existing three data-verification guards.

Ruff lint/format, lockfile and Git whitespace checks passed. Documentation checks validated 98 local links; 22 protected data/reference/license files were unchanged. All four measured inputs and their code/prompt hashes were reconstructed from the pilot files without provider requests.

The recorded code fingerprint belongs to the pilot revision, available in commit `f3be9ea`. A later comments-only review changed file bytes while preserving the Python syntax trees and all non-comment tokens. Historical request hashes and measurements remain unchanged; a new execution will record the current code fingerprint.

The [provider decision](../architecture/PROVIDER_SELECTION.md) now passes its three-request source-case latency gate. Actual project quotas are now recorded in the [account-limit evidence](B03_ACCOUNT_LIMITS.md). The subsequent [native tool check](B03_TOOL_CALL.md) passed and completed B03. Its provider/source-reader changes are separate from this historical pilot revision. Full RAG quality, numerical answer accuracy, general abstention behavior, strict wall-clock cancellation and complete API execution records require later work.
