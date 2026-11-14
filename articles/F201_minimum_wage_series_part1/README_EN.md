# F201 Minimum wage and work (Part 1): who it reaches, and how much the answer depends on the estimation method

Japanese version: [README.md](README.md). Part 2 is [F202](../F202_minimum_wage_series_part2/README_EN.md).

This article consolidates earlier minimum-wage articles in this repository (F01 difference-in-differences, F15 border comparison, F17 causal forest, F26 statistical power, F156 by wage level) and adds two new things:
- the 20-year trend in how many workers the minimum wage "reaches" (the impact rate);
- four estimation methods applied side by side to the same prefecture × year data.

## Question

- How has Japan's minimum wage risen over 20 years, and how many workers' wages has it reached?
- How much does the estimated employment effect change with the method (difference-in-differences, synthetic control, comparing neighboring prefectures)?
- Is the effect larger in low-wage areas or particular industries?

## Data

| Data | Contents | Period | File |
|---|---|---|---|
| Basic Survey on Minimum Wages (Ministry of Health, Labour and Welfare) | National impact rate and below-minimum rate (establishments with fewer than 30 employees; fewer than 100 for manufacturing etc.) | 2005–2024 | data/raw/national_impact_rate.csv |
| Basic Survey on Wage Structure, special tabulation (MHLW) | National impact rate and below-minimum rate (establishments with 5+ employees) | 2022–2024 | data/raw/national_impact_rate_special_tab.csv |
| Basic Survey on Wage Structure (part-time workers, by prefecture) | Average hourly wage by prefecture × year (collected in F156) | 2009–2025 | data/raw/f156_panel_wage.csv |
| Labour Force Survey prefectural model estimates etc. (F01 panel) | Employment rate, unemployment rate, minimum wage by prefecture × year | 2008–2025 | data/raw/f01_panel.csv |
| Regional minimum wages | Hourly amount for 47 prefectures × fiscal year | FY2002–2026 | data/raw/minimum_wage_2002_2026.csv |
| Pairs of neighboring prefectures | 89 pairs built from F15's border municipality pairs | — | data/raw/pref_border_pairs_from_F15.csv |

Impact and below-minimum rates were transcribed by hand from materials of the Central Minimum Wages Council's guideline subcommittee. For the FY2005–2014 table the category names could not be read from the text, so the row whose FY2014 values (below-minimum 2.0%, impact 7.3%) matched the national total in another document was taken as the national total.

**Terms**
- **Impact rate**: share of workers who would fall below the revised minimum wage, i.e. whose pay must be raised by the revision.
- **Below-minimum rate**: share of workers already below the minimum wage before the revision.
- **Kaitz index**: minimum wage ÷ average wage (here, the average hourly wage of part-time workers). Closer to 1 means the minimum wage is closer to the average (it "bites" more).
- **Elasticity**: % change in employment when the minimum wage rises 1%.

## What I did

All results are expressed "per 10% rise in the minimum wage". The main period is 2008–2025, excluding the COVID years 2020–22.

| Method | Comparison | Details |
|---|---|---|
| Difference-in-differences (two-way fixed effects) | Prefectures nationwide | employment rate = log(minimum wage) + prefecture effect + year effect; standard errors clustered by prefecture |
| DiD + prefecture-specific trends | Same | adds a linear trend for each prefecture |
| Neighboring prefectures | Only the two sides of the same border | stacks the two prefectures of each of 89 borders, with pair × year and pair × prefecture effects (a prefecture-level version of the Dube et al. approach); clustered by prefecture |
| Synthetic control | A weighted "synthetic prefecture" with similar past trends | treated: the 10 prefectures with the largest FY2019→2025 increase (average 26.8%); donors: the 20 with the smallest (21.6%); weights matched on 2008–19 employment; the 2023–25 gap is divided by the difference in increases (5.25% on average) to express it per 10% |

Differences were examined two ways:
- **By bite**: prefectures split into thirds by 2009–11 "minimum wage ÷ average hourly wage", with separate DiD slopes.
- **By industry**: F15's results (2016→21, employee counts in municipalities on both sides of a border) shown for reference, since the data differ.

## Findings

### 1. Who it reaches (Figures 1–2)

- **Impact rate**: 1.6% (2005) → 7.3% (2014) → 16.3% (2019) → 23.2% (2024). In 2020 the increase was almost zero (weighted average +1 yen), so it fell to 4.7%.
- **Below-minimum rate**: between 1.1% and 2.7%, with no steady rise. The increases seem to have worked by raising the number of people paid exactly the minimum, rather than by raising non-compliance (my interpretation).
- **Impact rate in the special tabulation (5+ employees)**: 6.9–8.8% (2022–24). The basic survey covers small establishments, so the same year shows about one third of its value. Which establishments are counted changes the impact rate a lot.
- **Kaitz index (median across prefectures)**: 0.709 (2009) → 0.756 (2019). The survey design changed in 2020, causing a step; 0.728 in 2025. The gap between prefectures where the minimum is closest to the average (top third) and farthest (bottom third) stayed around 0.04 (`results/kaitz_by_tercile.csv`).

### 2. Four methods side by side (Figure 3, `results/method_comparison.csv`)

Employment rate (percentage points per 10%, 2008–25 excluding 2020–22):

| Method | Estimate | 95% interval | As elasticity |
|---|---|---|---|
| DiD (two-way fixed effects) | −0.21 | −1.10 to +0.68 | −0.04 |
| DiD + prefecture trends | −1.07 | −2.03 to −0.11 | −0.18 |
| Neighboring prefectures (89 pairs) | −0.13 | −1.05 to +0.80 | −0.02 |
| Synthetic control (top 10 vs bottom 20) | −0.56 | −2.38 to +1.26 (permutation p = 0.51) | −0.10 |

Unemployment rate (pp per 10%):

| Method | Estimate | 95% interval |
|---|---|---|
| DiD | −0.27 | −0.76 to +0.22 |
| DiD + prefecture trends | +0.31 | −0.02 to +0.64 |
| Neighboring prefectures | +0.12 | −0.09 to +0.33 |
| Synthetic control | −0.45 | −0.80 to −0.10 (permutation p = 0.015) |

- All four employment estimates fall between negative and about zero. All intervals are wide, and all but the trend model cross 0.
- For unemployment, the direction differs by method. Only the synthetic control clearly shows "unemployment fell in prefectures with large increases". But the 10 treated prefectures are mostly rural, and this may overlap with regional business cycles (my interpretation).

### 3. Usable variation and power (Figures 4–5, `results/mde.csv`)

- **Size of minimum-wage variation**:
  - remaining standard deviation after removing prefecture and year (DiD): 0.86%
  - difference across the same border: 0.48%
  - difference in increases in the synthetic control: 5.25%
- **Minimum detectable effect at 80% power (employment rate, per 10%)**: DiD 1.27, prefecture trends 1.37, neighbors 1.32, synthetic control 2.59 (pp). All are 7–14 times the size commonly reported abroad (elasticity −0.3 ≈ 0.18 pp).
- **Synthetic control gap over time (Figure 5)**: in 2008–19 the top 10 and the synthetic prefecture stayed within ±0.3 pp. In 2024–25 the gap shifted down to −0.4 to −0.7 pp. But randomly chosen groups of 10 prefectures produce similar shifts (95% range −0.96 to +0.87).

### 4. Heterogeneity (Figure 6, `results/heterogeneity_bite.csv`)

- **By bite (employment rate, per 10%)**: far −0.57, middle −0.59, close −0.35. Close minus far is +0.21 (±0.22), not in the direction "worse where the minimum is close to the average". In F156 too, the employment difference disappeared when comparing within the same region.
- **By industry (F15, employee count per 10%)**: accommodation and food +3%, wholesale and retail +41%, manufacturing +27%, all industries +3%. All intervals cross 0; this design cannot tell small effects apart.

## Robustness (`results/method_comparison.csv`)

| Check | Employment rate (per 10%) |
|---|---|
| Include the COVID years (all of 2008–25) | DiD −0.09, prefecture trends −1.20, neighbors −0.06 |
| 2008–19 only | DiD −0.01, prefecture trends −0.71, neighbors +0.91 (−0.01 to +1.83) |
| Only borders with long contact (72 pairs with 5+ municipality pairs) | +0.23 (−0.74 to +1.19) |
| Change synthetic control treated/donors | top 5 vs bottom 20: −0.67; top 10 vs bottom 30: −0.16 |
| Synthetic control permutation (200 random sets of 10) | p = 0.51 (employment), p = 0.015 (unemployment) |

- Depending on the period and pairs, estimates moved between −1.2 and +0.9, and the sign flipped.
- Only "DiD with prefecture trends" stayed negative across periods. But a prefecture-specific linear trend can also absorb part of the minimum-wage effect itself (the slowly arriving part), so this one result alone cannot say that employment fell.

## What this does not show

1. It cannot say "the minimum wage does not reduce employment". With every method, the smallest detectable effect is larger than the size commonly reported abroad. What can be said is only that "a large negative effect (well beyond an elasticity of −0.3) is not visible".
2. Only national impact rates were used, not prefectural time series. The two surveys cover different establishments, so their levels cannot be compared.
3. The FY2005–2014 impact rates were transcribed from a table whose category names could not be read, choosing the national total by matching the FY2014 values.
4. The neighbor comparison is at the prefecture level, coarser than F15's municipality level. Whether the two sides of each border are really similar labor markets was not checked.
5. Synthetic-control treated prefectures are "those with large increases". Increases are set by local councils considering local conditions, so they may not be unrelated to the business cycle.
6. Since 2020, prefectural hourly wages move more from year to year because of the survey change and sampling noise; some prefectures show sudden jumps.
7. No prefecture is named or evaluated.

## How to use this at work

- When an effect is "not significant", report the minimum detectable effect next to it, so readers can see whether the data could have found a realistic effect at all.
- Put several identification strategies on the same data before choosing one; the spread between them is part of the uncertainty.
- Check where the usable variation comes from before trusting a design.

## Handed to Part 2 (F202)

- `for_F202` in `results/main.json`: the range of the employment effect per 10% (across methods), the ends of the 95% intervals, and the 2025 Kaitz index by prefecture.
- **Assumptions for scenario calculations (e.g. a uniform national minimum wage)**:
  - vary the employment elasticity in two steps: "−0.18 to 0 (range across methods)" and "−0.35 (interval end)";
  - for pass-through to hourly wages, use F156's estimate (in a prefecture whose minimum wage is 1 SD lower, +0.35% hourly wage per 1% national increase);
  - do not use `results/wage_passthrough.csv` (simple pass-through with year effects): differences in increases within a year are too small and the interval is too wide.
- Part 2 covers the overlap of the "annual income walls" and the minimum wage (Employment Status Survey, F82), a uniform national scenario, and what the data can and cannot say.

## Changes from the design document

- The deep series was condensed from six articles into two parts, so the original F201–F203 (impact rate, method comparison, heterogeneity) became one article.
- Prefectural time series of impact rates were not available, so national values and the prefectural Kaitz index (F156 wage data) were used instead.
- In addition to re-showing F15 (municipalities, 2016→21), the neighbor comparison was redone on the same prefecture × year panel so that all four methods use the same data.
- With no single event, the synthetic control defines treated prefectures by their FY2019→2025 increase.

## Figures

The figures have Japanese labels.
- `figures/fig1_impact_rate.png`: impact rate and below-minimum rate over 20 years.
- `figures/fig2_kaitz_pref.png`: Kaitz index by prefecture over time.
- `figures/fig3_method_comparison.png`: the four methods' estimates with intervals.
- `figures/fig4_variation_mde.png`: usable variation and minimum detectable effect by method.
- `figures/fig5_synth_gap.png`: gap between the treated prefectures and the synthetic prefecture.
- `figures/fig6_heterogeneity.png`: effects by bite and by industry.

## Reproduce

```sh
pip install -r requirements.txt
sh src/run_all.sh
```

## Files

| File | Contents |
|---|---|
| src/01_取得.py | checks the input files (notes on sources) |
| src/02_整形.py | adds bite thirds to the employment panel |
| src/03_分析.py | impact rate and Kaitz index, the four methods, heterogeneity by bite, power, numbers for Part 2 |
| src/04_図.py | Figures 1–6 |

## Sources

- Ministry of Health, Labour and Welfare: Basic Survey on Minimum Wages, Basic Survey on Wage Structure, and its special tabulation (materials of the Central Minimum Wages Council guideline subcommittee)
- Statistics Bureau of Japan: Labour Force Survey (prefectural model estimates) and others (F01 panel)
- MHLW: list of regional minimum wages
- Related articles: F01, F15, F17, F26, F156 (under articles/ in this repository)
