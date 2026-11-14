# japan-open-data-notes (English summary)

[![reproduce](https://github.com/takayuki-0127/japan-open-data-notes/actions/workflows/reproduce.yml/badge.svg)](https://github.com/takayuki-0127/japan-open-data-notes/actions/workflows/reproduce.yml)

This repository holds the code, data, figures and results behind about 800 analysis articles written in Japanese on note.com.
Most articles use Japanese government statistics and open data; some recreate everyday business tasks with clearly fictional companies and synthetic data.

- One folder per article: `articles/<number>_<name>/` (README, data, figures, results, code). Each folder runs on its own.
- Articles from No. 551 onward are re-run every week by GitHub Actions to check that the results are reproduced ([tools/repro_check.py](tools/repro_check.py)).
- Index by method and business scene: [INDEX.md](INDEX.md) (Japanese). How the articles are made: [HOWTO.md](HOWTO.md). Known errors and fixes: [CORRECTIONS.md](CORRECTIONS.md). Code that was not executed: [UNVERIFIED.md](UNVERIFIED.md).
- Every article states what it **cannot** claim (data limits, association vs. causation, assumptions of the simulation).

## Ten articles to read first

| # | Article | Methods |
|---|---|---|
| 1 | [F205](articles/F205_power_forecast_practice_part1) / [F206](articles/F206_power_forecast_practice_part2) Running electricity demand forecasts in practice | forecast evaluation, asymmetric loss, monitoring, hierarchical reconciliation |
| 2 | [F201](articles/F201_minimum_wage_series_part1) / [F202](articles/F202_minimum_wage_series_part2) Minimum wage and employment | difference-in-differences, synthetic control, border-county comparison, power analysis |
| 3 | [F207](articles/F207_landprice_series_part1) / [F208](articles/F208_landprice_series_part2) Land prices and housing | hedonic regression, spatial models, explanation vs. prediction |
| 4 | [F165](articles/F165_reproducibility_audit) Re-running 40 article folders | reproducibility audit, environment pinning |
| 5 | [youtube-data-mart](https://github.com/takayuki-0127/youtube-data-mart) | SQL Server star schema, Power BI (DAX, RLS), BigQuery + dbt cross-check |
| 6 | [F250](articles/F250_sales_drop_explanation_fictional_retail) Explaining a month when sales fell | LMDI decomposition, calendar adjustment, noise band by simulation |
| 7 | [F237](articles/F237_ab_test_peeking_sequential) What goes wrong when you peek at an A/B test | group sequential tests (O'Brien–Fleming, Pocock), mSPRT |
| 8 | [F239](articles/F239_marketing_mix_model) How much does advertising drive sales? | marketing mix model (adstock, saturation), geo experiments, budget allocation |
| 9 | [F241](articles/F241_customer_churn_survival) How fast do customers leave? | Kaplan–Meier, Cox model, cohort tables, LTV extrapolation |
| 10 | [F275](articles/F275_sql_change_requests) Writing reporting SQL that survives definition changes | shared views, reconciliation tests, mutation testing |

### Short summaries

1. **Electricity demand forecasting (F205/F206).** One year of day-ahead forecasts. The ranking of models flipped depending on the error metric. Pricing the cost of misses showed that adding 3% to the point forecast cut the loss by about 40%. Simply summing area forecasts reduced the total error from 2.77% to 2.08%, as good as more elaborate reconciliation methods.
2. **Minimum wage (F201/F202).** Four designs on the same data all gave "inconclusive". The reason was not the method but the small variation in increases across prefectures: detecting an effect would need differences 7–14 times larger than those reported abroad. The articles separate "no effect" from "cannot be distinguished".
3. **Land prices (F207/F208).** Twenty years of official land price data. The effect of distance to a station ranged from −3% to −32% depending on specification, and new-station effects appeared before opening. Yearly re-fitted forecasts kept missing at the same sites; 94% of the error was site-specific.
4. **Reproducibility audit (F165).** Forty randomly chosen folders were re-run from scratch in a fresh environment. All regular articles reproduced; about half of the flagship articles did not, due to network access, empty folders and unpinned versions. The fixes were applied to later articles and led to the weekly check in this repository.
5. **YouTube data mart.** CSV exports flow through pandas → SQL Server (staging → star-schema mart) → Power BI with DAX and row-level security. The same views were rebuilt in BigQuery with dbt and the results matched.
6. **Sales drop explanation (F250, fictional supermarket).** Year-over-year sales of −1.1% were split exactly into customers, items per visit and unit price (LMDI), with calendar effects estimated separately. Twenty re-runs with different random seeds gave a noise band of ±1.1 pt for the whole company and ±1.3–1.7 pt for regions, so a one-month regional gap could not be called a cause.
7. **A/B test peeking (F237, simulation).** Checking daily and stopping at |z| > 1.96 raised the false positive rate from 4.8% to 21.9% (46% if checked hourly). An O'Brien–Fleming design kept 5% and about 84% power while ending three days earlier on average when there was an effect, but every early-stopping rule overstated the effect by 1.13–1.42×.
8. **Marketing mix model (F239).** On industry statistics the advertising elasticity moved from +0.15 to −0.06 depending on controls. In a simulated company where spend follows expected demand, the MMM overstated ROI by 53–68%; geo experiments were nearly unbiased but noisy (24–31% per run). Reallocating budget had about 5% upside, and an MMM-based plan was worse than the status quo in 1 of 4–10 runs.
9. **Customer churn (F241, IBM Telco sample data + corporate registry).** A "26.5% churn rate" has no time frame; survival analysis gave 84.3% retained at 12 months and 59.3% at 72 months, with churn concentrated in the first months. LTV to 72 months was $3,124, while extrapolating to 30 years gave $5,180–7,903 depending on the model.
10. **Reporting SQL (F275, fictional retailer).** Eight monthly reports were written three ways and eight definition changes were applied. Shared views cut the files to edit from 8 to 1. Reconciliation tests caught 80% of single missed edits; a small golden dataset with edge cases caught 95%.

## Data and licenses

Public data come from Japanese government sources (e-Stat, ministries, the National Tax Agency corporate number database, etc.) under their terms of use; sources are listed in each article's README. Fictional companies and synthetic data are labeled as such.
