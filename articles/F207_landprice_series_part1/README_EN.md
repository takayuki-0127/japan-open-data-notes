# F207 Where did land prices rise, and what happens when a new station opens? (Part 1)

Japanese version: [README.md](README.md). Part 2 is [F208](../F208_landprice_series_part2/README_EN.md).

This deep-dive series on land prices and housing reuses the data of earlier land-price articles in this repository (F03 machine learning, F37 prediction ranges, F91 interpretation methods, F158 yearly updates, 042 changes over ten years) and looks at one question from three angles: "how much of land-price movement can be explained, and how much do stations matter?"

## Question

1. Over 20 years (2006→2026), where did land prices rise and where did they fall? What do the rising points have in common?
2. Do a model that "explains" land prices (regression) and a model that "predicts" them (machine learning) give the same answers?
3. When a new station opens, how much do nearby land prices rise?

## Data

| Data | Contents |
|---|---|
| Official land price publication (National Land Numerical Information L01-26, 2026) | 25,565 points. Prices for each point 1996–2026 (L01_075–L01_105) and attribute-change codes 2007–2026 (L01_129–L01_148) |
| Point features and station locations | Same as F03 (`articles/F03_land_price_ml/data/features.csv`, `stations.csv`): distance from the centers of the three major metro areas, distance to the nearest station, passengers at stations within 1 km, municipality population, density, 2015→20 population change, floor-area ratio, etc. |
| Opening dates of new stations | 74 stations (20 lines) opened 2005–2023, entered by hand in `data/stations_new.csv` from railway operators' published materials, and matched to F03 station locations by name and latitude |

- `data/price_hist_1996_2026.csv.gz`: price by point × year (0 means the point did not exist that year).
- `data/chg_2007_2026.csv.gz`: yearly attribute-change codes (a leading 1 means the same point continued from the previous year).
- Only the history of points selected in 2026; points dropped along the way are not included (see "What this does not show").

## What I did

| Question | Method |
|---|---|
| 1. 20-year change | For 11,877 points that continued every year 2007–2026, log(2026 price ÷ 2006 price). Summarized by distance from the three metro centers, municipality population change, etc., and compared features with a standardized regression (standard errors clustered by municipality). Also compared the first decade (2006→16) with the second (2016→26). |
| 2. Explain vs predict | Predicted 2026 log(price) with (1) regression (7 variables), (2) regression + municipality population, (3) LightGBM (14 variables). Compared errors (median of \|prediction ÷ actual − 1\|) under spatial cross-validation (5 folds of 20 km blocks) and random 5-fold CV. Also compared the effect of "distance to the nearest station" across four regression specifications and LightGBM (average difference in predictions when the distance is nudged). |
| 3. New stations | Points within 1 km of a new station and more than 1 km from any other station (points that first got a nearby station) are "treated"; points 1.5–4 km from the same station are "comparison". With the first price publication after opening as year 0, compared price changes from −5 to +5 years (relative to the publication 1 year before opening) station by station (event study). Intervals from a station-level bootstrap (2,000 draws). |

## Findings

### 1. 44% of points rose over 20 years; 93% within 10 km of the three metro centers (Figures 1–2)

- Of 11,877 continuing points, 43.9% rose 2006→2026; median change −6.2%.
- By region (share rising / median): Tokyo area 73% / +21%, Nagoya area 60% / +6%, Osaka area 53% / +2%, other regions 24% / −24%.
- By distance from the three metro centers: within 10 km 93% / +89%; 10–20 km 82% / +29%; 20–40 km 61% / +7%; 40–80 km 29% / −14%; 80 km+ 25% / −24%.
- By municipality population change (2015→20): where population fell by more than 5%, only 2% of points rose (median −38%); where it grew 2% or more, 90% rose (+46%).
- In a standardized regression with six features together, municipality population change (+0.27) and station passengers within 1 km (+0.12) were large; distance from the metro centers (+0.01, SE 0.016) lost its effect once the other variables were included (R² 0.58).

### 2. Much of the second decade's rise is a rebound of points that fell in the first (Figure 3)

- Points rising: 24% in 2006→16, 63% in 2016→26.
- Rose in both decades 23%; fell then rose 40%; rose then fell 0.3%; fell in both 36%.
- Correlation between the two decades' changes: 0.65 (points that fell a lot earlier stayed weak later).
- Other start years: 2011→26, 52% rising, median +1.8%; 2016→26, 63% rising, +7.1%.

### 3. Machine learning predicts better, but the regression's answer on "how much stations matter" moves a lot with its specification (Figures 4–5)

Median error (spatial CV / random CV):

| Model | Spatial | Random |
|---|---|---|
| Regression (7 variables) | 54.8% | 53.9% |
| Regression + municipality population | 36.3% | 36.0% |
| LightGBM (14 variables) | 22.9% | 16.6% |

Difference in land price from right next to a station to about 1.7 km away (log(1 + km) up by 1):

| Model | Difference | 95% interval |
|---|---|---|
| Regression (7 variables) | −13% | −15 to −11% |
| Regression + municipality population | −3% | −5 to −2% |
| Regression + population + latitude/longitude | −5% | −6 to −3% |
| Regression comparing within municipalities (fixed effects) | −32% | −34 to −31% |
| LightGBM (average difference) | −34% | — |

- Adding municipality population made the station effect smaller (station proximity overlaps with the size of the municipality — my interpretation), and comparing within the same municipality made it larger. LightGBM's answer (−34%) was close to the within-municipality regression.
- LightGBM's difference varied by region: Tokyo −47%, Osaka −38%, Nagoya −28%, others −25% (7-variable regression: −25%, −28%, −23%, −13%).

### 4. Land prices near new stations were already rising before opening (Figure 6)

- 32 stations had qualifying treated points (68 points; 3,962 comparison points).
- Treated minus comparison, relative to 1 year before opening: 5 years before −5.8%, 3 years before −4.0%, 2 years before −1.4%, first publication after opening +1.7%, 2 years after +2.9%, 5 years after +2.0%.
- Average difference 1–5 years after opening: +2.4% (95% interval +0.4 to +4.3%). But the pre-opening difference (−5 to −2 years) was also −3.9% (−5.8 to −1.9%): treated points were already growing 1–2% a year faster before opening.
- A "fake opening" shifted 5 years earlier also gave +5.7% (+3.4 to +8.0%), so a before/after difference-in-differences around the opening does not measure the station effect correctly. The station effect (and price rises in anticipation) seems to appear gradually over many years before opening (my interpretation).
- From −5 to +2 years in total, treated points rose about 8.7% more than comparison points.

## Robustness

| Check | Result |
|---|---|
| Start year of the 20-year change (2006, 2011, 2016) | share rising 44%, 52%, 63%; the pattern "closer to metro centers rises more" holds for every start (results/main.json) |
| Explain vs predict: how CV is split (spatial / random) | regression barely changes; LightGBM's error widens from 16.6% to 22.9% with spatial splits; ranking unchanged |
| Station effect: residential land only | regression (7 variables) −18%, LightGBM −31%; regression still smaller |
| New stations: treated radius 0.5 km | after opening +4.3% (+2.4 to +6.1%), before −2.7% |
| New stations: drop the "more than 1 km from other stations" condition (58 stations) | +2.2% (+0.5 to +3.9%), before −2.9% |
| New stations: comparison band 1–2 km / 2–5 km | +1.4% (−0.2 to +3.1%) / +2.9% (+0.9 to +4.8%) |
| New stations: excluding the Tsukuba Express / excluding Shinkansen | +1.7% (−0.2 to +3.6%) / +2.7% (+0.8 to +4.6%) |
| New stations: fake opening 5 years earlier | +5.7% (+3.4 to +8.0%), showing growth before opening |

## What this does not show

- **Survivors only.** This is the history of points selected in 2026, so points dropped along the way (possibly more common where prices fell sharply — my interpretation) are missing. Declines may be understated.
- **Features are current values.** Municipality population change is 2015→20 and passengers are 2024, i.e. partly measured after the 20-year change. Whether prices rose because population grew, or people moved to where prices rose, cannot be separated.
- **The station effect is not causal.** Both the regression coefficients and LightGBM's differences describe "points near stations are expensive", not the effect of moving a station.
- **The effect of new stations was not measured.** Because prices rose before opening, the station's effect, rises in anticipation of the plan, and stations being built where growth was already happening cannot be separated. Plan announcement dates were not used.
- **Few new-station points.** 32 stations, 68 points; lines cannot be compared (1–18 points per line).
- **Opening dates were entered by hand** from railway operators' materials and matched to F03 station locations by name and latitude; checking that no same-named station was picked up was done by eye.
- **No judgment about areas.** Rising or falling land prices are movements in land values, not a verdict on whether an area is good. No municipality ranking is given.

## How to use this at work

- When a model is used to explain a driver (here, station distance), report how the answer moves across reasonable specifications, not one coefficient.
- Validate spatial models with spatial splits; random splits flatter flexible models.
- Before reading an event study as an effect, look at the pre-period and run a placebo (fake event date).

## Handed to Part 2 (F208)

- `data/price_hist_1996_2026.csv.gz`: price by point × year (1996–2026), usable as is for comparing condominium prices with land prices (F56, F182).
- `results/A_change_2006_2026.csv.gz`: the 20-year change with point, region and land use, which can be overlaid on Part 2's map of "places where forecasts miss".
- `B_cv` and `B_eff` in `results/main.json`: numbers from the explain-vs-predict comparison, a starting point for Part 2's "where do yearly-updated forecasts miss?" (bringing in F158).
- Conclusions carried over: (1) rises concentrate near big-city centers and in growing municipalities, and much of the second decade was a rebound; (2) the station effect changes a lot with how you compare; (3) new stations' effects appear before opening and cannot be measured by before/after alone.
- Part 2 covers how condominium prices move with land prices (real estate transaction price data, F56, F182), where yearly-updated land price forecasts tend to miss (F158, F108, F109), and what the data can and cannot say.

## Figures

The figures have Japanese labels.
- `figures/f207_1_map_20y.png`: map of the 20-year change by point.
- `figures/f207_2_where_rose.png`: share rising by region, distance and population change.
- `figures/f207_3_two_decades.png`: first-decade vs second-decade change.
- `figures/f207_4_explain_vs_predict.png`: errors of regression and LightGBM under spatial and random CV.
- `figures/f207_5_station_effect_models.png`: station-distance effect by model specification.
- `figures/f207_6_new_station_event.png`: event study around new station openings.

## Reproduce

```
pip install -r requirements.txt
python src/01_取得.py <L01-26.geojson> data/      # builds the two csv.gz files in data/ (download is manual)
python src/02_分析.py . ..                         # second argument: the articles folder containing F03_land_price_ml
python src/03_図.py . figures
```
Random seed 207. LightGBM uses n_jobs=2.

## Files

| File | Contents |
|---|---|
| src/01_取得.py | extracts price histories and change codes from the land price GeoJSON |
| src/02_分析.py | 20-year change, explain vs predict, new-station event study |
| src/03_図.py | Figures 1–6 |
| data/stations_new.csv | hand-entered opening dates of new stations |
| results/ | tables and main.json |

## Sources

Processed by the author from the Ministry of Land, Infrastructure, Transport and Tourism "Official Land Price Publication" (National Land Numerical Information L01-26, https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-2026.html), MLIT "passengers by station" (S12-25), and the 2020 Census (Ministry of Internal Affairs and Communications). New-station opening dates are from railway operators' published materials.
