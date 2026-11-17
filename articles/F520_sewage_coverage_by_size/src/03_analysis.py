"""主な分析：汚水処理人口普及率（下水道・農業集落排水等・コミュニティプラント・合併処理浄化槽の処理人口÷住基人口）を人口規模別に比べる。仮説、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "sewage_pop.csv", dtype={"code": str})
BINS = [0, 5000, 10000, 30000, 100000, 300000, 1e9]
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]
OFFICIAL = {2024: 93.7, 2019: 91.7}  # 国土交通省・農林水産省・環境省の公表値（年度末）
d["rural"] = d[["agri", "fishery", "forest", "simple", "small"]].sum(axis=1)  # 農業集落排水などの集落単位の施設
d["served"] = d[["public_sewer", "rural", "community_plant", "johkaso"]].sum(axis=1)
d["collective"] = d["public_sewer"] + d["rural"] + d["community_plant"]
d["rate"] = 100 * d.served / d["pop"]
d["sewer_rate"] = 100 * d.public_sewer / d["pop"]
d["size"] = pd.cut(d["pop"], BINS, right=False, labels=LABELS).astype(str)
d.to_csv(R / "rate_by_municipality.csv", index=False, float_format="%.4f")


def r(x, k=1):
    return round(float(x), k)


rows = []
for (y, s), g in d.groupby(["year", "size"]):
    P = g["pop"].sum()
    rows.append({"year": y, "size": s, "n": len(g), "pop_total": int(P),
                 "rate_weighted": r(100 * g.served.sum() / P, 2), "rate_median": r(g.rate.median(), 2),
                 "rate_q1": r(g.rate.quantile(0.25), 2), "rate_q3": r(g.rate.quantile(0.75), 2),
                 "sewer_pct": r(100 * g.public_sewer.sum() / P, 2), "rural_pct": r(100 * g.rural.sum() / P, 2),
                 "plant_pct": r(100 * g.community_plant.sum() / P, 2), "johkaso_pct": r(100 * g.johkaso.sum() / P, 2),
                 "unserved_pct": r(100 * (1 - g.served.sum() / P), 2), "unserved_people": int(round(P - g.served.sum())),
                 "nonsewer_share_of_served": r(100 * (1 - g.public_sewer.sum() / g.served.sum()), 2),
                 "collective_weighted": r(100 * g.collective.sum() / P, 2),
                 "n_over100": int((g.rate > 100).sum()), "n_below80": int((g.rate < 80).sum())})
bs = pd.DataFrame(rows)
bs["size"] = pd.Categorical(bs["size"], LABELS, ordered=True)
bs = bs.sort_values(["year", "size"]).reset_index(drop=True)
bs.to_csv(R / "by_size.csv", index=False)


def get(y, s, k):
    return float(bs[(bs.year == y) & (bs["size"] == s)][k].iloc[0])


nat = {y: 100 * g.served.sum() / g["pop"].sum() for y, g in d.groupby("year")}
nat_sewer = {y: 100 * g.public_sewer.sum() / g["pop"].sum() for y, g in d.groupby("year")}
# 2019→2024 の変化は、2024年の規模で団体をそろえる
w = d[d.year == 2019].merge(d[d.year == 2024], on="code", suffixes=("_19", "_24"))
w["size"] = w["size_24"]
chg = []
for s in LABELS:
    g = w[w["size"] == s]
    a = 100 * g.served_19.sum() / g.pop_19.sum(); b = 100 * g.served_24.sum() / g.pop_24.sum()
    chg.append({"size": s, "n": len(g), "rate_2019": r(a, 2), "rate_2024": r(b, 2), "change_pt": r(b - a, 2),
                "pop_change_pct": r(100 * (g.pop_24.sum() / g.pop_19.sum() - 1), 2),
                "served_change_pct": r(100 * (g.served_24.sum() / g.served_19.sum() - 1), 2),
                "median_change_pt": r((g.rate_24 - g.rate_19).median(), 2)})
chg = pd.DataFrame(chg)
chg.to_csv(R / "change_2019_2024.csv", index=False)
cs = chg.set_index("size")

S, M = "5千人未満", "30万人以上"
gap = nat[2024] - get(2024, S, "rate_weighted")
hyp = {
    "H1": {"computed_2024": r(nat[2024], 2), "official_2024": OFFICIAL[2024], "computed_2019": r(nat[2019], 2), "official_2019": OFFICIAL[2019],
           "verdict": "支持" if abs(nat[2024] - OFFICIAL[2024]) <= 1 else "外れ"},
    "H2": {"small_rate": get(2024, S, "rate_weighted"), "national": r(nat[2024], 2), "gap_pt": r(gap, 2), "verdict": "支持" if gap >= 15 else "外れ"},
    "H3": {"small_nonsewer_share": get(2024, S, "nonsewer_share_of_served"), "verdict": "支持" if get(2024, S, "nonsewer_share_of_served") >= 50 else "外れ"},
    "H4": {"small_change_pt": float(cs.loc[S, "change_pt"]), "large_change_pt": float(cs.loc[M, "change_pt"]),
           "verdict": "支持" if cs.loc[S, "change_pt"] > cs.loc[M, "change_pt"] else "外れ"},
}
d24 = d[d.year == 2024]
cap = d24[d24.rate <= 100]
small_cap = cap[cap["size"] == S]
rob = [
    {"check": "本線：5千人未満の普及率（加重＝処理人口の合計÷人口の合計）2024年", "value": get(2024, S, "rate_weighted")},
    {"check": "5千人未満の普及率（団体の中央値）2024年", "value": get(2024, S, "rate_median")},
    {"check": "5千人未満の普及率（団体の単純平均）2024年", "value": r(d24[d24["size"] == S].rate.mean(), 2)},
    {"check": "普及率が10%未満の団体の数 2024年", "value": int((d24.rate < 10).sum())},
    {"check": "5千人未満の普及率（100%を超える団体を除く、加重）2024年", "value": r(100 * small_cap.served.sum() / small_cap["pop"].sum(), 2)},
    {"check": "5千人未満の集合処理だけ（浄化槽を除く）2024年", "value": get(2024, S, "collective_weighted")},
    {"check": "全国の集合処理だけ（浄化槽を除く）2024年", "value": r(100 * d24.collective.sum() / d24["pop"].sum(), 2)},
    {"check": "全国との差（中央値どうし）pt 2024年", "value": r(d24.rate.median() - get(2024, S, "rate_median"), 2)},
    {"check": "全国との差（加重）pt 2019年", "value": r(nat[2019] - get(2019, S, "rate_weighted"), 2)},
    {"check": "100%を超える団体の数 2024年", "value": int((d24.rate > 100).sum())},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
low = d24[d24.rate < 80]
main = {
    "n_2024": int(len(d24)), "pop_2024": int(d24["pop"].sum()), "served_2024": int(d24.served.sum()),
    "national_rate": {str(k): r(v, 2) for k, v in nat.items()}, "national_sewer_rate": {str(k): r(v, 2) for k, v in nat_sewer.items()},
    "national_nonsewer_share_2024": r(100 * (1 - d24.public_sewer.sum() / d24.served.sum()), 2),
    "national_median_rate_2024": r(d24.rate.median(), 2),
    "n_below80_2024": int(len(low)), "n_below80_small_2024": int((low["size"] == S).sum()),
    "pop_below80_2024": int(low["pop"].sum()), "unserved_2024": int(d24["pop"].sum() - d24.served.sum()),
    "unserved_by_size_2024": {s: int(bs[(bs.year == 2024) & (bs["size"] == s)].unserved_people.iloc[0]) for s in LABELS},
    "unserved_share_by_size_2024": {s: r(100 * bs[(bs.year == 2024) & (bs["size"] == s)].unserved_people.iloc[0] / (d24["pop"].sum() - d24.served.sum()), 1) for s in LABELS},
    "hypotheses": hyp,
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(bs[bs.year == 2024].to_string()); print(chg.to_string()); print(json.dumps(main, ensure_ascii=False, indent=1)); print(pd.DataFrame(rob).to_string())
