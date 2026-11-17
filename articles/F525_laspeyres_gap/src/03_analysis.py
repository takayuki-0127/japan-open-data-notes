"""主な分析：ラスパイレス指数のばらつきの推移（市区町村）、団体の種類別、2025年の人口規模別。仮説と頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "laspeyres.csv", dtype={"code": str})
KIND = {1: "都道府県", 2: "指定都市", 3: "市", 4: "特別区", 5: "町", 6: "村"}
d["kind"] = d.kubun.map(KIND)
Y = [2008, 2013, 2018, 2025]
BINS = [0, 5000, 10000, 30000, 100000, 300000, 1e9]
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]


def r(x, k=2):
    return round(float(x), k)


def stat(s):
    return pd.Series({"n": len(s), "median": r(s.median(), 1), "mean": r(s.mean()), "sd": r(s.std()), "q1": r(s.quantile(.25), 1), "q3": r(s.quantile(.75), 1),
                      "iqr": r(s.quantile(.75) - s.quantile(.25)), "p10": r(s.quantile(.1), 1), "p90": r(s.quantile(.9), 1),
                      "p90_p10": r(s.quantile(.9) - s.quantile(.1)), "over100_pct": r(100 * (s >= 100).mean(), 1), "min": r(s.min(), 1), "max": r(s.max(), 1)})


mu = d[d.kubun >= 3]  # 市区町村（指定都市を除く。ファイルの区分どおり）
by_year = mu.groupby("year").las.apply(stat).unstack()
by_year.to_csv(R / "muni_by_year.csv")
by_kind = d.groupby(["year", "kind"]).las.apply(stat).unstack().reset_index()
by_kind["kind"] = pd.Categorical(by_kind.kind, list(KIND.values()), ordered=True)
by_kind = by_kind.sort_values(["year", "kind"])
by_kind.to_csv(R / "by_kind.csv", index=False)
m25 = d[(d.year == 2025) & (d.kubun >= 2)].copy()
m25["size"] = pd.cut(m25.pop2025, BINS, right=False, labels=LABELS).astype(str)
by_size = m25.groupby("size").las.apply(stat).unstack().reindex(LABELS)
by_size.to_csv(R / "size_2025.csv")
corr = float(np.corrcoef(np.log(m25.pop2025), m25.las)[0, 1])
k = by_kind.set_index(["year", "kind"])
sd08, sd25 = by_year.loc[2008, "sd"], by_year.loc[2025, "sd"]
town25 = mu[(mu.year == 2025) & mu.kubun.isin([5, 6])].las.median()
city25 = mu[(mu.year == 2025) & (mu.kubun == 3)].las.median()
hyp = {
    "H1": {"sd_2008": sd08, "sd_2025": sd25, "shrink_pct": r(100 * (1 - sd25 / sd08), 1), "verdict": "支持" if sd25 <= 0.7 * sd08 else "外れ"},
    "H2": {"town_median_2025": r(town25, 1), "city_median_2025": r(city25, 1), "gap": r(city25 - town25, 1), "verdict": "支持" if city25 - town25 >= 2 else "外れ"},
    "H3": {"over100_2008": by_year.loc[2008, "over100_pct"], "over100_2025": by_year.loc[2025, "over100_pct"],
           "verdict": "支持" if by_year.loc[2025, "over100_pct"] < by_year.loc[2008, "over100_pct"] else "外れ"},
    "H4": {"r_logpop_las_2025": r(corr, 3), "verdict": "支持" if corr >= 0.3 else "外れ"},
}
nk = mu[mu.kubun != 4]
a13 = mu[mu.year == 2013].las_actual
adj25 = mu[mu.year == 2025].las_adj
rob = [
    {"check": "本線：市区町村の標準偏差 2008→2025", "v2008": sd08, "v2025": sd25},
    {"check": "四分位の幅", "v2008": by_year.loc[2008, "iqr"], "v2025": by_year.loc[2025, "iqr"]},
    {"check": "10%点〜90%点の幅", "v2008": by_year.loc[2008, "p90_p10"], "v2025": by_year.loc[2025, "p90_p10"]},
    {"check": "特別区を除く標準偏差", "v2008": r(nk[nk.year == 2008].las.std()), "v2025": r(nk[nk.year == 2025].las.std())},
    {"check": "2013年：参考値／実際の指数の中央値", "v2008": by_year.loc[2013, "median"], "v2025": r(a13.median(), 1)},
    {"check": "2013年：参考値／実際の指数の標準偏差", "v2008": by_year.loc[2013, "sd"], "v2025": r(a13.std())},
    {"check": "2025年：地域手当補正後の指数の中央値／標準偏差", "v2008": r(adj25.median(), 1), "v2025": r(adj25.std())},
    {"check": "人口（対数）との相関：本線（2025年、指定都市を含む）／市だけ", "v2008": r(corr, 3),
     "v2025": r(np.corrcoef(np.log(m25[m25.kubun == 3].pop2025), m25[m25.kubun == 3].las)[0, 1], 3)},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
main = {"muni": {str(y): {c: float(by_year.loc[y, c]) for c in ["n", "median", "sd", "iqr", "p10", "p90", "over100_pct", "min", "max"]} for y in Y},
        "kind_median": {f"{y}_{kk}": float(k.loc[(y, kk), "median"]) for y in Y for kk in KIND.values()},
        "kind_sd": {f"{y}_{kk}": float(k.loc[(y, kk), "sd"]) for y in Y for kk in KIND.values()},
        "size_median_2025": {s: float(by_size.loc[s, "median"]) for s in LABELS},
        "size_sd_2025": {s: float(by_size.loc[s, "sd"]) for s in LABELS},
        "hypotheses": hyp}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(by_year.to_string()); print(by_kind[["year", "kind", "n", "median", "sd", "p10", "p90"]].to_string()); print(by_size.to_string())
print(json.dumps(hyp, ensure_ascii=False)); print(pd.DataFrame(rob).to_string())
