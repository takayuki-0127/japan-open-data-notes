# F239 How much does advertising actually drive sales? (Marketing mix modeling)

Japanese version: [README.md](README.md).

The ninth article in the series "analyses close to real work" (F231–F245). It examines the relationship between advertising spend and sales using (A) public data (industry-wide, monthly) and (B) a simulation of a fictional company, "Midori Home (fictional)", and (C) checks what happens when budget allocation is decided from the estimated response curves. Using simulations where the true values are known, it compares the conditions under which an MMM (marketing mix model: a model that estimates each channel's effect from time series of ad spend and sales) gets it right and wrong.

## Question

- In industry-wide public data, are sales higher in months with more advertising? Can that be called the effect of advertising?
- How well can an MMM with adstock (carry-over of the effect) and saturation (diminishing returns) recover each channel's ROI (incremental sales ÷ ad spend)?
- What happens when ad spend is moved in line with expected demand? How does a geographic experiment compare?
- If budget allocation is decided from the estimated response curves, what happens to the true incremental sales?

## Data

- Ministry of Economy, Trade and Industry, "Current Survey on Selected Service Industries", long-term data, "advertising", monthly values (Jan 1988 – Dec 2024; 2024 annually revised). This is advertising agencies' revenue, not the spend paid by advertisers (used as a proxy).
- METI "Commercial Dynamics Statistics", sales by store type (supermarkets, convenience stores, department stores, Jan 2014 – Dec 2024; collected in F135 and F231).
- Midori Home (fictional) data comes from the simulation in `src/03_分析.py` (not a real company's numbers).

## What I did

- A: regressed log sales of three retail formats on log advertising revenue, adding in turn month dummies, a trend, a COVID period (Apr 2020 – Dec 2021) and consumption-tax rush/rebound dummies. HAC standard errors.
- B: adstock a_t = s_t + decay × a_{t−1}; saturation x/(x+K). The MMM picks decay (0–0.8) and K (4 values) by grid search and fits the rest by least squares (seasonality as Fourier terms up to two cycles a year, plus a trend).
- "Spend follows demand" scenario: spend is raised in line with seasonality and a demand movement (AR(1)) that the marketer can see but that is not recorded in the data.
- Geographic experiment: split 47 regions in half and switch off Web ads in one half for 12 weeks; ROI from a difference-in-differences against the 16 weeks before.
- Experiment-calibrated MMM: fix Web's ROI at the experiment's value and re-estimate the other channels.
- C: optimize the allocation of a weekly budget of 1.3 million yen in 5% steps on the estimated curves, and evaluate on the true curves.

## Findings

### A. Industry-wide (Jan 2014 – Dec 2024, 132 months)

| Specification | Elasticity of total advertising revenue (95% interval) |
|---|---|
| 1 As is (levels) | +0.153 (+0.103 to +0.203) |
| 2 + month effects | −0.057 (−0.324 to +0.210) |
| 3 + month + trend | +0.148 (−0.000 to +0.295) |
| 4 + month + trend + COVID and consumption tax | +0.020 (−0.063 to +0.104) |
| 5 Year-on-year changes | +0.056 (−0.036 to +0.148) |

- Elasticity = how many % higher the three retail formats' sales are in a month with 1% more advertising (HAC standard errors, 12 lags).
- TV ranged from −0.288 to +0.101 and internet advertising from −0.118 to +0.103: even the sign flipped with the specification.
- Correlation of year-on-year changes (excluding COVID): +0.26 with sales leading by 6 months, −0.11 in the same month, −0.22 with advertising leading by 3 months. Sales move first and advertising follows (weakly).

### B. Midori Home (fictional) simulation (3 years = 156 weeks, 60 runs)

True settings: TV (decay 0.6, ROI 5.51), Web (0.2, 5.88), flyers (0, 1.91). ROI = incremental sales from the channel under the current average spending ÷ that channel's spend.

| Scenario | Method | TV | Web | Flyers |
|---|---|---|---|---|
| Spend moves independently of demand | MMM (median bias) | −10% | +13% | +16% |
| 〃 | MMM (median absolute error) | 38% | 33% | 37% |
| Spend follows expected demand | MMM (median bias) | +3% | +53% | +68% |
| 〃 | MMM (median absolute error) | 23% | 53% | 68% |
| Both | Geographic experiment (Web off for 12 weeks in half of 47 regions) | — | +2% / +0% (abs. error 17% / 19%) | — |
| Spend follows demand | MMM with Web calibrated by the experiment | +27% | +0% | +97% |

- When spend follows demand, the 25th–75th percentiles of Web's ROI estimates over 60 runs were +25% to +84%, and flyers +52% to +116%: overestimated in almost every run.
- The geographic experiment is almost unbiased, but its run-to-run spread (SD) is 24–31%.
- Calibrating only Web with the experiment increased the overestimate for flyers from +68% to +97% in the demand-following scenario (what Web had explained moved to another channel).

### C. Budget allocation (1.3 million yen a week, fictional)

| How the allocation is chosen | True incremental sales (optimum = 100) | Runs worse than the current allocation |
|---|---|---|
| Current allocation (TV 35%, Web 19%, flyers 46%) | 95.0 | — |
| Optimized on the true curves (45, 30, 25%) | 100.0 | — |
| MMM (spend independent of demand) | 98.3 (25th–75th pct 96.4–99.2) | 17% of 60 |
| MMM (spend follows demand) | 98.5 (95.2–99.1) | 25% |
| Experiment-calibrated MMM (independent) | 98.8 (97.6–99.5) | 10% |
| Experiment-calibrated MMM (follows demand) | 99.1 (98.1–99.5) | 13% |

- Re-allocation can gain about 5%. Allocations chosen by MMM mostly get close, but in 1 of 4 to 1 of 10 runs they were worse than the current allocation.
- The loss is small even when ROI is far off, because the response curves flatten out and moderate changes in allocation do not change sales much (my interpretation).

### SQL

- Wrote adstock (recursive CTE) and 4-week sums and 52-week averages (window functions) in T-SQL, ran them in DuckDB and compared with Python: max difference 7×10⁻¹² (`results/D_sql_check.json`).

## Robustness (B, spend independent of demand, 30 runs)

| Condition | TV | Web | Flyers |
|---|---|---|---|
| Main (3 years, with seasonality) | mean −3%, median abs. 34% | +25%, 29% | +49%, 48% |
| 1 year of data (52 weeks) | +28%, 43% | +35%, 47% | −1%, 55% |
| Twice the noise | −6%, 41% | +22%, 36% | +102%, 71% |
| No seasonality in the model | +8%, 80% | +25%, 42% | −49%, 90% |
| Assume no adstock | −76%, 76% | −35%, 40% | +26%, 33% |

(mean bias, median absolute error)
- For a channel whose effect carries over, like TV, leaving out adstock estimates ROI at about a quarter of the truth.
- Length of the geographic experiment: switching Web off for 8 weeks gives an error SD of 37%, 12 weeks 29% (checked by repeating only the experiment 150 times; mean bias −7% and −4%).

## What this does not show

- The industry-wide regression does not measure the effect of advertising. Sales move first and advertising follows, and season, the economy and COVID move both.
- Advertising agencies' revenue differs from advertisers' spend (agency handling, changes in the surveyed companies). Dentsu's "Advertising Expenditures in Japan" is annual only and was not used.
- The simulation results hold for the settings chosen (three channels, decay, shape of saturation, noise level). How well a real MMM works depends on the amount of data and how spend has varied.
- The geographic experiment assumes that demand moves together across regions and that the switched-off channel does not spill into other regions.
- The "about 5%" allocation gain is for this fictional setting.

## How to use this at work

- Do not take MMM ROIs at face value, especially when spend has been planned around expected demand.
- Verify one channel with an experiment before using the model for allocation, and expect calibration of one channel to shift bias to others.
- Always include adstock for channels with carry-over.

## Folders

- `data/`: `ad_monthly_1988_2024.csv`, `panel_2014_2024.csv`, `sim_weekly_midorihome.csv` (one run, for the SQL check), `raw/`
- `results/`: A (regressions, lead-lag correlations), B (60 runs of ROI, summaries, robustness), C (allocation, response curves), D (SQL check), `main.json`
- `dashboard/index.html`: a budget allocation simulator (for a fictional internal team; moving the sliders shows MMM increments, ROI and the increment from one more 10,000 yen)
- `figures/`: Figures 1–6

## Figures

The figures have Japanese labels.
- `figures/fig1_industry_lead_lag.png`: lead-lag correlation between advertising and retail sales.
- `figures/fig2_industry_specs.png`: elasticity by regression specification.
- `figures/fig3_adstock_saturation.png`: how adstock and saturation shape the response.
- `figures/fig4_roi_recovery.png`: estimated vs true ROI across runs and scenarios.
- `figures/fig5_allocation.png`: true incremental sales under each allocation method.
- `figures/fig6_dashboard.png`: screenshot of the allocation simulator.

## Reproduce

```
pip install -r requirements.txt
python src/02_整形.py
python src/03_分析.py      # about 2 minutes
python src/04_SQL検算.py
python src/05_図.py
python src/06_ダッシュボード画像.py   # needs playwright and chromium
python src/07_実験の長さの確認.py      # checks the experiment length (8 and 12 weeks)
```
Random seeds are fixed (simulation runs 0–59, experiments in the 5000s, robustness in the 7000s).

## Sources

- Processed by the author from METI "Current Survey on Selected Service Industries" (https://www.meti.go.jp/statistics/tyo/tokusabido/) and METI "Commercial Dynamics Statistics".
- Midori Home is a fictional company; all its numbers are simulated.
