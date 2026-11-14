# Reading papers and trying them on real or simulated data (English summary)

Each folder reads well-known papers that matter in day-to-day data work and applies the same ideas to Japanese public data or to seeded simulations. These are not replications of the papers' own results: the question is what happens when the method is used on different data. Text and figures are written and drawn from scratch; links point to free versions of the papers. Full write-ups are in Japanese.

## Long reads

**[P01](P01_did_reading_order) — New difference-in-differences estimators, in reading order.**
Papers: Goodman-Bacon (2021), Callaway & Sant'Anna (2021), Sun & Abraham (2021), Rambachan & Roth (2023).
In a simulation where effects grow over time, two-way fixed effects underestimated the true effect by 52% (by 92% when no unit is never treated), because 25% of the weight came from comparisons against already-treated units. Callaway–Sant'Anna and Sun–Abraham estimators were within 1%. A binned event study (−5 to +5) produced spurious pre-trends (mean −0.71 where the truth is 0). When parallel trends fail, the new estimators are also off (+26%); on the prefecture panel from F296, no effect can be claimed even without allowing for violations (simplified Rambachan–Roth bound).

**[P02](P02_ab_testing_practice) — Where A/B test results stop being trustworthy.**
Papers: Kohavi et al. (2012), Deng et al. (2013, CUPED), Johari, Pekelis & Walsh (always-valid inference).
A 1% logging loss in the treatment group shifted the effect by +1.1%, but a sample ratio mismatch test caught it within 14 days in only 2.3% of runs (92% within 7 days for a 5% loss). CUPED's remaining variance followed 1−ρ² (34% with a 14-day pre-period); using an in-experiment covariate shrank a +3.0% effect to +0.57%. Peeking daily raised false positives from 5.3% to 23% (47% hourly); mSPRT kept them at 2–3% at the cost of power (84% → about 60% at 14 days).

**[P03](P03_forecast_uncertainty) — Do prediction intervals cover as promised?**
Papers: Angelopoulos & Bates (2021), Wickramasuriya, Athanasopoulos & Hyndman (2019, MinT), Gibbs & Candès (2021).
With exchangeable data, split conformal reached 90% on average, but with only 20 calibration points coverage fell below 85% in 18% of 2,000 runs. On Tokyo electricity demand, switching to forecast temperatures in production dropped a fixed interval's coverage to 82% (66% in the worst month); recalibrating on the last 28 days or adaptive conformal restored 89–90%, with intervals 1.3–1.5 times wider. On 58 lodging series, shrinkage MinT cut the total squared error by 18%; reconciled point forecasts add up, but interval bounds do not (prefecture upper bounds summed 3% above the national one).

## Short reads

- **[P04](P04_double_ml) Double/debiased ML (Chernozhukov et al., 2018).** OLS was biased by +0.51 (0% coverage); DML with LightGBM removed the bias, but with deep random forests a bias of +0.09 remained (25% coverage). DML is only as good as its nuisance learners.
- **[P05](P05_causal_forest) Causal forests (Wager & Athey, 2018).** Honest splitting halved the RMSE of individual effects (0.20 vs 0.40; T-learner 0.57), and 90% intervals covered 87%.
- **[P06](P06_shap) SHAP (Lundberg & Lee, 2017).** With correlated features, a feature with no effect received up to 26% of total SHAP importance in a column-subsampling model; SHAP scaled with effect size (2:1) while permutation importance scaled with its square (4:1).
- **[P07](P07_leakage) Leakage (Kapoor & Narayanan, 2022; Kaufman et al., 2012).** Preprocessing leakage: CV AUC 0.80 vs 0.50 in production. Target leakage: 0.94 vs 0.72, worse than the honest model (0.73). Time leakage: 1.7% vs 2.8% error.
- **[P08](P08_ml_technical_debt) Hidden technical debt (Sculley et al., 2015).** Applied to three of this repository's systems: the forecasting app had 8 of 9 debt types unaddressed or partly addressed; the dbt mart handled 7.
- **[P09](P09_ml_test_score) ML Test Score (Breck et al., 2017).** An honest self-assessment of the YouTube views predictor: 0.5 points out of the rubric's 28 tests, with no automated checks yet.
- **[P10](P10_forking_paths) Garden of forking paths (Gelman & Loken, 2013).** In A/A tests, a pre-specified analysis gave 4.4% false positives; choosing among 40 reasonable analyses gave 43%.
