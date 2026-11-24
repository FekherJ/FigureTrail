# B10 - Selected-case comparison and table previews

**Live measurement: 23 November 2026. Report and preservation review: 24 November 2026. B10 remains In progress.**

## Published baseline

The user's commit `d1434b1db9609998529617acd4c8490ac9af7f03` passed [GitHub CI](https://github.com/FekherJ/FigureTrail/actions/runs/45240820878), job `137924659753`: all steps succeeded, 88 tests in 7.087 seconds. The checkout was clean before this follow-up. The original [C01 pilot](B10_BOUNDED_AGENT.md) and its measured JSON remain unchanged.

## Declared protocol and actual scope

The [protocol](B10_COMPARISON_PROTOCOL.json) was saved before new live calls. Candidate order: C02 (monetary growth), C07 (known ambiguous-unit case), C10 (signed decline). These were conditional, separate one-case pilots, not a guaranteed three-case batch. Each required a fresh EUR 5.02 worst-case preflight and at least EUR 2.25 headroom after that reservation. Stop after a failed/blocked mode, recording fault or insufficient headroom. No retries or prompt/code changes were allowed within the live measurement.

Only C02 ran. Both modes used the same original question, full-corpus semantic retriever, source/index versions and application code. Gold references opened only after execution. C07 and C10 were not attempted because the agent received HTTP 504. They are not counted as completed cases or independent observations. No reserved or new live negative cases ran.

## Retained result

| Mode | Outcome | Duration | New calls |
|---|---|---:|---|
| Fixed | Correct 2.89% | 1.623226 s | 1 generation |
| Agent | HTTP 504; no answer | 23.362420 s | 3 generations, 2 embeddings |

The source calculation is `100 * (2467.1 - 2397.8) / 2397.8`, using original Cabinets sales for 2017/2016. The agent retrieved the required row at rank one, searched again and then failed on its third model request before reading/calculating. Required evidence was present; this failure is a provider failure, not a demonstrated retrieval miss or arithmetic error.

Campaign: `87ecf882-bb54-4c46-bb38-690b7c94c142`. Fixed execution: `e17f653c-91f3-494d-bc18-e5e6fe1d373b`. Agent execution: `397f7ea6-fed2-4f18-be88-1ae5e4386caa`. [Structured evidence](B10_COMPARISON_RESULTS.json) records the failure, cells, actions, versions, timing and unknown costs. Local journals are ignored and are not distributed with a fresh clone.

Together with the earlier C01 trials, there are three paired attempts across two distinct development questions: fixed succeeds three times; agent succeeds once. This selected, tiny sample does not establish general superiority or independent accuracy. Fixed remains default; broader comparison is incomplete.

Four generations and two embeddings were added. Conservative local allowance increased from EUR 17.7216200 to EUR 18.7633500, leaving EUR 6.2366500 under the EUR 25 cap. These are allowances/estimates, not verified billing. The failed request retains EUR 1 and unknown usage remains unknown. A further EUR 5.02 pair would leave EUR 1.2166500, below this protocol's EUR 2.25 headroom. No further live calls or budget changes occurred.

## Observed preview problem and offline correction

Different table-row candidates all displayed the same first 200 characters of parent introduction. Consequently the search tool did not show which row each candidate represented, even when the right row ranked first.

After the failed measurement, `app/agent.py` was changed to `bounded-agent-v2`: search output adds `kind` and previews original `Columns:` / `Row` lines for table rows, capped at 400 characters. Text previews remain capped at 200. Search/ranking, source data, prompt, scope, read permissions, calculator and call limits are unchanged. Previewed numbers still grant no calculation permission: an explicit permitted read is required.

The new regression first failed because “Canada” was absent behind repeated introductory text. It then passed, checking headers/row labels, bounded size, unchanged stored hits and rejection of calculation from searched-but-unread cells. All 89 offline tests pass in 30.231 seconds; lint and 34-file formatting pass. Model/network responses in tests are simulated.

This correction is **not a proven cause or cure of HTTP 504**, and there is no live before/after quality claim for v2. It addresses the independently observed preview deficiency. The C02 report remains tied to its original v1 code and retains its original failure.

## Handoff

README, architecture, instructions, backlog and implementation log identify the new evidence and v2 scope. Historical measurement files remain intact. GitHub B10 remains open/In progress; its broader comparison task is not checked off. No commit or push is performed by the assistant. Preservation and saved-result checks are recorded in the JSON after verification.
