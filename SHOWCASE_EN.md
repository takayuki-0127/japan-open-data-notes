# Showcase: 14 works in English

I publish more than 1,000 analyses built on public data and fictional companies' data, each with its code and data.

Below are 14 of them with full English write-ups. Each line gives the question and the main result; the link opens the English README in the work's folder. Numbers come from each work's README and results/. Fictional companies and simulated data are labeled as such in every write-up.

## Forecasting and causal inference on public data

| # | Work | Question | Main result |
|---|---|---|---|
| 1 | [F205](articles/F205_power_forecast_practice_part1/README_EN.md) / [F206](articles/F206_power_forecast_practice_part2/README_EN.md) Electricity demand forecasting in practice | What should be decided before using a forecast, what does an error cost, and how should area and total forecasts be reconciled? | The "best" model changed with the metric; with shortage costing 9× surplus, adding about 3% to the point forecast cut the cost of errors by about 40%; summing area forecasts cut the total's error from 2.77% to 2.08%. |
| 2 | [F201](articles/F201_minimum_wage_series_part1/README_EN.md) / [F202](articles/F202_minimum_wage_series_part2/README_EN.md) Minimum wage and work | How much does the estimated employment effect depend on the method? | Four methods all gave an unclear effect (elasticity −0.18 to −0.02); the smallest detectable effect was 7–14 times the size commonly reported abroad. |
| 3 | [F207](articles/F207_landprice_series_part1/README_EN.md) / [F208](articles/F208_landprice_series_part2/README_EN.md) Land prices and housing | Where did land prices rise, how much do stations matter, and where do forecasts keep missing? | The station-distance effect ranged from −3% to −32% by specification; prices near new stations rose before opening; 94% of forecast error variance was specific to the location. |

## Business analysis (fictional companies and simulations)

| # | Work | Question | Main result |
|---|---|---|---|
| 4 | [F250](articles/F250_sales_drop_explanation_fictional_retail/README_EN.md) Explaining a month when sales fell (fictional supermarket) | How do you explain a sales drop on one page without turning noise into reasons? | −1.1% split into price +4.1 pt, items −1.3 pt, calendar −0.9 pt and customers −3.1 pt; a one-month regional gap could not be separated from a range of chance of ±1.3–1.7 pt. |
| 5 | [F237](articles/F237_ab_test_peeking_sequential/README_EN.md) Peeking at A/B tests (simulation) | What happens if you check daily and stop when significant? | False positives rose from 4.8% to 21.9%; an O'Brien–Fleming boundary kept 5% and finished 3 days earlier on average, but early stops overstated the effect 1.13–1.42×. |
| 6 | [F239](articles/F239_marketing_mix_model/README_EN.md) Marketing mix modeling (industry data + fictional company) | How well can an MMM recover each channel's ROI? | When spend follows demand, MMM overstated ROI by 53–68%; geographic experiments were nearly unbiased but noisy; budget re-allocation had about 5% upside. |
| 7 | [F241](articles/F241_customer_churn_survival/README_EN.md) Customer churn (public sample data) | What does a churn rate mean, and how certain is LTV? | "26.5% churned" has no time period; survival was 84.3% at 12 months and 59.3% at 72 months; LTV extrapolated to 30 years ranged from $5,180 to $7,903. |

## Data engineering and BI

| # | Work | Question | Main result |
|---|---|---|---|
| 8 | [youtube-data-mart](https://github.com/takayuki-0127/youtube-data-mart/blob/main/README_EN.md) | What are a YouTube channel's views associated with, using a pipeline that gives the same numbers every run? | pandas → SQL Server star schema → Power BI (DAX, RLS); Shorts got about 2.8× the daily views of long-form videos (association); the same view matched in BigQuery and dbt. |
| 9 | [F275](articles/F275_sql_change_requests/README_EN.md) Reporting SQL and definition changes (fictional retailer) | How should reporting SQL be written so changes are easy and forgotten edits are caught? | Shared views cut files to edit from 8 to 1; reconciliation caught 80% of single forgotten edits, answer checks with edge cases 95%, but a mistake in a shared view passed every reconciliation. |
| 10 | [F298](articles/F298_bigquery_scan_cost/README_EN.md) BigQuery scan cost on 64.6 billion rows | How much does the way you write a query change the bytes read? | Filtering by a clustered column cut bytes read to 1/23; `SELECT * LIMIT 10` read 1/67 of the estimate; approximate counting cut computation to a third. |
| 11 | [dbt_retail_mart](projects/dbt_retail_mart/README_EN.md) (with [Dagster](projects/dbt_retail_mart/orchestration/README_EN.md)) | Can report definitions live in one place, with tests that stop the pipeline when they drift? | 26 models and 71 tests; each of 8 definition changes is one `vars` change; a Dagster job stops before downstream steps when an answer check fails. |

## Reproducibility and reading research

| # | Work | Question | Main result |
|---|---|---|---|
| 12 | [F165](articles/F165_reproducibility_audit/README_EN.md) Re-running 40 article folders | Do the analyses give the same numbers when re-run from scratch? | Numbers matched in 33 of 40 (estimated 85% overall); all 20 regular articles reproduced as is, 9 of 20 feature articles. |
| 13 | [F297](articles/F297_article_practice_audit/README_EN.md) Auditing 1,066 articles against my own writing rules | From when, and how well, were the rules followed? | "What this does not show" appears in 95% of articles from number 266; a plan written in advance appears in only 5% of feature articles; 25 random re-runs all matched. |
| 14 | [P01](papers/P01_did_reading_order/README_EN.md), [P02](papers/P02_ab_testing_practice/README_EN.md), [P03](papers/P03_forecast_uncertainty/README_EN.md) Reading papers and trying them | What happens when methods from key papers are tried on other data? | Staggered DiD: TWFE gave half the true effect when effects grew; A/B testing: a 1% logging loss went unnoticed for 14 days; conformal intervals fell to 82% coverage when inputs changed and recovered to 90% when rebuilt from recent errors. Summaries of all ten papers: [papers/README_EN.md](papers/README_EN.md). |

The full Japanese index is in [INDEX.md](INDEX.md); the English overview of the repository is in [README_EN.md](README_EN.md).
