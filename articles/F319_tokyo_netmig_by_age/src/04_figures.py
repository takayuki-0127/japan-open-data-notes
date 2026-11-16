"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(p).exists():
        fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "svg.hashsalt": "f319"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
INK2 = "#52514e"
SRC = "出典：総務省「住民基本台帳人口移動報告」年報 第3-3表（日本人移動者）をもとに作成者が加工して作成"
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
        "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"]
AGEJ = [a.replace("-", "〜").replace("90+", "90〜") for a in AGES]
d = pd.read_csv(ROOT / "data" / "netmig_tokyo_age.csv")
M = json.load(open(RES / "main.json", encoding="utf-8"))

def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

def w(area, sex="総数"):
    q = d[(d.area == area) & (d.nat == "日本人") & (d.sex == sex)]
    return q.pivot(index="year", columns="age", values="net")

# fig1 年齢の形（東京圏、2019・2021・2025）
W = w("東京圏")
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(AGES))
for i, (y, c) in enumerate([(2019, C[0]), (2021, C[1]), (2025, C[2])]):
    ax.plot(x, W.loc[y, AGES] / 1000, color=c, lw=2, marker="o", ms=4, label=f"{y}年")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(x, AGEJ, rotation=45, ha="right")
ax.set_xlabel("移動したときの年齢（5歳階級）"); ax.set_ylabel("転入超過数（千人）")
ax.set_title("東京圏に集まるのは15〜29歳。45歳以上は差し引きで出ていく側", loc="left")
ax.legend(frameon=False)
ax.annotate(f"20〜24歳 {W.loc[2025,'20-24']/1e4:.1f}万人（2025年）", (4, W.loc[2025, "20-24"] / 1000),
            xytext=(7, 70), fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
fig.subplots_adjust(bottom=0.24, left=0.09, right=0.98, top=0.9)
save(fig, "fig1_age_profile.png")

# fig2 年齢帯の積み上げ（東京圏、2010〜2025）
B = pd.read_csv(RES / "bands_by_year.csv")
B = B[(B.area == "東京圏") & (B.sex == "総数")].set_index("year")
bands = ["0-14", "15-19", "20-24", "25-29", "30-44", "45-64", "65+"]
bj = ["0〜14歳", "15〜19歳", "20〜24歳", "25〜29歳", "30〜44歳", "45〜64歳", "65歳以上"]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
yrs = B.index.values
pos = np.zeros(len(yrs)); neg = np.zeros(len(yrs))
for k, (b, lab) in enumerate(zip(bands, bj)):
    v = B[b].values / 1000
    bottom = np.where(v >= 0, pos, neg)
    ax.bar(yrs, v, bottom=bottom, color=C[k], width=0.75, label=lab, edgecolor="#fcfcfb", linewidth=1)
    pos = pos + np.where(v >= 0, v, 0); neg = neg + np.where(v < 0, v, 0)
ax.plot(yrs, B["total"] / 1000, color="#0b0b0b", lw=2, marker="o", ms=4, label="全年齢の合計")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(yrs, [str(y) if y % 5 == 0 or y in (2019, 2021) else "" for y in yrs])
ax.set_ylabel("転入超過数（千人）"); ax.set_xlabel("年")
ax.set_title("2020年以降、東京圏の転入超過は15〜29歳の分だけで全体を上回る", loc="left")
ax.legend(ncol=4, frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.14))
fig.subplots_adjust(bottom=0.3, left=0.09, right=0.98, top=0.9)
save(fig, "fig2_bands_stacked.png")

# fig3 東京都の変化（2019→2021、2019→2025）
T = pd.read_csv(RES / "bands_by_year.csv")
T = T[(T.area == "東京都") & (T.sex == "総数")].set_index("year")
d21 = (T.loc[2021, bands] - T.loc[2019, bands]) / 1000
d25 = (T.loc[2025, bands] - T.loc[2019, bands]) / 1000
fig, ax = plt.subplots(figsize=(8, 4.6))
xx = np.arange(len(bands))
ax.bar(xx - 0.2, d21, width=0.38, color=C[1], label="2019→2021年", edgecolor="#fcfcfb")
ax.bar(xx + 0.2, d25, width=0.38, color=C[0], label="2019→2025年", edgecolor="#fcfcfb")
for i in range(len(bands)):
    ax.text(xx[i] - 0.2, d21.iloc[i] - 1.2, f"{d21.iloc[i]:.1f}", ha="center", va="top", fontsize=8, color=INK2)
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(xx, bj)
ax.set_ylabel("転入超過数の変化（千人）")
ax.set_title(f"東京都のコロナ期の落ち込み（{M['H2']['東京都_変化_2019_2021']/1e4:.1f}万人）の中心は30〜44歳", loc="left")
ax.set_ylim(min(d21.min(), d25.min()) - 6, 4)
ax.legend(frameon=False, loc="lower right")
fig.subplots_adjust(bottom=0.16, left=0.09, right=0.98, top=0.9)
save(fig, "fig3_tokyo_change.png")

# fig4 問い直し：子育ての年齢（0〜14歳＋30〜44歳）の東京都と3県
Q = pd.read_csv(RES / "requestion_within_tokyoken.csv").groupby("year", sort=True).sum(numeric_only=True)
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(Q.index, Q["東京都"] / 1000, color=C[1], lw=2, marker="o", ms=4, label="東京都")
ax.plot(Q.index, Q["3県（東京圏−東京都）"] / 1000, color=C[0], lw=2, marker="o", ms=4, label="埼玉・千葉・神奈川の3県")
ax.plot(Q.index, Q["東京圏"] / 1000, color="#0b0b0b", lw=2, marker="o", ms=4, ls="--", label="東京圏（1都3県の合計）")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xlabel("年"); ax.set_ylabel("0〜14歳と30〜44歳の転入超過数（千人）")
ax.set_title("東京都を出た子育て年齢は、3県が受けとめたのは一部だけ", loc="left")
ax.legend(frameon=False, loc="lower left")
fig.subplots_adjust(bottom=0.16, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_family_within_tokyoken.png")
print("figures ok")
