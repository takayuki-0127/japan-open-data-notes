"""04 図：5枚"""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import DATA, RES, FIG

for f in fm.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
CR, CU = "#3b7dbf", "#d0573a"
d = pd.read_csv(DATA / "annual_clean.csv")
t = pd.read_csv(RES / "gev_linear_1901_2025.csv")
shp = pd.read_csv(RES / "trend_shape.csv")
cnt = pd.read_csv(RES / "count_models.csv")
pr = pd.read_csv(RES / "exceed_prob_1925_2025.csv")
per = pd.read_csv(RES / "period_sensitivity.csv")
S = json.load(open(RES / "summary.json"))

# 図1：4地点の年最高気温と、位置母数の直線・1980年で折れる線（GEV の当てはめ）
# 03_分析.py の関数（fit・design）をそのまま使う
exec(open(__file__.replace("04_図.py", "03_分析.py"), encoding="utf-8").read().split("out = {}")[0])
fig, axs = plt.subplots(2, 2, figsize=(10, 6.4), sharex=True)
for ax, s in zip(axs.flat, ["熊谷", "東京", "飯田", "境"]):
    g = d[(d.station == s) & (d.year >= 1901)].dropna(subset=["tmax_abs"])
    x, yr = g.tmax_abs.values.astype(float), g.year.values.astype(float)
    ax.plot(yr, x, "o", ms=2.5, color="#999")
    yy = np.arange(1901, 2026).astype(float)
    for shape, col, lab in (("lin", "#333", "直線"), ("hinge", CU, "1980年で折れる線")):
        f = fit(x, yr, shape); mu = design(yy, shape) @ f["p"][:f["X"].shape[1]]
        ax.plot(yy, mu, color=col, lw=1.8, label=f"位置母数（{lab}）")
    ax.axhline(35, color="#bbb", lw=0.8, ls="--"); ax.set_title(f"{s}（{'都市化の影響が少ない15地点' if G[s]=='R' else '大都市など'}）", fontsize=10)
    ax.set_ylabel("年最高気温（℃）")
axs[0, 0].legend(fontsize=8, frameon=False, loc="upper left")
fig.suptitle("年最高気温と、GEV の位置母数のトレンド（1901〜2025年）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f168_timeseries.png"); plt.close()

# 図2：地点ごとの100年あたりの上昇（位置母数）
tt = t.sort_values("mu1")
fig, ax = plt.subplots(figsize=(8, 8))
yv = np.arange(len(tt)); col = [CR if g == "R" else CU for g in tt.group]
ax.hlines(yv, tt.lo, tt.hi, color=col, lw=2); ax.plot(tt.mu1, yv, "o", color="k", ms=4)
ax.set_yticks(yv); ax.set_yticklabels(tt.station, fontsize=9); ax.axvline(0, color="#888", lw=0.8)
for g, c, lab in (("R", CR, "都市化の影響が少ない15地点"), ("U", CU, "大都市など15地点")):
    m = t[t.group == g].mu1.mean(); ax.axvline(m, color=c, ls="--", lw=1); ax.plot([], [], color=c, lw=2, label=f"{lab}（平均 {m:.2f}℃）")
ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_xlabel("年最高気温の位置母数の上昇（℃／100年、95%区間）")
ax.set_title("30地点すべてで、年最高気温は上がっている（1901〜2025年）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f168_slopes.png"); plt.close()

# 図3：年最高気温が38℃以上になる年は「何年に1度」か（1925年と2025年の当てはめ）
p = pr[(pr.thr == 38) & (pr.rp2025 < 200)].copy()
p["rp1925c"] = p.rp1925.clip(upper=1000)
p = p.sort_values("rp2025")
fig, ax = plt.subplots(figsize=(8, 6.5))
yv = np.arange(len(p))
ax.hlines(yv, p.rp2025, p.rp1925c, color="#ccc", lw=2)
ax.hlines(yv, p.rp2025_lo, p.rp2025_hi, color=CU, lw=4, alpha=0.4)
ax.plot(p.rp1925c, yv, "o", color="#777", label="1925年の当てはめ（1000年以上は1000に置く）")
ax.plot(p.rp2025, yv, "o", color=CU, label="2025年の当てはめ（帯は95%区間）")
ax.set_xscale("log"); ax.set_yticks(yv); ax.set_yticklabels(p.station)
ax.set_xlabel("年最高気温が38℃以上になるのは「何年に1度」か（対数目盛）")
ax.legend(frameon=False, fontsize=8, loc="lower right")
e = S["数えるだけ"]["38度"]
ax.set_title(f"38℃以上の年：数えるだけでも 1901〜50年 {e['前50年']} → 1976〜2025年 {e['後50年']}（地点×年）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f168_return_38.png"); plt.close()

# 図4：猛暑日の数：最初の30年と最近の30年の平均、負の二項回帰の10年あたり倍率
c = cnt[cnt.total_d35 >= 20].sort_values("late")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 6.5), sharey=True, gridspec_kw=dict(width_ratios=[1.3, 1]))
yv = np.arange(len(c))
a1.hlines(yv, c.early, c.late, color="#ccc", lw=2)
a1.plot(c.early, yv, "o", color="#777", label="1901〜1930年の平均")
a1.plot(c.late, yv, "o", color=CU, label="1996〜2025年の平均")
a1.set_yticks(yv); a1.set_yticklabels(c.station); a1.set_xlabel("猛暑日の数（日／年）"); a1.legend(frameon=False, fontsize=8)
ok = c.d35_nb_lo.notna()
a2.hlines(yv[ok], c.d35_nb_lo[ok], c.d35_nb_hi[ok], color=[CR if g == "R" else CU for g in c.group[ok]], lw=2)
a2.plot(c.d35_nb_rr, yv, "o", color="k", ms=4); a2.axvline(1, color="#888", lw=0.8)
a2.set_xlabel("10年あたりの倍率（負の二項回帰、95%区間）")
fig.suptitle(f"猛暑日（日最高気温35℃以上）：23地点すべてで最近30年の方が多く、10年あたりの倍率がはっきり1を超えたのは{S['猛暑日']['NBで増加はっきり']}地点（横浜は区間を計算できず）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f168_hotdays.png"); plt.close()

# 図5：頑健性：期間の取り方とトレンドの形
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.4))
for g, col, lab in (("R", CR, "都市化の影響が少ない15地点"), ("U", CU, "大都市など15地点")):
    m = per[per.group == g].groupby("start").mu1.agg(["mean", "sem"])
    a1.errorbar(m.index + (-1.5 if g == "R" else 1.5), m["mean"], yerr=1.96 * m["sem"], fmt="o-", color=col, capsize=3, label=lab)
a1.set_xticks([1901, 1931, 1961, 1991]); a1.set_xticklabels(["1901〜", "1931〜", "1961〜", "1991〜"])
a1.set_ylabel("位置母数の上昇（℃／100年）"); a1.set_xlabel("分析の始まりの年（終わりは2025年）"); a1.legend(frameon=False, fontsize=8)
a1.set_title("始まりを遅らせるほど、傾きは急になる", fontsize=10)
a2.scatter(shp.hinge_pre, shp.hinge_post, c=[CR if g == "R" else CU for g in shp.group], s=25)
lim = [-2, 9]; a2.plot(lim, lim, color="#999", lw=0.8, ls="--")
a2.set_xlabel("1980年までの傾き（℃／100年）"); a2.set_ylabel("1980年からの傾き（℃／100年）")
a2.set_title(f"1980年で折れる線が AIC で最良：30地点中{S['形']['AIC最良'].get('hinge', 0)}地点", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f168_robust.png"); plt.close()
print("ok")
