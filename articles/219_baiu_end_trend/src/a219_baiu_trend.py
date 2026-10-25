"""219 梅雨明けは早まっているのか？ 地方別の長期トレンド（Mann-Kendall検定・Theil-Sen推定）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import load, save, RES, REGIONS, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

d = load()
d["length"] = d.end_doy - d.onset_doy


def trend(s):
    s = s.dropna(); x, y = s.index.values.astype(float), s.values
    tau, p = stats.kendalltau(x, y)  # Mann-Kendall 検定（年との順位相関）
    sl, ic, lo, hi = stats.theilslopes(y, x, 0.95)
    return dict(n=len(s), tau=round(tau, 3), p=round(p, 4), slope10=round(sl * 10, 2) + 0.0, lo10=round(lo * 10, 2) + 0.0, hi10=round(hi * 10, 2) + 0.0,
                intercept=ic, sl=sl)


rows = []
for r in REGIONS:
    g = d[d.region == r].set_index("year")
    for v, lab in [("end_doy", "梅雨明け"), ("onset_doy", "梅雨入り"), ("length", "梅雨の長さ")]:
        t = trend(g[v]); t.update(region=r, var=lab, missing=int(g[v].isna().sum()))
        rows.append(t)
T = pd.DataFrame(rows)
T.drop(columns=["intercept", "sl"]).to_csv(RES / "trend_by_region.csv", index=False, encoding="utf-8-sig")

# 前半・後半の平均と、年ごとのばらつき（標準偏差）
cmp = []
for r in REGIONS:
    g = d[d.region == r]
    a, b = g[g.year <= 1988], g[g.year >= 1989]
    cmp.append(dict(region=r, end_mean_1951_88=round(a.end_doy.mean(), 1), end_mean_1989_2026=round(b.end_doy.mean(), 1),
                    end_sd_1951_88=round(a.end_doy.std(), 1), end_sd_1989_2026=round(b.end_doy.std(), 1),
                    onset_mean_1951_88=round(a.onset_doy.mean(), 1), onset_mean_1989_2026=round(b.onset_doy.mean(), 1),
                    end_missing_1951_88=int(a.end_doy.isna().sum()), end_missing_1989_2026=int(b.end_doy.isna().sum())))
C = pd.DataFrame(cmp); C.to_csv(RES / "halves_by_region.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 200)
print(T.drop(columns=["intercept", "sl"]).to_string()); print(C.to_string())

MD = lambda doy: f"{(pd.Timestamp('2001-01-01') + pd.Timedelta(days=doy - 1)).month}/{(pd.Timestamp('2001-01-01') + pd.Timedelta(days=doy - 1)).day}"
TICKS = [152, 166, 182, 196, 213, 227]  # 6/1, 6/15, 7/1, 7/15, 8/1, 8/15

# 図1 4地方の梅雨明けの散布とTheil-Sen直線
fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
for ax, r in zip(axes.flat, ["九州北部", "近畿", "関東甲信", "東北北部"]):
    g = d[d.region == r].set_index("year"); t = T[(T.region == r) & (T["var"] == "梅雨明け")].iloc[0]
    ax.scatter(g.index, g.end_doy, s=12, color=BLUE)
    xx = np.array([1951, 2026]); ax.plot(xx, t.intercept + t.sl * xx, color=INK, lw=1.5)
    miss = g.index[g.end_doy.isna()]
    for y in miss: ax.axvline(y, color=GRAY, lw=0.6, ls=":")
    ax.set_yticks(TICKS, [MD(v) for v in TICKS]); ax.set_ylim(160, 232)
    ax.set_title(f"{r}：10年あたり{t.slope10:+.1f}日（p={t.p:.2f}）", loc="left", fontsize=11)
fig.suptitle("梅雨明けの日付（1951〜2026年）。黒線はTheil-Sen推定の直線、点線は「特定しない」年", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); save(fig, "a219_scatter.png")

# 図2 地方別の梅雨明けの傾き（10年あたり日数）と95%信頼区間
fig, ax = plt.subplots(figsize=(8, 5.2))
E = T[T["var"] == "梅雨明け"].reset_index(drop=True); yy = np.arange(len(E))[::-1]
col = [ORANGE if p < 0.05 else GRAY for p in E.p]
ax.errorbar(E.slope10, yy, xerr=[E.slope10 - E.lo10, E.hi10 - E.slope10], fmt="none", ecolor=LIGHT, lw=3)
ax.scatter(E.slope10, yy, color=col, zorder=3, s=40)
for yi, v, p in zip(yy, E.slope10, E.p): ax.text(E.hi10.max() + 0.3, yi, f"{v:+.1f}日（p={p:.2f}）", va="center", fontsize=9)
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(yy, E.region)
ax.set_xlabel("10年あたりの変化（日）　マイナス＝早まる、プラス＝遅くなる"); ax.set_xlim(E.lo10.min() - 0.3, E.hi10.max() + 1.6)
ax.set_title("梅雨明けの日付の傾き（1951〜2026年、横線は95%信頼区間）\nオレンジはMann-Kendall検定で5%有意", loc="left", fontsize=11)
save(fig, "a219_slopes.png")

# 図3 梅雨入り・梅雨明け・長さの傾きを並べる
fig, ax = plt.subplots(figsize=(9, 5.2))
w = 0.27
for i, (lab, c) in enumerate([("梅雨入り", GREEN), ("梅雨明け", BLUE), ("梅雨の長さ", ORANGE)]):
    s = T[T["var"] == lab].set_index("region").loc[REGIONS]
    x = np.arange(len(REGIONS)) + (i - 1) * w
    ax.bar(x, s.slope10, w, color=c, label=lab)
    for xi, v, p in zip(x, s.slope10, s.p):
        if p < 0.05: ax.text(xi, v + (0.03 if v >= 0 else -0.03), "*", ha="center", va="bottom" if v >= 0 else "top", fontsize=14)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(np.arange(len(REGIONS)), REGIONS, rotation=45, ha="right")
ax.set_ylabel("10年あたりの変化（日）"); ax.set_ylim(-1.25, 1.2); ax.legend(frameon=False, ncol=3, loc="upper left")
ax.set_title("梅雨入り・梅雨明け・梅雨の長さの傾き（Theil-Sen、＊はMann-Kendall検定で5%有意）", loc="left", fontsize=11)
save(fig, "a219_components.png")
