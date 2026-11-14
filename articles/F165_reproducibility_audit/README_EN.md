# F165 How reproducible are these analyses really? Re-running 40 article folders from scratch

Japanese version: [README.md](README.md). A follow-up audit of all articles is [F297](../F297_article_practice_audit/README_EN.md).

## Question

If someone else follows the README steps of an article folder in this repository, do they get the same numbers? If not, where does it stop, and what differs?

## Data

- This repository itself (commit `de944aa`, 4 Nov 2026, 8:55): 379 folders under `articles/` (160 feature articles and 219 regular articles). F162 and F164, which were in progress, and this F165 were excluded. F30, listed as related in the design document, has no article folder.
- No new external data.

## What I did

1. **Static inventory, without running (all 379)**: `src/01_棚卸し.py`. Counted README reproduction steps, requirements.txt, pinned versions, mismatches between code imports and requirements, network access, references to other article folders, random numbers and seeds, absolute paths, and large files.
2. **Sample (40)**: `src/02_抽出.py`. 10 at random (seed 165) from each of four strata: early feature articles (F01–F80), later feature articles (F81–), early regular articles (000–109), later regular articles (110–).
3. **Re-run**: `src/03_実行.py`. A fresh virtual environment (uv) per article with only that article's requirements.txt installed, versions matched to the authoring environment (`data/constraints_authoring_env.txt`). Emptied results/ and figures/, then ran the README's code blocks from the top, up to 600 seconds per article.
4. **Compare**: `src/04_比較.py`. Compared the regenerated CSV, JSON and text files in results/ with the originals in the repository (relative error: exact / within 1e-6 / 1e-3 / 1e-2 / different / different shape). Figures (PNG) were not compared; run logs were excluded.
5. **Summary and figures**: `src/05_集計.py`, `src/06_図.py`.

Verdict per article:
- **Reproduced as is**: all steps ran and every result file was within relative error 1e-3.
- **Reproduced except download**: only the first data download stopped on the network (this working environment cannot reach government sites, etc.); the remaining steps ran on the data included in the repository and the numbers matched.
- **A step stopped but numbers matched**: a step stopped for a reason other than download, but the remaining results matched.
- **Numbers differed**: at least one result file differed by more than 1e-3.

## Findings

### The 40 re-run articles

| Verdict | Feature | Regular | Total |
|---|---|---|---|
| Reproduced as is | 9 | 20 | 29 |
| Reproduced except download | 3 | 0 | 3 |
| A step stopped but numbers matched | 1 | 0 | 1 |
| Numbers differed | 7 | 0 | 7 |

- Numbers matched for 33 of 40 (83%). Weighted by the sizes of the four strata, the estimate for all 379 is **85% (95% interval 77–94%)**.
- **All 20 regular articles reproduced as is** (one script each, data included in the folder). But 0 failures out of 20 can still miss a failure rate of up to about 14% among the 379 (the "3/n" rule of thumb).
- **Only 9 of 20 feature articles (45%) reproduced as is**; numbers matched for 13 (65%).
- The 7 with differing numbers:
  - F35 (business cycle phases): real-time turning-point calls moved by 1–2 months in two places — a calculation that re-runs an optimization many times, differing the same way in both environments.
  - F51 (childcare and employment): one end of a confidence interval changed (1.2% of the overall maximum).
  - F69 (data quality): the number of detected rows changed a lot in the new environment (13 → 5,730 rows); it matched in the authoring environment.
  - F74 (temperature interpolation): the RMSE table excluding Mt. Fuji went from 10 to 15 rows. The code probably changed after the table was produced and the stored result was stale (my interpretation).
  - F113 (price index): only the order of tied rows; sorted, it matches.
  - F147 (synthesis from tables): 0.3% of cells in a method comparison table differed, only in the new environment.
  - F155 (multiverse): 3–12% of cells among 528 specifications differed.
- Stopped steps: 4 stopped on the network (F43, F44, F74, F87, all at the first download). F77's download step stopped because its target folder `data/raw/` is not in the repository (git does not store empty folders); the next preparation step also stopped, but prepared data was included, so analysis and figures ran and matched.
- Time: median run time 8.2 seconds; longest F155 at 474 seconds.

### Static count of all 379

| Item | Articles |
|---|---|
| README has reproduction steps and requirements.txt | 379 (100%) |
| All versions pinned in requirements.txt | 5 (1%) |
| Packages imported in code but missing from requirements | 13 (3%) |
| Code connects to the network | 66 (17%; 62 feature) |
| Reads another article's folder | 25 (7%; all feature) |
| Uses random numbers without a seed | 5 (1%) |
| Has a run-all script | 20 (5%) |
| Absolute paths | 1 |
| Files over 10 MB | 0 |

## Robustness

| Check | Setting | Numbers matched |
|---|---|---|
| Tolerance | 1e-6 | 33/40 |
| | 1e-3 (main) | 33/40 |
| | 1e-2 | 34/40 |
| | 1e-2, ignoring row order | 35/40 |
| Environment (15 feature articles run in both) | new environment (requirements.txt only) | 9/15 |
| | authoring environment | 12/15 |
| Unit of counting | result files (245) | 231/245 (94%) |
| Steps | counting network failures as failures too (all steps ran) | 35/40 |
| Weighting | unweighted / weighted by four strata | 83% / 85% |

- Environment differences: F69, F113 and F147 matched in the authoring environment but differed in the new one. Since versions were matched, the presence or absence of packages not listed in requirements.txt probably matters (my interpretation; the cause was not identified). F35, F51 and F74 differed in both.
- Articles with a static warning sign (network access, reading another folder, unseeded randomness or missing requirements) ended up other than "reproduced as is" in 6 of 14 cases, versus 5 of 26 without (43% vs 19%, Fisher's exact test p = 0.15). The signs alone cannot reliably tell them apart.

## What this does not show

- **Figures were not compared.** Matching numbers do not guarantee identical figures.
- **Download steps were not verified.** For the 4 that stopped on the network, it is unknown whether the same data can still be obtained from the original sites; if a site's table format changes, the download may break.
- With a sample of 40, the rate for all 379 has a range of about ±9 points; with only 20 feature articles, their range is wider.
- Even the "new environment" used the same Python version and OS as this working environment. On another OS or Python version, there may be more differences.
- Causes of differences were not identified, except F74 (stale result — my interpretation) and F113 (row order).
- "Numbers matched" means matching the stored results/, not the numbers in the article text.

## How to use this at work

- Audit reproducibility by sampling and actually re-running in a clean environment; static checks alone did not separate good from bad folders.
- Pin versions and list every imported package; several differences appeared only when unlisted packages were missing.
- Store results that come from the current code; stale outputs look like irreproducibility.
- Since this audit, the repository runs a weekly automatic re-run check with GitHub Actions.

## Figures

The figures have Japanese labels.
- `figures/f165_verdict.png`: verdicts by stratum.
- `figures/f165_static.png`: results of the static inventory.
- `figures/f165_tolerance.png`: matches by tolerance.
- `figures/f165_env.png`: new vs authoring environment.
- `figures/f165_files.png`: matches counted by result file.

## Reproduce

```bash
git clone https://github.com/takayuki-0127/japan-open-data-notes.git repo
cd repo && git checkout de944aa && cd ..
cd articles/F165_reproducibility_audit   # this article's folder
python src/01_棚卸し.py ../../repo/articles data/inventory.csv
python src/02_抽出.py data/inventory.csv data/sample.csv
python src/03_実行.py ../../repo/articles work data/sample.csv data/run_clean_env.csv --constraints data/constraints_authoring_env.txt --cap 600
python src/04_比較.py work data/run_clean_env.csv data/compare_clean_env_by_article.csv data/compare_clean_env_by_file.csv
python src/03_実行.py ../../repo/articles work2 data/sample.csv data/run_authoring_env.csv --system --cap 600   # authoring environment (optional)
python src/04_比較.py work2 data/run_authoring_env.csv data/compare_authoring_env_by_article.csv data/compare_authoring_env_by_file.csv
python src/05_集計.py
python src/06_図.py
```
- Step 03 uses uv. Times in `data/run_*.csv` are from this working environment and will differ on your machine.
- The authoring-environment run was stopped at the 15 feature articles (time limit).

## Files

| File | Contents |
|---|---|
| src/01_棚卸し.py | static inventory of all folders |
| src/02_抽出.py | stratified sample of 40 |
| src/03_実行.py | re-runs each article in a fresh environment |
| src/04_比較.py | compares regenerated and stored results |
| src/05_集計.py, src/06_図.py | summary and figures |
| data/ | inventory, sample, run logs, comparisons |

## Sources

- The articles/ folder of takayuki-0127/japan-open-data-notes (commit de944aa).
