"""問い1：同じ品目の値段は、都市によってどれだけ違うか。差は縮まっているか

25品目の年平均価格を、2010〜2025年の16年すべてにある都市（76市）にそろえて、
都市間の変動係数（標準偏差÷平均）と、最も高い都市÷最も安い都市の比を年ごとに計算する。
"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load_prices, DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, note

d = load_prices()
d = d[d.avg.notna() & (d.avg > 0)]
ny = d.year.nunique()
cities = d.groupby("city").year.nunique()
cities = sorted(cities[cities == ny].index)
d = d[d.city.isin(cities)]
print("都市数（16年すべてにある市）", len(cities))

rows = []
for (k, y), g in d.groupby(["key", "year"]):
    p = g.set_index("city").avg
    rows.append([k, y, len(p), p.mean(), p.std(ddof=0) / p.mean(), p.max() / p.min(),
                 p.idxmax(), p.max(), p.idxmin(), p.min(), p.quantile(0.9) / p.quantile(0.1)])
cv = pd.DataFrame(rows, columns=["key", "year", "n", "mean", "cv", "max_min", "max_city", "max", "min_city", "min", "p90_p10"])
cv.round(4).to_csv(RES / "w1_cv_by_year.csv", index=False)

# 期首（2010〜12年）と期末（2023〜25年）の平均で比べる。傾きは年あたり（変動係数のポイント）
def slope(g):
    return np.polyfit(g.year, g.cv * 100, 1)[0]
s = cv.groupby("key").apply(lambda g: pd.Series({
    "cv_2010_12": g[g.year <= 2012].cv.mean() * 100, "cv_2023_25": g[g.year >= 2023].cv.mean() * 100,
    "slope_per_10y": slope(g) * 10})).reset_index()
s["change"] = s.cv_2023_25 - s.cv_2010_12
last = cv[cv.year == 2025].set_index("key")[["mean", "max_city", "max", "min_city", "min", "max_min", "p90_p10"]]
s = s.join(last, on="key").sort_values("cv_2023_25", ascending=False)
# 銘柄・単位の改正（2011年以降）。改正の前後で変動係数が飛ぶことがある（例：しょうゆは2024年に1L入り→特定の450mL商品）
bc = pd.read_csv(DATA / "brand_changes.csv", dtype={"code": str})
code = d.groupby("key").code.first().astype(str)
s["brand_changes"] = s.key.map(lambda k: " ".join(bc[(bc.code == code[k]) & (bc.t >= "2011")].t))
s.round(3).to_csv(RES / "w1_summary.csv", index=False)
print(s.round(2).to_string(index=False))
print("縮小した品目", (s.change < 0).sum(), "/", len(s), " 変動係数の中央値", s.cv_2010_12.median().round(2), "→", s.cv_2023_25.median().round(2))

# 都市の「高い・安い」は品目をまたいで続くか：各品目で都市の価格を全市平均で割った比（対数）を平均した都市の物価指数
d["rel"] = np.log(d.avg / d.groupby(["key", "year"]).avg.transform("mean"))
idx = d[d.year >= 2023].groupby("city").rel.mean().sort_values()
idx10 = d[d.year <= 2012].groupby("city").rel.mean()
ci = pd.DataFrame({"index_2023_25": (np.exp(idx) * 100), "index_2010_12": np.exp(idx10.reindex(idx.index)) * 100})
ci.round(2).to_csv(RES / "w1_city_index.csv")
print("安い都市", ci.head(5).round(1).to_dict("index"))
print("高い都市", ci.tail(5).round(1).to_dict("index"))
print("都市指数の相関（2010〜12 vs 2023〜25）", np.corrcoef(np.log(ci.index_2010_12), np.log(ci.index_2023_25))[0, 1].round(3))
# 品目どうし：ある品目で高い都市は別の品目でも高いか（2023〜25年平均の相対価格の品目間相関の中央値）
w = d[d.year >= 2023].groupby(["city", "key"]).rel.mean().unstack()
cm = w.corr().values[np.triu_indices(w.shape[1], 1)]
print("品目間の相関の中央値", np.median(cm).round(3), " 正の割合", (cm > 0).mean().round(3))
# 同じ品目で、2010〜12年に高かった都市は2023〜25年も高いか
per = []
for k, g in d.groupby("key"):
    a = g[g.year <= 2012].groupby("city").rel.mean(); b = g[g.year >= 2023].groupby("city").rel.mean()
    per.append([k, a.corr(b, method="spearman")])
per = pd.DataFrame(per, columns=["key", "rank_corr_2010_12_vs_2023_25"]).sort_values("rank_corr_2010_12_vs_2023_25")
s = s.merge(per, on="key")
s.round(3).to_csv(RES / "w1_summary.csv", index=False)
print(per.round(2).to_string(index=False))

# 図1：品目ごとの変動係数（2010〜12年 → 2023〜25年）
fig, ax = plt.subplots(figsize=(8, 8.2))
s2 = s.sort_values("cv_2023_25")
y = np.arange(len(s2))
ax.hlines(y, s2.cv_2010_12, s2.cv_2023_25, color=GRAY, lw=1.2)
ax.scatter(s2.cv_2010_12, y, color=LIGHT, s=36, label="2010〜12年平均", zorder=3)
ax.scatter(s2.cv_2023_25, y, color=BLUE, s=36, label="2023〜25年平均", zorder=3)
ax.set_yticks(y); ax.set_yticklabels(s2.key)
ax.set_xlabel("都市間の変動係数（%）＝都市の価格の標準偏差÷平均")
ax.set_title(f"同じ品目でも都市で値段が違う（{len(cities)}市、年平均価格）", loc="left")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="x", color="#eee"); ax.set_axisbelow(True)
note(ax, y=-0.08)
fig.savefig(FIG / "w1_cv.png"); plt.close(fig)

# 図2：5品目の2025年の都市ごとの価格（全市平均＝100）と最高・最安の都市
ex = ["鶏卵", "牛乳", "米（コシヒカリ）", "食パン", "中華そば（外食）", "すし（外食）"]
fig, ax = plt.subplots(figsize=(8.4, 5))
rng = np.random.default_rng(0)
for i, k in enumerate(ex):
    g = d[(d.key == k) & (d.year == 2025)]
    v = g.avg / g.avg.mean() * 100
    ax.scatter(v, i + rng.uniform(-0.18, 0.18, len(v)), s=12, color=BLUE, alpha=0.55, lw=0)
    hi, lo = g.loc[g.avg.idxmax()], g.loc[g.avg.idxmin()]
    ax.annotate(f"{hi.city} {hi.avg:,.0f}円", (hi.avg / g.avg.mean() * 100, i), xytext=(6, 8), textcoords="offset points", fontsize=8.5, color=ORANGE)
    ax.annotate(f"{lo.city} {lo.avg:,.0f}円", (lo.avg / g.avg.mean() * 100, i), xytext=(-6, 8), textcoords="offset points", fontsize=8.5, color=INK, ha="right")
ax.axvline(100, color=GRAY, lw=0.8)
ax.set_yticks(range(len(ex))); ax.set_yticklabels(ex); ax.invert_yaxis()
ax.set_xlabel("2025年の年平均価格（全市平均＝100）　1点が1市")
ax.set_title("いちばん高い市と安い市（2025年）", loc="left")
ax.set_xlim(45, 160)
note(ax, y=-0.14)
fig.savefig(FIG / "w1_range.png"); plt.close(fig)

# 図3：変動係数の推移（例の品目）
fig, ax = plt.subplots(figsize=(8, 4.6))
cols = {"鶏卵": ORANGE, "牛乳": BLUE, "米（コシヒカリ）": "#3aa07a", "食パン": "#7a5bd6", "中華そば（外食）": INK, "すし（外食）": GRAY}
for k, c in cols.items():
    g = cv[cv.key == k]
    ax.plot(g.year, g.cv * 100, color=c, lw=2, marker="o", ms=3)
    ax.text(2025.2, g.cv.iloc[-1] * 100, k, color=c, fontsize=9, va="center")
ax.set_xlim(2009.5, 2028.6); ax.set_xticks(range(2010, 2026, 3))
ax.set_ylabel("都市間の変動係数（%）")
ax.set_title("都市間の差の推移", loc="left")
ax.grid(axis="y", color="#eee"); ax.set_axisbelow(True)
note(ax, y=-0.12)
fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

# 銘柄・単位の改正がなかった品目だけで、差が縮んだか
nc = s[s.brand_changes == ""]
print("改正のない品目", len(nc), "縮小", (nc.change < -0.5).sum(), "拡大", (nc.change > 0.5).sum(), "ほぼ同じ（±0.5ポイント）", (nc.change.abs() <= 0.5).sum(),
      " 中央値", nc.cv_2010_12.median().round(2), "→", nc.cv_2023_25.median().round(2))
