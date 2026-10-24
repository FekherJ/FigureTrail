# B01 reference case: percentage change

**Source verification: 24 October 2026. English edition: 25 October 2026. B01 data feasibility: 10/10 cases verified.**

Purpose: establish reliable references for later retrieval and LLM cell-selection evaluation. These checks do not evaluate the application itself.

## Question and evidence

Case: `FBHS/2017/page_23.pdf-2`; context: `FBHS/2017/page_23.pdf`.

Original question: **what was the percentage growth in sales of cabinets from 2016 to 2017**.

Use annual Cabinets segment net sales. `pre_text[22]` describes annual divisional net sales for the last three fiscal years. This passage describes historical values without identifying them as forecasts.

Zero-based coordinates:

| Role | Cell | Row | Header | Value | Unit and scale |
|---|---|---|---|---:|---|
| New | `table[1][1]` | cabinets | 2017 | 2467.1 | million dollars, `$` symbol |
| Old/base | `table[1][2]` | cabinets | 2016 | 2397.8 | million dollars, `$` symbol |

`table[0][0]` states “in millions”; both cells contain `$`. No ISO currency code appears in this context, so none is inferred. Both operands share units and scale; no conversion is required.

The corresponding `table_ori` cells contain `$2,467.1` and `$2,397.8`, under `<i>2017</i>` and `<i>2016</i>`. Remove currency symbols/thousands separators before `Decimal` parsing. The numeric values agree.

The row/headers establish values and years; `pre_text[22]` establishes annual sales. The 2015 column and Plumbing, Doors and Security rows are not operands.

## Formula and answer

```text
percentage change = 100 × (new − old) / old
                  = 100 × (2467.1 − 2397.8) / 2397.8
                  = 2.890149303528234214696805405…%

display at reference precision: 2.9%
```

The base, 2397.8, is positive. The absolute increase is 69.3 million, not the percentage answer. Dividing by 2467.1 would use the wrong base. This is relative change, not a difference between percentage rates.

FinQA stores `answer = "2.9%"`, while `exe_ans = 0.0289` is a **decimal ratio**. The first case instead stores `exe_ans` in percentage units. Preserve both original conventions. Compare the calculated ratio against `exe_ans` with absolute tolerance `0.000005`, equivalent to `0.0005` percentage points. Check one-decimal display separately.

The annotated program, `subtract(2467.1, 2397.8), divide(#0, 2397.8)`, remains reference data. It is never executed. `gold_inds` identifies `table_1`; period context is checked separately.

## Separation, duplicates and limits

- Full source export: `data/samples/finqa-b01-growth-source.json`, containing only `filename`, `pre_text`, `post_text`, `table`, `table_ori`; no gold-row filtering.
- Evaluation-only annotations: `evals/cases/finqa-b01-growth-reference.json`.
- `FBHS/2017/page_23.pdf-1` has exactly the same source fields. Deduplicate before indexing and group these questions together when splitting development/final cases. The two detailed reference cases come from different reports.
- Operand values agree across table versions. Text still contains artifacts such as `2019s` for apostrophes; the whole document is not claimed to be clean.
- Verification uses distributed FinQA text/tables, without original-PDF inspection. The download hash and license are recorded in [provenance](../../data/FINQA_PROVENANCE.md).

## Reproduce

```powershell
python3.14.exe -X utf8 scripts/inspect_finqa.py --case growth
python3.14.exe -X utf8 scripts/inspect_finqa.py --case growth --check
```

The first command regenerates separate exports; the second checks them without writing. With no option, the command retains the first-case behavior. Assertions require normal Python execution, without `-O`.

Checks cover the raw hash, labels/periods, both table versions, positive base, source-cell calculation, ratio/display convention, source-field allowlist and export equality. Model/API cost: **€0**.

## Evaluation conventions

References must state units, conventions and tolerances. A correct number with incorrect years, or a misnormalized reference, can invalidate evaluation.

Both operation families have a verified example. The [B01 report](../verification/B01_DATA_VERIFICATION.md) covers ten cases and duplicate/distractor checks. B01 data feasibility is complete; no RAG/LLM score is claimed.
