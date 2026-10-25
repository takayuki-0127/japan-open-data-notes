"""03 語の出現率（発言1万件あたり）の推移と、物価・賃上げ率との関係"""
import numpy as np, pandas as pd
from common import DATA, RES

c = pd.read_csv(DATA / "counts_by_year.csv", keep_default_na=False)
tot = c[c.keyword == ""].set_index(["scope", "year"]).n
c = c[c.keyword != ""].copy()
c["total"] = [tot[(s, y)] for s, y in zip(c.scope, c.year)]
c["per10k"] = c.n / c.total * 1e4
c.to_csv(RES / "rates_by_year.csv", index=False)

allr = c[c.scope == ""].pivot(index="year", columns="keyword", values="per10k")
allr.round(2).to_csv(RES / "rates_wide_all.csv")

# 年代別の平均とピーク
rows = []
for k in allr.columns:
    s = allr[k]
    rows.append({"keyword": k, "peak_year": int(s.idxmax()), "peak": round(s.max(), 1),
                 "1985_94": round(s.loc[1985:1994].mean(), 1), "1995_2004": round(s.loc[1995:2004].mean(), 1),
                 "2005_14": round(s.loc[2005:2014].mean(), 1), "2015_25": round(s.loc[2015:2025].mean(), 1),
                 "2025": round(s.loc[2025], 1), "2026_part": round(s.loc[2026], 1)})
pd.DataFrame(rows).sort_values("peak", ascending=False).to_csv(RES / "keyword_summary.csv", index=False)

# 物価上昇率・賃上げ率との関係（1985〜2025年）
cpi = pd.read_csv(DATA / "cpi_annual_yoy.csv").set_index("year").cpi_yoy_pct
wage = pd.read_csv(DATA / "wage_increase_rate.csv").set_index("year").wage_increase_pct
yrs = range(1985, 2026)
df = pd.DataFrame({"bukka": allr["物価"].loc[yrs], "chinage": allr["賃上げ"].loc[yrs],
                   "deflation": allr["デフレ"].loc[yrs], "cpi": cpi.loc[yrs], "wage": wage.loc[yrs]})
df.to_csv(RES / "merged_macro.csv")


def lagcorr(a, b, lags=range(-2, 3)):
    """lag>0：b（統計）が a（発言）より lag 年先に動く＝発言が後追い"""
    out = {}
    for L in lags:
        out[L] = float(round(a.corr(b.shift(L)), 3))
    return out


def boot_ci(a, b, n=2000, seed=1):
    rng = np.random.default_rng(seed); idx = np.arange(len(a)); v = []
    for _ in range(n):
        # 3年のブロックブートストラップ（自己相関を考える）
        starts = rng.integers(0, len(a) - 2, size=len(a) // 3 + 1)
        ii = np.concatenate([idx[s:s + 3] for s in starts])[:len(a)]
        v.append(np.corrcoef(a.values[ii], b.values[ii])[0, 1])
    return np.round(np.percentile(v, [2.5, 97.5]), 3).tolist()


res = []
for name, a, b in [("物価の出現率×CPI上昇率", df.bukka, df.cpi), ("賃上げの出現率×賃上げ率", df.chinage, df.wage),
                   ("デフレの出現率×CPI上昇率", df.deflation, df.cpi)]:
    r = round(a.corr(b), 3)
    rd = round(a.diff().corr(b.diff()), 3)
    res.append({"pair": name, "r_level": r, "ci95_level": boot_ci(a, b), "r_diff": rd, "lags": lagcorr(a, b)})
for sub, lab in [((1985, 2012), "1985〜2012"), ((2013, 2025), "2013〜2025")]:
    d = df.loc[sub[0]:sub[1]]
    res.append({"pair": f"物価×CPI {lab}", "r_level": round(d.bukka.corr(d.cpi), 3), "ci95_level": None,
                "r_diff": round(d.bukka.diff().corr(d.cpi.diff()), 3), "lags": None})
    res.append({"pair": f"賃上げ×賃上げ率 {lab}", "r_level": round(d.chinage.corr(d.wage), 3), "ci95_level": None,
                "r_diff": round(d.chinage.diff().corr(d.wage.diff()), 3), "lags": None})
pd.DataFrame(res).to_csv(RES / "macro_correlations.csv", index=False)

# 頑健性：会議の範囲（全体／本会議／予算委員会）での推移の相関、表記ゆれ
rob = []
for k in ["賃上げ", "物価", "少子化", "デフレ"]:
    w = c[c.keyword == k].pivot(index="year", columns="scope", values="per10k")
    rob.append({"check": f"{k}：全体×本会議", "r": round(w[""].corr(w["本会議"]), 3)})
    rob.append({"check": f"{k}：全体×予算委員会", "r": round(w[""].corr(w["予算委員会"]), 3)})
    rob.append({"check": f"{k}：ピーク年（全体/本会議/予算委員会）",
                "r": f"{int(w[''].idxmax())}/{int(w['本会議'].idxmax())}/{int(w['予算委員会'].idxmax())}"})
for v in ["賃金引上げ", "賃金の引上げ", "ベースアップ"]:
    rob.append({"check": f"賃上げ×{v}（出現率の相関）", "r": round(allr["賃上げ"].corr(allr[v]), 3)})
    rob.append({"check": f"{v}のピーク年", "r": int(allr[v].idxmax())})
pd.DataFrame(rob).to_csv(RES / "robustness_scope_variants.csv", index=False)
print(pd.DataFrame(rows).to_string()); print(pd.DataFrame(res).to_string()); print(pd.DataFrame(rob).to_string())
