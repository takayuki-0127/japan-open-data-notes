"""04 図：6枚。"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import DATA, RES, FIG, CPI, SHORT

for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
SRC = "出典：厚生労働省「毎月勤労統計調査」、総務省「消費者物価指数」をもとに作成（調査産業計・5人以上・就業形態計）"
def save(fig, name, note=SRC):
    fig.text(0.01, 0.01, note, fontsize=8.5, color="#555"); fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / name, dpi=150); plt.close(fig)

m = pd.read_csv(DATA / "monthly_calc.csv", parse_dates=["month"]).set_index("month")
real = lambda n, p: (((1 + n / 100) / (1 + p / 100) - 1) * 100).round(1) + 0.0
K = list(CPI); COL = {"0163": "#c0392b", "0001": "#2c7fb8", "0161": "#7fcdbb", "0166": "#e6a0a0", "0178": "#6a3d9a", "0168": "#999999"}
w = m.loc["2015-01-01":"2026-08-01"]

# 図1 実質賃金の前年同月比：公表と同じ物価・総合・コアコア
fig, ax = plt.subplots(figsize=(10, 4.8))
for k in ["0163", "0001", "0178"]:
    ax.plot(w.index, real(w.pub_total, w[f"p_{k}"]), color=COL[k], lw=1.6 if k == "0163" else 1.1, label=SHORT[k])
ax.axhline(0, color="k", lw=0.8); ax.set_ylim(-5, 5)
ax.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2024-12-01"), color="#f3f3f3", zorder=0)
ax.set_title("実質賃金の前年同月比（現金給与総額）：どの物価で割るか"); ax.set_ylabel("%"); ax.legend(loc="upper left", frameon=False, ncol=3)
save(fig, "fig1_real_wage_three_deflators.png")

# 図2 物価6系列の前年同月比
fig, ax = plt.subplots(figsize=(10, 4.8))
x = m.loc["2021-01-01":"2026-08-01"]
for k in K:
    ax.plot(x.index, x[f"p_{k}"], color=COL[k], lw=1.6 if k == "0163" else 1.0, label=SHORT[k])
ax.axhline(0, color="k", lw=0.8); ax.set_title("6つの物価の前年同月比"); ax.set_ylabel("%"); ax.legend(ncol=3, frameon=False, fontsize=9, loc="upper left")
save(fig, "fig2_cpi_six.png", "出典：総務省「消費者物価指数」（2020年基準、全国）をもとに作成")

# 図3 2022〜2024年の最長の連続マイナス：総額ときまって支給する給与
r = json.load(open(RES / "reask.json"))
names = [SHORT[k] for k in K]
tot = [r["total_longest_by_cpi"][n][0] for n in names]; reg = [r["regular_longest_by_cpi"][n][0] for n in names]
fig, ax = plt.subplots(figsize=(10, 4.8)); y = np.arange(len(names))
ax.barh(y + 0.2, tot, 0.4, color="#2c7fb8", label="現金給与総額（賞与を含む）")
ax.barh(y - 0.2, reg, 0.4, color="#fdae61", label="きまって支給する給与（賞与などを除く）")
for i, (a, b) in enumerate(zip(tot, reg)):
    ax.text(a + 0.3, i + 0.2, f"{a}か月", va="center", fontsize=9); ax.text(b + 0.3, i - 0.2, f"{b}か月", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis(); ax.set_xlabel("2022〜2024年の中で、最も長くマイナスが続いた月数")
ax.set_title("「連続マイナス」の長さは、物価と賃金の選び方で9〜30か月に動く"); ax.legend(frameon=False, loc="lower right")
save(fig, "fig3_streak_by_deflator.png")

# 図4 向きの入れ替わり（2015〜）：物価ごとのプラス・マイナス
sg = pd.DataFrame({SHORT[k]: np.sign(real(w.pub_total, w[f"p_{k}"])) for k in K})
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.imshow(sg.T.values, aspect="auto", cmap=matplotlib.colors.ListedColormap(["#d6604d", "#f7f7f7", "#4393c3"]), vmin=-1, vmax=1,
          extent=[0, len(sg), len(K), 0], interpolation="nearest")
dis = sg.nunique(axis=1) > 1
for i, v in enumerate(dis):
    if v: ax.plot(i + 0.5, -0.25, "v", color="k", ms=3, clip_on=False)
ax.set_yticks(np.arange(len(K)) + 0.5); ax.set_yticklabels(sg.columns, fontsize=9)
yrs = [i for i, t in enumerate(sg.index) if t.month == 1]; ax.set_xticks(yrs); ax.set_xticklabels([sg.index[i].year for i in yrs], fontsize=9)
ax.set_title(f"実質賃金の向き（赤＝マイナス、青＝プラス）。▼は物価によって向きが分かれた月（{int(dis.sum())}／{len(dis)}か月）", fontsize=10.5)
save(fig, "fig4_sign_map.png")

# 図5 再問い：2022〜2024年、総額ときまって支給する給与の実質と、特別給与の寄与
t = pd.read_csv(RES / "reask_bonus_2022_2024.csv", parse_dates=[0], index_col=0)
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.bar(t.index, t["特別給与の寄与"], width=20, color="#fee08b", label="名目の伸びのうち、賞与など（総額−きまって）")
ax.plot(t.index, t["実質_総額"], color="#2c7fb8", marker="o", ms=3, label="実質（現金給与総額）")
ax.plot(t.index, t["実質_きまって"], color="#d95f02", marker="o", ms=3, label="実質（きまって支給する給与）")
for d in t.index[t["総額だけ0以上"]]:
    ax.annotate("", (d, t.loc[d, "実質_総額"] + 0.25), (d, t.loc[d, "実質_総額"] + 1.0), arrowprops=dict(arrowstyle="->", color="k", lw=0.8))
ax.axhline(0, color="k", lw=0.8); ax.set_ylabel("%（前年同月比・ポイント）")
ax.set_title("連続を切ったのは賞与の多い月：矢印は「総額だけ0以上」の月（公表と同じ物価で割った値）", fontsize=10.5); ax.legend(frameon=False, fontsize=9, loc="lower left")
save(fig, "fig5_reask_bonus.png")

# 図6 頑健性：最長の連続（2015年〜）を条件ごとに
rb = pd.read_csv(RES / "robustness.csv")
cases = rb["case"].unique().tolist()
fig, ax = plt.subplots(figsize=(11, 4.8))
for j, k in enumerate(K):
    v = rb[rb.cpi.astype(str).str.zfill(4) == k].set_index("case").reindex(cases)["longest"]
    ax.plot(v.values, np.arange(len(cases)) + (j - 2.5) * 0.1, "o", color=COL[k], ms=7, alpha=0.85, label=SHORT[k])
ax.set_yticks(range(len(cases))); ax.set_yticklabels([c.replace("主（現金給与総額・公表の伸び率・丸め・2015年〜）", "基本の条件") for c in cases], fontsize=9); ax.invert_yaxis()
ax.set_xlabel("最も長い連続マイナス（か月）"); ax.set_title("条件を変えると、最長の連続も物価の順位も動く"); ax.legend(frameon=False, fontsize=8.5, ncol=1, loc="upper left", bbox_to_anchor=(1.0, 1.0))
save(fig, "fig6_robustness.png")
print("ok")
