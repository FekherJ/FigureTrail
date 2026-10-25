# B03 provider connection verification

**Checked: 25 October 2026. Scope: authentication, SDK compatibility and two inference requests. B03 remains open.**

## Observed results

| Check | Result | Duration |
|---|---|---:|
| Generation model metadata | HTTP 200; `gemini-3.5-flash-lite`, version `3.5-flash-lite-07-2026` | 0.231 s |
| Embedding model metadata | HTTP 200; `gemini-embedding-2`, version `2` | 0.113 s |
| Structured generation | JSON Schema response validated by Pydantic: `{"status":"ready"}` | 1.015 s |
| Text embedding | Exactly one vector; 768 finite values; norm `1.000000458832834` | 0.376 s |

Python 3.14.5 and Google GenAI SDK **2.33.0** were used. The SDK and dependencies are resolved in `uv.lock`. These are single-request measurements. No report context, reference answer or private document was sent. The exact prompts and sanitized results are in the [result snapshot](B03_PROVIDER_CONNECTION_RESULTS.json).

Generation usage reported 17 input tokens, 6 candidate-output tokens and 23 total tokens; the thought-token field was absent and remains `null`. The SDK embedding response provided no token usage. Complete cost estimates and actual charges remain unknown. The published free tier covers the selected requests, but the account's billing tier and numeric quotas were not independently inspected. No billing settings were changed. [Published pricing](https://ai.google.dev/gemini-api/docs/pricing), [project-specific limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Reproduction and safeguards

Set `GEMINI_API_KEY` locally without putting its value in source control or a command. With dependencies installed:

```powershell
uv run --locked python -B -X utf8 -m scripts.check_provider --live
```

The check reads that variable explicitly. It does not load `.env` files. Without `--live`, no request is sent. The command makes at most two inference requests, stops on the first failure, limits generation to 64 output tokens and configures a 20-second transport timeout. It starts no further check after the 60-second elapsed-time gate. Transport timeouts are not a guaranteed end-to-end wall-clock deadline. No tools or automatic retries are enabled.

A run record is written before calls and updated under the ignored `data/local/provider-checks/` directory. Unavailable usage stays `null`; raw exceptions, HTTP bodies, keys and vectors are excluded. A recording failure stops further calls. This report describes the original connection snapshot. During the subsequent [source-case implementation](B03_SOURCE_CASE.md), shared calls moved into `app/llm.py` and acquired a cumulative SQLite allowance journal. The current command uses that module; the original snapshot is preserved.

The SDK's Interactions adapter translated retry counts differently from its other endpoints, including a mutation of zero attempts during client initialization. An offline test caught a repeated request. The connection check therefore uses the documented, model-supported `generateContent` and `embedContent` paths with one attempt. The retained test simulates HTTP 429 separately on both paths, verifies exactly one request for each failure, and checks that the saved record excludes a test credential. [Generation API](https://ai.google.dev/api/generate-content), [official SDK](https://github.com/googleapis/python-genai), [embedding guide](https://ai.google.dev/gemini-api/docs/embeddings).

```powershell
uv run --locked python -B -X utf8 -m unittest discover -s tests -p test_provider_connection.py -v
```

Observed: one passing test with two endpoint subcases; no network or real key required.

Regression verification also passed: locked offline synchronization (33 installed packages), Ruff lint, formatting of the five selected files, ten FinQA case checks and all four offline tests. No additional inference requests were used for these checks.

## Remaining B03 work

The subsequent [source-case pilot](B03_SOURCE_CASE.md) implemented the shared provider boundary, source selection, versions, SQLite allowances and three-call latency check. Numeric project quotas and tool-call compatibility remain pending. The connection response above does not establish RAG quality. See the [implementation log](IMPLEMENTATION_LOG.md) for commands and historical versus current behavior.
