"""218 今のペースで、食品ロスの2030年度目標に届くか？（トレンドの外挿）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

d, g = load()
KIND = {"business": "事業系", "household": "家庭系"}
WINDOWS = {"2012〜24年度": (2012, 2024), "2015〜24年度": (2015, 2024), "2019〜24年度": (2019, 2024)}
T95 = {11: 2.201, 8: 2.306, 4: 2.776}  # t分布 97.5%点（自由度 = n-2）


def fit(y, x0, x1, xp=2030):
    s = y.loc[x0:x1]; x = s.index.values.astype(float); n = len(x)
    b, a = np.polyfit(x, s.values, 1)
    res = s.values - (a + b * x); se = np.sqrt((res ** 2).sum() / (n - 2))
    pi = T95[n - 2] * se * np.sqrt(1 + 1 / n + (xp - x.mean()) ** 2 / ((x - x.mean()) ** 2).sum())
    return a, b, a + b * xp, pi


rows = []
for k in KIND:
    tgt = g.loc[k, "target"]
    for w, (x0, x1) in WINDOWS.items():
        a, b, p30, pi = fit(d[k], x0, x1)
        reach = (tgt - a) / b if b < 0 else np.nan
        rows.append(dict(kind=KIND[k], window=w, slope=round(b, 2), pred2030=round(p30, 1),
                         pi_low=round(p30 - pi, 1), pi_high=round(p30 + pi, 1), target=tgt,
                         reach_fy=round(reach, 1) if reach == reach else None))
proj = pd.DataFrame(rows); proj.to_csv(RES / "projection_by_window.csv", index=False, encoding="utf-8-sig")

# 必要な年率（2024→2030、6年）と過去の年率（幾何平均）
req = []
for k in KIND:
    v24, tgt = d.loc[2024, k], g.loc[k, "target"]
    need = (tgt / v24) ** (1 / 6) - 1
    p1 = (d.loc[2019, k] / d.loc[2012, k]) ** (1 / 7) - 1
    p2 = (d.loc[2024, k] / d.loc[2019, k]) ** (1 / 5) - 1
    p3 = (d.loc[2024, k] / d.loc[2012, k]) ** (1 / 12) - 1
    req.append(dict(kind=KIND[k], v2024=v24, target=tgt, gap=v24 - tgt, need_pct=round(need * 100, 2),
                    past_2012_19=round(p1 * 100, 2), past_2019_24=round(p2 * 100, 2), past_2012_24=round(p3 * 100, 2)))
req = pd.DataFrame(req); req.to_csv(RES / "required_vs_past_rate.csv", index=False, encoding="utf-8-sig")
print(proj.to_string()); print(req.to_string())

# 図1 実績と外挿（2012〜24年度の直線）、目標線
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, k, c in zip(axes, KIND, [BLUE, ORANGE]):
    y = d[k]; tgt = g.loc[k, "target"]
    ax.plot(y.index, y.values, "o-", color=c, lw=2, ms=4, label="推計値")
    for w, ls in zip(["2012〜24年度", "2019〜24年度"], ["--", ":"]):
        x0, x1 = WINDOWS[w]; a, b, p30, pi = fit(y, x0, x1)
        xx = np.arange(x0, 2031); ax.plot(xx, a + b * xx, ls, color=INK, lw=1.2, label=f"直線の当てはめ（{w}）")
        ax.errorbar([2030.15 if ls == ":" else 2029.85], [p30], yerr=[pi], fmt="s", color=INK, ms=4, capsize=3)
    ax.axhline(tgt, color=GREEN, lw=1.5); ax.text(2012.2, tgt + 6, f"2030年度目標 {tgt:.0f}万t", color=GREEN, fontsize=9)
    ax.set_title(f"{KIND[k]}の食品ロス量（万t）"); ax.set_xlim(2011.5, 2031); ax.set_ylim(150, 360); ax.set_xticks([2012, 2015, 2018, 2021, 2024, 2027, 2030])
    ax.legend(fontsize=8, frameon=False, loc="upper right")
fig.suptitle("このままの直線を2030年度まで伸ばすと（■は2030年度の予測と95%予測区間）", fontsize=12, x=0.01, ha="left", y=1.04)
save(fig, "a218_projection.png")

# 図2 必要な年率と過去の年率
fig, ax = plt.subplots(figsize=(8, 4))
cols = [("past_2012_19", "2012→19年度", LIGHT), ("past_2019_24", "2019→24年度", BLUE), ("need_pct", "目標に必要（2024→30年度）", GREEN)]
x = np.arange(len(req)); wdt = 0.26
for i, (cname, lab, c) in enumerate(cols):
    v = -req[cname].values; ax.bar(x + (i - 1) * wdt, v, wdt, color=c, label=lab)
    for xi, vi in zip(x, v): ax.text(xi + (i - 1) * wdt, vi + 0.08, f"{vi:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x, req["kind"]); ax.set_ylabel("年あたりの減少率（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("1年あたり何％減らせば目標に届くか（過去のペースと比べる）", loc="left")
save(fig, "a218_rate.png")

# 図3 当てはめ期間による2030年度予測の違い
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8)); fig.subplots_adjust(wspace=0.45)
for ax, k, c in zip(axes, KIND, [BLUE, ORANGE]):
    p = proj[proj.kind == KIND[k]].reset_index(drop=True); tgt = g.loc[k, "target"]
    yy = np.arange(len(p))[::-1]
    ax.errorbar(p.pred2030, yy, xerr=[p.pred2030 - p.pi_low, p.pi_high - p.pred2030], fmt="o", color=c, capsize=4)
    for yi, v in zip(yy, p.pred2030): ax.text(v, yi + 0.18, f"{v:.0f}", ha="center", fontsize=9)
    ax.axvline(tgt, color=GREEN, lw=1.5); ax.text(tgt, len(p) - 0.45, f"目標 {tgt:.0f}", color=GREEN, fontsize=9, ha="center")
    ax.set_yticks(yy, p.window); ax.set_ylim(-0.6, len(p) - 0.2); ax.set_title(f"{KIND[k]}：2030年度の予測（万t）", loc="left")
fig.suptitle("どの期間で直線を引くかで、予測はこれだけ変わる（横線は95%予測区間）", fontsize=12, x=0.01, ha="left", y=1.03)
save(fig, "a218_window.png")
