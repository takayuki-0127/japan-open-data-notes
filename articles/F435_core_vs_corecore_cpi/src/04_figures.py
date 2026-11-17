"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：総務省「消費者物価指数」2025年基準（全国）をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
y = pd.read_csv(R / "yoy.csv").set_index("ym")
d = pd.read_csv(D / "cpi.csv").set_index("ym")
LAB = {"headline": "総合", "core": "コア（生鮮食品を除く）", "corecore": "コアコア（生鮮食品とエネルギーを除く）", "us_core": "食料（酒類を除く）とエネルギーを除く"}
COL = {"headline": C[5], "core": C[1], "corecore": C[0], "us_core": C[2]}

# 図1 前年比 2015〜
s = y.loc[201501:]
x = (s.index // 100) + ((s.index % 100) - 0.5) / 12
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for k in ["headline", "core", "corecore", "us_core"]:
    ax.plot(x, s[k], color=COL[k], lw=2.2 if k in ("core", "corecore") else 1.3, label=LAB[k])
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("前年同月比（%）")
ax.legend(frameon=False, loc="upper left", fontsize=8.8)
style(ax)
ax.set_title(f"コアの山は{m['core_peak_month']//100}年{m['core_peak_month']%100}月（{m['core_peak']:.1f}%）、コアコアの山は{m['corecore_peak_month']//100}年{m['corecore_peak_month']%100}月（{m['corecore_peak']:.1f}%）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_yoy.png", SRC, "注：2014・2019年の消費税率の引き上げの月から1年は、前年比が押し上げられている。")

# 図2 差とエネルギーの寄与
s = y.loc[200001:]
x = (s.index // 100) + ((s.index % 100) - 0.5) / 12
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(x, s.gap, width=1 / 12, color=[C[1] if v >= 0 else C[0] for v in s.gap])
ax.plot(x, s.energy_contrib, color=INK, lw=1.2, label="エネルギーの前年比×ウエイトの割合（近似の寄与）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("コア − コアコア（ポイント）")
ax.legend(frameon=False, loc="lower left", fontsize=9)
style(ax)
ax.set_title(f"二つの差はエネルギーでほぼ説明できる（相関{q['corr_gap_energy']:.2f}）。2022年以降の差は +{m['gap_max']:.1f}〜{m['gap_min']:.1f}ポイント", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig2_gap_energy.png", SRC, f"注：差が最も大きいのは{m['gap_max_month']//100}年{m['gap_max_month']%100}月（+{m['gap_max']:.1f}）、最も小さいのは{m['gap_min_month']//100}年{m['gap_min_month']%100}月（{m['gap_min']:.1f}、電気・ガス代の補助の時期）。")

# 図3 予測の誤差
fc = pd.read_csv(R / "forecast.csv"); rb = pd.read_csv(R / "robustness.csv")
t = pd.concat([fc, rb]).set_index("check")
fig, ax = plt.subplots(figsize=(8.8, 5.0))
xx = np.arange(len(t)); wdt = 0.2
for i, k in enumerate(["headline", "core", "corecore", "us_core"]):
    ax.bar(xx + (i - 1.5) * wdt, t[k], wdt, color=COL[k], label=LAB[k])
ax.set_xticks(xx, [c.replace("、", "\n") for c in t.index], fontsize=8.6)
ax.set_ylabel("12か月先などの総合の前年比を当てる誤差（ポイント）")
ax.legend(frameon=False, loc="upper left", fontsize=8.4, ncol=2)
ax.set_ylim(0, 2.4)
style(ax)
ax.set_title("今の前年比で先の総合を当てると、コアコアはコアより当たらない", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.2)
save(fig, F / "fig3_forecast_rmse.png", SRC, "注：誤差は二乗平均の平方根。今の各指標の前年比を、そのまま先の総合の前年比の予測とみなした。")

# 図4 2021年平均＝100
a21 = d.loc[202101:202112].mean()
s = d.loc[202101:] / a21 * 100
x = (s.index // 100) + ((s.index % 100) - 0.5) / 12
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for k in ["headline", "core", "corecore", "us_core"]:
    ax.plot(x, s[k], color=COL[k], lw=2.2 if k in ("core", "corecore") else 1.3, label=LAB[k])
    ax.text(x[-1] + 0.05, s[k].iloc[-1], f"{s[k].iloc[-1]:.1f}", fontsize=8.6, color=COL[k], va="center")
ax.set_xlim(2021, 2027.2); ax.set_ylabel("2021年平均＝100")
ax.legend(frameon=False, loc="upper left", fontsize=8.8)
style(ax)
ax.set_title(f"2021年からの上がり幅はコア{q['cum_core']:.1f}%、コアコア{q['cum_corecore']:.1f}%で同じ。食料も除くと{q['cum_us_core']:.1f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, F / "fig4_cumulative.png", SRC)
