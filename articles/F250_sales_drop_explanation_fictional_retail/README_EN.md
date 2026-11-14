# F250 Explaining why sales fell in a month (reproducing a business task at a fictional company)

Japanese version: [README.md](README.md).

The fifth article in the series "reproducing business tasks at a fictional company". At the fictional supermarket chain **SampleMart (fictional)**, the reasons why same-store sales fell below the previous year in one month (March 2026) are broken down into factors, and a one-page report for a management meeting is written.

> **The company and all its numbers are fictional (data synthesized with random numbers).** No real company, store or customer data is used. Only the seasonal shape of sales and the pace of food price increases (F246's settings), and the industry year-on-year change shown for reference (Commercial Dynamics Statistics), are borrowed from public data.

## Question

In a month when same-store sales fell below the previous year, how do you explain "why" on one page without turning random fluctuation into reasons?

## Data

| Data | Contents | How obtained |
|---|---|---|
| F247's mart | store × day, store × day × department, store × month, dimensions (store, department, date) | `src/01_取得.py` fetches it from F247 commit e8ba90f (not stored in this folder) |
| F246's synthesis code | `gen(seed)`: regenerates the data changing only the random seed | fetched from F246 commit 3006b82 |
| Commercial Dynamics Statistics (supermarkets, monthly) | industry year-on-year change, for reference | the prepared file in F246's data/raw (no new collection) |

## What I did

1. **Same-store year-on-year**: same stores = open 13+ months at the start of the month and open through the end of the month (F246's rule). Year-on-year is a ratio of totals.
2. **Three factors**: sales = customers (number of receipts) × items per visit × price per item. Contributions were allocated with log-mean weights (LMDI) so that they add up exactly to the sales year-on-year change.
3. **Calendar effect**: regressed log receipts by store × day for the previous fiscal years (FY2022–FY2024) on weekday, weekday holidays and year-end (removing store × month means, i.e. store × month fixed effects). Using those coefficients, the calendar effect is the ratio of the summed "day weights" of this year's month to the same month last year (this includes differences in the number of days).
4. **Regions, departments, stores**: looked at the difference (pt) from the overall movement. Only differences beyond the range of chance become candidate reasons.
5. **Range of chance**: generated 20 datasets with F246's `gen(seed)` (seeds 0–19) and repeated the calculation. 1.645 × the standard deviation of deviations from the seed average (the "true" value of the settings) is the half-width of a 90% range.
6. **Answer check**: computed the true factors from the synthesis settings (weekday coefficients, prices, seasonal shape of sales, regional trends) and compared.
7. **SQL**: also computed same-store year-on-year and the three factors in SQL (`sql/10_existing_store_yoy.sql`) and matched them with pandas, using DuckDB (not run on SQL Server).

## Findings

- **Same-store sales in March 2026 were −1.1% year on year (21 stores)**, the only month below the previous year in FY2025.
- Contributions to the change: price per item **+4.1 pt** (price increases), items per visit **−1.3 pt**, calendar **−0.9 pt** (one fewer Saturday than last year), calendar-adjusted customers **−3.1 pt**. Calendar-adjusted, sales were **−0.2%**.
- Calendar-adjusted customers (−3.0%) were the weakest month of the fiscal year. The industry (Commercial Dynamics Statistics, supermarkets, all stores, nominal) also had its lowest growth of the year in March at +1.3%.
- The **90% range of chance**, measured over 20 datasets that differ only in random numbers, was **±1.1 pt for company-wide monthly sales year-on-year**; ±1.3–1.7 pt for regional differences, ±0.3–0.6 pt for departments and ±3.4–6.6 pt for a single store.
- Looking at March alone suggests "suburbs are weak (−1.7 pt vs overall)" and "rural areas are unremarkable (−0.6 pt)", but the true differences in the settings were suburbs −0.1 pt and rural −2.2 pt. **One month of regional differences loses to chance.** Over the 12 months of the fiscal year, rural −2.3 pt and urban +2.1 pt (range ±0.4–0.5 pt) show the differences as set.
- Among 31 items (regions, departments, stores), chance alone pushes an average of 3.1 (up to 6) outside their ranges. In March, two stores were outside (rural store 19 and urban store 08); checking the answer, store 08 really was +4.2 pt in the settings (ramp-up after opening), while store 19 was −1.8 pt and the rest was chance.
- Based on this, the one-page report is ordered "conclusion → numbers (contributions and ranges of chance) → what not to treat as a reason → what to do next" (`reports/report_202603_onepage.md`). For comparison, a "first draft" that lists numbers from the top and turns random noise into reasons is also kept (`reports/report_202603_first_draft.md`).

| Item (March 2026, same stores) | Value | 90% range of chance | True value in the settings |
|---|---|---|---|
| Sales year-on-year | −1.13% | ±1.12 pt | −0.87% (mean of 20 datasets) |
| Price per item | +4.18% | ±0.23 pt | +4.0% (price setting; shifts slightly with the order of flyer days) |
| Items per visit | −1.26% | ±0.22 pt | −1.37% |
| Calendar effect (customers) | −0.89% | ±0.01 pt | −0.89% |
| Calendar-adjusted customers | −3.02% | ±1.09 pt | −2.50% (mean of 20; market volume −2.25% and regional trend −0.15%) |
| All stores (including new and closed) | −1.02% | | |
| Industry (Commercial Dynamics Statistics, supermarkets) | +1.25% | | fiscal-year average +4.2% |

| Region (calendar-adjusted customers, difference from overall) | March | March range | 12 months | 12-month range | True difference (12 months, mean of 20) |
|---|---|---|---|---|---|
| Urban | +2.0 pt | ±1.3 pt | +2.1 pt | ±0.4 pt | +1.7 pt |
| Suburban | −1.7 pt | ±1.6 pt | −0.4 pt | ±0.5 pt | −0.0 pt |
| Rural | −0.6 pt | ±1.7 pt | −2.3 pt | ±0.5 pt | −2.2 pt |

- Month by month, the urban and rural regions (which have true differences) were outside their ranges in 60% and 69% of 12 months × 20 datasets in FY2025; the suburban region (no true difference) was outside in 12%.
- Applying the same template to the six months below the previous year (Apr, May, Jul, Sep, Oct 2024 and Mar 2026), every month shows "price per item about +4 pt > 0, calendar-adjusted customers < 0". September 2024 (−0.4%) was below the previous year in only half of the 20 datasets — indistinguishable from chance.
- Detailed tables: `results/A_monthly_decomposition_seed0.csv` (each month's breakdown), `results/C_target_items_vs_band.csv` (March items and ranges), `results/E_down_months.csv` (the six months below the previous year), `results/main.json`.

## Robustness

| Check | Result |
|---|---|
| Order of decomposition (customers → items → price, etc., 6 orders) | customers −3.84 to −4.05 pt, items −1.21 to −1.31 pt, price +3.97 to +4.18 pt; the LMDI values lie in between |
| How the calendar is measured | regression −0.89%, compared with 364 days earlier (same weekday) −0.96%, weighting by last year's weekday averages −0.89%, answer in the settings −0.89% |
| Regression training period | FY2022–24 −0.893%, FY2024 only −0.898%, FY2023–24 −0.890%, including FY2025 −0.891% |
| Weekday coefficients (log) vs the answer | Sat 0.251 (answer 0.250), Sun 0.146 (0.147), Wed 0.138 (0.139), weekday holiday 0.071 (0.068) |
| 20 random seeds | March sales year-on-year −1.87% to +0.63% (mean −0.87%); below the previous year in 17 of 20 (85%); calendar-adjusted customers negative for every seed (−3.4 to −1.1%) |
| SQL vs pandas | same-store counts and the four year-on-year rates match for 24 months (max difference 9.7×10⁻¹⁷) |
| F247's mart vs F246's gen(0) | max difference in monthly sales year-on-year 1.7×10⁻⁸ (yen rounding only) |

## What this does not show

- **The numbers are synthetic data for a fictional company.** They do not show real supermarkets' customers, prices or ranges of chance. The range of chance is set by the synthesis settings (e.g. store × month noise σ = 2%).
- In the synthesis, the monthly shape of customers is built from Commercial Dynamics Statistics, so **moving in the same direction as the industry is partly by construction**. In practice, "market-wide movement" in the report would be judged together with other evidence (competitor openings, weather, nearby stores' promotions).
- The calendar effect was measured on customers only. Flyer days (Wed, Sat) slightly lower price per item in the settings, so a March with fewer Saturdays shows a slightly higher price per item (part of the gap between +4.18% and the set +4.0% — my interpretation).
- The range of chance was measured as deviation from the set values. In practice the true values are unknown, so it must be estimated from past month-to-month variation or by recombining stores.
- The one-page format is the author's choice; the right form depends on the company and the readers.

## How to use this at work

- Report contributions together with a range of chance, and write down what you will not treat as a reason this month.
- Always separate the calendar effect before talking about customers.
- Treat a single month of regional or store differences as a candidate to check next month, not a conclusion.

### How to write the one-page report (decided in this article)

1. Put the conclusion in the first three lines: what, by how much, and why (largest contribution first). Always show the calendar effect separately.
2. Use one table that puts contributions next to the ranges of chance.
3. Write "what not to treat as a reason": regions, departments and stores within the range of chance. Even items beyond the range, if only for one month, stay "candidates" to check next month.
4. Next steps: what to check with next month's numbers, and what not to do until then.

## Figures

The figures have Japanese labels.
- `figures/fig1_monthly_yoy_band.png`: monthly same-store year-on-year with the range of chance.
- `figures/fig2_waterfall_202603.png`: waterfall of March 2026 contributions.
- `figures/fig3_area_month_vs_year.png`: regional differences, one month vs the full year.
- `figures/fig4_category_store_band.png`: departments and stores against their ranges.
- `figures/fig5_down_months_same_template.png`: the same template applied to all months below the previous year.
- `figures/fig6_onepage_report.png`: image of the one-page report.

## Reproduce

```
pip install -r requirements.txt
python src/01_取得.py      # fetches F247's mart and F246's synthesis code into data/
python src/02_整形.py      # checks shapes (does the same-store flag match the mart?)
python src/03_分析.py      # decomposition, range of chance (20 datasets, about 1 minute), answer check, robustness → results/
python src/04_報告.py      # one-page report and first draft → reports/
python src/05_図.py        # figures (Figure 6 renders the report HTML with playwright)
python src/06_SQL照合.py   # SQL vs pandas
```

## Files

| Path | Contents |
|---|---|
| src/ | the six scripts above |
| sql/10_existing_store_yoy.sql | same-store year-on-year and factors in SQL |
| reports/ | the one-page report and the first draft |
| results/ | tables and main.json |
| figures/ | six figures |

## Sources

- Processed by the author from the Ministry of Economy, Trade and Industry "Commercial Dynamics Statistics" (supermarkets, monthly sales), using F246's prepared data.
- SampleMart (fictional) synthetic data is from F246 (synthesized by the author from METI Commercial Dynamics Statistics, the MIC Family Income and Expenditure Survey, and Cabinet Office national holidays). Data shaping is F247.
- Not related to any real company.
