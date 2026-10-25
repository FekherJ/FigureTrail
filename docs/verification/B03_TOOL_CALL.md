# B03 native tool-call verification

**25 October 2026. One live request and one local evidence read passed. B03 is complete.**

## Result

Gemini returned a native `read_evidence` function call with these arguments:

```json
{"cell_ids": ["DVN/2007/page_58.pdf#table[3][4]", "DVN/2007/page_58.pdf#table[5][4]"]}
```

Python validated the function name and argument schema, then resolved original source values **60** (Canada) and **243** (Total), both under the `Total (MMBoe)` column. The selected cell set matches the reviewed reference. Expected references were read only after the request and local tool execution.

| Measurement | Observed value |
|---|---|
| Run ID | `4003b7f3-68ff-4330-9652-2a3e733ee4d5` |
| Model / SDK | `gemini-3.5-flash-lite` / Google GenAI 2.33.0 |
| Model requests / local tool executions | 1 / 1 |
| Model-request duration | 1.302 seconds |
| Local check duration | 1.337 seconds, excluding client setup and post-run evaluation |
| Input / output / total tokens | 2,250 / 62 / 2,312 |
| Thought-token count | Unknown; retained as `null` |
| Conservative paid-equivalent upper estimate | $0.00578; not an actual charge |
| Local allowance for this request | EUR 0.01156 |

The journal snapshot has **6 rows** and a cumulative allowance of **EUR 0.0797150**, including the opening allowance for pre-journal checks. This is not provider-billed spending. The [account screenshot](B03_ACCOUNT_LIMITS.md) shows the free tier; actual charges remain unverified. No billing settings changed.

See the [exact sanitized result](B03_TOOL_CALL_RESULTS.json) and [implementation log](IMPLEMENTATION_LOG.md).

## Implemented boundaries

- `app/llm.py` exposes one function declaration in `AUTO` mode, with automatic SDK function execution disabled. It accepts exactly one native call to the configured name and validates arguments with Pydantic. Tool-looking text, parallel calls and unknown names are rejected.
- `EvidenceRead` permits one or two distinct cell IDs and rejects extra fields. `SourceDocument.read_evidence` reads only numeric cells in the supplied original table; there is no dynamic function dispatch, shell execution, URL or file-path tool.
- The command makes at most one model request and one local read. It uses the existing cumulative journal, one SDK attempt, a 20-second transport timeout and a 256-token output ceiling. Strict wall-clock cancellation remains unverified.
- The only supplied report is an explicit feasibility context. This check does not perform retrieval, calculate a numerical answer, send a tool result back to Gemini, or establish a multi-step agent. Conversation continuation and repeated tool decisions belong to B10.
- The shared generation configuration preserves limits for existing structured-output calls. Earlier source-case JSON, prompts, data and health behavior were retained.

The native-call API follows the [official Python SDK example](https://github.com/googleapis/python-genai#manually-declare-and-invoke-a-function-for-function-calling). This implementation uses the already-tested `generate_content` endpoint, rather than the Interactions path whose retry behavior was previously rejected.

## Reproduce

After configuring `GEMINI_API_KEY` and preparing the source data:

```powershell
uv run --locked python -B -X utf8 -m scripts.check_tool_call --live
```

Without `--live`, the command refuses network requests. Local summaries are written under the ignored `data/local/tool-checks/` folder; provider records remain in `data/local/runs.sqlite`. Do not reset that journal to repeat a check.

## Offline verification and limits

All **nine offline tests** pass. The native-call tests cover eleven response/execution cases, including unknown tools, parallel calls, text pretending to be a call, extra arguments, wrong types, duplicate/excess IDs, truncation, another report and header cells. A simulated HTTP 429 produces one request, no tool execution and a retained unknown-usage allowance. Existing source, budget and credential guards also pass. Ruff lint and formatting pass.

The first offline run failed because the new test expected a camel-case JSON-schema key; SDK 2.33.0 emits `parameters_json_schema`. Correcting that test assumption resolved the failures before any live request. No provider code or validation boundary was relaxed for the test.

The live result covers one controlled example. It does not establish broader cell-selection accuracy, retrieval quality, capacity or multi-turn agent compatibility. B03's seven checklist items are verified; the next milestone is the annotation-free corpus in B04.
