# B01 reference case: percentage ratio

**Source verification: 24 October 2026. English edition: 25 October 2026. B01 contains ten verified references.**

References: [backlog](BACKLOG.md), [architecture](../architecture/ARCHITECTURE.md), [provenance and license](../../data/FINQA_PROVENANCE.md).

## Question and scope

Case: `DVN/2007/page_58.pdf-2`, the third entry in `dev.json`.

Original question: **what percentage of the total oil and gas mmboe comes from canada?**

Interpret this as Canada's share of the total production volume in MMBoe. The table includes oil, gas and natural gas liquids (NGLs). Use its existing Total column rather than reconstructing a different oil-and-gas-only total.

The first dataset entry, `V/2008/page_17.pdf-1`, asks for an average monetary value per transaction, outside the two supported operation families. This selected two-cell ratio is a development example, not a representative dataset sample.

## Cells and context

Coordinates are **zero-based**: row 0 contains headers; column 0 contains labels.

| Role | Cell | Row | Column | Value | Unit | Period |
|---|---|---|---|---:|---|---|
| Numerator | `table[3][4]` | Canada | Total (MMBoe) | 60 | MMBoe | 2008 estimate |
| Denominator | `table[5][4]` | Total | Total (MMBoe) | 243 | MMBoe | 2008 estimate |

MMBoe means million barrels of oil equivalent. Matching units/scales cancel in the ratio. Do not directly add oil in MMBbls to gas in Bcf. Devon's [annual report, note 1](https://media.corporate-ir.net/media_files/irol/67/67097/reports/AR2007/08_02_01.htm) describes energy conversion and NGL inclusion; this calculation uses only the supplied total column.

Required source evidence:

- `table[0][4]` and `table_ori[0][4]`: header and unit.
- `table[3][0]`, `[3][4]`, `[5][0]`, `[5][4]`: labels and values. Operands agree numerically with `table_ori`.
- `pre_text[16]`: 2008 estimates section.
- `pre_text[27]`: exclusion of West African operations from the following forecast.
- `pre_text[30]`: estimated 2008 production; `[31]` gives a range and `[33]` places the table at its midpoint. Use the tabulated total of 243 rather than a recalculated midpoint.

The report identifier's year, 2007, is not the operands' period. These are forecasts, not actual production. Verification covers distributed FinQA text/tables, without inspecting the original PDF.

## Calculation and reference

```text
share = 100 × Canada volume / total volume
      = 100 × 60 / 243
      = 24.691358024691358…%

display to two decimal places: 24.69%
```

The denominator is positive. Without multiplication by 100, the ratio is approximately 0.2469. The answer is a percentage, not a volume or a change between years.

The [separate annotations](../../evals/cases/finqa-b01-reference.json) contain `answer = 24.69%`, `exe_ans = 24.69136` and `program = divide(60, 243), multiply(#0, const_100)`. The program is reference data, never executable code. Allow **0.000005 percentage points** against the rounded `exe_ans`, and check the two-decimal display separately.

Gold evidence names `table_3`, `table_5` and `text_34` for units. Reviewed context also establishes period and forecast status; gold annotations alone do not describe all of it.

## Known anomaly and limits

`table[4][3]` contains `2014`, while `table_ori[4][3]` contains a dash. This International/NGLs cell is not an operand. The anomaly is recorded in the review metadata; the verifier checks only selected evidence/operands and does not repair it. B04 must resolve it explicitly before indexing.

This B01 review establishes no model score. At the time of that review, no indexed corpus, live LLM, abstention evaluation or reserved final split was available. The subsequent B03 pilot selected these cells three times and tested one missing-period abstention; broader model quality and RAG remain unmeasured. Evaluation references must never enter the analysis service's inference inputs.

## Reproduce

```powershell
python3.14.exe -X utf8 scripts/inspect_finqa.py
```

The verifier resolves repository paths, checks labels/coordinates/headers, and allowlists five source fields. Removing only `answer` would still leak programs, gold evidence or prepared retrieval fields. It parses source strings with `Decimal` and separates display rounding from calculation.

Assertions belong to this offline verifier, not runtime API validation. Do not use `-O`. Observed result: checks passed, two separate exports created and reference matched. Model/API cost: **€0**.

## Related evidence

The [second case](B01_SECOND_CASE.md) covers percentage change. Review combines AI-assisted source inspection and deterministic calculation; it is not an independent human review. The [B01 report](../verification/B01_DATA_VERIFICATION.md) records all ten cases, duplicate checks and distractor candidates. B03's controlled pilot is now verified; its quota and tool-call checks remain pending.
