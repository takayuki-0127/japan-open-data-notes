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
SRC = "出典：観光庁「宿泊旅行統計調査」（日本人延べ宿泊者数、月別）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8")); req = json.load(open(R / "requestion.json", encoding="utf-8"))
nat = pd.read_csv(R / "measures_national.csv", index_col="year")
msh = pd.read_csv(R / "monthly_share_national.csv", index_col="month")
pp = pd.read_csv(R / "pref_change.csv")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：8月の割合と12月＋1月の割合の推移
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.axvspan(2019.5, 2022.5, color="#ecebe7", zorder=0)
ax.text(2021, 12.5, "2020〜22年は\nコロナの影響が\n大きいので\n線を切った", ha="center", fontsize=8.5, color=INK2)
nn = nat.copy(); nn.loc[[2020, 2021, 2022], ["aug_share", "decjan_share"]] = np.nan
ax.plot(nn.index, nn.aug_share, marker="o", ms=4, lw=2, color=C[1], label="8月の割合")
ax.plot(nn.index, nn.decjan_share, marker="o", ms=4, lw=2, color=C[0], label="12月と1月の割合（2か月の合計）")
for y in (2012, 2019, 2025):
    ax.text(y, nat.loc[y, "aug_share"] + 0.35, f"{nat.loc[y, 'aug_share']:.1f}%", ha="center", fontsize=8.5, color=C[1])
    ax.text(y, nat.loc[y, "decjan_share"] + 0.35, f"{nat.loc[y, 'decjan_share']:.1f}%", ha="center", fontsize=8.5, color=C[0])
ax.set_ylim(6, 18); ax.set_ylabel("日本人延べ宿泊者数（年計）に占める割合（%）")
ax.set_xticks(range(2011, 2026, 2)); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.set_title("図1　8月の割合は下がり、12月と1月の割合は変わらない", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.2)
foot(fig, "月の値なので、お盆は8月、年末年始は12月と1月で近づけて見ている。")
save(fig, "fig1_aug_decjan_share.png")

# 図2：月ごとの割合（2012〜14年平均と2023〜25年平均）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = np.arange(1, 13); w = 0.38
ax.bar(x - w / 2, msh["2012-14"], w, color="#9b9a96", label="2012〜14年平均")
ax.bar(x + w / 2, msh["2023-25"], w, color=C[0], label="2023〜25年平均")
for xi, a, b in zip(x, msh["2012-14"], msh["2023-25"]):
    if xi == 8:
        ax.text(xi - w / 2, a + 0.15, f"{a:.1f}", ha="center", fontsize=8.5, color=INK2)
        ax.text(xi + w / 2, b + 0.15, f"{b:.1f}", ha="center", fontsize=8.5, color=C[0])
ax.axhline(100 / 12, color=INK2, lw=0.8, ls=":")
ax.text(12.6, 100 / 12, "均等なら\n8.3%", va="center", fontsize=8, color=INK2)
ax.set_xticks(x, [f"{m}月" for m in x]); ax.set_ylim(0, 13.5); ax.set_xlim(0.4, 13.4)
ax.set_ylabel("年計に占める割合（%）"); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("図2　月ごとの割合：8月だけが目立って下がった", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.2)
foot(fig)
save(fig, "fig2_monthly_share.png")

# 図3：都道府県 もとの8月の割合と変化
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.scatter(pp.aug_share_early, pp.aug_diff, s=26, color=C[0], alpha=0.85)
for _, r in pp.iterrows():
    if r.pref in ("山梨県", "長野県", "和歌山県", "滋賀県", "東京都", "宮城県", "奈良県", "京都府", "北海道", "沖縄県"):
        ax.annotate(r.pref, (r.aug_share_early, r.aug_diff), xytext=(4, 3), textcoords="offset points", fontsize=8.5, color=INK2)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlabel("2012〜14年平均の8月の割合（%）"); ax.set_ylabel("8月の割合の変化（ポイント）")
ax.grid(color=GRID); ax.set_axisbelow(True)
ax.set_title(f"図3　8月の割合が高かった都道府県ほど下がった（順位相関 {main['H4']['spearman']:.2f}）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.18)
foot(fig, "点は47都道府県。変化＝2023〜25年平均−2012〜14年平均。名前は一部だけ表示。")
save(fig, "fig3_pref_scatter.png")

# 図4：月ごとの増え方（2023〜25年平均÷2012〜14年平均）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
mr = req["month_ratio"]
v = [mr[str(m)] for m in range(1, 13)]
cols = [C[1] if m == 8 else C[0] for m in range(1, 13)]
ax.bar(x, [(t - 1) * 100 for t in v], 0.6, color=cols)
for xi, t in zip(x, v):
    ax.text(xi, (t - 1) * 100 + 0.4, f"+{(t - 1) * 100:.1f}%", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(x, [f"{m}月" for m in x]); ax.set_ylim(0, 24)
ax.set_ylabel("2012〜14年平均からの増え方（%）"); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.set_title("図4　8月も増えたが、ほかの月の方が大きく増えた", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.2)
foot(fig, "2023〜25年平均の月の値 ÷ 2012〜14年平均の月の値 − 1。")
save(fig, "fig4_month_growth.png")
print("figures ok")
