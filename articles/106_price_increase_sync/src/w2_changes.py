"""問い2：値上げは一斉か、ばらばらか

各都市・各品目の価格が前月と変わったか（上がった・下がった）を数え、
・毎月、価格が変わった「都市×品目」の割合（価格改定の頻度）と、変わったときの幅
・2021年以降の物価上昇期に、頻度と幅がどう変わったか
・ある品目で、同じ月に上げた都市の割合（一斉かどうか）
を見る。銘柄・単位が改正された月の変化は除く（data/brand_changes.csv）。
"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load_prices, DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, note, MONTHS

f = pd.concat([pd.read_csv(DATA / f"freq_all_{i}.csv", dtype={"code": str}) for i in (1, 2)])
names = pd.read_csv(DATA / "item_names.csv", dtype={"code": str}).set_index("code").item
c = f.code.astype(int)
# 生鮮（魚介・野菜・果物の生もの）は毎月の相場で動くので分ける
fresh = c.between(1101, 1133) | c.between(1401, 1443) | c.between(1501, 1584)
f["group"] = np.where(fresh, "生鮮", np.where(c >= 2101, "外食", "生鮮以外の食品"))
f["year"] = f.t.str[:4].astype(int)
f["period"] = pd.cut(f.year, [2009, 2014, 2019, 2021, 2025], labels=["2010〜14", "2015〜19", "2020〜21", "2022〜25"])

def agg(g):
    ch = g.up.sum() + g.dn.sum()
    return pd.Series({"n": g.n.sum(), "freq_change": ch / g.n.sum() * 100, "freq_up": g.up.sum() / g.n.sum() * 100,
                      "freq_down": g.dn.sum() / g.n.sum() * 100, "size_pct": (np.exp(g.sum_abs.sum() / ch) - 1) * 100 if ch else np.nan,
                      "items": g.code.nunique()})

yr = f.groupby(["group", "year"]).apply(agg).reset_index()
print(yr.pivot(index="year", columns="group", values="freq_up").round(1).to_string())
per = f.groupby(["group", "period"]).apply(agg).reset_index()
per.round(3).to_csv(RES / "w2_by_period.csv", index=False)
print(per.round(2).to_string(index=False))
mon = f.groupby(["group", "t"]).apply(agg).reset_index()
mon.round(3).to_csv(RES / "w2_by_month.csv", index=False)
nf = mon[mon.group == "生鮮以外の食品"].set_index("t")
print("生鮮以外：上げた割合の高い月\n", nf.freq_up.sort_values(ascending=False).head(12).round(1).to_string())
ex = mon[mon.group == "外食"].set_index("t")
print("外食：上げた割合の高い月\n", ex.freq_up.sort_values(ascending=False).head(8).round(1).to_string())

# 一斉かどうか：品目×月で「上げた都市の割合」を出し、全国の値上げ（都市×品目）のうち、
# 半数以上の都市が同じ月に上げた品目×月に入っているものの割合
f["share_up"] = f.up / f.n
f["sync"] = (f.share_up >= 0.5) & (f.n >= 20)
TAX = ["2014-04", "2019-10"]  # 消費税率の引き上げ月は別扱い
sy = f[(f.group != "生鮮") & (f.n >= 20) & ~f.t.isin(TAX)].groupby("period").apply(lambda g: pd.Series({
    "rises": g.up.sum(), "rises_in_sync_months": g.loc[g.sync, "up"].sum(),
    "sync_share": g.loc[g.sync, "up"].sum() / g.up.sum() * 100,
    "item_months_sync": g.sync.sum(), "item_months": len(g)})).reset_index()
sy.round(3).to_csv(RES / "w2_sync.csv", index=False)
print(sy.round(2).to_string(index=False))
syl = f[(f.group != "生鮮") & f.sync].assign(name=lambda x: x.code.map(names)).sort_values("t")[["t", "code", "name", "n", "up", "share_up"]]
syl.round(3).to_csv(RES / "w2_sync_item_months.csv", index=False)
print("半数以上の都市が同じ月に上げた品目×月（年別の件数、増税月を除く）\n", syl[~syl.t.isin(TAX)].t.str[:4].value_counts().sort_index().to_dict())

# 25品目：期間ごとの頻度と幅
p = load_prices()
ch = pd.read_csv(DATA / "brand_changes.csv", dtype={"code": str})
m = p.melt(id_vars=["key", "code", "city", "year"], value_vars=MONTHS, var_name="m", value_name="price")
m["ti"] = m.year * 12 + m.m.str[1:].astype(int) - 1
m = m.sort_values(["key", "city", "ti"])
m["p0"] = m.groupby(["key", "city"]).price.shift(); m["t0"] = m.groupby(["key", "city"]).ti.shift()
m = m[(m.ti - m.t0 == 1) & (m.price > 0) & (m.p0 > 0)]
m["t"] = [f"{t // 12}-{t % 12 + 1:02d}" for t in m.ti]
m = m.merge(ch[["code", "t"]].assign(x=1), on=["code", "t"], how="left"); m = m[m.x.isna()]
m["r"] = np.log(m.price / m.p0)
m["period"] = pd.cut(m.ti // 12, [2009, 2014, 2019, 2021, 2025], labels=["2010〜14", "2015〜19", "2020〜21", "2022〜25"])
it = m.groupby(["key", "period"]).apply(lambda g: pd.Series({
    "freq_change": (g.r != 0).mean() * 100, "freq_up": (g.r > 0).mean() * 100, "freq_down": (g.r < 0).mean() * 100,
    "size_up_pct": (np.exp(g.r[g.r > 0].mean()) - 1) * 100, "size_down_pct": (np.exp(-g.r[g.r < 0].mean()) - 1) * 100})).reset_index()
it.round(3).to_csv(RES / "w2_items_by_period.csv", index=False)
w = it.pivot(index="key", columns="period", values="freq_up")
w["ratio"] = w["2022〜25"] / w["2015〜19"]
print(w.round(2).sort_values("2022〜25").to_string())
print(it[it.period.isin(["2015〜19", "2022〜25"])].pivot(index="key", columns="period", values="size_up_pct").round(1).to_string())
# 品目ごとの「上げた都市の割合」月次
mo = m.groupby(["key", "t"]).apply(lambda g: pd.Series({"n": len(g), "share_up": (g.r > 0).mean() * 100,
                                                       "share_down": (g.r < 0).mean() * 100})).reset_index()
mo.round(2).to_csv(RES / "w2_items_monthly.csv", index=False)

# 図1：毎月、前月から値段を上げた・下げた割合（生鮮以外の食品／外食）
fig, axs = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True)
for ax, gname in zip(axs, ["生鮮以外の食品", "外食"]):
    g = mon[mon.group == gname].copy()
    x = pd.PeriodIndex(g.t, freq="M").to_timestamp()
    ax.bar(x, g.freq_up, width=25, color=ORANGE, label="上げた")
    ax.bar(x, -g.freq_down, width=25, color=BLUE, label="下げた")
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_title(f"{gname}（{g['items'].max():.0f}品目前後×約80市）", loc="left", fontsize=11)
    ax.set_ylabel("前月から変えた割合（%）")
    ax.grid(axis="y", color="#eee"); ax.set_axisbelow(True)
axs[0].legend(frameon=False, ncol=2, loc="upper center")
for ax in axs:
    for d0 in ["2014-04", "2019-10"]:
        ax.axvline(pd.Timestamp(d0), color=GRAY, lw=0.6, ls=":")
for lab, d0 in [("消費税8%", "2014-05"), ("消費税10%", "2019-11")]:
    axs[1].text(pd.Timestamp(d0), axs[1].get_ylim()[1] * 0.9, lab, fontsize=8, color=GRAY)
fig.suptitle("毎月、値段を変えた「都市×品目」の割合", x=0.07, ha="left", fontsize=13)
note(axs[1], y=-0.2)
fig.savefig(FIG / "w2_monthly.png"); plt.close(fig)

# 図2：25品目の「上げた月の割合」2015〜19年と2022〜25年
w2 = w.dropna(subset=["2015〜19", "2022〜25"]).sort_values("2022〜25")
fig, ax = plt.subplots(figsize=(8, 8.2))
y = np.arange(len(w2))
ax.hlines(y, w2["2015〜19"], w2["2022〜25"], color=GRAY, lw=1.2)
ax.scatter(w2["2015〜19"], y, color=LIGHT, s=36, zorder=3, label="2015〜19年")
ax.scatter(w2["2022〜25"], y, color=ORANGE, s=36, zorder=3, label="2022〜25年")
ax.set_yticks(y); ax.set_yticklabels(w2.index)
ax.set_xscale("log"); ax.set_xlim(2, 70); ax.set_xticks([2, 5, 10, 20, 40]); ax.set_xticklabels(["2", "5", "10", "20", "40"])
ax.set_xlabel("前月より上がった割合（%、都市×月あたり、対数目盛）")
ax.set_title("値上げの頻度（25品目）", loc="left")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="x", color="#eee"); ax.set_axisbelow(True)
note(ax, y=-0.08)
fig.savefig(FIG / "w2_items.png"); plt.close(fig)

# 図3：同じ月に上げた都市の割合（4品目）
ex = ["食用油", "牛乳", "食パン", "中華そば（外食）"]
fig, axs = plt.subplots(len(ex), 1, figsize=(9, 7), sharex=True, sharey=True)
for ax, k in zip(axs, ex):
    g = mo[mo.key == k]
    x = pd.PeriodIndex(g.t, freq="M").to_timestamp()
    ax.bar(x, g.share_up, width=25, color=ORANGE)
    ax.axhline(50, color=GRAY, lw=0.6, ls=":")
    ax.text(0.005, 0.92, k, transform=ax.transAxes, fontsize=10, va="top")
    ax.set_ylim(0, 100); ax.grid(axis="y", color="#eee"); ax.set_axisbelow(True)
axs[len(ex) // 2].set_ylabel("その月に上げた都市の割合（%）")
fig.suptitle("値上げは一斉か：同じ月に値段を上げた都市の割合", x=0.07, ha="left", fontsize=13)
note(axs[-1], y=-0.35)
fig.savefig(FIG / "w2_sync.png"); plt.close(fig)
