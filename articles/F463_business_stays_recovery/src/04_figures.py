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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：観光庁「宿泊旅行統計調査」（年の確定値）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8")); req = json.load(open(R / "requestion.json", encoding="utf-8"))
N = pd.read_csv(R / "national_by_year.csv", index_col="year")
pref = pd.read_csv(R / "pref_under50.csv", index_col="area")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：推移
fig, ax = plt.subplots(figsize=(8.8, 4.8))
yrs = list(N.index); x = np.arange(len(yrs))
for col, c, nm in [("tourism_under50", C[0], "観光目的の宿泊者が50%未満の施設"), ("tourism50plus", C[1], "観光目的の宿泊者が50%以上の施設"), ("unknown", "#9b9a96", "宿泊目的割合が不詳")]:
    v = N[col] / 1e6
    ax.plot(x[:5], v.iloc[:5], marker="o", ms=4, lw=2, color=c, label=nm)
    ax.plot(x[5:], v.iloc[5:], marker="o", ms=4, lw=2, color=c)
    ax.text(x[-1] + 0.15, v.iloc[-1], f"{v.iloc[-1]:.0f}", va="center", fontsize=9, color=c)
    ax.text(x[4], v.iloc[4] + 8, f"{v.iloc[4]:.0f}", ha="center", fontsize=9, color=c)
ax.set_xticks(x, [str(y) for y in yrs]); ax.set_ylim(0, 360); ax.set_xlim(-0.4, len(yrs) - 0.2)
ax.axvline(4.5, color=INK2, lw=0.8, ls=":"); ax.text(4.55, 340, "2020・2021年は省いた", fontsize=8.5, color=INK2)
ax.set_ylabel("延べ宿泊者数（百万人泊）"); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.set_title("図1　施設の宿泊目的別の延べ宿泊者数", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.96, top=0.9, bottom=0.2)
foot(fig, "日本人と外国人の合計。不詳は合計−50%以上−50%未満。")
save(fig, "fig1_series.png")

# 図2：2019年比
rob = main["robustness"]
labels = ["50%未満の施設", "50%未満の施設\n（不詳を振り分け）", "50%以上の施設", "50%以上の施設\n（不詳を振り分け）", "ビジネスホテルの\n日本人"]
vals = [main["H2"]["under50"], rob["R1_unknown_allocated"]["under50"], main["H2"]["plus50"], rob["R1_unknown_allocated"]["plus50"], rob["R4_business_hotel_japanese"]["ratio"]]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.bar(range(5), [v * 100 for v in vals], 0.55, color=[C[0], "#8fb8ea", C[1], "#f3ae8c", C[2]])
for i, v in enumerate(vals):
    ax.text(i, v * 100 + 1.5, f"{v * 100:.1f}", ha="center", fontsize=10, color=INK2)
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xticks(range(5), labels, fontsize=9); ax.set_ylim(0, 125); ax.set_ylabel("2025年（2019年＝100）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.set_title("図2　2025年の延べ宿泊者数（2019年＝100）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.22)
foot(fig, "振り分け：不詳の分を、その年の50%以上と50%未満の割合で分けた。ビジネスホテルの日本人＝合計−外国人。")
save(fig, "fig2_ratio_2019.png")

# 図3：都道府県（50%未満の施設、2019年比）
fig, ax = plt.subplots(figsize=(9.6, 4.8))
xx = np.arange(len(pref))
ax.bar(xx, pref.ratio * 100, 0.7, color=C[0], label="表の値のまま")
ax.scatter(xx, pref.ratio_alloc * 100, color=C[1], s=14, zorder=3, label="不詳を振り分け")
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xticks(xx, [a if a == "北海道" else a[:-1] for a in pref.index], rotation=90, fontsize=7.6)
ax.set_ylim(0, max(160, float(pref[["ratio", "ratio_alloc"]].max().max()) * 100 + 15)); ax.set_xlim(-0.8, len(pref) - 0.2); ax.set_ylabel("2025年（2019年＝100）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=2)
ax.set_title("図3　50%未満の施設の延べ宿泊者数、都道府県別（北から南の順）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.24)
foot(fig, "並びは都道府県コード順で、値の順ではない。")
save(fig, "fig3_pref.png")

# 図4：県内・県外
fig, ax = plt.subplots(figsize=(8.8, 4.6))
g = [("tourism_under50", "50%未満の施設"), ("tourism50plus", "50%以上の施設")]
w = 0.35
for k, (col, c, nm) in enumerate([("in_pref", C[2], "県内に住む人"), ("out_pref", C[0], "県外に住む人")]):
    v = [req[gg][col]["ratio"] * 100 for gg, _ in g]
    ax.bar(np.arange(2) + (k - 0.5) * w, v, w, color=c, label=nm)
    for xi, vv in zip(np.arange(2) + (k - 0.5) * w, v):
        ax.text(xi, vv + 1.5, f"{vv:.1f}", ha="center", fontsize=10, color=INK2)
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xticks(range(2), [nm for _, nm in g]); ax.set_ylim(0, 145); ax.set_ylabel("2025年（2019年＝100）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
ax.set_title("図4　県内の人の宿泊は減り、県外の人の宿泊は増えた", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.2)
foot(fig, "居住地は施設のある都道府県から見た県内・県外。居住地不詳は含めていない。")
save(fig, "fig4_residence.png")
print("figures ok")
