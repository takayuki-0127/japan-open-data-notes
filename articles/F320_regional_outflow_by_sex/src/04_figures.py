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
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2 = "#52514e"
SRC1 = "出典：総務省「住民基本台帳人口移動報告」年報 第3-3表（日本人移動者）をもとに作成者が加工して作成"
SRC2 = "出典：総務省「住民基本台帳人口移動報告」年報 第3-3表、「人口推計」第10表（いずれも日本人）をもとに作成者が加工して作成"
NOTE = "地方圏＝東京圏・名古屋圏・大阪圏を除く36道県"
T = pd.read_csv(RES / "chiho_sex_bands.csv").set_index("year")
M = json.load(open(RES / "main.json", encoding="utf-8"))

def save(fig, name, src):
    fig.text(0.01, 0.01, src + "。\n" + NOTE, fontsize=7.2, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 年齢帯ごとの 女−男
fig, ax = plt.subplots(figsize=(8, 4.6))
for k, (b, lab) in enumerate([("15-19", "15〜19歳"), ("20-24", "20〜24歳"), ("25-29", "25〜29歳")]):
    ax.plot(T.index, T[f"女−男_{b}"] / 1000, color=C[k], lw=2, marker="o", ms=4, label=lab)
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_ylabel("転出超過数の女性−男性（千人）"); ax.set_xlabel("年")
ax.text(T.index[0], 0.4, "↑ 女性の方が多く出ていく", fontsize=8.5, color=INK2)
ax.text(T.index[0], -0.9, "↓ 男性の方が多く出ていく", fontsize=8.5, color=INK2, va="top")
ax.set_title("地方圏から出ていく人の女性の多さは、20〜24歳に集まっている", loc="left")
ax.legend(frameon=False, loc="upper right")
fig.subplots_adjust(bottom=0.19, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_sex_gap_by_age.png", SRC1)

# fig2 県別の率（20〜24歳、北から南）
R = pd.read_csv(RES / "pref_rates_20_24_2024_2025.csv").sort_values("pref_code")
fig, ax = plt.subplots(figsize=(8, 9.2))
y = np.arange(len(R))[::-1]
ax.hlines(y, R["男_率_%"], R["女_率_%"], color="#c3c2b7", lw=1.5)
ax.plot(R["男_率_%"], y, "o", color=C[0], ms=6, label="男性", mec="#fcfcfb", mew=1)
ax.plot(R["女_率_%"], y, "o", color=C[1], ms=6, label="女性", mec="#fcfcfb", mew=1)
ax.set_yticks(y, R["県"]); ax.tick_params(axis="y", labelsize=8.5)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_xlabel("20〜24歳の転出超過率（2024・2025年の平均 ÷ 2024年10月の人口、%）")
ax.set_title(f"20〜24歳の転出超過率は、36道県のうち{M['H3']['女の率＞男の率の県数']}で女性の方が高い（北から南の順）", loc="left", fontsize=10.5)
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.1, left=0.1, right=0.98, top=0.95)
save(fig, "fig2_pref_rates_20_24.png", SRC2)

# fig3 女−男（15〜29歳）の推移
fig, ax = plt.subplots(figsize=(8, 4.6))
v = T["女−男_15-29"] / 1000
ax.bar(T.index, v, color=[C[1] if x > 0 else C[0] for x in v], width=0.7, edgecolor="#fcfcfb")
for yy in (2012, 2018, 2025):
    ax.text(yy, v.loc[yy] + (0.25 if v.loc[yy] >= 0 else -0.25), f"{T.loc[yy,'女−男_15-29']:,}", ha="center",
            va="bottom" if v.loc[yy] >= 0 else "top", fontsize=8.5, color=INK2)
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(range(2010, 2026, 2))
ax.set_ylabel("15〜29歳の転出超過数の女性−男性（千人）"); ax.set_xlabel("年")
ax.set_title("女性の多さは2018年まで広がり、その後は縮んでいる", loc="left")
fig.subplots_adjust(bottom=0.19, left=0.1, right=0.98, top=0.9)
save(fig, "fig3_gap_trend.png", SRC1)

# fig4 問い直し：30〜44歳
B4 = pd.read_csv(RES / "requestion_30_44.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(B4.index, B4["女_30_44"] / 1000, color=C[1], lw=2, marker="o", ms=4, label="女性")
ax.plot(B4.index, B4["男_30_44"] / 1000, color=C[0], lw=2, marker="o", ms=4, label="男性")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.text(2013.2, 0.3, "↑ 出ていく方が多い", fontsize=8.5, color=INK2)
ax.text(2013.2, -0.3, "↓ 入ってくる方が多い", fontsize=8.5, color=INK2, va="top")
ax.set_ylabel("30〜44歳の転出超過数（千人）"); ax.set_xlabel("年")
ax.set_title("30〜44歳では、男性は地方圏に入ってくる年が多く、女性は少ない", loc="left")
ax.legend(frameon=False, loc="lower right")
fig.subplots_adjust(bottom=0.19, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_age30_44_by_sex.png", SRC1)
print("figures ok")
