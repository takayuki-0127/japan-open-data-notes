# F206 Running an electricity demand forecast in practice (Part 2): reconciling areas and totals, presenting forecasts, and one year of monitoring

Japanese version: [README.md](README.md). Part 1 is [F205](../F205_power_forecast_practice_part1/README_EN.md).

## Part 1 in three lines

- With the same nine forecasts, the "best" one changed with the metric; differences between close models were within chance.
- If being short costs 9 times as much as surplus, adding about 3% to the point forecast cut the cost of errors by about 40% (the cost ratio is illustrative).
- To detect drift, watching the direction of the error was several times faster than watching its size (MAPE).

## Question

1. If you forecast each area and the total separately, the numbers do not add up. What is the best way to make them consistent (bottom-up, top-down, OLS, WLS, MinT)?
2. For daily energy, is it better to forecast it directly or to add up 24 hourly forecasts (temporal hierarchy)?
3. How should forecasts be shown? Do 80% and 95% intervals cover as often as stated? What belongs on a dashboard?
4. Over one year of operation, when does the monitoring alarm fire? What does this become as a practical checklist?

## Data

- Hourly actual demand for the Tokyo and Kansai areas, and the F157 forecasts (Oct 2025 – Sep 2026). Mainly the F157 "LightGBM retrained weekly", checked with "monthly" and "fixed".
- A forecast that predicts the total (Tokyo + Kansai) directly was built in this folder (LightGBM, retrained monthly, trained from Apr 2024; inputs: hour, weekday, month, holiday, Tokyo and Osaka temperature, total demand 24 hours and 1 week earlier, previous-day mean).
- No new data was collected. Details in src/01_データ.md.

## What I did

- **Reconciliation (3 series: total = Tokyo + Kansai)**: for each day, weights were set using only the errors (actual − forecast) of the previous 90 days, and the 24 hours were reconciled (never using errors that were not yet known).
  - No reconciliation / bottom-up (BU) / top-down (TD: split by Tokyo's share per hour over the last 28 days) / equal weights (OLS) / weights from error variance (WLS) / also using error correlation (MinT, with Schäfer–Strimmer-type shrinkage of correlations toward 0).
- **Temporal hierarchy**: compared a LightGBM that forecasts daily energy directly (retrained monthly), the sum of the 24 hourly forecasts, and reconciliations of the two (weighted by count / by error variance).
- **Intervals**: hour-by-hour quantiles (10/90%, 2.5/97.5%) of "actual ÷ forecast − 1" over the previous 90 days, applied to the forecast.
- **Monitoring**: applied the example rule from F205 (alarm when the 7-day mean error exceeds ±1.5%) to Tokyo's weekly forecast for one year.
- **Evaluation period**: 1 Jan – 30 Sep 2026 (Oct–Dec 2025 builds up the error history). Monitoring starts Oct 2025.
- **Uncertainty of differences**: weekly block bootstrap (2,000 draws). Random seed 206.

## Findings

### 1. Before reconciliation, the total and its parts disagree

The gap between the direct total forecast and "Tokyo forecast + Kansai forecast" averaged 1.8% of the total per hour, and was 4.7% or more in the top 5% of hours. As daily means, it ranged from −6.0% to +6.1%.

### 2. Error by reconciliation method (hourly MAPE, %)

| Method | Total | Tokyo | Kansai |
|---|---|---|---|
| No reconciliation | 2.77 | 2.31 | 2.71 |
| Bottom-up (BU) | **2.08** | 2.31 | 2.71 |
| Top-down (TD) | 2.77 | 3.13 | 3.76 |
| Equal weights (OLS) | 2.42 | 2.50 | 3.28 |
| Error-variance weights (WLS) | 2.15 | 2.38 | 2.75 |
| Error correlation too (MinT) | **2.09** | 2.31 | 2.74 |

- For the total, adding Tokyo and Kansai (2.08%) beat forecasting the total directly (2.77%). The errors of Tokyo and Kansai correlate at 0.39, so part of them cancels when added.
- MinT minus BU: total +0.007 points (95% interval −0.002 to +0.016), Tokyo +0.002 (−0.005 to +0.009), Kansai +0.020 (−0.021 to +0.055). Practically the same.
- Top-down and equal weights pushed the error-prone total forecast into the parts and made Tokyo and Kansai worse.
- MinT's shrinkage intensity averaged 0.004, so the correlations were used almost as they were.

### 3. Daily energy (MAPE, %)

| Method | Tokyo | Kansai |
|---|---|---|
| Forecast daily energy directly | 2.22 | 2.32 |
| Add the 24 hourly forecasts | **1.37** | 1.89 |
| Reconcile (weighted by count) | 1.62 | 1.91 |
| Reconcile (weighted by error variance) | 1.38 | **1.87** |

### 4. Did the intervals cover as stated? (Jan–Sep 2026)

| Area | Error history | Share inside 80% interval | Share inside 95% interval | Width of 80% interval |
|---|---|---|---|---|
| Tokyo | 30 days | 75.3% | 90.3% | 7.0% |
| Tokyo | 90 days | 76.6% | 91.4% | 7.0% |
| Tokyo | 180 days | 77.2% | 92.3% | 6.9% |
| Kansai | 90 days | 76.8% | 91.7% | 8.3% |

- By month (Tokyo, 90 days): March–June had 82–87% inside the 80% interval, but January 67%, July 72%, August 63%. The 95% interval covered only 81% in August.
- At the daily peak hour, the actual stayed below the upper end of the 95% interval 90.8% of the time.

### 5. Monitoring (Tokyo, Oct 2025 – Sep 2026)

The 7-day mean error exceeded ±1.5% 9 times, on 28 days: end of year (28–31 Dec), around the January long weekend, the February long weekend (11–14 Feb), early March, mid-July (12–16 Jul), and the Obon holidays (12–17 Aug, up to 3.2%).

### 6. A sample dashboard

`dashboard/dashboard_sample.html` (static HTML with no external files). Assuming it was published at midnight before 22 Jul 2026 (the highest-demand day of the first half of FY2026), it places four things on one screen:

- Tomorrow's peak forecast and the 95% upper bound
- The 24-hour forecast with 80% and 95% intervals, and a preparation guide (peak forecast + 3.3%: F205's example where shortage costs 9× surplus)
- MAPE over the last 7 days and the 7-day mean error (monitoring)
- A note on how to read it (what to do when what happens)

## What one year taught (a practical checklist)

1. Do not forecast the total separately; add up the area forecasts. If you want reconciliation, use MinT or WLS. Top-down and equal weights make the parts worse.
2. Produce daily energy by adding the 24 hourly forecasts too; this had smaller errors than forecasting it directly.
3. Check every month whether the intervals cover as stated. They were too narrow at season changes and in midsummer and midwinter.
4. Monitor the direction of the error (7-day mean error). Most alarms came around long holidays, the New Year and Obon.
5. Put "forecast, intervals, preparation guide, monitoring, how to read" on one screen. Agree on the cost ratio with stakeholders and write it down.
6. Before comparing, align the deadline, evaluation period and metrics (Part 1).

## Robustness

- Length of error history (30, 90, 180 days): MinT total 2.08–2.10%, difference from BU +0.007 to +0.018.
- Area forecasts switched to "monthly" and "fixed": MinT minus BU on the total +0.008 and +0.012 (for "fixed" the interval does not cross 0; MinT is slightly worse).
- A weaker total forecast (no temperature, MAPE 4.06%): BU 2.08%, MinT 2.06% (difference −0.015, −0.033 to +0.003). MinT automatically lowered the weight of the total forecast. OLS worsened to 3.19%, TD to 4.06%.
- Seasons (Jan–Jun / Jul–Sep): the order of MinT and BU is the same in both. All methods have larger errors in Jul–Sep.
- Intervals: across error histories (30, 90, 180 days) and Kansai, 80% intervals covered 74–78% and 95% intervals 90–93%.

## What this does not show

- **Only two areas.** Demand for all 10 areas of Japan could not be collected because this working environment could not reach the grid operators' sites. With 10 areas, estimating MinT's correlations becomes harder and results may change.
- **Only one way of forecasting the total.** The direct total forecast has a shorter training period than Tokyo and Kansai (from Apr 2024). A better total forecast might let MinT beat BU.
- **Only one way of building intervals.** "Quantiles of the last 90 days of errors" cannot keep up with season changes. Methods such as adding last year's errors from the same season were not tried.
- **Costs are illustrative.** The preparation guide (+3.3%) uses Part 1's example where shortage costs 9× surplus, not a real company's costs.
- **The dashboard is a sample.** It is a static sample built from public data, not a real screen. What belongs on it depends on who looks at it and what they decide.
- **The causes of the alarms were not checked.** They coincided with holidays, the New Year and Obon, but whether those were the causes was not investigated (my interpretation).
- **One year only.** Oct 2025 – Sep 2026; another year may differ.

## How to use this at work

- Build forecasts at the most detailed level you trust and add them up; reconcile with MinT or WLS only when a separate total forecast must be kept.
- Report intervals together with their realized coverage, by month.
- Use a signed-error monitor and expect alarms around holidays.

## Figures

The figures have Japanese labels.
- `figures/f206_1_incoherence.png`: gap between the direct total forecast and the sum of the area forecasts.
- `figures/f206_2_reconcile_mape.png`: MAPE by reconciliation method.
- `figures/f206_3_mint_vs_bu.png`: difference between MinT and bottom-up, with intervals.
- `figures/f206_4_temporal.png`: daily energy — direct vs sum of hours vs reconciled.
- `figures/f206_5_dashboard.png`: screenshot of the sample dashboard.
- `figures/f206_6_coverage_alerts.png`: monthly interval coverage and monitoring alarms.

## Reproduce

```
pip install -r requirements.txt
python src/02_整形.py   # builds data/ (assumes the F205 and F22 folders are alongside; data/ is included, so this can be skipped)
python src/03_分析.py   # builds results/ (about 30 seconds)
python src/04_図.py     # builds figures/ and dashboard/dashboard_sample.html
```
figures/f206_5_dashboard.png is a screenshot of dashboard_sample.html taken with Playwright (Chromium, width 1100px, 2×).

## Files

| Path | Contents |
|---|---|
| data/ | actuals and forecasts for Tokyo and Kansai, and the direct total forecast |
| src/01_データ.md | data notes |
| src/02_整形.py | data preparation |
| src/03_分析.py | reconciliation, temporal hierarchy, intervals, monitoring |
| src/04_図.py | figures and the sample dashboard |
| dashboard/dashboard_sample.html | the sample dashboard |
| results/, figures/ | outputs |

## Sources

- Processed from TEPCO Power Grid "area supply-demand data", Kansai Transmission and Distribution "area supply-demand results", and Japan Meteorological Agency historical weather data (collected in F22).
- Forecasts are the results of F157 and F205 in japan-open-data-notes.
