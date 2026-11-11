"""A248 観光目的の客が多い施設は、季節の山が大きいのか
施設は「観光目的の宿泊者が50%以上」（観光の宿）と「50%未満」（出張などの宿）の2つ（調査の区分）。
季節の山の大きさ＝1日あたり延べ宿泊者数を年平均で割った月の指数の、ばらつき（標準偏差）と最大÷最小。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import table, RES, FIG, GRAY, days, note
from common import C as COL

t2, t6 = table(2), table(6)
m = t2[t2.month > 0].copy()
m["days"] = [days(y, mo) for y, mo in zip(m.year, m.month)]
m["jp_tour"] = m.tour - m.foreign_tour; m["jp_biz"] = m.biz - m.foreign_biz
V = {"tour": "観光の宿（全体）", "biz": "出張などの宿（全体）", "jp_tour": "観光の宿・日本人", "jp_biz": "出張などの宿・日本人",
     "foreign_tour": "観光の宿・外国人", "foreign_biz": "出張などの宿・外国人"}
for v in V:
    pdv = m[v] / m.days
    m[v + "_i"] = pdv / pdv.groupby(m.year).transform("mean")

rows = []
for y, g in m.groupby("year"):
    r = {"year": y}
    for v in V:
        i = g[v + "_i"]
        r[v + "_sd"] = round(i.std(ddof=0), 3); r[v + "_maxmin"] = round(i.max() / i.min(), 2)
        r[v + "_peak"] = int(g.month.iloc[i.values.argmax()])
    r["foreign_share_tour"] = round(g.foreign_tour.sum() / g.tour.sum() * 100, 1)
    r["foreign_share_biz"] = round(g.foreign_biz.sum() / g.biz.sum() * 100, 1)
    rows.append(r)
yr = pd.DataFrame(rows).set_index("year"); yr.to_csv(RES / "a248_season_by_year.csv")

PER = {"2015〜2019年": (2015, 2019), "2023〜2025年": (2023, 2025)}
prof = {}
for p, (a, b) in PER.items():
    d = m[(m.year >= a) & (m.year <= b)]
    prof[p] = d.groupby("month")[[v + "_i" for v in V]].mean().round(3)
    prof[p].to_csv(RES / f"a248_profile_{a}_{b}.csv")

# 観光の宿の季節の山（標準偏差）が小さくなった分のうち、外国人の割合が増えた分（日本人・外国人の月の形を2019年のまま、割合だけ2025年にする）
def mix_sd(y_shape, y_share):
    g = m[m.year == y_shape].set_index("month"); s = yr.loc[y_share, "foreign_share_tour"] / 100
    jp = g.jp_tour / g.days; fr = g.foreign_tour / g.days
    jp_i, fr_i = jp / jp.mean(), fr / fr.mean()
    return float(((1 - s) * jp_i + s * fr_i).std(ddof=0))
cf = {"sd_2019_actual": float(yr.loc[2019, "tour_sd"]), "sd_2025_actual": float(yr.loc[2025, "tour_sd"]),
      "sd_shape2019_share2019": round(mix_sd(2019, 2019), 3), "sd_shape2019_share2025": round(mix_sd(2019, 2025), 3),
      "sd_shape2025_share2019": round(mix_sd(2025, 2019), 3), "sd_shape2025_share2025": round(mix_sd(2025, 2025), 3)}

# 頑健性：定員稼働率の月の幅（最大−最小、ポイント）
occ = t6[t6.month > 0].groupby("year").agg(tour_range=("tour", lambda s: s.max() - s.min()), biz_range=("biz", lambda s: s.max() - s.min())).round(1)
occ.to_csv(RES / "a248_capacity_occupancy_range.csv")
# 頑健性：8月を除いたばらつき
ex8 = {p: {v: round(float(prof[p].drop(8)[v + "_i"].std(ddof=0)), 3) for v in ["jp_tour", "jp_biz"]} for p in PER}

pre, post = yr.loc[2015:2019].mean(), yr.loc[2023:2025].mean()
summary = {"mean_sd_2015_2019": {v: round(pre[v + "_sd"], 3) for v in V}, "mean_sd_2023_2025": {v: round(post[v + "_sd"], 3) for v in V},
           "mean_maxmin_2015_2019": {v: round(pre[v + "_maxmin"], 2) for v in V}, "mean_maxmin_2023_2025": {v: round(post[v + "_maxmin"], 2) for v in V},
           "aug_index": {p: {v: float(prof[p].loc[8, v + "_i"]) for v in ["jp_tour", "jp_biz", "foreign_tour"]} for p in PER},
           "jan_index": {p: {v: float(prof[p].loc[1, v + "_i"]) for v in ["jp_tour", "jp_biz"]} for p in PER},
           "foreign_share_tour": yr["foreign_share_tour"].to_dict(), "foreign_share_biz": yr["foreign_share_biz"].to_dict(),
           "counterfactual": cf, "sd_excl_august": ex8, "capacity_occ_range": occ.loc[[2015, 2019, 2023, 2024, 2025]].to_dict(orient="index"),
           "sd_by_year": yr[[v + "_sd" for v in V]].to_dict(orient="index")}
json.dump(summary, open(RES / "a248_summary.json", "w"), ensure_ascii=False, indent=1)

# 図1：月の形（2015〜2019年の平均、日本人）
fig, ax = plt.subplots(figsize=(8, 4.4))
p = prof["2015〜2019年"]; mo = p.index
ax.plot(mo, p.jp_tour_i * 100, marker="o", color=COL[1], lw=2, label="観光の宿・日本人")
ax.plot(mo, p.jp_biz_i * 100, marker="o", color=COL[0], lw=2, label="出張などの宿・日本人")
ax.axhline(100, color="#888", lw=0.8); ax.set_xticks(mo); ax.set_xticklabels([f"{i}月" for i in mo])
ax.set_ylabel("1日あたり延べ宿泊者数（年平均＝100）"); ax.set_title("日本人の泊まり方の季節：観光の宿は8月に1.5倍（2015〜2019年の平均）")
ax.legend(frameon=False, fontsize=9); note(ax); fig.savefig(FIG / "a248_profile.png"); plt.close(fig)

# 図2：季節の山の大きさ（標準偏差）の推移
fig, ax = plt.subplots(figsize=(8, 4.4))
yrs = [y for y in yr.index if y not in (2020, 2021, 2022)]
for v, col, ls, mk in [("tour", COL[1], "-", "o"), ("jp_tour", COL[1], "--", "s"), ("biz", COL[0], "-", "o"), ("jp_biz", COL[0], "--", "s")]:
    s = yr.loc[yrs, v + "_sd"] * 100
    ax.plot(range(len(yrs)), s, marker=mk, color=col, ls=ls, lw=2, label=V[v])
ax.set_xticks(range(len(yrs))); ax.set_xticklabels([str(y) for y in yrs])
ax.axvspan(4.4, 4.6, color="#eee"); ax.text(4.5, 2, "2020〜22年は\n除いた", ha="center", fontsize=8, color="#666")
ax.set_ylim(0, 24); ax.set_ylabel("月の指数のばらつき（標準偏差、年平均＝100）")
ax.set_title("季節の山の大きさ：観光の宿は小さくなった"); ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper right")
note(ax); fig.savefig(FIG / "a248_sd_trend.png"); plt.close(fig)

# 図3：2023〜2025年の観光の宿、日本人と外国人の月の形
fig, ax = plt.subplots(figsize=(8, 4.4))
p = prof["2023〜2025年"]
ax.plot(mo, p.jp_tour_i * 100, marker="o", color=COL[1], lw=2, label="観光の宿・日本人")
ax.plot(mo, p.foreign_tour_i * 100, marker="o", color=COL[2], lw=2, label="観光の宿・外国人")
ax.plot(mo, p.tour_i * 100, color=GRAY, lw=2, ls="--", label="観光の宿・全体")
ax.axhline(100, color="#888", lw=0.8); ax.set_xticks(mo); ax.set_xticklabels([f"{i}月" for i in mo])
ax.set_ylabel("1日あたり延べ宿泊者数（年平均＝100）"); ax.set_title("外国人は山の月が違う（2023〜2025年の平均）")
ax.legend(frameon=False, fontsize=9); note(ax); fig.savefig(FIG / "a248_jp_vs_foreign.png"); plt.close(fig)
print(json.dumps({k: summary[k] for k in ["mean_sd_2015_2019", "mean_sd_2023_2025", "mean_maxmin_2015_2019", "mean_maxmin_2023_2025", "aug_index", "jan_index", "counterfactual", "sd_excl_august", "capacity_occ_range"]}, ensure_ascii=False, indent=0))
print(yr[["foreign_share_tour", "foreign_share_biz"]].T)
