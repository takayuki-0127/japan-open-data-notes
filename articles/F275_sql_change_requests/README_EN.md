# F275 How should reporting SQL be written so that it is easy to change, and so that you notice what you forgot to change?

Japanese version: [README.md](README.md). The dbt version of the same reports is [projects/dbt_retail_mart](../../projects/dbt_retail_mart/README_EN.md).

Using two years of synthetic data for a fictional retailer, "Midori Mart (fictional)", eight monthly report packages (company-wide, by store, by department, same-store year-on-year, customers and spend per customer, store × department, KPI summary, daily for the latest month) were built in three SQL styles. Eight typical "definition change requests" were then applied, counting how many places must be edited and which tests notice when an edit is forgotten. The plan ([PLAN.md](PLAN.md), commit 5beb93c) was committed before looking at results.

F244 (21 common mistakes and tests) dealt with "typos in a single query". This article deals with "definition changes and forgotten edits".

## Question

- How many places must be edited per change request, depending on the writing style?
- When an edit is forgotten, which tests notice?
- Follow-up question: if definitions are written in one place, is a mistake in that place found? (Not in the plan; added later.)

## Data

- Synthetic data (`src/zz_f275_01_データ生成.py`, random seeds 2751–2755): 13 stores (one test store, three opened mid-period), Apr 2024 – Mar 2026, about 130,000 receipts, 260,000 line items and 5,000 returns. Statuses include cancel (2%) and void (1%); about 40% of member IDs are NULL.
- A small dataset for answer checks (`data/fixture_*`): 4 stores, about 350 receipts. It contains edge cases: a store whose opening date sits on the same-store boundary, a sale at month-end returned the next month, sales on the 20th and 21st, a receipt with only voids, the same member visiting twice on one day, departments 5 and 8, and test-store sales. For comparison, a version without edge cases (`fixture_plain_*`) was also built.
- No real company data is used.

## What I did

### Three writing styles (base SQL in `sql/`, diffs per change request in `sql/*_changes.diff`)

| Style | Contents | Base lines |
|---|---|---|
| S1 Copy-paste | each of the 8 reports writes the definitions (excluding cancels, tax, returns, same store, month, test store, department, customer count) directly in its expressions | 248 |
| S2 CTE | each report is split into CTE steps, but the definition blocks are written in every file (not shared) | 270 |
| S3 Shared views | the definitions are written once in six views (line_ok, net, mon, comp_store, dept_grp, cust); reports read from the views | 114 |

S2's CTEs and S3's views are the same statements; the only difference is whether they are shared. The SQL avoids date functions (months come from a calendar table), integer division and string concatenation, so the same code runs on DuckDB and SQLite. sqlglot (T-SQL dialect) parsed all 270 files without errors, but this does not guarantee compatibility (its T-SQL dialect also accepts LIMIT, ::, QUALIFY, ILIKE, etc.); syntax not in T-SQL was avoided by eye. Not run on SQL Server.

### Change requests (8)

CR1 book returns on the original sale date / CR2 same store: 13 → 12+ months / CR3 months as fiscal months closing on the 21st / CR4 tax-inclusive → tax-exclusive / CR5 exclude the test store / CR6 also exclude void status / CR7 change how departments are grouped / CR8 customers: receipts → members per day (a receipt without a member ID counts as one person)

### Tests

- T1 cross-report reconciliation: R1 monthly total = totals of R2, R3, R6 = sales in R5, R7; R8 daily total = R1's latest month.
- T2 internal consistency: same-store sales ≤ all stores; spend per customer × customers = sales.
- "Reconciliation" in this article means T1 + T2, compared on the two-year production data with near-exact equality (relative error 1e-9).
- T3 answer check for R1 only (on the small dataset, against expected values computed separately in pandas).
- T4 answer check for all reports (all 8 on the same small dataset).

Expected values were computed in pandas separately from the SQL (`src/zz_f275_spec.py`). The correct SQL matched pandas for all 3 styles × 9 versions × 8 reports (1,824 comparisons, 0 mismatches: seed 2751 on both DuckDB and SQLite for all versions on production and answer-check data; the other four seeds on DuckDB for all versions on answer-check data and the base version on production data).

### Measurement

- Places to edit: number of files and lines changed, from diffs between before and after (difflib).
- Forgotten-edit mutants: for S1 and S2, mutants that leave exactly one affected report on the old definition (46) and mutants that forget all edits (8). For S3, only "forget all" (8), since there is one place to edit.
- Mutant outputs were assembled from the outputs of the correct and base versions (each S1/S2 file runs on its own, so this equals re-running).
- Size of error: in affected reports, difference from the correct value ÷ mean absolute correct value of that column (%); year-on-year columns in points. Rows whose keys do not match count as differences from 0, so values can exceed 100%.

## Findings

| Hypothesis | Threshold | Result | Verdict |
|---|---|---|---|
| H1 Median files to edit: S1 ≥ 3× S3 | 3× | 8 vs 1 (8×) | Supported (mostly determined by structure) |
| H2 S2 files to edit ≥ 0.8× S1 | 0.8× | 8 vs 8 (1.0×); median lines 8 vs 18 | Supported |
| H3 Of S1 single forgotten edits, T1 + T2 find less than 70% | 70% | 80.4% (37 of 46) | Not supported |
| H4 T4 finds 90%+ of forgotten edits in all styles | 90% | 94.8% (110 of 116) | Supported |

- Lines to edit (S1 / S2 / S3): CR5 exclude test store 52 / 16 / 3; CR3 fiscal month 30 / 8 / 1; CR6 void 26 / 8 / 1; CR4 tax-exclusive 24 / 8 / 1.
- The 9 S1 forgotten edits that slipped past T1 + T2 (T1 alone found 76%): four in same-store year-on-year (R4: CR1, CR2, CR5, CR6), same store in the KPI summary (R7 under CR2), department grouping (R3 and R6 under CR7) and customer counts (R5 and R7 under CR8). Changes that do not alter totals, and reports not reconciled against anything, are not caught by reconciliation.
- Size of the errors that slipped through: up to 7.3 points in year-on-year (CR2); department rows themselves swapped (CR7); customers 0.9%.
- The 6 that T4 missed were all in R8 (daily, latest month) under CR1, CR5 and CR6 for S1 and S2: the answer-check data had no returns, test-store or void rows in its latest month.
- Note: S2's results are identical to S1's, and S3's "forget all" output equals S1's. Removing duplicates leaves 54 cases, of which T4 finds 51 (94.4%).
- T3 (answer check for R1 only) found 62.5% of "forget all" mutants but only 10.9% of single forgotten edits.

## Robustness

- Five random seeds: T1 + T2 at 80.4% for all; T4 93.5–95.7%.
- SQLite: same results as DuckDB (0 mismatches for correct versions, same detection rates).
- With a 0.5% reconciliation tolerance, T1 + T2 drops to 65.2% (shifting the month in which returns are booked moves monthly totals by at most 0.49%, so all 7 CR1 forgotten edits fall within tolerance).
- With 5 reports (R1–R5), T1 + T2 find 22 of 28 (78.6%) and T4 all 28.
- Forgetting each place independently with 20% probability (200 runs per change request, S1 and S2): over 1,040 S1 runs with at least one forgotten edit, T1 + T2 found 77.1% and T4 98.4%.
- Not in the plan: with answer-check data without edge cases, T4 drops to 74–75% (single forgotten edits in S1 and S2). None of the forgotten edits for excluding the test store (CR5) or counting customers (CR8) were found, because ordinary data rarely contains a test store or the same member visiting twice in one day.

## Follow-up: if definitions live in one place, is a mistake there noticed?

Four mistakes were planted in the base SQL (B1 cancels not excluded, B2 missing join key for returns, B3 same-store boundary `<=` written as `<`, B4 counting receipts without line items as customers): one file at a time in S1 and S2 (20 cases each), and in the shared views in S3 (4 cases).

| | Found by T1 + T2 | Found by T4 | Reports whose numbers changed (mean) |
|---|---|---|---|
| S1 (one file) | 14/20 (70%) | 18/20 (90%) | 1 |
| S2 (one file) | 14/20 (70%) | 18/20 (90%) | 1 |
| S3 (shared views) | 0/4 (0%) | 4/4 (100%) | 5 (all 8 for B1 and B2) |

A mistake in a shared view flows into every report consistently, so reconciling reports against each other shows no disagreement (only 4 kinds; a result largely determined by structure). Only answer checks against correct values found them. Copy-paste code behaves the same if the same mistake is copied into every file; the difference is how easily a mistake spreads consistently. The 6 cases reconciliation missed in S1 and S2 (R4 under B1 and B2, B3, B4) were in the same kinds of places as in the main experiment: "not reconciled" and "does not change totals". The 2 that T4 missed in S1 and S2 were both mistakes in R8 (as above, the answer-check data had no cancels or returns in its latest month).

## Deviations from the plan

- The plan did not define how to measure the size of an error; "% of the mean absolute correct value of that column" was used (can exceed 100% when keys do not match).
- The check with answer-check data without edge cases (last robustness item) and the planted-mistake experiment in the follow-up were not in the plan.
- Five figures (the plan did not fix a number).

## What this does not show

- Results come from fictional data and from 8 reports, 8 change requests and 4 mistakes chosen by the author. Real-world SQL styles and the distribution of change requests were not measured.
- H1 and H2's "files to edit" are largely determined by the structure of the styles. What was actually measured is lines to edit and how detectable forgotten edits are.
- The strength of answer checks (T4) depends on how many edge cases the answer-check data contains. Here the latest month lacked cases, so forgotten edits in R8 were missed.
- The edge cases were added knowing these 8 change requests. For changes not known in advance, the 74% without edge cases may be closer (my interpretation).
- T4 assumes the correct-answer calculation (pandas) is also updated to the new definition; that effort, and forgetting it, were not measured.
- Mutants are file-level only. "Forgetting part of one file" — probably the most common case in copy-paste code — was not tested and may be even harder to find (my interpretation).
- SQL and change requests were generated by a script (sqlgen.py), so line counts depend on formatting.
- Other aspects of maintainability — readability, speed, permissions, checking which reports use a view before changing it — were not measured.
- Not run on SQL Server (parsing only). Japanese strings such as department names must be written as N'...' in SQL Server. Division by zero returns NULL in DuckDB and SQLite but raises an error in SQL Server (R4 year-on-year, R5 spend per customer).

## Corrections after review

After an independent review (checking numbers, sampling the SQL, re-running with 149 of 150 files byte-identical), the following were fixed:

| # | Point raised | Fix |
|---|---|---|
| 1 | The 95% for answer checks depends on edge cases added knowing the 8 change requests, and on the correct-answer calculation being updated | Added to the conclusion and limitations: "for unknown changes, the 74% without edge cases may be closer (my interpretation)" and "the effort and forgetting of updating the correct answers were not measured"; changed Figure 4's title |
| 2 | n and nature of "reconciliation found none" | Added that there are 4 kinds, that it follows from structure, that copy-paste code behaves the same if the mistake is copied to every file, and that S1's misses are in the same kinds of places; "4 kinds" in the heading |
| 3 | Definition of "reconciliation" | Defined as T1 + T2; added that T1 alone is 76% and the 1e-9 tolerance |
| 4 | T-SQL parsing is a weak check | Rewritten as "not a guarantee of compatibility"; added the division-by-zero difference |
| 5 | File-level mutants only; line counts depend on formatting | Added to limitations |
| 6 | S2 gives the same results as S1 | Noted 54 distinct cases and T4's 51 (94.4%) |
| 7 | With 0.5% tolerance, all 7 CR1 mutants are within tolerance | Changed "most" to "all" and stated the maximum monthly total shift of 0.49% (computed) |
| 8 | The 9th slipped mutant (R7 under CR2) missing from the text | Added to the findings |
| 9 | Scope of the 1,824 comparisons | Stated the scope per seed |
| 10 | Interpretation markers; cause of R8 misses | Marked interpretations; added the cause of the R8 misses |
| 11 | Wording of CR8 | "members per day (a receipt without a member ID counts as one person)" |

## How to use this at work

- Put each business definition in one shared place (a view or a dbt model) so a change request touches one file.
- But do not rely on reports reconciling with each other: a mistake in a shared definition makes everything agree and wrong. Add answer checks against independently computed expected values.
- Build answer-check data with deliberate edge cases (boundaries, late returns, test stores, repeat visits), including in the latest period.

## Figures

The figures have Japanese labels.
- `figures/fig1_edits.png`: files and lines to edit per change request, by style.
- `figures/fig2_detection.png`: share of forgotten edits found by each test.
- `figures/fig3_s1_matrix.png`: which S1 forgotten edits each test found.
- `figures/fig4_robustness.png`: detection under robustness checks, including data without edge cases.
- `figures/fig5_reask.png`: the follow-up experiment with planted mistakes.

## Reproduce

```
pip install -r requirements.txt
for s in 2751 2752 2753 2754 2755; do python3 src/zz_f275_01_データ生成.py $s; done
python3 src/zz_f275_03_分析.py    # about 10 minutes (2 cores); builds results/ and sql/
python3 src/zz_f275_04_図.py
```

`src/zz_f275_sqlgen.py` generates the SQL for the three styles, and `src/zz_f275_spec.py` computes the pandas expected values.

Check: copying only src to another folder and re-running everything reproduced 149 of 150 files in data, sql, results and figures byte for byte. The only difference was the 13th decimal place of the error-size column in results/B_mutants.csv (DuckDB sums in parallel); all verdict columns were identical.

Only the answer-check data (`data/fixture_2751/`) is stored in the repository; production data can be regenerated with step 01.

## Files

| Path | Contents |
|---|---|
| PLAN.md | the plan committed before the results |
| sql/S1, S2, S3 | base SQL for each style; `*_changes.diff` per change request |
| src/ | data generation, SQL generation, pandas specification, analysis, figures |
| data/fixture_2751/ | the small answer-check dataset |
| results/, figures/ | outputs |

## Sources

Synthetic data (created by the author). The comparison builds on F244 (common mistakes and tests in reporting SQL) and F247 (data mart).
