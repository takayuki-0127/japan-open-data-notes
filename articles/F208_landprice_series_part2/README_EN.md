# F208 How do condominium prices move with land prices, and where do land price forecasts keep missing? (Part 2)

Japanese version: [README.md](README.md). Part 1 is [F207](../F207_landprice_series_part1/README_EN.md).

## Part 1 in three lines

- Of 12,000 points that continued from 2006 to 2026, 44% rose; within 10 km of the three metro centers, 93% rose.
- "How much land prices fall as you move away from a station" ranged from −3% to −32% depending on which variables the regression included.
- Land prices near new stations were rising before opening; before/after comparisons around the opening cannot measure the station effect.

Part 2 covers (1) how used-condominium prices move with land prices, (2) where land price forecasts that are updated every year tend to miss, and (3) what the data can and cannot say (a wrap-up of the series). No new data was collected; it uses data from F207, F182, F158 and F03.

## Question

1. How closely does the price per m² of used condominiums move with land prices in the same municipality? Does it differ by building age?
2. When a land price forecast is updated every year by retraining on the previous year's publication, where does it miss, and in which direction? Does it miss at the same points every year?
3. Together with Part 1, what can and cannot land price data say?

## Data

| Data | Contents | From |
|---|---|---|
| Used-condominium transactions | MLIT "Real Estate Transaction Price Information", used condominiums etc., 2015–2025, nationwide; 525,764 RC/SRC transactions | F182 `data/condo_clean.csv.gz` |
| Land price history | Price for each point 1996–2026 and a flag for whether the same point continued from the previous year | F207 `data/price_hist_1996_2026.csv.gz`, `chg_2007_2026.csv.gz` |
| Land price panel | Point × year prices 2017–2026 (244,684 rows) | F158 `data/panel.csv` |
| Point features | 30 features such as distance to station, passengers, floor-area ratio, municipality population (as of 2026) | F03 `data/features.csv` |

## What I did

### A: Condominiums and land

- **Quality-adjusting condominium prices**: regressed log(price per m²) on building age (one dummy per year), log(floor area), minutes to station, SRC structure and renovation (with municipality × year fixed effects), and subtracted those parts to get a "quality-adjusted price". The municipality × year mean became the index (municipality-years with 20+ transactions).
- **Land price change**: mean log change of residential points in the same municipality, using only points that continued from the previous year.
- **Timing**: land prices are as of 1 January, so transactions in year y were matched with the publication of January y+1 (the movement during year y) as the main setting; shifts of 0 and 2 years were also compared.
- **Strength of the link**: regression of municipality × year changes on each other, with year fixed effects ("within the same year, did condominiums rise more where land rose more?"), weighted by number of transactions. Intervals from 300 municipality-level bootstrap draws.
- **National index**: yearly municipality changes averaged with transaction weights and chained.

### B: Errors of a yearly-updated forecast

- Same form as F158's "yearly update": forecast year T land prices with a LightGBM trained on year T−1 (same settings as F158). Split into 5 folds of 20 km blocks and predict points in blocks not used for training (predicting unseen places). 2018–2026.
- Error e = log(prediction) − log(actual) (positive means the forecast was too high). Averaged over 9 years per point, then broken down by map, price level, the point's 10-year change and municipality population change.
- **Persistence of errors**: correlation between e(T) and e(T−1) at the same point. For 23,054 points with all 9 years, the share of error variance that is specific to the point (variance of point means ÷ total variance).

## Findings

### A: Condominiums rose faster than land; the year-to-year link is "0.35% per 1% of land price"

| Indicator | Value |
|---|---|
| National index (2015→2025; land 2016→Jan 2026) | condominiums 176, land 136 |
| 8-year change by municipality (332 municipalities, median) | condominiums +52%, land +12%; condominiums beat land in 94% |
| Slope between 8-year changes | 0.22 (correlation 0.27) |
| Link within the same year (year fixed effects) | **0.35** (95% interval 0.29–0.42), 3,387 municipality-years |
| Without year fixed effects | 0.23 |
| Correlation of municipality × year changes | 0.08 |

- Timing: same January 0.32, next January 0.35 (main), the January after that 0.27. Next January was strongest.
- By building age: 0–9 years 0.14 (0.01–0.29), 10–19 years 0.23, 20–29 years 0.31, 30+ years 0.33. **Older condominiums move more with land prices.** Probably because land makes up a larger share of the price of older buildings (my interpretation).
- In the national index, buildings aged 20–29 reached 191 and those aged 0–9 reached 165; newer buildings grew less.

### B: Forecast errors persist "at the same points, in the same direction"

| Indicator | Value |
|---|---|
| Size of error (median, 2018–2026) | 18.2% (17.1% → 19.5% by year) |
| Share within ±20% | 54% |
| Direction of error (median) | −2.6% (forecasts low; −2.9 to −3.7% from 2023) |
| Correlation with the same point's error the year before | **0.95** (0.947–0.952 in every year) |
| Share of error variance specific to the point | **94%** |

Direction of error (median of each point's 9-year mean):

| Breakdown | Lowest group | Highest group |
|---|---|---|
| 2017 land price level (deciles) | cheapest 10%: **+20%** (too high) | most expensive 10%: **−12%** (too low) |
| The point's 2017→2026 change (deciles) | fell most 10%: +12% | rose most 10%: −11% |
| Municipality population change (2015→20) | below −5%: +0.3% | +2% or more: −5.1% |

- Cheap points are forecast too high and expensive points too low (pulled toward the average). Points whose prices moved are missed in the opposite direction of the move.
- Errors occur at the same points every year, so they do not "fix themselves next year". Most of the error seems to come from point-specific circumstances not in the features (my interpretation).
- Adding the previous year's national change (median of training points) shrank the direction of error from −2.6% to −2.2%, but the size barely changed (18.35% → 18.33%).

## Robustness

| Check | Result |
|---|---|
| A: commercial land prices | 0.26 (0.21–0.30) |
| A: residential + commercial | 0.30 (0.25–0.34) |
| A: municipality-years with 50+ transactions only | 0.34 (0.27–0.42) |
| A: Tokyo area only / outside Tokyo area | 0.43 (0.35–0.51) / 0.28 (0.20–0.37) |
| A: 2020 onward only | 0.40 (0.29–0.48) |
| A: timing of the land price (0, 1, 2 years) | 0.32, 0.35, 0.27 |
| B: random split by point | error 13.9%, correlation with previous year 0.94 |
| B: ridge regression | error 28.0%, correlation with previous year 0.998 |
| B: residential land only | error 17.4% |
| B: first half (2018–21) / second half (2022–26) | 17.5% / 18.7%, direction −1.9% / −3.1% |

Under every condition, "condominiums move 0.25–0.43% per 1% of land price" and "forecast errors persist at the same points (correlation 0.94 or more)" held.

## What this does not show

- **Land prices alone do not explain how condominium prices rose.** Construction costs, interest rates and demand were not included; why condominiums rose faster than land cannot be separated with these data.
- **The link is not causal.** Whether land prices push condominium prices, the reverse, or another factor drives both cannot be separated. The land price publication is a once-a-year appraisal and may lag transaction prices (my interpretation).
- **Transaction prices cover only what was sold.** They are not the price of the same property every year. Quality was adjusted for age, size, minutes to station and structure, but not for floor, orientation or maintenance.
- **Land price errors are about unseen places.** This is not about predicting a published point from its own price last year; simply reusing last year's own price gives a median error of only 1.3%.
- **What the point-specific errors consist of is unknown.** Probably circumstances not in the features (redevelopment, plot shape, surroundings — my interpretation), but none was identified.
- **Features are 2026 values.** As in Part 1, passengers and population change include values from during or after the period.
- **No judgment about areas.** Places with large errors or flat land prices are only places the model handles poorly, not good or bad areas. No municipality ranking is given.
- **Not for investment decisions.** These are counts of past co-movement and errors, not forecasts of future prices.

## How to use this at work

- Before trusting year-to-year updates of a spatial model, check whether errors persist by location; persistent errors call for new features or local corrections, not more retraining.
- Report the direction of errors by price level — regression toward the mean is easy to miss in an overall error rate.
- When linking two price series, test several timing alignments and use fixed effects to separate common trends from local co-movement.

## Series D in four lines

1. Land price rises concentrated in big-city centers and growing municipalities, and much of the last decade's rise was a rebound (Part 1).
2. "What matters" changed a lot with how you compare, and the station effect appeared before opening (Part 1).
3. Condominium prices rose faster than land prices; the year-to-year link was 0.35% per 1% of land price, and older buildings moved more with land (Part 2).
4. Even with yearly updates, land price forecasts kept missing at the same points in the same direction: cheap places too high, expensive places too low (Part 2).

## Figures

The figures have Japanese labels.
- `figures/f208_1_condo_vs_land_index.png`: national indices of condominium and land prices.
- `figures/f208_2_muni_scatter.png`: 8-year changes by municipality, condominiums vs land.
- `figures/f208_3_link_by_age_and_robust.png`: strength of the link by building age and under robustness checks.
- `figures/f208_4_miss_map.png`: map of each point's average forecast error.
- `figures/f208_5_where_misses.png`: direction of errors by price level, change and population.
- `figures/f208_6_persistence.png`: correlation of errors with the previous year.

## Reproduce

```
# after getting the repository, under articles/
python F208_landprice_series_part2/src/02_分析.py F208_landprice_series_part2 .
python F208_landprice_series_part2/src/03_図.py F208_landprice_series_part2
```
- Random seed 208. LightGBM is trained 9 years × 5 folds × 2 (block and random), about 5 minutes on 2 cores.
- If `results/B_oof_yearly.csv.gz` exists, later runs load the main forecasts from it.

## Files

- `src/01_取得.py`: where the input data comes from (no new collection)
- `src/02_分析.py`: analyses A and B
- `src/03_図.py`: six figures
- `results/main.json`: main numbers
- `results/A_national_index.csv`, `A_muni_cumulative.csv`, `A_panel_muni_year.csv.gz`: condominium and land indices and municipality changes
- `results/B_oof_yearly.csv.gz`: the yearly-updated forecasts (point × year)
- `results/B_point_miss.csv.gz`: average error and features by point

## Sources

Processed by the author from MLIT "Real Estate Transaction Price Information" (Real Estate Information Library), MLIT "Official Land Price Publication" and "passengers by station" (National Land Numerical Information L01-26, S12-25), and the 2020 Census (Ministry of Internal Affairs and Communications).
