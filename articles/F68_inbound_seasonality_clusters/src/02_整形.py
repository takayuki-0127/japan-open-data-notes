"""02 整形：国・地域ごとの「季節の形」（各月の人数÷年平均、5年平均）を作る"""
import pandas as pd

from common import DATA, MARKETS, BASE_YEARS, POST_YEARS, load_long, panel, profile

d = load_long()
p = panel(d)
assert p[[y for y in range(2005, 2026) if y not in (2020, 2021, 2022)]].notna().all().all()

profile(p, BASE_YEARS).round(5).to_csv(DATA / "profile_2015_2019.csv")
profile(p, POST_YEARS).round(5).to_csv(DATA / "profile_2023_2025.csv")
profile(p, [2005, 2006, 2007, 2008, 2009]).round(5).to_csv(DATA / "profile_2005_2009.csv")
profile(p, BASE_YEARS, per_day=True).round(5).to_csv(DATA / "profile_2015_2019_perday.csv")
for y in BASE_YEARS + POST_YEARS:
    profile(p, [y]).round(5).to_csv(DATA / f"profile_year_{y}.csv")

ann = d[d.market.isin(MARKETS + ["総数"])].groupby(["market", "year"]).visitors.sum().unstack()
ann.to_csv(DATA / "annual_visitors.csv")
print(ann[[2015, 2019, 2025]].loc[MARKETS].sum() / ann.loc["総数", [2015, 2019, 2025]])
