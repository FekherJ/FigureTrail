# B10 - Bounded native-tool agent

**23 November 2026: implementation and one-question paired live pilot verified; broader comparison pending. B10 stays in progress.**

## Implementation

`app/agent.py:run_agent()` uses `app/llm.py:agent_turn()` for one native decision at a time.

| Tool | Input | Code-enforced boundary |
|---|---|---|
| `search_evidence` | Query of 1-2000 characters | Original report scope/method; five hits per search. |
| `read_evidence` | One to five distinct retrieved chunk IDs | Only retrieved chunks and their original cells/context. |
| `calculate` | Operation and two distinct cell IDs | Only explicitly read evidence; original question and shared Decimal/unit/period checks. |

Limits: four generation calls, six tool calls, two searches, 22,000 serialized history characters and the existing 60-second deadline. With one action per turn, normally at most four tools are reached; six is an independent upper bound. Reject unknown tools, extra arguments, inaccessible evidence, parallel calls and numerical final text. Valid calculation ends the execution without another model call. Exact structured abstention is allowed. Validation errors may receive bounded model correction; budget, deadline, provider and recording failures stop work. Save actions/outcomes before further generation; storage failures propagate rather than allow untracked calls.

SDK Content, native IDs and opaque thought signatures remain in memory for continuation. Persist sanitized actions/call summaries, not private reasoning or raw SDK content. The existing sequential 12-RPM generation pacer now lives in `app/llm.py`; it is not cross-process reservation or a quota guarantee. Hidden retries and automatic SDK tool execution remain disabled.

Explicit `POST /analyses` with `mode: "agent"` and `scripts.analyze --mode agent --live` reuse this loop. Fixed semantic mode remains default. The browser form still submits fixed mode; saved agent lookup exposes events under technical details. No framework, dependency, model/provider switch or extra service was added.

## Commands and protocol

```powershell
# Read-only plans; no model key, client, cache/report creation or calls.
uv run --locked python -B -X utf8 -m evals.agent
uv run --locked python -B -X utf8 -m evals.agent --case-id C01

# Explicit live pair, only if its worst-case plan fits.
uv run --locked python -B -X utf8 -m evals.agent --case-id C01 --live
```

The default plans all ten development questions and currently exceeds the allowance. Each pair plans one fixed generation, at most four agent generations, two rewritten-query embeddings and any missing fixed query vector. Both modes receive the same original question, explicit scope and retriever. References open after execution. The existing scorer checks ordered cells, operation, finite answer/tolerance, units/scales and years. Fixed coverage uses configured top-k; agent coverage uses its union, at most ten chunks. This is a workflow comparison, not a same-k retrieval comparison. Report-write faults stop before another call; quota/budget faults block remaining work. Invalid plans are rejected before SDK initialization.

## Both live attempts retained

| Attempt | Fixed | Agent | Agent actions |
|---|---|---|---|
| Initial | Correct 24.69%, 1.352216 s | HTTP 504, 24.973209 s | Search -> read; third generation failed. |
| Explicit follow-up | Correct 24.69%, 3.185002 s | Correct 24.69%, 17.882660 s | Search -> revised search -> read -> calculate. |

Campaigns: `71869bee-f944-47cb-b755-c8aa58e33f92` and `75edec30-c85a-40f0-9e34-97953476de1e`. Protocol/application code were unchanged between attempts. The follow-up was a separate execution after a fresh plan, not an automatic retry or replacement for the failure. Fixed succeeded twice; agent succeeded once in two attempts on **one question**. This is not broad accuracy or evidence of agent benefit. Fixed stays default.

Successful agent execution: `5fcdb9df-d81f-4ca8-b44a-bbe3a4abb3e8`. Gemini chose four actions, including two searches, and source cells `DVN/2007/page_58.pdf#table[3][4]` / `DVN/2007/page_58.pdf#table[5][4]`. Python calculated `100 * 60 / 243`. [JSON evidence](B10_BOUNDED_AGENT_RESULTS.json) preserves both outcomes, actions, operands, timing, accounting and fingerprints. Local IDs refer to ignored journals, not records shipped in a fresh clone.

Nine generation requests and three embeddings were made. Conservative allowance rose from EUR 16.6120700 to EUR 17.7216200. The failed call retains EUR 1; unknown usage/charges remain unknown. These are allowances/estimates, not confirmed billing. The EUR 25 cap and spending policy were unchanged. No further live calls were made.

## Verification and remaining scope

Offline checks cover native SDK HTTP serialization/ID/signature continuation, success, abstention, rejected numerical prose, scope, unknown tools, unread cells, parallel calls, limits, cancellation, deadline/budget/provider/storage failures, API dispatch/lookup, read-only plans and paired scoring. Test network/model responses are simulated. All 88 offline tests pass in 23.665 s; lint, 34-file formatting, environment, ten source cases, prepared corpus and current index checks pass. All 67 existing analyses and 272 call rows retain their hashes; all 71 saved results validate without model calls. Sources/index/document cache, old measurement reports and private PDFs are preserved. The query cache, shared journal and private guide are intentionally updated. JSON evidence records the checks. Browser assets are unchanged; B09 browser checks were not rerun.

A regression check caught literal top-five scoring after generalizing the evaluator; it was corrected to preserve configured fixed top-k. Both live attempts used k=5 and retain their original scores/files. Historical measurements remain unchanged.

Broader comparison across distinct development cases remains open. A full ten-question worst-case campaign does not fit the remaining allowance. Do not bypass reservations or present repeated C01 as independent cases. Reserved validation, provider reliability, conservative source-format coverage, B11 adversarial checks and B12 observability remain open.

Native continuation was checked against the installed SDK and Google's [function-calling documentation](https://ai.google.dev/gemini-api/docs/function-calling) and [signature guidance](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/thinking/thought-signatures). The existing GenerateContent path remains; there is no Interactions migration.
