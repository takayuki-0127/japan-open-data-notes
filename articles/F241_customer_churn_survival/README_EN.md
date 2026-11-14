# F241 How long do customers stay? (Survival analysis, cohort tables and LTV in practice)

Japanese version: [README.md](README.md).

The eleventh article in the series "analyses close to real work" (F231–F245). It turns churn analysis into a practical form using the tools of survival analysis. Earlier related articles: F236–F238 (A/B testing), F28 (survival of companies).

## Question

1. What does a number like "churn rate 26.5%" mean, and what does it not mean?
2. How much does leaving differ by contract type and services used?
3. How do you build and read a retention table by cohort (start year)?
4. How confidently can LTV (future revenue per customer) be stated?

## Data

- **A: IBM "Telco Customer Churn"** (a public sample of 7,043 customers of a fictional telecom company, Apache License 2.0): tenure (0–72 months), whether they churned, contract type, services, payment method and monthly charge. Not a real company or real customers.
- **B: company survival** (data from F28 in this series, built from the National Tax Agency's Corporate Number Publication Site bulk data: 1.288 million joint-stock and limited liability companies founded 2016–2025, observed until 30 Sep 2026). Company names and numbers are not used.
- "Sakura Line" in the dashboard is a fictional company name.

## What I did

- Kaplan–Meier (survival accounting for censoring), monthly life table (hazard), restricted mean survival time (to 72 months).
- Log-rank test, Cox proportional hazards model, test of proportional hazards (Schoenfeld residuals), Cox stratified by contract, train on half and validate on the other half.
- Cohort retention table (founding year × years elapsed, only cells everyone could be observed for), also built in SQL.
- LTV: monthly charge × survival, discounted at 5% a year and summed (the discount rate is illustrative). Beyond 72 months, extrapolated with a constant rate from the last year, exponential, Weibull, log-normal and sBG (a model where each customer has a different monthly churn probability), and compared.
- Wrote the life table and cohort table in SQL (SQL Server compatible: CTE, CASE and SUM only), ran them in DuckDB and matched with Python.

## Findings

### A: Fictional telecom company

- "Share who churned" is 26.5%, but it counts customers with very different tenures at once, so it has no time period. With Kaplan–Meier, the share remaining is 84.3% at 12 months, 78.9% at 24 months and 59.3% at 72 months.
- Monthly hazard: 5.4% in month 1, 0.76% in month 12, 0.45% on average in years 2–3. Churn concentrates in the first few months, then rises slightly to 0.84% on average in years 5–6.
- Churned customers stayed 18.0 months on average, but the restricted mean tenure of everyone up to 72 months is 54.5 months. Computing "how many months until people leave" only from those who left makes it look much shorter.
- Contract type: month-to-month (3,875 customers) 70.3% remaining at 12 months and 12.9% at 72 months; one-year contracts 56.8% at 72 months; two-year contracts 93.6% (log-rank p < 0.001).
- Cox (hazard ratio, 95% interval): two-year contract 0.03 (0.02–0.05), one-year 0.18 (0.15–0.21), fiber 3.70 (3.01–4.55), electronic check 1.65 (1.50–1.82), has a partner 0.55, has tech support 0.76. $10 higher monthly charge 0.75 (holding services such as fiber fixed). C-index 0.846.
- Proportional hazards did not hold for contract type and others (p < 0.01). Stratifying by contract left the other hazard ratios almost unchanged (fiber 3.53, electronic check 1.63, partner 0.56).
- Training on half and predicting the other half: 12-month survival predicted 83.6% vs actual 84.6%; 24-month 75.8% vs 80.0% (C-index 0.847).
- LTV (up to 72 months, 5% annual discount): $3,124 per customer (95% interval from resampling customers 3,067–3,179). Month-to-month 2,168, one-year 3,807, two-year 3,822.
- Extrapolating to 30 years gives $5,180–7,903, a 1.5-fold range: constant last-year rate 5,180, exponential 5,250, Weibull 6,586, log-normal 7,176, sBG 7,903. sBG fits best by AIC (20,936; log-normal 21,041, Weibull 21,157, exponential 21,697). At 72 months, the models give 55–66% vs KM 59.3%.
- The common shortcut "monthly charge ÷ monthly churn rate" (churns ÷ total customer-months = 0.82%) gives $7,900 (no discount, infinite horizon). "Monthly charge ÷ 26.5%" mixes units and is meaningless ($244).

### B: Company cohort table

- For joint-stock companies founded 2016–2020, the share still operating is 99.3–99.4% after 1 year and 94.6–95.0% after 5 years, almost the same across founding years.
- Limited liability companies: 92.4–93.0% after 5 years, about 2 points lower than joint-stock companies.
- For cohorts observable for the full 5 years (joint-stock, founded 2016–2020), the cohort table and Kaplan–Meier agree on 5-year survival (94.75%). When mixing cohorts observed only partway, use KM.

## Robustness

- Proportional hazards violation: hazard ratios are almost unchanged in the contract-stratified Cox.
- Calibration with a train/validation split (above).
- Five extrapolation models for LTV; discount rates 0%, 3%, 10% (to 72 months: $3,567, 3,289, 2,771).
- Bootstrap of LTV (300 draws).
- Excluding customers with 0 months (11): 84.3% at 12 months and 59.3% at 72 months, unchanged.
- Matching with SQL: life table, max difference over 72 rows 9×10⁻¹⁰; cohort table, max difference over 90 cells 3×10⁻⁸ (CSV rounding).

## What this does not show

- **Dataset A is a snapshot.** Customers who joined more than 72 months ago and already left are not included (left truncation). Treating tenure as "time" is common, but this is not proper follow-up data.
- The reasons for churn are unknown. Cox hazard ratios are associations, not causes such as "removing fiber would reduce churn" (fiber customers also pay more and face more competition, etc.).
- The monthly-charge hazard ratio of 0.75 holds services fixed; it does not mean "raising prices reduces churn".
- The LTV discount rate, the 30-year horizon and using revenue rather than gross profit are all illustrative.
- B is about companies closing, not customers churning; it is an example of how to build a cohort table.

## How to use this at work

- Replace a single "churn rate" with a survival curve and say over what period.
- Compute average tenure with censoring (restricted mean), not from churned customers only.
- Present LTV as a range across extrapolation models, and state the horizon and discount rate.

## Figures

The figures have Japanese labels.
- `figures/fig1_km_vs_naive.png`: Kaplan–Meier survival vs the naive churn share.
- `figures/fig2_km_contract.png`: survival by contract type.
- `figures/fig3_cox.png`: Cox hazard ratios.
- `figures/fig4_cohort_table.png`: company cohort retention table.
- `figures/fig5_ltv_extrapolation.png`: LTV under different extrapolation models.
- `figures/fig6_dashboard.png`: screenshot of the churn and retention dashboard.

## Reproduce

```
pip install -r requirements.txt
python src/01_取得.py      # downloads two files into data/raw/ (the company data comes from F28's repository, about 6 MB)
python src/02_整形.py
python src/03_分析.py      # results/
python src/04_図.py        # figures/, dashboard.html
python src/05_SQL照合.py   # runs sql/ in DuckDB and matches
```
Figure 6 is a screenshot of `dashboard.html` taken with Playwright.

## Files

- `data/telco_clean.csv`: prepared A (needed columns only)
- `data/houjin_cohort.csv.gz`: prepared B (founding year, type, months survived, closed or not)
- `data/raw/Telco-Customer-Churn.csv`: raw A (Apache 2.0). Raw B is not stored because of size; 01_取得.py downloads it.
- `sql/01_life_table.sql`, `sql/02_cohort_retention.sql`
- `results/`: summary.json, life table, KM, Cox, proportional hazards test, cohort table, extrapolation, SQL check
- `dashboard.html`: churn and retention dashboard (an example for a fictional company's internal team)

## Sources

- Processed from IBM "Telco Customer Churn" sample data (https://github.com/IBM/telco-customer-churn-on-icp4d, Apache License 2.0).
- Processed from the National Tax Agency "Corporate Number Publication Site" bulk data (collected and prepared in F28).
