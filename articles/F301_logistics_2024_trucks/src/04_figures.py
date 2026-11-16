"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BLUE, ORANGE, GRAY, INK2 = "#2a78d6", "#eb6834", "#9a9893", "#52514e"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
SRC_M = "出典：厚生労働省「毎月勤労統計調査」（事業所規模5人以上、就業形態計）をもとに作成者が加工"
SRC_T = "出典：国土交通省「自動車輸送統計月報」（営業用、2020年4月からの調べ方）をもとに作成者が加工"
POST = 2024 * 12 + 3
ymx = lambda ym: (ym // 12) + ((ym % 12)) / 12.0

def save(fig, name, src):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：前年同月比の差（H44 − 産業計）
es = pd.read_csv(RES / "event_yoy.csv")
es = es[es.ym >= 2021 * 12]
fig, axes = plt.subplots(2, 1, figsize=(8.4, 6.2), sharex=True); fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.11, hspace=0.25)
for ax, (col, ttl, pre, post) in zip(axes, [("yoy_diff_total_hours", "総実労働時間", m["yoy_diff_total_pre12"], m["yoy_diff_total_post12"]),
                                            ("yoy_diff_ot_hours", "所定外労働時間（残業）", m["yoy_diff_ot_pre12"], m["yoy_diff_ot_post12"])]):
    x = ymx(es.ym)
    ax.bar(x, es[col], width=1 / 12 * 0.8, color=np.where(es.ym >= POST, BLUE, GRAY))
    ax.axhline(0, color=INK2, lw=0.8); ax.axvline(ymx(POST) - 1 / 24, color=ORANGE, lw=1.5, ls="--")
    ax.set_title(f"{ttl}　直前12か月の平均 {pre:+.1f} → 規制後12か月 {post:+.1f}%pt", fontsize=10, loc="left")
    ax.set_ylabel("%pt"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
axes[0].text(ymx(POST), axes[0].get_ylim()[1] * 0.85, " 2024年4月 上限規制", color=ORANGE, fontsize=8.5)
axes[1].set_xlabel("年")
fig.suptitle("道路貨物運送業の労働時間は、2024年4月から産業全体より減った", x=0.02, ha="left", fontsize=13, y=0.975)
fig.text(0.02, 0.915, "前年同月比の差（道路貨物運送業 − 調査産業計）。灰色は規制前、青は規制後", fontsize=9, color=INK2)
save(fig, "fig1_hours_yoy_gap.png", SRC_M)

# 図2：年度の水準（2019年度＝100）
lv = pd.read_csv(RES / "fy_levels.csv")
fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.8)); fig.subplots_adjust(left=0.08, right=0.97, top=0.8, bottom=0.17, wspace=0.28)
for ax, (v, ttl) in zip(axes, [("total_hours", "総実労働時間"), ("sched_pay", "所定内給与")]):
    for ind, col, nm in (("H44", BLUE, "道路貨物運送業"), ("TL", GRAY, "調査産業計")):
        s = 100 * lv[f"{ind}_{v}"] / lv[f"{ind}_{v}"].iloc[0]
        ax.plot(lv.fy, s, color=col, lw=2, marker="o", ms=4, label=nm)
        ax.text(2025.15, s.iloc[-1], f"{s.iloc[-1]:.1f}", fontsize=8.5, va="center")
    ax.axvline(2023.5, color=ORANGE, lw=1.2, ls="--")
    ax.set_title(ttl + "（2019年度＝100）", fontsize=10, loc="left"); ax.set_xticks(range(2019, 2026)); ax.set_xticklabels([f"{y}" for y in range(2019, 2026)], fontsize=8)
    ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.set_xlabel("年度")
axes[0].legend(frameon=False, fontsize=8.5, loc="lower left")
fig.suptitle("2024年度から時間は減ったが、給与の伸びは産業全体より小さかった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"差の差（2024年4月以降、暦の月と時間の流れを調整）：総実労働時間 {m['H2']['pct']:+.1f}%、所定内給与 {m['H3']['pct']:+.1f}%", fontsize=9, color=INK2)
save(fig, "fig2_fy_hours_pay.png", SRC_M)

# 図3：運ぶ量の実績と、規制前の流れを延ばした値
tr = pd.read_csv(ROOT / "data" / "truck_monthly.csv"); tr["ym"] = tr.year * 12 + tr.month - 1
S = 2021 * 12 + 3
def fit(col):
    d = tr[tr.ym >= S].set_index("ym").sort_index(); y = np.log(d[col])
    X = pd.DataFrame(index=d.index)
    for k in range(2, 13): X[f"m{k}"] = (((d.index % 12) + 1) == k).astype(float)
    X["trend"] = (d.index - S) / 12.0; X = sm.add_constant(X)
    pre = d.index < POST
    mm = sm.OLS(y[pre], X[pre]).fit()
    return d.index, np.exp(y), np.exp(mm.predict(X))
fig, axes = plt.subplots(2, 1, figsize=(8.4, 6.4), sharex=True); fig.subplots_adjust(left=0.11, right=0.97, top=0.86, bottom=0.11, hspace=0.3)
rt = {r["spec"]: r for r in m["robustness_truck"]}
for ax, (col, ttl, unit, scale, key) in zip(axes, [("ton_commercial", "輸送トン数（運んだ重さ）", "百万トン", 1e-3, "主（輸送トン数）"),
                                                 ("tonkm_commercial", "輸送トンキロ（重さ×距離）", "億トンキロ", 1e-2, "R5a 輸送トンキロ")]):
    idx, y, p = fit(col)
    x = ymx(idx)
    ax.plot(x, y * scale, color=BLUE, lw=1.8, label="実績")
    ax.plot(x[idx >= POST], p[idx >= POST] * scale, color=GRAY, lw=1.8, ls="--", label="規制前（2021年4月〜2024年3月）の流れを延ばした値")
    ax.axvline(ymx(POST) - 1 / 24, color=ORANGE, lw=1.5, ls="--")
    r = rt[key]
    ax.set_title(f"{ttl}　規制後の平均のずれ {r['mean_dev_pct']:+.1f}%（1年目 {r['year1_dev_pct']:+.1f}%、2年目 {r['year2_dev_pct']:+.1f}%）", fontsize=10, loc="left")
    ax.set_ylabel(unit); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
axes[0].legend(frameon=False, fontsize=8.5, loc="lower left"); axes[1].set_xlabel("年")
fig.suptitle("運んだ重さは流れどおり、重さ×距離は流れより下がった", x=0.02, ha="left", fontsize=13, y=0.975)
fig.text(0.02, 0.915, "営業用トラック、月の値。破線（灰）は暦の月と直線の時間の流れで延ばした値", fontsize=9, color=INK2)
save(fig, "fig3_truck_volume_vs_trend.png", SRC_T)

# 図4：1トンあたりの距離（車の大きさ別、年度）
f = pd.DataFrame(q["fy"])
fig, ax = plt.subplots(figsize=(8.2, 4.8)); fig.subplots_adjust(left=0.1, right=0.8, top=0.82, bottom=0.14)
for col, c, nm in (("dist_large", BLUE, "最大積載量11トン以上"), ("dist_all", GRAY, "営業用の計"), ("dist_small_mid", ORANGE, "11トン未満の普通車")):
    ax.plot(f.fy, f[col], color=c, lw=2, marker="o", ms=4)
    ax.text(2025.12, f[col].iloc[-1], f"{nm}\n{f[col].iloc[-1]:.1f}km", fontsize=8.5, va="center")
ax.axvline(2023.5, color=ORANGE, lw=1.2, ls="--"); ax.set_xticks(range(2021, 2026))
ax.set_ylim(0, 130); ax.set_ylabel("1トンあたりの輸送距離（km、トンキロ÷トン）"); ax.set_xlabel("年度"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ql = q["its"]["dist_large"]["mean_dev_pct"]; qs = q["its"]["dist_small_mid"]["mean_dev_pct"]
fig.suptitle("距離が縮んだのは、おもに大きな車", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"規制前の流れからのずれ（2024年4月〜）：11トン以上 {ql:+.1f}%、11トン未満 {qs:+.1f}%", fontsize=9, color=INK2)
save(fig, "fig4_distance_by_size.png", SRC_T)
print("ok")
