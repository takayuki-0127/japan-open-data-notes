# F205 Running an electricity demand forecast in practice (Part 1): what to decide before building, what an error costs, and when to rebuild

Japanese version: [README.md](README.md). Part 2 is [F206](../F206_power_forecast_practice_part2/README_EN.md).

This is the first half of a deep-dive series. It reuses forecasts built in earlier articles (F22 next-day demand, F92 peak upper bounds, F104 temperature and demand, F157 one year of operation) and checks with data **what you should decide before putting a forecast model to work**.

## Question

1. What should be decided before building a forecast model? Does the "best" model change depending on how you measure it and how early you must submit it?
2. How much does a forecast error cost? When running short and having too much have different costs, what value should you submit?
3. When should a model be rebuilt? How quickly can a shift ("drift") be detected, and how many false alarms does that cost?

## Data

No new data was collected.

| Data | Source article | Period | File |
|---|---|---|---|
| Hourly actual demand, Tokyo area | F22 (TEPCO Power Grid area supply-demand data) | Apr 2016 – Sep 2026 | data/hourly_tokyo_demand.csv |
| Hourly forecasts from one year of operation (Tokyo, by retraining policy) | F157 | Oct 2025 – Sep 2026, Oct 2024 – Sep 2025 | data/f157_pred_tokyo_2025_26.csv.gz, data/f157_pred_tokyo_2024_25.csv.gz |
| Same (Kansai) | F157 (Kansai Transmission and Distribution area data) | Oct 2025 – Sep 2026 | data/f157_pred_kansai_2025_26.csv.gz |
| Next-day peak point forecasts and quantile forecasts (Tokyo) | F92 | Apr 2020 – Sep 2026 | data/f92_peak_quantiles_tokyo.csv |

## What I did

### 1. How to measure, and when to submit
- Ranked the nine forecasts from F157 (fixed, quarterly, monthly, weekly retraining, a monitoring rule, last-3-years only, frozen 1 year ago, frozen 2 years ago, linear regression) on six metrics: hourly MAPE and RMSE, daily-volume MAPE, daily-peak MAPE, number of days the peak was under-forecast by more than 3%, and the 95th percentile of daily MAPE ("bad days").
- Measured agreement between metric rankings with Kendall's rank correlation. Differences from the fixed model got intervals from a block bootstrap that resamples one-week blocks of daily differences (1,000 draws).
- Effect of the deadline: compared "use the value from the same hour d days earlier" (d = 1, 2, 3, 7, 14) with a model submitted the evening before.

### 2. The cost of an error
- For the next-day peak, the cost of being 1 MW short was set to r times the cost of 1 MW of surplus (r = 1, 2, 4, 9, 19, 49). **These cost ratios are illustrative, not the costs of any real company.**
- Candidate values to submit: the point forecast as is; point forecast + 3, 5, 8%; quantile forecasts (F92 conformal prediction, τ = 0.5–0.99).
- In theory, with ratio r, submitting the τ = r/(1+r) quantile minimizes expected cost.
- As a practical procedure, **choose the cheapest margin based on errors up to the previous fiscal year and apply it to the next year** (6 rounds, FY2021 to the first half of FY2026). Also compared with F92's LightGBM quantiles.

### 3. When to rebuild
- Into the "fixed" F157 forecast, artificially injected a drift that raises actual demand by 1, 2, 3 or 5% from a given date (18 start dates, every two weeks from 15 Nov 2025 to 15 Jul 2026).
- Three monitoring rules, each with five thresholds:
  - MAPE over the last 14 days exceeds x%
  - Mean error (forecast − actual) over the last 7 days exceeds ±x%
  - Cumulative sum of daily errors (CUSUM, allowance 0.5%) exceeds x
- Alarms in a year with no injected drift count as "false alarms"; days from drift start to the first alarm count as "days to detect" (after an alarm, 14 days of quiet).
- Also checked how far a simple fix recovers accuracy after detection: rescaling the forecast by the last-14-day ratio of actual to forecast, instead of retraining.

## Findings

### 1. The "best" model changes with the metric, but differences between close models are within the intervals

| Forecast | Hourly MAPE | Daily volume MAPE | Peak MAPE | Days peak under by >3% | Bad days (95th pct) |
|---|---|---|---|---|---|
| Fixed (trained once before start) | 2.27% | 1.34% | 2.29% | 78 | 4.62% |
| Quarterly | 2.28% | 1.35% | 2.33% | 82 | **4.39%** |
| Monthly | 2.25% | 1.34% | 2.32% | 76 | 4.40% |
| Weekly | **2.23%** | **1.30%** | **2.24%** | **70** | 4.59% |
| Monitoring rule | 2.26% | 1.35% | 2.27% | 71 | 4.49% |
| Fixed, trained 1 year ago | 2.32% | 1.44% | 2.32% | **70** | 4.42% |
| Fixed, trained 2 years ago | 2.63% | 1.81% | 2.73% | 111 | 4.81% |
| Linear regression, retrained daily | 3.57% | 2.13% | 3.19% | 96 | 6.94% |

- On "bad days", quarterly ranks 1st and weekly 5th. On "peak under-forecast days", the model frozen 1 year ago ties with weekly for 1st.
- Rank correlations between metrics ranged from 0.22 to 1.00. "Bad days" agreed with other metrics only at 0.22–0.44.
- But for fixed, quarterly, monthly, weekly and the monitoring rule, the intervals crossed 0 on every metric (e.g. weekly − fixed on hourly MAPE: −0.04, interval −0.09 to +0.002). Clear differences appeared only for "frozen 2 years ago" (+0.37, +0.29 to +0.44), "trained on the last 3 years only" (+0.20) and linear regression (+1.30).
- In Tokyo FY2024/25, the model frozen 2 years ago had the fewest "peak under-forecast days" (18). It was biased 1.35% high on average (others: 0.13%); a habit of over-forecasting makes a model look good on an under-forecast metric.

### 2. The deadline changes the error
- Same hour 1 day earlier: 6.9%; 2 days: 10.7%; 3 days: 11.9%; 1 week: 8.1%; 2 weeks: 10.2%.
- Model submitted the evening before (retrained monthly): 2.25%.
- If the deadline is the morning of the previous day, only half of "yesterday" is known. Moving the deadline one day earlier changes which values are available and changes the error a lot.

### 3. The cost of an error: the higher the cost of shortage, the more a margin helps

Index with the point forecast as is = 100 (FY2020 to first half of FY2026).

| Cost of 1 MW short (× surplus) | Cheapest option | Index |
|---|---|---|
| 1× | Quantile 0.5 | 99.5 (about the same) |
| 2× | Point forecast as is | 100 |
| 4× | Quantile 0.8 | 84.7 |
| 9× | Point + 3% | 56.4 |
| 19× | Point + 5% | 35.7 |
| 49× | Point + 5% | 18.8 |

Choosing the margin from previous years and applying it to the next year (median and range over 6 rounds):

| Ratio | Margin | Point + margin | Quantile (conformal) | Quantile (LightGBM) |
|---|---|---|---|---|
| 1× | −0.5% | 98.0 (96.5–101.5) | 99.2 | 106.5 |
| 2× | +0.6% | 98.1 (94.4–104.5) | 113.9 | 116.7 |
| 4× | +1.8% | 84.3 (75.5–96.5) | 86.3 | 90.2 |
| 9× | +3.3% | 57.7 (47.7–71.5) | 61.7 | 69.3 |
| 19× | +4.6% | 36.8 (28.1–47.7) | 40.5 | 48.2 |
| 49× | +6.3% | 18.4 (13.3–27.0) | 21.4 | 27.4 |

- The margin chosen from the previous year is nearly the same in the next year (e.g. 3.1–4.1% at 9×). The simple "point + margin" was as cheap as, or cheaper than, the quantile models.
- If the ratio is about 2× or less, the point forecast as is is enough.

### 4. When to rebuild: watching the direction of the error detects drift sooner

Tokyo, Oct 2025 – Sep 2026, fixed model (drift = demand up 2%):

| Rule | Threshold | False alarms (1 year) | Days to detect (median) | Share of 1% drifts detected within 30 days |
|---|---|---|---|---|
| Last-14-day MAPE | 2.5% | 10 | 7.5 | 83% |
| Last-14-day MAPE | 3.0% | 7 | 19 | 44% |
| Last-14-day MAPE | 3.5% | 1 | 49.5 | 11% |
| Last-7-day mean error | ±1.5% | 6 | 4 | 94% |
| Last-7-day mean error | ±2.0% | 4 | 5 | 72% |
| CUSUM | 8 | 6 | 3 | 100% |
| CUSUM | 12 | 4 | 4.5 | 100% |

- At the same number of false alarms, rules that watch the direction of the error (7-day mean, CUSUM) detected drift several times faster than MAPE rules. MAPE gets buried in day-to-day noise.
- False alarms came around the New Year and long holidays (e.g. 27 Dec 2025, 13 Jan 2026).
- With demand raised 3% from Feb 2026, doing nothing gives MAPE 3.63% from February on (2.33% without drift). Simply rescaling by the last-14-day ratio brought it back to 2.40%. This works as first aid before retraining.

## Robustness

1. **Other data and years**: also ranked metrics for Kansai (FY2025/26) and Tokyo (FY2024/25). In Kansai, weekly and the monitoring rule ranked high on most metrics and the fixed model was last on 5 of 6 metrics (the fixed model itself had drifted; in F157, Kansai also improved from 2.89% to 2.64% with retraining). In Tokyo FY2024/25, rankings among close models again changed with the metric.
2. **Cost of errors**: showed the range over the 6 yearly re-choices of the margin, and compared two ways of building quantiles (conformal, LightGBM).
3. **When to rebuild**: 4 drift sizes × 18 start dates × 3 rules × 5 thresholds. In Tokyo FY2024/25, MAPE rules were also slow (2% drift, MAPE 3.0%: 32.5 days; 7-day mean ±2.0%: 9.5 days; 3 and 1 false alarms). In Kansai, the fixed model was off from the start, so there were many false alarms even without injected drift (MAPE 4.0%: 3 per year; others 6–26).
4. **Intervals**: the differences in 1 use a one-week block bootstrap (1,000 draws).

## What this does not show

- **The cost ratios are examples.** They are not the costs of any real company or electricity market prices. They only show how the answer moves when the ratio changes.
- The drift was only the artificial "demand rises uniformly by x%" kind. Drifts whose shape changes by hour or season (e.g. lower only at midday) were not tested.
- The rescaling after detection is first aid; it was not compared with retraining (retraining effects are in F157).
- Forecasts are limited to the LightGBM models (light settings) from F22 and F157. How rankings would change with other models is unknown.
- Two areas (Tokyo and Kansai), one to two years.

## How to use this at work

- Agree on the metric and the submission deadline before comparing models; they decide which model "wins".
- Treat small differences between similar retraining policies as noise unless an interval says otherwise.
- If shortage costs much more than surplus, add a margin chosen from past errors; a plain "point + margin" is a strong baseline.
- Monitor the signed error (7-day mean or CUSUM), not only MAPE, to catch drift early. Use ratio rescaling as a stopgap until retraining.

## Handed to Part 2 (F206)

- Part 2 covers: making area forecasts and the total consistent (hierarchical reconciliation: bottom-up, MinT), how to communicate forecast results (reports, dashboards, showing uncertainty as in F154), and what one year of operation taught.
- Useful files:
  - `data/f157_pred_tokyo_2025_26.csv.gz`, `data/f157_pred_kansai_2025_26.csv.gz`: hourly forecasts and actuals for Tokyo and Kansai over the same period (Oct 2025 – Sep 2026) — a starting point for reconciling "sum" vs "by area" (demand for all 10 areas must be collected separately).
  - `results/A_metrics_tokyo.csv`, `A_metrics_kansai.csv`: the six candidate reporting metrics and their values.
  - `results/B_rolling_margin.csv`: peak margins by cost ratio — an example of how to set an "upper bound" on a dashboard.
  - `results/C_drift_detection.csv`: candidate monitoring rules (suggested: 7-day mean ±1.5% or CUSUM 8; in Tokyo, 6 false alarms per year and a 2% drift detected in 3–4 days).
  - `results/main.json`: summary numbers.

## Figures

The figures have Japanese labels.
- `figures/f205_1_metric_rank.png`: rank of each forecast on each metric.
- `figures/f205_2_leadtime.png`: error by how many days before the target the forecast is fixed.
- `figures/f205_3_cost_curves.png`: cost index by submitted value, for each cost ratio.
- `figures/f205_4_cost_rolling.png`: cost when the margin is chosen from the previous years.
- `figures/f205_5_drift_tradeoff.png`: false alarms vs days to detect, by rule and threshold.
- `figures/f205_6_drift_example.png`: an example of a 3% drift from Feb 2026 and the rescaling fix.

## Reproduce

```
pip install -r requirements.txt
python src/03_分析.py   # builds results/ (about 8 seconds)
python src/04_図.py     # builds figures/
```
The data is in data/ (original collection steps are in the src/ of F22, F92 and F157). Random seed: 205.

## Files

| Path | Contents |
|---|---|
| data/ | demand actuals and the reused forecasts listed above |
| src/02_整形.py | data preparation |
| src/03_分析.py | analysis (metrics, costs, drift detection) |
| src/04_図.py | figures |
| results/ | tables for each part (A: metrics, B: costs, C: drift) and main.json |
| figures/ | six figures |

## Sources

- Processed from TEPCO Power Grid "area supply-demand data", Kansai Transmission and Distribution "area supply-demand results", and Japan Meteorological Agency historical weather data (collected in F22 and F157).
- Forecasts are the results of F22, F92 and F157 in japan-open-data-notes.
