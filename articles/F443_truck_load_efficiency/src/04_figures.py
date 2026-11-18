"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cd1"]
INK2, GRID, MUTE = "#52514e", "#e4e3df", "#a3a29d"
SRC = "出典：国土交通省「自動車輸送統計年報」（各年度、e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}
W = pd.read_csv(R / "fy_metrics.csv")
main = json.load(open(R / "main.json", encoding="utf-8"))
ERAS = [(2000, 2009), (2010, 2019), (2020, 2025)]


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


def seg_plot(ax, s, **kw):
    lab = kw.pop("label", None)
    for i, (a, b) in enumerate(ERAS):
        x = s.loc[a:b]
        ax.plot(x.index, x.values, label=lab if i == 0 else None, **kw)


def breaks(ax):
    for y in [2009.5, 2019.5]:
        ax.axvline(y, color=MUTE, lw=0.8, ls=":")


# 図1 積載効率の推移
bt = pd.Series({int(k): v for k, v in main["biz_total_eff"].items()})
bo = W[W.group == "biz_ordinary"].set_index("fy")
fig, ax = plt.subplots(figsize=(9.5, 5.2)); fig.subplots_adjust(bottom=0.2, top=0.88, left=0.08, right=0.97)
seg_plot(ax, bt, color=C[0], lw=2.2, marker="o", ms=4, label="営業用の計")
seg_plot(ax, bo.eff, color=C[1], lw=1.6, marker="s", ms=3.5, label="営業用の普通車")
ax.axhline(40, color=INK2, lw=0.8, ls="--"); ax.text(2000, 40.4, "40%", color=INK2, fontsize=9)
breaks(ax)
for y in [2015, 2016, 2024, 2025]:
    ax.annotate(f"{y}年度\n{bt.loc[y]:.1f}%", (y, bt.loc[y]), xytext=(0, -30 if y in (2016, 2025) else 12), textcoords="offset points",
                ha="center", fontsize=8.3, color=INK2)
ax.set_ylabel("積載効率（%）＝輸送トンキロ÷能力トンキロ"); ax.set_ylim(30, 56); ax.grid(axis="y", color=GRID, lw=0.7)
ax.legend(frameon=False, loc="lower left"); ax.set_xticks(range(2000, 2026, 5))
ax.text(2004.5, 54.5, "旧い作り方", ha="center", color=INK2, fontsize=9); ax.text(2014.5, 54.5, "2010年度〜", ha="center", color=INK2, fontsize=9)
ax.text(2022.5, 54.5, "2020年度〜", ha="center", color=INK2, fontsize=9)
fig.suptitle("図1 営業用トラックの積載効率は2016年度に40%を切り、2024年度に41.3%、2025年度に39.0%", x=0.01, ha="left", fontsize=12)
foot(fig, "点線で区切った3つの期間は調査の作り方が違うため、線をつないでいない（2010年度は作り方の変更の年）。年度は4月〜翌3月")
save(fig, "fig1_load_efficiency_trend.png")

# 図2 分解：積載効率＝実車率×実車時の積載率（営業用普通車）
fig, ax = plt.subplots(figsize=(9.5, 5.2)); fig.subplots_adjust(bottom=0.2, top=0.88, left=0.08, right=0.97)
seg_plot(ax, bo.lr, color=C[2], lw=2, marker="o", ms=4, label="実車率（走った距離のうち荷を積んでいた割合）")
seg_plot(ax, bo.load_when_loaded, color=C[3], lw=2, marker="o", ms=4, label="実車時の積載率（荷を積んで走るときの重さの埋まり方）")
seg_plot(ax, bo.eff, color=C[1], lw=2.2, marker="s", ms=4, label="積載効率（＝上の2つの積）")
breaks(ax); ax.set_ylim(30, 80); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_ylabel("%")
ax.legend(frameon=False, loc="lower left", fontsize=9); ax.set_xticks(range(2000, 2026, 5))
y = 2025
ax.annotate(f"{bo.lr.loc[y]:.2f}", (y, bo.lr.loc[y]), xytext=(6, -10), textcoords="offset points", fontsize=8.5, color=INK2)
ax.annotate(f"{bo.load_when_loaded.loc[y]:.2f}", (y, bo.load_when_loaded.loc[y]), xytext=(6, 4), textcoords="offset points", fontsize=8.5, color=INK2)
ax.annotate(f"{bo.eff.loc[y]:.2f}", (y, bo.eff.loc[y]), xytext=(6, -4), textcoords="offset points", fontsize=8.5, color=INK2)
fig.suptitle("図2 「4割」は、空で走る距離と、積んだときの埋まり方の掛け算（営業用普通車）", x=0.01, ha="left", fontsize=12)
foot(fig, f"実車時の積載率＝積載効率÷実車率（作成者の計算）。2025年度は 実車率{bo.lr.loc[2025]:.2f}% × 実車時の積載率{bo.load_when_loaded.loc[2025]:.2f}% ＝ 積載効率{bo.eff.loc[2025]:.2f}%")
save(fig, "fig2_decomposition_ordinary.png")

# 図3 大きさ別（2020〜2025年度の平均）
sm = main["size_mean_2020_2025"]
groups = [("biz_lt3", "普通車 3トン未満"), ("biz_3to6_5", "普通車 3〜6.5トン"), ("biz_6_5to11", "普通車 6.5〜11トン"), ("biz_11to16", "普通車 11〜16トン"),
          ("biz_16plus", "普通車 16トン以上"), ("biz_special", "特種用途車"), ("own_ordinary", "（参考）自家用普通車")]
fig, ax = plt.subplots(figsize=(9.5, 5.6)); fig.subplots_adjust(bottom=0.17, top=0.88, left=0.22, right=0.97)
yy = np.arange(len(groups))[::-1]; h = 0.26
for j, (k, lab, col) in enumerate([("eff", "積載効率", C[1]), ("lr", "実車率", C[2]), ("load_when_loaded", "実車時の積載率", C[3])]):
    vals = [sm[g][k] for g, _ in groups]
    ax.barh(yy + (1 - j) * h, vals, height=h - 0.02, color=col, label=lab)
    for v, y0 in zip(vals, yy + (1 - j) * h):
        ax.text(v + 0.6, y0, f"{v:.1f}", va="center", fontsize=7.8, color=INK2)
ax.set_yticks(yy); ax.set_yticklabels([l for _, l in groups]); ax.set_xlim(0, 85); ax.set_xlabel("%（2020〜2025年度の平均）")
ax.axvline(40, color=INK2, lw=0.8, ls="--"); ax.grid(axis="x", color=GRID, lw=0.7); ax.legend(frameon=False, loc="lower right", fontsize=9)
fig.suptitle("図3 6年度の平均で40%を超えるのは11〜16トンの車だけ。16トン以上は空で走る割合が大きい", x=0.01, ha="left", fontsize=12)
foot(fig, f"営業用（参考の1行を除く）。11〜16トンの車は営業用普通車の輸送トンキロの{sm['biz_11to16']['share_tonkm_biz_ordinary']:.0f}%を運ぶ。大きさは最大積載量")
save(fig, "fig3_by_truck_size.png")

# 図4 問い直し：大きさ別の積載効率の年ごとの動き
se = main["size_by_year_eff"]
fig, ax = plt.subplots(figsize=(9.5, 5.2)); fig.subplots_adjust(bottom=0.17, top=0.88, left=0.08, right=0.84)
years = list(range(2020, 2026))
for i, (g, lab) in enumerate(groups[:5]):
    v = [se[g][str(y)] for y in years]
    ax.plot(years, v, color=C[i], lw=2, marker="o", ms=4)
    ax.text(2025.15, v[-1], lab.replace("普通車 ", ""), color=INK2, fontsize=9, va="center")
v = [main["biz_ordinary"][str(y)]["eff"] for y in years]
ax.plot(years, v, color="#1f1e1c", lw=1.4, ls="--", marker="s", ms=3.5)
ax.text(2025.15, v[-1] + 0.6, "普通車の計", color=INK2, fontsize=9, va="center")
ax.axhline(40, color=MUTE, lw=0.8, ls=":"); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_ylabel("積載効率（%）"); ax.set_xticks(years)
ax.set_xticklabels([f"{y}年度" for y in years])
fig.suptitle("図4 2024年度の上昇と2025年度の低下は、どの大きさの車でも同じ向き", x=0.01, ha="left", fontsize=12)
foot(fig, "営業用普通車の最大積載量別。2024→2025年度の低下（−2.3ポイント）のうち−1.3ポイントは11〜16トンの車の積載効率の低下による")
save(fig, "fig4_size_by_year.png")
print("figures done")
