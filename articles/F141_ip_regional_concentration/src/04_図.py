"""図を5枚つくる。入力: results/*.csv, results/summary.json  出力: figures/*.png"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False

M = pd.read_csv(ROOT / "results/concentration_by_series_year.csv")
T = pd.read_csv(ROOT / "results/trend_table.csv")
S = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
SER = ["特許出願", "特許登録", "特許の発明者数", "意匠出願", "商標出願", "実用新案出願"]
COL = {"特許出願": "#1f4e79", "特許登録": "#6c8ebf", "特許の発明者数": "#c0392b", "意匠出願": "#2e8b57", "商標出願": "#d68910", "実用新案出願": "#7f7f7f"}
STY = {"特許登録": "--", "特許の発明者数": "-"}

def lines(metric, fn, title, ylab):
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for s in SER:
        x = M[M.series == s]
        ax.plot(x.year, x[metric] * 100, STY.get(s, "-"), color=COL[s], lw=2.2 if s in ("特許出願", "特許の発明者数", "意匠出願") else 1.5, label=s)
        ax.text(2024.3, x[metric].iloc[-1] * 100, s, color=COL[s], va="center", fontsize=9)
    ax.set_xlim(2006.5, 2027.5); ax.set_xticks(range(2007, 2025, 3)); ax.set_title(title, fontsize=13, loc="left"); ax.set_ylabel(ylab)
    ax.axvspan(2019.5, 2021.5, color="#eeeeee", zorder=0); ax.text(2020.5, ax.get_ylim()[1], "2020–21", ha="center", va="top", fontsize=8, color="#777")
    ax.grid(axis="y", alpha=.3)
    fig.text(0.01, 0.01, "出典：特許庁「特許行政年次報告書」2010〜2025年版の都道府県別の表（日本人による出願）から作成", fontsize=7.5, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / fn, dpi=150); plt.close(fig)

lines("東京の割合", "fig1_tokyo_share.png", "東京都の割合：発明者の住所で数えると、18年で11ポイント上がった", "47都道府県の合計に占める割合（%）")
lines("地方の割合", "fig2_nonmetro_share.png", "三大都市圏以外（36道県）の割合：特許は1割のまま", "47都道府県の合計に占める割合（%）")

# 図3 要因分解
dc = S["decomp"]
fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.4), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axs[0]
vals = [dc["変化"] * 100, dc["権利ごとの変化"] * 100, dc["構成の変化"] * 100]
ax.bar(["変化の合計", "権利ごとの\n地方割合の変化", "権利の構成の\n変化"], vals, color=["#555", "#2e8b57", "#d68910"])
for i, v in enumerate(vals):
    ax.text(i, v + 0.03, f"{v:+.2f}pt", ha="center", fontsize=10)
ax.set_title("4つの権利を合わせた地方の割合\n（2007–09年平均→2022–24年平均）", fontsize=11, loc="left"); ax.set_ylabel("ポイント")
ax = axs[1]
R = ["特許出願", "商標出願", "意匠出願", "実用新案出願"]
a = [dc["構成_2007_09"][r] * 100 for r in R]; b = [dc["構成_2022_24"][r] * 100 for r in R]
y = np.arange(len(R))
ax.barh(y + 0.2, a, 0.4, color="#bbbbbb", label="2007–09年"); ax.barh(y - 0.2, b, 0.4, color=[COL[r] for r in R], label="2022–24年")
for i, r in enumerate(R):
    ax.text(max(a[i], b[i]) + 1, y[i], f"地方の割合 {dc['権利ごとの地方割合_2007_09'][r]*100:.0f}%→{dc['権利ごとの地方割合_2022_24'][r]*100:.0f}%", va="center", fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels(R); ax.invert_yaxis(); ax.set_xlim(0, 100)
ax.set_title("出願の構成（%）：地方の割合が高い商標が増えた", fontsize=11, loc="left"); from matplotlib.patches import Patch; ax.legend(handles=[Patch(color="#bbbbbb", label="2007–09年"), Patch(color="#555555", label="2022–24年（色つき）")], fontsize=8, loc="lower right")
fig.text(0.01, 0.01, "地方＝三大都市圏（埼玉・千葉・東京・神奈川・岐阜・愛知・三重・京都・大阪・兵庫・奈良）以外の36道県", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig3_decomposition.png", dpi=150); plt.close(fig)

# 図4 地方ブロック別の割合の変化
B = pd.read_csv(ROOT / "results/block_change.csv")
P = B.pivot(index="block", columns="series", values="diff_pt")
order = ["東京都", "関東", "中部", "近畿", "北海道", "東北", "中国", "四国", "九州・沖縄"]
cols = ["特許出願", "特許の発明者数", "意匠出願", "商標出願", "実用新案出願"]
P = P.loc[order, cols]
fig, ax = plt.subplots(figsize=(8, 5))
v = np.abs(P.values).max()
im = ax.imshow(P.values, cmap="RdBu_r", vmin=-v, vmax=v, aspect="auto")
for i in range(P.shape[0]):
    for j in range(P.shape[1]):
        ax.text(j, i, f"{P.values[i, j]:+.1f}", ha="center", va="center", fontsize=9, color="white" if abs(P.values[i, j]) > 0.6 * v else "black")
ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, fontsize=9)
ax.set_yticks(range(len(order))); ax.set_yticklabels(["東京都", "関東（東京以外）", "中部", "近畿", "北海道", "東北", "中国", "四国", "九州・沖縄"], fontsize=9)
ax.set_title("地方ブロック別の割合の変化（ポイント、2007–09年平均→2022–24年平均）", fontsize=11.5, loc="left")
fig.colorbar(im, ax=ax, shrink=.7, label="ポイント")
fig.text(0.01, 0.01, "出典：特許庁「特許行政年次報告書」各年版から作成", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig4_block_change.png", dpi=150); plt.close(fig)

# 図5 頑健性：指標ごとの10年あたりの傾き（95%区間、HAC）
mets = [("地方の割合", "地方（36道県）の割合"), ("上位5都府県以外の割合", "上位5都府県以外の割合"), ("HHI_東京を除く", "HHI（東京を除く46道府県）"), ("ジニ係数", "ジニ係数")]
fig, axs = plt.subplots(1, 4, figsize=(12, 4.2), sharey=True)
for ax, (m, lab) in zip(axs, mets):
    x = T[T.metric == m].set_index("series").loc[SER]
    yy = np.arange(len(SER))
    sc = 100 if m in ("地方の割合", "上位5都府県以外の割合") else 1
    ax.errorbar(x.slope10 * sc, yy, xerr=[(x.slope10 - x.lo) * sc, (x.hi - x.slope10) * sc], fmt="o", color="k", ms=4, capsize=3)
    ax.errorbar(x.slope10_ex2020_21 * sc, yy + 0.25, xerr=[(x.slope10_ex2020_21 - x.lo_ex) * sc, (x.hi_ex - x.slope10_ex2020_21) * sc], fmt="s", color="#999", ms=3, capsize=2)
    ax.axvline(0, color="#c00", lw=.8); ax.set_title(lab, fontsize=10)
    ax.set_xlabel("10年あたりの変化" + ("（ポイント）" if sc == 100 else ""), fontsize=8.5)
axs[0].set_yticks(np.arange(len(SER))); axs[0].set_yticklabels(SER); axs[0].invert_yaxis()
fig.suptitle("頑健性：指標を変えた時系列の傾き（●全期間、■2020–21年を除く。線は95%区間）", fontsize=11.5, x=0.01, ha="left")
fig.text(0.01, 0.01, "地方の割合が増えると＋、HHI・ジニ係数は集中が強まると＋", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 0.94)); fig.savefig(FIG / "fig5_robustness.png", dpi=150); plt.close(fig)
print("ok")
