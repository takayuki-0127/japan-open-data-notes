"""A155 病床利用率は冬に高くなるのか（病院報告 月末病床利用率 2000〜2025年）

手法：一般病床（2004〜2025年）・療養病床・精神病床の月末病床利用率（月次）を STL 分解（周期12か月、ロバスト）して、
傾向・季節・残りに分ける。季節成分を月ごとに平均して「どの月が高いか」を見る。
さらに、月末が土日・祝日（年末年始を含む）にあたる月の値が低くなるかを、傾向・季節を除いた残りで比べる。
"""
import datetime as dt
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
from common import load, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

d = load("month_end_occupancy.csv")
M = [f"m{i}" for i in range(1, 13)]
L = d.melt(id_vars=["year", "type"], value_vars=M, var_name="m", value_name="rate")
L["month"] = L.m.str[1:].astype(int)
L["date"] = pd.to_datetime(dict(year=L.year, month=L.month, day=1))
L = L.sort_values(["type", "date"])

# 祝日の簡易判定（固定日のみ＋ハッピーマンデーは近似せず）：土日と年末年始・固定祝日
FIXED = {(1, 1), (2, 11), (4, 29), (5, 3), (5, 4), (5, 5), (11, 3), (11, 23), (12, 31)}


def month_end(y, m):
    nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
    return nxt - dt.timedelta(days=1)


def off_day(day):
    return day.weekday() >= 5 or (day.month, day.day) in FIXED


L["end"] = [month_end(y, m) for y, m in zip(L.year, L.month)]
L["end_wd"] = [e.weekday() for e in L.end]
L["end_off"] = [off_day(e) for e in L.end]

out, comps = [], {}
for ty, start in (("general", 2004), ("ltc", 2004), ("psych", 2000), ("total", 2000)):
    s = L[(L.type == ty) & (L.year >= start)].set_index("date").rate.astype(float)
    s.index.freq = "MS"
    r = STL(s, period=12, robust=True).fit()
    comps[ty] = r
    seas = r.seasonal.groupby(r.seasonal.index.month).mean()
    amp = seas.max() - seas.min()
    for m_ in range(1, 13):
        out.append({"type": ty, "month": m_, "seasonal": round(seas[m_], 2)})
    var_s = np.var(r.seasonal); var_r = np.var(r.resid)
    out.append({"type": ty, "month": 0, "seasonal": round(amp, 2), "note": f"amp; strength_season={max(0, 1 - var_r / np.var(r.seasonal + r.resid)):.2f}"})
S = pd.DataFrame(out)
S.to_csv(RES / "a155_seasonal_by_month.csv", index=False)

# 月末の曜日・休日の効果（一般病床、12月を除く、STLの残り）
g = comps["general"]
G = L[(L.type == "general") & (L.year >= 2004)].set_index("date").copy()
G["resid"] = g.resid
G["seasonal"] = g.seasonal
G["trend"] = g.trend
G.loc[:, ["year", "month", "rate", "trend", "seasonal", "resid", "end", "end_wd", "end_off"]].to_csv(RES / "a155_general_stl.csv")
# 季節成分に月末の曜日の偏りが入らないよう、傾向だけを除いた値（rate - trend）で月×休日を比べる
G["detr"] = G.rate - G.trend
nd = G[G.month != 12]
wd_tab = nd.groupby("end_wd").detr.agg(["mean", "count"]).round(2)
wd_tab.index = ["月", "火", "水", "木", "金", "土", "日"]
wd_tab.to_csv(RES / "a155_monthend_weekday.csv")
off_mean = nd.groupby("end_off").detr.mean()
# 月ごとに、月末が休日の年と平日の年の差（月の違いを取り除く）
pair = nd.groupby(["month", "end_off"]).detr.mean().unstack()
pair["diff"] = pair[True] - pair[False]
pair["n_off"] = nd.groupby("month").end_off.sum()
pair.round(2).to_csv(RES / "a155_offday_diff_by_month.csv")

# 冬（12〜2月）と夏（6〜8月）を、12月を除いて比べる（1・2月 vs 7・8月）、月末平日の月だけ
wk = nd[~nd.end_off]
win = wk[wk.month.isin([1, 2])].detr.mean(); sumr = wk[wk.month.isin([7, 8])].detr.mean()
spr = wk[wk.month.isin([4, 5, 6])].detr.mean()

# ---- 図1：一般病床の STL 分解 ----
fig, ax = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True)
ax[0].plot(g.observed.index, g.observed, color=BLUE, lw=1); ax[0].plot(g.trend.index, g.trend, color=INK, lw=1.6)
ax[0].set_ylabel("観測値と傾向（%）"); ax[0].set_title("一般病床の月末病床利用率をSTL分解（2004〜2025年）")
ax[1].plot(g.seasonal.index, g.seasonal, color=ORANGE, lw=1); ax[1].axhline(0, color=GRAY, lw=.6); ax[1].set_ylabel("季節（ポイント）")
ax[2].plot(g.resid.index, g.resid, color=GRAY, lw=.8); ax[2].axhline(0, color=GRAY, lw=.6); ax[2].set_ylabel("残り（ポイント）")
for a in ax: a.grid(axis="y", color="#eee")
save(fig, "a155_stl.png")

# ---- 図2：月ごとの季節成分 ----
fig, ax = plt.subplots(figsize=(8.6, 4.8))
lab = {"general": ("一般病床", BLUE), "ltc": ("療養病床", GREEN), "psych": ("精神病床", PURPLE)}
x = np.arange(1, 13)
for ty, (nm, c) in lab.items():
    v = S[(S.type == ty) & (S.month > 0)].seasonal.to_numpy()
    ax.plot(x, v, "o-", color=c, lw=2, ms=4, label=nm)
gv = S[(S.type == "general") & (S.month > 0)].set_index("month").seasonal
for m_ in (1, 2, 4, 12):
    ax.annotate(f"{gv[m_]:+.1f}", (m_, gv[m_]), xytext=((-26, -4) if m_ == 12 else (0, 7 if gv[m_] > 0 else -14)), textcoords="offset points", ha="center", fontsize=9, color=BLUE)
ax.axhline(0, color=GRAY, lw=.8)
ax.set_xticks(x, [f"{i}月" for i in x]); ax.set_ylabel("季節成分（ポイント）")
ax.set_title("月ごとの季節成分の平均（月末の値。12月は年末の退院で大きく下がる）")
ax.legend(frameon=False, loc="lower left")
save(fig, "a155_seasonal.png")

# ---- 図3：月末が休日か平日か ----
fig, ax = plt.subplots(figsize=(8.4, 4.6))
pm_ = pair.drop(columns=["diff", "n_off"])
xx = np.arange(len(pm_))
ax.bar(xx - .2, pm_[False], .4, color=BLUE, label="月末が平日の年")
ax.bar(xx + .2, pm_[True], .4, color=ORANGE, label="月末が土日・祝日の年")
ax.set_xticks(xx, [f"{m}月" for m in pm_.index]); ax.axhline(0, color=INK, lw=.8)
ax.set_ylabel("傾向からのずれ（ポイント）")
ax.set_title("一般病床：月末が土日・祝日だと、その月の月末の値は低くなる")
ax.legend(frameon=False, loc="lower left")
save(fig, "a155_weekend.png")

lines = []
for ty in ("general", "ltc", "psych", "total"):
    t = S[(S.type == ty) & (S.month > 0)].set_index("month").seasonal
    a = S[(S.type == ty) & (S.month == 0)].iloc[0]
    lines.append(f"{ty}: amp {a.seasonal} {a.note} | " + " ".join(f"{m}:{v:+.2f}" for m, v in t.items()))
lines.append(f"general detr off-day mean {off_mean.get(True):.2f} vs weekday {off_mean.get(False):.2f} (Dec excluded); offday diff by month mean {pair['diff'].mean():.2f}")
lines.append("weekday table:\n" + wd_tab.to_string())
lines.append(f"weekday-ends only: Jan-Feb {win:.2f}, Apr-Jun {spr:.2f}, Jul-Aug {sumr:.2f}")
yr = d[d.type == "general"].set_index("year").annual
lines.append("general annual: " + ", ".join(f"{y}:{v}" for y, v in yr.items() if y in (2004, 2010, 2019, 2020, 2021, 2022, 2025)))
for ty in ("general", "total"):
    tt = d[d.type == ty]
    lines.append(f"{ty} Dec minus Nov mean: {(tt.m12 - tt.m11).mean():.2f}; Jan minus Dec mean {(tt.m1 - tt.m12).mean():.2f}")
(RES / "a155_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines)); print(pair.round(2))
