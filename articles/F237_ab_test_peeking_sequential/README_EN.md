# F237 What goes wrong when you peek at an A/B test before it ends?

Japanese version: [README.md](README.md).

The seventh article in the series "analyses close to real work" (F231–F245). It uses simulation to check what happens if, after starting an A/B test, you look at the results every day (or every hour) and "stop when it becomes significant". It also compares, under the same conditions, methods that keep false positives at 5% even when peeking (group sequential tests with α-spending functions, and mSPRT), and summarizes them as a table of operating rules. The assumptions (baseline conversion 5%, target lift +10%, 5,000 visitors a day) are the same as the design table in F236 ("how many people does an A/B test need?"). All test data is simulated, imagining a fictional online store, "Midori Mall".

## Question

- If you check the result many times and stop whenever |z| ≥ 1.96, how much more often do you declare "significant" when there is no real difference?
- What boundaries (stopping rules) keep false positives at 5% even with peeking? Do they stop earlier?
- How does an "always-valid p-value" (mSPRT) compare with looking only on planned days?
- Can you trust the size of the difference when you stop early?

## Data

All test data is simulated (`src/common.py`).

| Assumption | Value | Reason |
|---|---|---|
| Current conversion (baseline) | 5% | same as F236 |
| Lift to detect | relative +10% (5% → 5.5%) | same as F236 |
| Visitors | 5,000 a day (half to each group, evenly by hour) | a row of F236's design table |
| Fixed decision day | day 14 (35,000 per group) | F236's formula needs 31,234 for +10%, rounded up to whole weeks |
| Cap for continuous monitoring | 28 days | for the mSPRT comparison |

20,000 runs per condition (10,000 for robustness checks). Fixed random seeds.

## What I did

- **Unadjusted peeking**: at a set number of looks (1 to 672), compute the cumulative z (difference of two proportions, pooled standard error) and stop as soon as |z| ≥ 1.96.
- **Group sequential tests (α-spending)**: allocate the α that may be used by each look's "information fraction" t (people so far ÷ maximum) with an O'Brien-Fleming-type function (α(t) = 2 − 2Φ(1.96/√t)) or a Pocock-type one (α(t) = 0.05·ln(1+(e−1)t)). Boundaries for each look were set by simulating Brownian motion (400,000 paths), following Lan-DeMets. The maximum sample size was kept equal to the fixed design (no inflation).
- **mSPRT**: with a normal mixture (mean 0, SD τ) over the difference θ, compute the likelihood ratio Λ and the always-valid p-value p_n = min(p_{n−1}, 1/Λ_n) every hour, stopping when it drops below 0.05. τ mainly equals the lift to detect (0.005 = 5% × 10%).
- Evaluation: false positive rate (stopping when there is no difference), power (stopping at +10%), mean days to finish, and the difference at stopping ÷ the true difference.

## Findings

### 1. Number of looks and false positives (no difference, 14 days)

| Looks | False positives |
|---|---|
| 1 (day 14 only) | 4.8% |
| 2 (days 7, 14) | 8.2% |
| 4 (days 4, 7, 11, 14) | 12.2% |
| 7 (every 2 days) | 16.5% |
| 14 (daily) | 21.9% |
| 336 (hourly) | 46.0% |
| 28 (daily, 28 days) | 27.8% |
| 672 (hourly, 28 days) | 50.3% |

With daily looks, 24% of false positives happened on day 1 and half by day 3: early on, with few people, z swings widely.

### 2. Boundaries that keep false positives at 5%

| Look day | O'Brien-Fleming | Pocock |
|---|---|---|
| Day 4 | 3.67 | 2.32 |
| Day 7 | 2.77 | 2.38 |
| Day 11 | 2.24 | 2.34 |
| Day 14 | 2.05 | 2.36 |

With daily looks (14), the O'Brien-Fleming boundary goes from 7.33 (day 1) to 2.14 (day 14).

### 3. Comparing rules (baseline 5%, +10%, 5,000 a day, 20,000 runs each)

| Rule | False positives | Power | Mean days (at +10%) | Difference at stop ÷ true difference (median) |
|---|---|---|---|---|
| Fixed (one look on day 14) | 4.8% | 84.6% | 14.0 | 1.07 |
| Daily looks, stop at 1.96 | 21.9% | 90.7% | 6.2 | 1.34 |
| 4 looks, O'Brien-Fleming | 5.0% | 83.7% | 11.0 | 1.13 |
| 4 looks, Pocock | 5.1% | 77.8% | 9.7 | 1.28 |
| Daily, O'Brien-Fleming | 4.9% | 82.9% | 10.0 | 1.19 |
| mSPRT (hourly, up to 14 days) | 1.8% | 59.8% | 10.4 | 1.42 |
| mSPRT (hourly, up to 28 days) | 2.5% | 92.3% | 13.2 | 1.18 |

- O'Brien-Fleming nearly kept 5% false positives and 84% power while finishing 3 days earlier on average when there was a difference.
- Pocock tends to stop early, but loses power (78%) unless the maximum sample size is increased.
- mSPRT has false positives below 5% (2–3%, conservative). Capped at 14 days its power is only 60%; extended to 28 days it reaches 92%, but mean duration is about the same as the fixed design (13.2 days).
- Every early-stopping method overstates the difference at stopping (1.13–1.42 times the truth); stopping daily at 1.96 gives 1.34 times.

### 4. Choosing τ for mSPRT (up to 28 days, 10,000 runs each)

| τ (difference in conversion) | False positives | Power | Mean days |
|---|---|---|---|
| 0.0025 (half the target) | 1.4% | 90.7% | 15.5 |
| 0.005 (the target) | 2.7% | 91.5% | 13.4 |
| 0.01 (2×) | 3.5% | 89.3% | 13.5 |
| 0.02 (4×) | 3.4% | 85.7% | 14.6 |

Setting τ near the lift you want to detect finished fastest.

### 5. SQL and dashboard

- `sql/01_日ごとの累積とzと止める判定_tsql.sql`: from daily visitors and purchases, window functions compute cumulative conversion and z, and show "judge daily at 1.96" next to "judge at the boundary on planned days" (SQL Server / T-SQL). Run in DuckDB (reading FLOAT as DOUBLE) and matched with Python on two examples (14 days each): max difference in z 4.4e-16, stopping decisions identical every day. Not run on SQL Server.
- `dashboard/index.html`: a dashboard for watching a test in progress (one static HTML page, for a fictional internal team). In example 1 (no real difference), judging daily at 1.96 says "significant" on day 3, but the planned boundaries are never crossed, and the day-14 difference is +2.7% (95% interval −3.9 to +9.3%).

## Robustness

| Check | Daily at 1.96 | 4 looks, O'Brien-Fleming | mSPRT (28 days) |
|---|---|---|---|
| Baseline conversion 2% (false positives / power) | 22.0% / 61.5% | 5.1% / 43.5% | 1.8% / 45.8% |
| Baseline conversion 20% | 21.8% / 100% | 4.9% / 100% | 3.3% / 100% |
| Weekday pattern (weekend visitors 1.6×, conversion 0.85×) | 22.2% / 91.0% | 5.2% / 83.8% | 2.4% / 92.5% |
| Three random seeds (false positives) | 22.2–23.1% | 4.8–5.1% | — |

- **Looks on days other than planned** (days 5, 9, 12, 14): recomputing boundaries with the actual information fractions gives 5.0% false positives; keeping the planned boundaries gives 4.7%.
- **Also judging daily at 1.96 on top of the 4 planned looks**: 20.4% false positives. Judging outside the agreed rule defeats the purpose of the boundaries.
- **One-sided (stop only if better, 1.645)**: 5.4% with one look, 19.6% with daily looks.
- With a weekday pattern, the fixed design (day 14) still had 5.0% false positives.

## What this does not show

- **Everything is simulated.** Real tests have novelty effects (strong response at first), repeat visitors, assignment bugs and so on, and can be worse than this.
- **Sample size was not increased.** Group sequential designs usually raise the maximum sample size a little to keep power (a few % for O'Brien-Fleming, about 20% for Pocock). Here the maximum equals the fixed design, so Pocock's power looks low.
- **mSPRT uses a normal approximation** with variance from hourly conversion rates; the approximation is rough in the first few hours when purchases are few. Details differ from real experimentation platforms.
- **The difference at stopping was not corrected.** Early-stopped estimates are inflated; corrected estimates (e.g. median-unbiased) and post-stopping intervals were not covered.
- **One metric (conversion).** Revenue metrics and watching several metrics at once (multiple comparisons) were not covered.
- **Methods that shrink variance (e.g. CUPED using pre-period data)** are covered in F238.

## How to use this at work

- Decide the look days and the stopping boundaries before the test starts, and do not judge outside them.
- If you must stop early, use an O'Brien-Fleming-type boundary; it keeps errors at 5% and power close to the fixed design.
- When a test stops early, tell stakeholders that the observed difference is likely larger than the true one.

## Figures

The figures have Japanese labels.
- `figures/f237_01_peeking.png`: false positives by number of looks.
- `figures/f237_02_paths.png`: example z paths under no difference.
- `figures/f237_03_bounds.png`: O'Brien-Fleming and Pocock boundaries.
- `figures/f237_04_compare.png`: comparison of rules (false positives, power, days).
- `figures/f237_05_stopday.png`: distribution of stopping days.
- `figures/f237_06_dashboard.png`: screenshot of the dashboard.

## Reproduce

```
pip install -r requirements.txt
python src/01_設定.py
python src/03_分析.py         # about 1 minute (2 cores)
python src/02_例のデータ.py   # uses the boundaries from 03
python src/04_図.py
python src/05_SQLの照合.py
python src/06_ダッシュボード.py  # screenshots the page with Playwright's Chromium
```

## Files

- `src/common.py`: simulation and decision rules
- `data/params.json`: assumptions; `data/example_test_H0_daily.csv`, `data/example_test_H1_daily.csv`: daily examples for SQL and the dashboard
- `results/A_peeking_false_positive.csv`, `C_bounds_4looks.csv`, `C_bounds_daily.csv`, `C_methods_comparison.csv`, `D_msprt_tau.csv`, `E_robustness.csv`, `main.json`, `sql_check.json`, `F_sql_output_*.csv`, `B_examples.json`, `run_log.txt`
- `sql/`, `dashboard/index.html`, `figures/` (6 images)

## Sources

- All data is simulated (assumptions as in F236, whose baseline was set from public data such as the MIC Survey of Household Economy).
- Methods: O'Brien & Fleming (1979), Pocock (1977), Lan & DeMets (1983) α-spending, Johari et al. (2017) "Peeking at A/B Tests" (mSPRT).
- Midori Mall is a fictional online store for explanation, not a real company or service.
