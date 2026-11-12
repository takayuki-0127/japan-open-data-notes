"""399 世帯主の年齢ごとの貯蓄と負債：全国家計構造調査（2014年遡及・2019年・2024年）第6-108表、2024年 第4-4表（総世帯）"""
import csv, json, re
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save
SRC = "出典：総務省統計局「全国家計構造調査」（2019年・令和6年、2014年は遡及集計）第6-108表ほかをもとに作成者が加工して作成"
num = lambda s: np.nan if s.strip() in ("", "-", "…", "X", "***") else float(s)
def load(f, lab_row, item_col, cls_col, v0):
    r = list(csv.reader(open(DATA / "raw" / f, encoding="utf-8")))
    ages = [re.sub(r"（.*", "", c) for c in r[lab_row][v0:v0 + 32]]
    out = {}
    for x in r[lab_row + 1:]:
        if len(x) > v0 and x[item_col] and x[cls_col]:
            out[(x[item_col], x[cls_col])] = dict(zip(ages, [num(c) for c in x[v0:v0 + 32]]))
    return ages, out
S = {2014: load("kakei2014retro_t6_108_total.csv", 7, 11, 13, 15), 2019: load("kakei2019_t6_108_total.csv", 7, 11, 13, 15), 2024: load("kakei2024_t6_108_total.csv", 5, 8, 10, 12)}
AG = [a for a in S[2024][0] if a[:1] == "1"]; assert len(AG) == 13, AG
NAME = {a: a.split("_")[1].replace("～", "〜") for a in AG}; NAME[AG[0]] = "30歳未満"; NAME[AG[-1]] = "85歳以上"
CL = [k[1] for k in S[2024][1] if k[0] == "世帯数分布" and k[1] != "00_平均"]; assert len(CL) == 19
EDGE = [0, 25, 50, 100, 150, 200, 300, 450, 600, 750, 900, 1200, 1500, 2000, 3000, 4000, 5000, 7500, 10000]  # 万円（各階級の下限）
def stats(y, a):
    T = S[y][1]; w = np.array([T[("世帯数分布", c)][a] for c in CL]); w = np.nan_to_num(w); tot = w.sum()
    gap = (T[("世帯数分布", "00_平均")][a] - tot) / T[("世帯数分布", "00_平均")][a] * 100  # 階級の合計が総数に足りない分（貯蓄が不詳の世帯とみられる）
    assert -0.1 < gap < 6, (y, a, gap)
    cum = np.cumsum(w)
    def q(p):
        h = tot * p; i = int(np.searchsorted(cum, h)); lo = cum[i - 1] if i else 0
        if i == len(CL) - 1: return np.nan
        return EDGE[i] + (h - lo) / w[i] * (EDGE[i + 1] - EDGE[i])
    mean = T[("1世帯当たり貯蓄現在高", "00_平均")][a] / 10; debt = T[("1世帯当たり負債現在高", "00_平均")][a] / 10  # 千円→万円
    return dict(year=y, age=a, label=NAME.get(a, "平均"), households=tot, mean=mean, debt=debt, median=q(0.5), q25=q(0.25), q75=q(0.75),
                p_u100=w[:3].sum() / tot * 100, p_u25=w[0] / tot * 100, p_2000p=w[13:].sum() / tot * 100, p_3000p=w[14:].sum() / tot * 100, p_1okup=w[18] / tot * 100,
                income=T[("1世帯当たり年間収入額", "00_平均")][a] / 10, class_gap=gap)
d = pd.DataFrame([stats(y, a) for y in S for a in ["000_平均"] + AG])
d["mean_over_median"] = d["mean"] / d["median"]; d["net"] = d["mean"] - d.debt
d.to_csv(DATA / "savings_by_age.csv", index=False)
# 2024年 第4-4表：負債の内訳・保有率
r = list(csv.reader(open(DATA / "raw" / "kakei2024_t4_4_total.csv", encoding="utf-8")))
ages4 = [re.sub(r"（.*", "", c) for c in r[5][12:44]]
T4 = {(x[8], x[10]): dict(zip(ages4, [num(c) for c in x[12:44]])) for x in r[7:] if len(x) > 12 and x[8]}
k = "1世帯当たり資産現在高・負債現在高"; kr = "資産保有率・負債保有率"
f4 = pd.DataFrame([{"age": a, "label": NAME.get(a, "平均"), "saving": T4[(k, "21_金融資産残高（貯蓄現在高）")][a] / 10, "deposit": T4[(k, "211_預貯金")][a] / 10,
                    "insurance": T4[(k, "212_生命保険など")][a] / 10, "securities": T4[(k, "213_有価証券")][a] / 10, "debt": T4[(k, "22_金融負債残高")][a] / 10,
                    "housing_debt": T4[(k, "221_住宅・土地のための負債")][a] / 10, "house_land": T4[(k, "3_住宅・宅地")][a] / 10,
                    "net_total": T4[(k, "4_純資産総額（純金融資産＋住宅・宅地）")][a] / 10, "debt_rate": T4[(kr, "6_負債保有率（％）")][a],
                    "housing_debt_rate": T4[(kr, "61_うち住宅･土地のための負債")][a], "sec_rate": T4[(kr, "54_有価証券")][a]} for a in ["000_平均"] + AG])
f4.to_csv(DATA / "assets_debt_2024.csv", index=False)
g = d.set_index(["year", "age"]); A0 = "000_平均"
assert abs(f4.set_index("age").saving[A0] - g.loc[(2024, A0), "mean"]) < 1 and abs(f4.set_index("age").debt[A0] - g.loc[(2024, A0), "debt"]) < 1
tab = d[d.year == 2024][["label", "households", "mean", "median", "mean_over_median", "q25", "q75", "debt", "net", "p_u100", "p_2000p", "income"]]
tab.round(1).to_csv(RES / "a399_2024_by_age.csv", index=False)
d.pivot(index="label", columns="year", values="median").reindex(["平均"] + [NAME[a] for a in AG]).round(0).to_csv(RES / "a399_median_by_year.csv")
x24 = d[d.year == 2024].set_index("age")
res = {
    "overall": {int(y): {c: round(float(g.loc[(y, A0), c]), 1) for c in ["mean", "median", "mean_over_median", "debt", "p_u100", "p_2000p", "p_3000p", "q25", "q75", "income"]} for y in S},
    "by_age_2024": {NAME[a]: {c: round(float(x24.loc[a, c]), 1) for c in ["mean", "median", "mean_over_median", "debt", "net", "p_u100", "p_2000p", "q25", "q75"]} for a in AG},
    "median_by_year": {NAME[a]: {int(y): round(float(g.loc[(y, a), "median"])) for y in S} for a in AG},
    "mean_by_year": {NAME[a]: {int(y): round(float(g.loc[(y, a), "mean"])) for y in S} for a in AG},
    "debt_exceeds_saving_2024": [NAME[a] for a in AG if x24.loc[a, "debt"] > x24.loc[a, "mean"]],
    "debt_exceeds_saving_2019": [NAME[a] for a in AG if g.loc[(2019, a), "debt"] > g.loc[(2019, a), "mean"]],
    "debt_exceeds_saving_2014": [NAME[a] for a in AG if g.loc[(2014, a), "debt"] > g.loc[(2014, a), "mean"]],
    "peak_median_age_2024": NAME[x24.loc[AG, "median"].idxmax()], "peak_mean_age_2024": NAME[x24.loc[AG, "mean"].idxmax()], "peak_debt_age_2024": NAME[x24.loc[AG, "debt"].idxmax()],
    "ratio_range_2024": [round(float(x24.loc[AG, "mean_over_median"].min()), 2), round(float(x24.loc[AG, "mean_over_median"].max()), 2)],
    "housing_debt_2024": {r_.label: [round(r_.debt), round(r_.housing_debt), round(r_.debt_rate, 1), round(r_.housing_debt_rate, 1)] for r_ in f4.itertuples()},
    "securities_2024": {r_.label: [round(r_.securities), round(r_.securities / r_.saving * 100, 1), round(r_.sec_rate, 1)] for r_ in f4.itertuples()},
    "house_land_2024": {r_.label: [round(r_.house_land), round(r_.net_total)] for r_ in f4.itertuples()},
    "sample_2024": int(S[2024][1][("集計世帯数（概数）", "00_平均")][A0]), "sample_2019": int(S[2019][1][("集計世帯数（概数）", "00_平均")][A0]),
    "sample_by_age_2024": {NAME[a]: int(S[2024][1][("集計世帯数（概数）", "00_平均")][a]) for a in AG},
    "class_gap_overall": {int(y): round(float(g.loc[(y, A0), "class_gap"]), 2) for y in S}, "class_gap_max": round(float(d.class_gap.max()), 2),
    "top_open_class_share_2024": round(float(g.loc[(2024, A0), "p_1okup"]), 2),
}
json.dump(res, open(RES / "a399_main.json", "w"), ensure_ascii=False, indent=1)

lab = [NAME[a] for a in AG]; xs = np.arange(len(AG))
fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.bar(xs - 0.2, x24.loc[AG, "mean"], 0.4, color=LIGHT, label="平均"); ax.bar(xs + 0.2, x24.loc[AG, "median"], 0.4, color=BLUE, label="中央値（階級から計算）")
for i, a in enumerate(AG):
    ax.text(i - 0.2, x24.loc[a, "mean"] + 25, f"{x24.loc[a,'mean']:,.0f}", ha="center", fontsize=7.5); ax.text(i + 0.2, x24.loc[a, "median"] + 25, f"{x24.loc[a,'median']:,.0f}", ha="center", fontsize=7.5, color=BLUE)
ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=8.5); ax.set_ylabel("貯蓄現在高（万円）"); ax.set_title("世帯主の年齢ごとの貯蓄：平均と中央値（2024年、総世帯）"); ax.legend(frameon=False)
save(fig, "a399_mean_median_2024.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.plot(xs, x24.loc[AG, "mean"], color=BLUE, marker="o", label="貯蓄（平均）"); ax.plot(xs, x24.loc[AG, "debt"], color=ORANGE, marker="o", label="負債（平均）")
ax.bar(xs, x24.loc[AG, "net"], 0.5, color=[ORANGE if v < 0 else LIGHT for v in x24.loc[AG, "net"]], alpha=0.6, label="貯蓄−負債")
for i, a in enumerate(AG):
    ax.text(i, x24.loc[a, "net"] / 2 if abs(x24.loc[a, "net"]) > 400 else (x24.loc[a, "net"] - 110 if x24.loc[a, "net"] < 0 else -110), f"{x24.loc[a,'net']:+,.0f}", ha="center", fontsize=7.5)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=8.5); ax.set_ylabel("万円"); ax.set_title("貯蓄と負債の平均、その差（2024年、総世帯）"); ax.legend(frameon=False)
save(fig, "a399_saving_debt_2024.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.6))
for y, c in zip(S, [GRAY, LIGHT, BLUE]):
    ax.plot(xs, [g.loc[(y, a), "median"] for a in AG], color=c, marker="o", label=f"{y}年" + ("（遡及集計）" if y == 2014 else ""))
ax.set_xticks(xs); ax.set_xticklabels(lab, fontsize=8.5); ax.set_ylabel("貯蓄現在高の中央値（万円）"); ax.set_title("貯蓄の中央値：2014年・2019年・2024年"); ax.legend(frameon=False)
save(fig, "a399_median_3surveys.png", SRC)
print(json.dumps(res, ensure_ascii=False))
