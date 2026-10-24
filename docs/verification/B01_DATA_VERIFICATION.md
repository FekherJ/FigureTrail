# B01 data verification: ten reference cases

**Data review: 24 October 2026. English edition: 25 October 2026. Feasibility verified: 10/10 cases.**

Method: AI-assisted review of supplied text/tables, deterministic recalculation and automated checks. This report is not an independent human review. The English edition preserves the original numerical results; the verifier is rerun after translation.

## 1. Outcome

All ten examples can be calculated from two cells with strictly positive bases and explicit units, scales and periods. Both FinQA table versions agree numerically on all twenty operands. Five examples are percentage ratios; five are percentage changes, including one decline. The contexts belong to ten distinct reports.

B01 data feasibility is complete. These checks did not evaluate a model, retrieval system, analysis API or agent. J1 still requires the B03 hosted-model trial. Resolve the identified normalization defects in B04 before indexing.

These are development references whose evidence and answers are already known. Preparing them is neither model training nor an evaluation on reserved cases.

## 2. Method and provenance

- Input: `data/raw/finqa-dev.json`, 883 entries.
- SHA-256: `a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51`.
- Upstream: [FinQA dataset/dev.json](https://github.com/czyssrs/FinQA/blob/main/dataset/dev.json), Chen et al., EMNLP 2021.
- Scope: distributed FinQA text/tables only; no original-PDF inspection or OCR.
- Selection: simple, deliberately chosen examples, not a random or representative FinQA sample. Annotations support curation, never inference retrieval.
- Review: identify measure, segment, years and historical/forecast/pro forma status; compare `table` with `table_ori`; calculate independently with `Decimal`; check original answers and display precision.
- Source exports allow only `filename`, `pre_text`, `post_text`, `table`, `table_ori`. Preserve the whole context rather than gold-selected lines.
- Never execute FinQA programs or generated code. No model/API calls were needed: **EUR 0**.
- Verification runtime: Python **3.14.5**, standard library only.

Retain the upstream MIT notice, copyright 2021 Zhiyu Chen, in `data/FINQA_LICENSE.txt` and attribution in [provenance](../../data/FINQA_PROVENANCE.md). Reviewing that notice does not independently establish rights to each underlying financial report. No complete PDF is redistributed.

## 3. Results

Display precision follows the original answer. Canonical results retain the calculated value without premature rounding.

| Case | FinQA ID | Operation | Display | Result |
|---|---|---|---:|---|
| C01 | `DVN/2007/page_58.pdf-2` | Percentage ratio | 24.69% | Verified |
| C02 | `FBHS/2017/page_23.pdf-2` | Percentage change | 2.9% | Verified |
| C03 | `PKG/2009/page_65.pdf-4` | Percentage ratio | 56% | Verified |
| C04 | `UNP/2008/page_77.pdf-1` | Percentage ratio | 14.3% | Verified |
| C05 | `INTC/2013/page_29.pdf-3` | Percentage ratio | 35.8% | Verified |
| C06 | `ZBH/2017/page_53.pdf-1` | Percentage ratio | 4.392% | Verified |
| C07 | `LMT/2012/page_47.pdf-3` | Percentage change | 3.2% | Verified |
| C08 | `MAS/2018/page_35.pdf-3` | Percentage change | 1.4% | Verified |
| C09 | `ETR/2004/page_213.pdf-4` | Percentage change | 5.5% | Verified |
| C10 | `ETR/2017/page_26.pdf-4` | Percentage change | -7.4% | Verified |

## 4. Evidence and calculations

Coordinates are zero-based. Quoted excerpts are preserved from the named source fields. Application questions clarify the scope in English; original FinQA questions remain unchanged.

### C01 — Canada's share of total estimated production

- **Original question:** what percentage of the total oil and gas mmboe comes from canada?
- **Application question:** In Devon's estimated 2008 production table, what percentage of total production in MMBoe comes from Canada?
- **Context:** `DVN/2007/page_58.pdf`; Estimated production for 2008.
- **Common unit:** MMBoe; **scale:** million barrels of oil equivalent.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| numerator | `table[3][4]` | 60 | 2008 estimate |
| denominator | `table[5][4]` | 243 | 2008 estimate |

**Calculation:** `100 * 60 / 243` = **24.69135802469135802469135802%**; display **24.69%**.

**Checked context evidence:**

- `table[0][4]` contains: “total ( mmboe )”.
- `table[3][0]` contains: “canada”.
- `table[5][0]` contains: “total”.
- `pre_text[30]` contains: “estimates of oil , gas and ngl production for 2008”.
- `pre_text[33]` contains: “midpoint”.

**FinQA reference:** `answer = 24.69%`; `exe_ans = 24.69136` in **percent** units. Absolute difference in that unit: `0.00000197530864197530864198`; tolerance: `0.000005`.

- 2007 is the report year; the values are forecasts for 2008.
- The Total column includes NGLs; preserve the scope of the supplied table.
- Non-operand anomaly: table[4][3] is 2014, but table_ori[4][3] is a dash. Explicitly reject or normalize this conflict in B04.
- Full source: `data/samples/finqa-b01-source.json`; original annotations: `evals/cases/finqa-b01-reference.json`.

### C02 — Growth in Cabinets segment sales

- **Original question:** what was the percentage growth in sales of cabinets from 2016 to 2017
- **Application question:** For FBHS, what was the percentage growth in annual Cabinets segment net sales from 2016 to 2017?
- **Context:** `FBHS/2017/page_23.pdf`; Historical annual sales.
- **Common unit:** dollar ($); **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| new | `table[1][1]` | 2467.1 | Fiscal year 2017 |
| old | `table[1][2]` | 2397.8 | Fiscal year 2016 |

**Calculation:** `100 * (2467.1 - 2397.8) / 2397.8` = **2.890149303528234214696805405%**; display **2.9%**.

**Checked context evidence:**

- `table[0][0]` contains: “in millions”.
- `table[0][1]` contains: “2017”.
- `table[0][2]` contains: “2016”.
- `table[1][0]` contains: “cabinets”.
- `pre_text[22]` contains: “annual net sales for each of the last three fiscal years”.

**FinQA reference:** `answer = 2.9%`; `exe_ans = 0.0289` in **ratio** units. Absolute difference in that unit: `0.00000149303528234214696805405`; tolerance: `0.000005`.

- Use the Cabinets segment, rather than total sales or the Plumbing segment.
- The $ symbol is explicit; do not infer an ISO currency code that is absent from the context.
- Full source: `data/samples/finqa-b01-growth-source.json`; original annotations: `evals/cases/finqa-b01-growth-reference.json`.

### C03 — Share of purchase commitments due after 2014

- **Original question:** what percentage of total purchase commitments are due after 2014?
- **Application question:** In PKG's 2009 purchase commitments schedule, what percentage of the total is due after 2014?
- **Context:** `PKG/2009/page_65.pdf`; Future commitments schedule in the 2009 report.
- **Common unit:** dollar ($); **scale:** thousand.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| numerator | `table[6][1]` | 25048 | After 2014: thereafter |
| denominator | `table[7][1]` | 44572 | Total schedule, 2010 onward |

**Calculation:** `100 * 25048 / 44572` = **56.19671542672529839361033833%**; display **56%**.

**Checked context evidence:**

- `table[0][1]` contains: “in thousands”.
- `table[5][0]` contains: “2014”.
- `table[6][0]` contains: “thereafter”.
- `table[7][0]` contains: “total”.
- `pre_text[0]` contains: “purchase commitments”.
- `pre_text[1]` contains: “total purchase commitments”.

**FinQA reference:** `answer = 56%`; `exe_ans = 0.56197` in **ratio** units. Absolute difference in that unit: `0.0000028457327470160638966167`; tolerance: `0.000005`.

- Thereafter means after the last explicit year, 2014; exclude 2014 itself.
- Future commitments are not purchases already made.
- Full source: `data/samples/finqa-b01-03-source.json`; original annotations: `evals/cases/finqa-b01-03-reference.json`.

### C04 — Accrued wages and vacation as a share of current liabilities

- **Original question:** as of december 31 , 2008 what was the percent of the total accounts payable and other liabilities that was accrued wages and vacation
- **Application question:** For Union Pacific at December 31, 2008, what percentage of total accounts payable and other current liabilities was accrued wages and vacation?
- **Context:** `UNP/2008/page_77.pdf`; Historical balance at December 31, 2008.
- **Common unit:** dollar ($); **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| numerator | `table[2][1]` | 367 | December 31, 2008 |
| denominator | `table[8][1]` | 2560 | December 31, 2008 |

**Calculation:** `100 * 367 / 2560` = **14.3359375%**; display **14.3%**.

**Checked context evidence:**

- `table[0][0]` contains: “millions of dollars”.
- `table[0][1]` contains: “2008”.
- `table[2][0]` contains: “accrued wages and vacation”.
- `table[8][0]` contains: “total accounts payable and other current liabilities”.
- `pre_text[15]` contains: “accounts payable and other current liabilities”.

**FinQA reference:** `answer = 14.3%`; `exe_ans = 0.14336` in **ratio** units. Absolute difference in that unit: `6.25E-7`; tolerance: `0.000005`.

- The question shortens the label. Use total current liabilities from the table, rather than Accounts payable alone.
- Do not use the 2007 column.
- Full source: `data/samples/finqa-b01-04-source.json`; original annotations: `evals/cases/finqa-b01-04-reference.json`.

### C05 — Share of owned facility space outside the United States

- **Original question:** what is the percent of the square feet in owned facilities in other countries?
- **Application question:** For Intel at December 28, 2013, what percentage of the total square footage of owned facilities was in other countries?
- **Context:** `INTC/2013/page_29.pdf`; Facility floor space at December 28, 2013.
- **Common unit:** square foot; **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| numerator | `table[1][2]` | 16.7 | December 28, 2013 |
| denominator | `table[1][3]` | 46.6 | December 28, 2013 |

**Calculation:** `100 * 16.7 / 46.6` = **35.83690987124463519313304721%**; display **35.8%**.

**Checked context evidence:**

- `table[0][0]` contains: “square feet in millions”.
- `table[0][2]` contains: “othercountries”.
- `table[0][3]` contains: “total”.
- `table[1][0]` contains: “owned facilities”.
- `pre_text[3]` contains: “as of december 28 , 2013”.

**FinQA reference:** `answer = 35.8%`; `exe_ans = 0.35837` in **ratio** units. Absolute difference in that unit: `9.012875536480686695279E-7`; tolerance: `0.000005`.

- The denominator is Owned facilities, 46.6, rather than Total facilities, 54.9.
- The unit measures area; no currency conversion applies. Superscripts in labels are footnote markers.
- Full source: `data/samples/finqa-b01-05-source.json`; original annotations: `evals/cases/finqa-b01-05-reference.json`.

### C06 — Net profit margin using 2015 pro forma figures

- **Original question:** what is the company's net earnings as a percent of net sales in 2015 ? ( net profit margin )
- **Application question:** Using Zimmer Biomet's unaudited pro forma figures for the year ended December 31, 2015, what were net earnings as a percentage of net sales?
- **Context:** `ZBH/2017/page_53.pdf`; Unaudited pro forma figures for the year ended December 31, 2015.
- **Common unit:** dollar ($); **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| numerator | `table[2][1]` | 330.2 | Year ended December 31, 2015, pro forma |
| denominator | `table[1][1]` | 7517.8 | Year ended December 31, 2015, pro forma |

**Calculation:** `100 * 330.2 / 7517.8` = **4.392242411343744180478331427%**; display **4.392%**.

**Checked context evidence:**

- `table[0][1]` contains: “2015 ( in millions )”.
- `table[2][0]` contains: “net earnings”.
- `table[1][0]` contains: “net sales”.
- `pre_text[34]` contains: “unaudited pro forma financial information”.
- `pre_text[36]` contains: “pro forma financial information ( unaudited )”.
- `post_text[0]` contains: “comparative purposes only”.

**FinQA reference:** `answer = 4.392%`; `exe_ans = 0.04392` in **ratio** units. Absolute difference in that unit: `0.00000242411343744180478331427`; tolerance: `0.000005`.

- The report identifier refers to 2017, but the values refer to 2015.
- State that the figures are unaudited and pro forma; do not describe them as unadjusted consolidated historical results.
- Calculate from the supplied values; do not reconstruct the merger accounting.
- Full source: `data/samples/finqa-b01-06-source.json`; original annotations: `evals/cases/finqa-b01-06-reference.json`.

### C07 — Growth in Space Systems operating profit in 2011

- **Original question:** what is the growth rate in operating profit for space systems in 2011?
- **Application question:** For Lockheed Martin Space Systems, what was the percentage change in operating profit from 2010 to 2011?
- **Context:** `LMT/2012/page_47.pdf`; Historical annual results for the Space Systems segment.
- **Common unit:** dollar ($); **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| new | `table[2][2]` | 1063 | Fiscal year 2011 |
| old | `table[2][3]` | 1030 | Fiscal year 2010 |

**Calculation:** `100 * (1063 - 1030) / 1030` = **3.203883495145631067961165049%**; display **3.2%**.

**Checked context evidence:**

- `table[0][2]` contains: “2011”.
- `table[0][3]` contains: “2010”.
- `table[2][0]` contains: “operating profit”.
- `table[1][1]` contains: “$”.
- `pre_text[16]` contains: “space systems 2019 operating results included the following ( in millions )”.

**FinQA reference:** `answer = 3.2%`; `exe_ans = 0.03204` in **ratio** units. Absolute difference in that unit: `0.00000116504854368932038834951`; tolerance: `0.000005`.

- Interpret annual growth in 2011 as 2011 compared with 2010. The original question does not explicitly state the base year.
- The opening paragraphs describe MST and a decline; they do not describe the table's Space Systems segment.
- The 2012 column is not part of the change in 2011.
- Full source: `data/samples/finqa-b01-07-source.json`; original annotations: `evals/cases/finqa-b01-07-reference.json`.

### C08 — Growth in operating profit as reported from 2017 to 2018

- **Original question:** what was the percentage growth in the operating profit as reported from 2017 to 2018
- **Application question:** For Masco, what was the percentage growth in operating profit as reported from 2017 to 2018?
- **Context:** `MAS/2018/page_35.pdf`; Historical annual operating profit, as reported.
- **Common unit:** dollar ($); **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| new | `table[1][1]` | 1211 | Fiscal year 2018 |
| old | `table[1][2]` | 1194 | Fiscal year 2017 |

**Calculation:** `100 * (1211 - 1194) / 1194` = **1.423785594639865996649916248%**; display **1.4%**.

**Checked context evidence:**

- `table[0][1]` contains: “2018”.
- `table[0][2]` contains: “2017”.
- `table[1][0]` contains: “operating profit as reported”.
- `pre_text[10]` contains: “dollars in millions”.

**FinQA reference:** `answer = 1.4%`; `exe_ans = 0.01424` in **ratio** units. Absolute difference in that unit: `0.00000214405360134003350083752`; tolerance: `0.000005`.

- Use as reported, rather than as adjusted or margin rows already expressed as percentages.
- Non-operand anomalies: table[3][2] and table[3][3] are 2014, but table_ori contains dashes. Resolve these conflicts in B04.
- Full source: `data/samples/finqa-b01-08-source.json`; original annotations: `evals/cases/finqa-b01-08-reference.json`.

### C09 — Growth in Entergy Louisiana net revenue from 2002 to 2003

- **Original question:** what is the growth rate in net revenue in 2003 for entergy louisiana , inc.?
- **Application question:** For Entergy Louisiana, what was the percentage change in the reported net revenue measure from 2002 to 2003?
- **Context:** `ETR/2004/page_213.pdf`; Historical annual net revenue, a gross-margin measure defined in the report.
- **Common unit:** dollar ($); **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| new | `table[7][1]` | 973.7 | Fiscal year 2003 |
| old | `table[1][1]` | 922.9 | Fiscal year 2002 |

**Calculation:** `100 * (973.7 - 922.9) / 922.9` = **5.504388341098710586195687507%**; display **5.5%**.

**Checked context evidence:**

- `table[0][1]` contains: “in millions”.
- `table[7][0]` contains: “2003 net revenue”.
- `table[1][0]` contains: “2002 net revenue”.
- `pre_text[0]` contains: “entergy louisiana”.
- `pre_text[5]` contains: “2003 compared to 2002 net revenue”.
- `pre_text[6]` contains: “comparing 2003 to 2002”.

**FinQA reference:** `answer = 5.5%`; `exe_ans = 0.05504` in **ratio** units. Absolute difference in that unit: `0.00000388341098710586195687507`; tolerance: `0.000005`.

- Here, net revenue is a gross-margin measure defined in pre_text[5], rather than gross operating revenues.
- Do not use intermediate changes as annual values. This section of the 2004 report describes 2003 and 2002.
- Full source: `data/samples/finqa-b01-09-source.json`; original annotations: `evals/cases/finqa-b01-09-reference.json`.

### C10 — Decline in Entergy Wholesale Commodities net revenue in 2016

- **Original question:** what is the growth rate in net revenue in 2016?
- **Application question:** For Entergy Wholesale Commodities, what was the signed percentage change in net revenue from 2015 to 2016?
- **Context:** `ETR/2017/page_26.pdf`; Historical annual results for the Entergy Wholesale Commodities segment.
- **Common unit:** dollar ($); **scale:** million.

| Role | Cell | Value | Period/scope |
|---|---|---:|---|
| new | `table[8][1]` | 1542 | Fiscal year 2016 |
| old | `table[1][1]` | 1666 | Fiscal year 2015 |

**Calculation:** `100 * (1542 - 1666) / 1666` = **-7.442977190876350540216086435%**; display **-7.4%**.

**Checked context evidence:**

- `table[0][1]` contains: “in millions”.
- `table[8][0]` contains: “2016 net revenue”.
- `table[1][0]` contains: “2015 net revenue”.
- `pre_text[8]` contains: “entergy wholesale commodities”.
- `post_text[0]` contains: “decreased by approximately $ 124 million in 2016”.

**FinQA reference:** `answer = -7.4%`; `exe_ans = -0.07443` in **ratio** units. Absolute difference in that unit: `2.2809123649459783913565E-7`; tolerance: `0.000005`.

- The result is negative despite the word growth; preserve the sign.
- The original question omits the base year and segment. The context establishes a 2016 versus 2015 comparison for this segment.
- Do not confuse this segment with Entergy Louisiana in the other selected report.
- Full source: `data/samples/finqa-b01-10-source.json`; original annotations: `evals/cases/finqa-b01-10-reference.json`.

## 5. Reference conventions and known defects

**Per-case units:** C01 stores `exe_ans` as a percentage; C02–C10 store decimal ratios. Multiply the latter by 100 before percentage comparison. Their native tolerance `0.000005` equals `0.0005` percentage points; C01 uses `0.000005` percentage points. These check rounded annotations, not final product thresholds.

**Future numerical evaluation:** use canonical `expected_percent` values and choose system tolerances before measurement. A matching rounded display is insufficient: C03 displays 56%, while its calculated reference is approximately 56.196715%. Check cells, periods and units as well.

**Non-operand defects:** C01 has a dash incorrectly normalized to `2014`. C08 has two such cells in the Kichler row for 2017/2016. They do not affect these calculations but remain in full source contexts. B04 must compare table versions, represent dashes as missing values and test conflicts before indexing. Do not replace every `2014`; some are valid years.

**Required context:** C06 is unaudited pro forma data; C01 is a forecast; C03 concerns future payments. Filename years do not establish value periods. Do not invent ISO currency codes for `$` amounts.

**Adapted questions:** some originals omit company or base year. Application questions explicitly state them, including C07/C10 and C06's pro forma status. This is an adapted benchmark, distinct from original FinQA. Retrieval must start from the question without a hidden gold `report_id`. Flag or clarify genuinely ambiguous requests.

## 6. Duplicates, report groups and distractors

The 883 entries contain **299 distinct exact contexts**, **299 distinct filenames** and **272 context groups with multiple questions**. Context hashes exclude `filename` to detect identical content under different paths.

Selected cases have ten distinct hashes and ten report groups (`company/year`). Questions sharing a page do not become independent documents. Retain report/content groups when splitting development and final cases.

| Selected case | Same-filename questions | Exact-context questions |
|---|---:|---:|
| C01 | 2 | 2 |
| C02 | 2 | 2 |
| C03 | 4 | 4 |
| C04 | 3 | 3 |
| C05 | 4 | 4 |
| C06 | 1 | 1 |
| C07 | 4 | 4 |
| C08 | 3 | 3 |
| C09 | 4 | 4 |
| C10 | 4 | 4 |

Full matching IDs appear in `B01_VERIFICATION_RESULTS.json`. Exact equality misses near-duplicates; report grouping adds protection. All ten are development cases; no reserved final split exists yet.

Three distinct distractor candidates are identified for B04:

- `AES/2017/page_157.pdf-1` (`AES/2017/page_157.pdf`): Different company, with 2017/2016/2015 revenues; similar years and amounts.
- `LMT/2015/page_56.pdf-4` (`LMT/2015/page_56.pdf`): Same company, LMT, but a different report and years; net sales and operating profit table.
- `UNP/2007/page_65.pdf-1` (`UNP/2007/page_65.pdf`): Another future-payment schedule that may compete with the PKG commitments schedule.


These are verified corpus candidates, not three additional reviewed calculation cases. B04 must export sources only, inspect quality and index them with target contexts. Neighboring rows and unrequested years also act as internal distractors. No retrieval score is available yet.

## 7. Candidates excluded from B01

These are observed selection issues, not claims that the cases are unusable in every scope.

| Candidate | Reason for exclusion |
|---|---|
| `HOLX/2015/page_98.pdf-2` | Dollar amounts and forecast status are clear, but the supplied context gives no monetary scale. Do not assume millions. |
| `LLY/2018/page_63.pdf-1` | Inventory cells agree, but the table's scale is absent from the selected context. |
| `PM/2017/page_99.pdf-1` | Cells yield approximately −13.3773%, rounding to −13.4% at one decimal place; the text answer is −13.3%. |
| `UNP/2006/page_37.pdf-2` | The annotated program mixes 3.2 and 2242; relevant values are not two comparable cells in the expected unit. Conversion/reconstruction is outside scope. |
| `LMT/2006/page_37.pdf-1` | The question asks for a quarter total, but the annotated denominator 929400 belongs to December. Total scope is inconsistent. |
| `PM/2015/page_85.pdf-1` | The text answer is positive 3.4%, while the program produces a negative change; both debt values are absent from the selected table cells. |

## 8. Data boundaries and artifacts

- `data/raw/finqa-dev.json`: raw annotations; local, ignored by Git and excluded from inference.
- `data/samples/*-source.json`: ten full contexts with the five allowed fields; generated locally and ignored.
- `evals/cases/*-reference.json`: unchanged original FinQA annotations, for evaluation only.
- `evals/cases/finqa-b01-reviewed.json`: adapted questions, cells, units, periods, operations, expected results and conventions; never inference context.
- `scripts/inspect_finqa.py`: repeatable standard-library checks.
- `tests/test_b01_verification.py`: three negative checks.
- `docs/verification/B01_DATA_VERIFICATION.md`: this report.
- `docs/verification/B01_VERIFICATION_RESULTS.json`: exact results, hashes, duplicate audit and distractor candidates.

**`docs/verification/` contains expected answers and coordinates. Exclude it from inference ingestion along with `evals/`.** Future preparation must allowlist sources rather than ingest every Markdown/JSON file.

## 9. Reproduce

From the repository root in PowerShell:

```powershell
python3.14.exe -B -X utf8 scripts/inspect_finqa.py --case all --check
python3.14.exe -B -X utf8 -m unittest discover -s tests -p test_b01_verification.py -v
```

Observed result: ten valid cases and three passing negative tests. Wrong year, ratio/percentage confusion and an answer injected into a source export are rejected. These test reference preparation, not future model guardrails.

To regenerate twenty exports from the hash-verified raw file:

```powershell
python3.14.exe -B -X utf8 scripts/inspect_finqa.py --case all
```

No option selects the first case; `--case growth` selects the second; `--case case03` through `case10` select the others. `--check` writes no exports. Do not use `-O`; the verifier rejects disabled assertions. The manifest and raw input must exist; see [README](../../README.md).

These JSON/Markdown snapshots are dated evidence, not automatically regenerated narratives. Rerun checks and update evidence after source, manifest or verifier changes. The English edition updates manifest/verifier hashes for translated text while retaining the original review date, numerical values and measurements.

## 10. Limits and next step

This verifies ten selected FinQA examples, not the independent truth of original reports or the entire dataset. There is no original-PDF review, reserved-case test, generalization measurement or model cost/latency result.

B02's local foundation is verified separately. B03 must test a hosted LLM with structured output and measure latency/usage before a campaign. Provider/model selection remains open. B04 must resolve known table conflicts and keep references outside the inference corpus.

The model will propose operation/cell IDs; code will calculate. These references support separate checks of retrieval, cell selection and numerical results.
