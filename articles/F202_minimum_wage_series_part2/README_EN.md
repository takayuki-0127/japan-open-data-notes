# F202 How does the minimum wage overlap with the "annual income walls", and what would a uniform national minimum wage do? (Part 2)

Japanese version: [README.md](README.md). Part 1 is [F201](../F201_minimum_wage_series_part1/README_EN.md).

## Part 1 in three lines

- The share of workers whose pay must be raised by a revision (impact rate) grew from 1.6% to 23.2% over 20 years.
- Four estimation methods on the same prefecture × year data all gave an "unclear" employment effect (elasticity −0.18 to −0.02).
- What decided the answer was not the method but how small the differences in increases between prefectures were: only effects 7–14 times the commonly reported size could be told apart.

## Question

1. As the minimum wage rose, how much shorter did the working hours that fit under the "annual income walls" become? Do the bunching below the walls (F82) and the share of workers who limit their hours move together with the minimum wage?
2. If Japan had a single national minimum wage, how much might employment change? Shown as a range, using Part 1's estimates and varying the assumptions.
3. What can and cannot the data say in the minimum-wage debate?

This article does not evaluate the level of the minimum wage or whether a uniform national rate is desirable. Its aim is to show how far the data can go.

## Data

| Data | Contents | Source |
|---|---|---|
| Regional minimum wages (FY2002–2026, with national weighted average) | prefecture × fiscal year | Ministry of Health, Labour and Welfare list of regional minimum wages (via F201) |
| Employment Status Survey, main table 8 (2017 and 2022) | Non-regular employees by sex, whether they adjust their hours, and age (national and prefectural) | Ministry of Internal Affairs and Communications (Excel files from e-Stat read in a browser) |
| F82 bunching results | Size of bunching b in the 0.5–1.49 million yen range for married women etc. (2017, 2022) | articles/F82_income_wall_bunching |
| F201 panel and estimates | Employment and employment rate by prefecture × year, the four methods' estimates, power, 2025 Kaitz index | articles/F201_minimum_wage_series_part1 |

- The "walls" used are the social insurance thresholds of **1.06 million yen** (at qualifying workplaces, enrolment at 20+ hours a week and 88,000 yen or more a month) and **1.3 million yen** (the guide for leaving a spouse's dependent coverage). The 1.03 million yen income-tax threshold was not used because it was revised in the FY2025 tax reform.
- To convert annual income to hours, one year = 52 weeks.

## What I did

1. **Walls as hours**: wall ÷ minimum wage ÷ 52 gives the weekly hours that stay under the wall when paid the minimum wage. Also counted prefectures whose minimum wage exceeds the hourly wage at which 20 hours a week reaches 88,000 yen a month (88,000 ÷ (20 × 52 ÷ 12) = 1,015.4 yen).
2. **Share adjusting hours vs minimum wage, by prefecture**: for non-regular female workers, the share who "adjust their hours" was compared (a) in the 2022 cross-section with the level of the minimum wage, and (b) in the 2017→2022 change with the rise in the minimum wage (log difference). Weighted regression by number of non-regular workers (robust standard errors) and a permutation test (4,000 draws), with men as a comparison group.
3. **Uniform national scenario**: raise each prefecture's FY2026 minimum wage (only where lower) to (i) the national weighted average of 1,177 yen, (ii) the highest prefecture's 1,280 yen, (iii) 1,500 yen. Change in employment = prefecture employment (2025) × elasticity × increase (log), summed over prefectures. Elasticities from Part 1:
   - range across the four methods: −0.18, −0.04, 0
   - interval ends: −0.35 (the end handed over by Part 1, equal to the lower end of the 95% interval) and +0.14 (the upper end)
   Also counted prefectures whose Kaitz index (minimum wage ÷ average hourly wage of part-time workers) would exceed the largest value ever observed (0.819). The 2026 Kaitz index was projected as the 2025 value × (FY2026 ÷ FY2025 minimum wage) ÷ (1 + 4.25% wage growth).
4. **Power**: converted Part 1's minimum detectable effect into an elasticity and then into a number of workers at 1,500 yen.

## Findings

### 1. The walls expressed as hours

| Fiscal year | Minimum wage (national weighted average) | Weekly hours under 1.06 million | Weekly hours under 1.3 million |
|---|---|---|---|
| 2005 | 668 yen | 30.4 | 37.4 |
| 2017 | 848 yen | 24.0 | 29.5 |
| 2022 | 961 yen | 21.1 | 26.0 |
| 2026 | 1,177 yen | 17.3 | 21.2 |

- Prefectures where 20 hours a week at the minimum wage exceeds 88,000 yen a month (1,016 yen or more): 2 in FY2021 → 6 in FY2023 → 12 in FY2024 → **all 47 in FY2025**. From FY2025, "20 hours a week" and "88,000 yen a month" are almost the same line everywhere.
- At FY2026 minimum wages, 88,000 yen a month is reached at 15.9–18.7 hours a week, and staying under 1.3 million yen allows 19.5–23.0 hours a week (depending on the prefecture).

### 2. 2017 vs 2022 (national)

- Bunching b for married women (F82): 2.37 → 1.79 (a fall of 0.21–0.60 under other fitting choices).
- Share of non-regular women adjusting hours: 31.7% → 30.6%. Men: 14.2% → 14.1%.
- Weekly hours under 1.3 million yen: 29.5 → 26.0 (−12%).
- With only two time points, whether the minimum wage was the cause cannot be separated.

### 3. Comparing prefectures (`results/adjust_vs_mw.csv`)

| Comparison | Coefficient | 95% interval | Permutation p |
|---|---|---|---|
| Women, 2022 cross-section (pt per +10% minimum wage) | +1.4 | −1.5 to +4.3 | 0.28 |
| Women, cross-section, excluding Tokyo | +3.5 | +2.4 to +4.6 | 0.001 |
| Women, cross-section, ages 25–54 | +0.1 | −3.2 to +3.5 | 0.94 |
| Women, cross-section, per +0.05 Kaitz | +0.2 | −2.4 to +2.7 | − |
| Men, 2022 cross-section (comparison) | +2.6 | +1.9 to +3.2 | 0.002 |
| Women, 2017→22 change (pt per +1% rise) | +0.10 | −0.58 to +0.77 | 0.80 |
| Women, change, ages 25–54 | +0.37 | −0.51 to +1.25 | 0.54 |
| Women, change, excluding Tokyo | −0.25 | −0.84 to +0.34 | 0.51 |
| Men, change | −0.72 | −1.93 to +0.50 | 0.25 |

- In the cross-section, prefectures with higher minimum wages have higher shares adjusting hours (unweighted correlation 0.51). But men show the same pattern (0.66), so this probably overlaps with differences in how non-regular work is organized in urban areas rather than the minimum wage itself (my interpretation).
- The 2017→22 rise in the minimum wage differed only between 11.2% and 14.7% across prefectures (SD 0.93%), and showed no relation to the change in the share adjusting hours (down in 36 of 47 prefectures, mean −0.99 pt).

### 4. Uniform national scenario (`results/scenario_uniform.csv`)

| Level | Prefectures raised | Mean increase (employment-weighted) | Max | Range across the four methods | To interval ends | Prefectures exceeding the highest Kaitz ever observed (share of employment) |
|---|---|---|---|---|---|---|
| 1,177 yen (national weighted average) | 40 | +2.8% | +8.5% | 0 to −350,000 | −660,000 to +260,000 | 14 (13.9%) |
| 1,280 yen (highest prefecture) | 46 | +9.4% | +18.0% | 0 to −1.11 million | −2.12 million to +830,000 | 29 (32.9%) |
| 1,500 yen | 47 | +28.3% | +38.2% | 0 to −3.11 million | −5.92 million to +2.32 million | 44 (77.4%) |

- Employment in 2025 was about 68.4 million; −3.11 million at 1,500 yen is −4.5%.
- The smallest effect Part 1's estimates can detect (elasticity 0.22–0.24) corresponds to about ±3.68 million at 1,500 yen. The range across the four methods sits inside it; current data cannot tell "how much employment would fall".

## Robustness

| Check | Result |
|---|---|
| Restrict the prefecture comparison to ages 25–54 | cross-section +0.1, change +0.37 (both intervals cross 0) |
| Exclude Tokyo | cross-section clearly positive at +3.5; change −0.25 (unclear) |
| Use the Kaitz index instead of the minimum-wage level | +0.2 (unclear) |
| Same analysis for men (comparison) | cross-section in the same direction as women (+2.6): not a minimum-wage-only story |
| Permutation tests | women's change p = 0.80, cross-section p = 0.28 |
| Scenario base year FY2025 | 1,500 yen at elasticity −0.18: −3.73 million (FY2026 base: −3.11 million) |
| Double the effect beyond the observed range | up to −8.82 million at 1,500 yen: assumptions outside the range move the answer a lot |
| Change F82's fitting | fall in b of 0.21–0.60 (excluding the setting that groups by 1 million yen) |

## What this does not show

- The prefecture comparison uses aggregates for 47 prefectures × 2 time points. Whether individuals who adjust their hours cut hours because of the minimum wage cannot be known.
- The 2017 vs 2022 comparison mixes in COVID and differences in survey design.
- The scenario is a mechanical calculation assuming Part 1's estimates still apply. At 1,500 yen, prefectures holding 77% of employment would go beyond the observed range (Kaitz up to 0.82), so it is an extrapolation. Whether the effect changes outside the range cannot be known from these data.
- The elasticity is estimated from prefecture-wide employment rates, not the effect on people working near the minimum wage.
- Pass-through to hourly wages (spillovers) and effects on prices, profits and hours were not calculated.
- Prefectural differences in the conditions for the 1.06 million yen threshold (such as workplace size) were not considered.
- FY2026 minimum wages are announced values; the 2026 Kaitz index is a projection.

## How to use this at work

- Translate money thresholds into the unit people actually decide in (here, weekly hours) before discussing behavior.
- Present scenarios as a band built from the estimated range and its interval ends, and flag where they leave the observed range.
- Use a comparison group (here, men) to check whether a cross-sectional pattern is really about the variable of interest.

## Figures

The figures have Japanese labels.
- `figures/fig1_wall_hours.png`: weekly hours under each wall, by year.
- `figures/fig2_20h_line.png`: prefectures crossing the "20 hours = 88,000 yen" line.
- `figures/fig3_two_points.png`: 2017 vs 2022 national indicators.
- `figures/fig4_adjust_pref.png`: share adjusting hours vs minimum wage, by prefecture.
- `figures/fig5_uniform_increase.png`: increase each prefecture would need under each uniform level.
- `figures/fig6_scenario_band.png`: the scenario band for employment.

## Reproduce

```
pip install -r requirements.txt
cd src
sh run_all.sh
```

## Files

| File | Contents |
|---|---|
| src/01_取得.py | checks that data/raw is complete (record of collection) |
| src/02_整形.py | joins share adjusting hours with minimum wages by prefecture × year; base for scenarios |
| src/03_分析.py | wall hours, the 20-hour line, prefecture comparison, uniform scenario, power |
| src/04_図.py | Figures 1–6 |

## Sources

- Ministry of Internal Affairs and Communications: Employment Status Survey (2017, 2022), main table 8
- Ministry of Health, Labour and Welfare: list of regional minimum wages
- Related articles: F01, F82, F156, F201 (under articles/ in this repository). F201's estimates use the Basic Survey on Minimum Wages, the Basic Survey on Wage Structure and the Labour Force Survey (prefectural model estimates).
