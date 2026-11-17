"""主な分析：住民1,000人あたりの職員数を人口の規模別に比べる、対数の回帰、2020→2025年の変化、仮説、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "staff_pop.csv", dtype={"code": str})
BINS = [0, 5000, 10000, 30000, 100000, 300000, 1e9]
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]
d["size"] = pd.cut(d["pop"], BINS, right=False, labels=LABELS).astype(str)
d.loc[d.kind == "指定都市", "size"] = "指定都市"
ORDER = LABELS + ["指定都市"]
for c in ["gen_admin", "welfare", "general", "ordinary", "total", "education", "fire"]:
    d[f"{c}_per1000"] = 1000 * d[c] / d["pop"]
d.to_csv(R / "per1000_by_municipality.csv", index=False, float_format="%.4f")


def r(x, k=2):
    return round(float(x), k)


rows = []
for (y, s), g in d.groupby(["year", "size"]):
    rows.append({"year": y, "size": s, "n": len(g), "pop_total": int(g["pop"].sum()),
                 "general_median": r(g.general_per1000.median()), "general_q1": r(g.general_per1000.quantile(0.25)), "general_q3": r(g.general_per1000.quantile(0.75)),
                 "general_weighted": r(1000 * g.general.sum() / g["pop"].sum()),
                 "gen_admin_median": r(g.gen_admin_per1000.median()), "welfare_median": r(g.welfare_per1000.median()),
                 "ordinary_median": r(g.ordinary_per1000.median()), "ordinary_weighted": r(1000 * g.ordinary.sum() / g["pop"].sum())})
bs = pd.DataFrame(rows)
bs["size"] = pd.Categorical(bs["size"], ORDER, ordered=True)
bs = bs.sort_values(["year", "size"]).reset_index(drop=True)
bs.to_csv(R / "by_size.csv", index=False)


def get(y, s, k):
    return float(bs[(bs.year == y) & (bs["size"] == s)][k].iloc[0])


def slope(df, col):
    x = df[(df[col] > 0)]
    b, a = np.polyfit(np.log(x["pop"]), np.log(x[col]), 1)
    return float(b)


d25 = d[d.year == 2025]; d20 = d[d.year == 2020]
sl = slope(d25, "general")
both = d20.merge(d25, on="code", suffixes=("_20", "_25"))
both["size"] = both["size_25"]
chg = both.groupby("size").apply(lambda g: pd.Series({"median_change": g.general_per1000_25.median() - g.general_per1000_20.median(),
                                                      "pop_change_pct": 100 * (g.pop_25.sum() / g.pop_20.sum() - 1),
                                                      "staff_change_pct": 100 * (g.general_25.sum() / g.general_20.sum() - 1)}), include_groups=False)
chg = chg.reindex(ORDER).round(3)
chg.to_csv(R / "change_2020_2025.csv")

ratio = get(2025, "5千人未満", "general_median") / get(2025, "10万〜30万人", "general_median")
ratio_ga = get(2025, "5千人未満", "gen_admin_median") / get(2025, "10万〜30万人", "gen_admin_median")
ratio_wf = get(2025, "5千人未満", "welfare_median") / get(2025, "10万〜30万人", "welfare_median")
hyp = {
    "H1": {"small_median": get(2025, "5千人未満", "general_median"), "mid_median": get(2025, "10万〜30万人", "general_median"), "ratio": r(ratio),
           "verdict": "支持" if ratio >= 3 else "外れ"},
    "H2": {"slope_general_2025": r(sl, 3), "verdict": "支持" if sl < 0.8 else "外れ"},
    "H3": {"small_change": r(chg.loc["5千人未満", "median_change"]), "mid_change": r(chg.loc["10万〜30万人", "median_change"]),
           "verdict": "支持" if (chg.loc["5千人未満", "median_change"] > 0 and chg.loc["5千人未満", "median_change"] > chg.loc["10万〜30万人", "median_change"]) else "外れ"},
    "H4": {"ratio_gen_admin": r(ratio_ga), "ratio_welfare": r(ratio_wf), "verdict": "支持" if ratio_wf < ratio_ga else "外れ"},
}
rob = [
    {"check": "本線：一般行政、中央値の比（5千人未満÷10万〜30万人）2025年", "value": r(ratio)},
    {"check": "加重（職員の合計÷人口の合計）の比 2025年", "value": r(get(2025, "5千人未満", "general_weighted") / get(2025, "10万〜30万人", "general_weighted"))},
    {"check": "普通会計計（教育・消防を含む）の中央値の比 2025年", "value": r(get(2025, "5千人未満", "ordinary_median") / get(2025, "10万〜30万人", "ordinary_median"))},
    {"check": "2020年の中央値の比", "value": r(get(2020, "5千人未満", "general_median") / get(2020, "10万〜30万人", "general_median"))},
    {"check": "対数の傾き：本線（2025年、全団体）", "value": r(sl, 3)},
    {"check": "対数の傾き：指定都市を除く", "value": r(slope(d25[d25.kind != "指定都市"], "general"), 3)},
    {"check": "対数の傾き：人口1千人未満を除く", "value": r(slope(d25[d25["pop"] >= 1000], "general"), 3)},
    {"check": "対数の傾き：2020年", "value": r(slope(d20, "general"), 3)},
    {"check": "対数の傾き：普通会計計（2025年）", "value": r(slope(d25, "ordinary"), 3)},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
main = {
    "n_2025": int(len(d25)), "pop_2025": int(d25["pop"].sum()), "general_2025": int(d25.general.sum()), "general_2020": int(d20.general.sum()),
    "pop_2020": int(d20["pop"].sum()),
    "general_per1000_national": {"2020": r(1000 * d20.general.sum() / d20["pop"].sum()), "2025": r(1000 * d25.general.sum() / d25["pop"].sum())},
    "by_size_2025": {s: {k: get(2025, s, k) for k in ["n", "general_median", "general_q1", "general_q3", "gen_admin_median", "welfare_median", "ordinary_median"]} for s in ORDER},
    "change_2020_2025": {s: {k: float(chg.loc[s, k]) for k in chg.columns} for s in ORDER},
    "min_pop_2025": int(d25["pop"].min()), "n_under1000": int((d25["pop"] < 1000).sum()),
    "hypotheses": hyp,
    "note": "職員数は4月1日（定員管理調査）、人口は1月1日（住民基本台帳）。一般行政＝一般管理＋福祉関係。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(hyp, ensure_ascii=False)); print(bs[bs.year == 2025].to_string()); print(chg); print(pd.read_csv(R / "robustness.csv").to_string())
