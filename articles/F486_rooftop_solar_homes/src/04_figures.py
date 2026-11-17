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
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「住宅・土地統計調査」（2003〜2023年）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
nat = pd.read_csv(R / "national.csv").set_index("year")
tk = pd.read_csv(R / "tatekata_share.csv").set_index("year")
jk = pd.read_csv(R / "jiki_share.csv")
pref = pd.read_csv(R / "prefectures.csv").set_index("pref")

# ---- 図1：全国の割合 ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for col, lab, c in [("share_own", "持ち家", C[1]), ("share_all", "住宅全体", C[0]), ("share_rent", "借家", C[2])]:
    ax.plot(nat.index, nat[col], color=c, lw=2.2, marker="o", ms=5)
    ax.text(2023.5, nat[col].loc[2023], f"{lab} {nat[col].loc[2023]:.2f}%", va="center", fontsize=9.5, color=INK)
for y in [2008, 2013, 2018, 2023]:
    ax.text(y, nat.share_all.loc[y] - 0.55, f"+{main['increment_pt'][str(y)]:.2f}", ha="center", fontsize=8.6, color=INK2)
ax.set_xlim(2002, 2027.5); ax.set_ylim(0, 8.5); ax.set_xticks([2003, 2008, 2013, 2018, 2023])
ax.set_ylabel("太陽光の発電機器のある住宅の割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"住宅全体で{main['share_all']['2003']:.2f}%→{main['share_all']['2023']:.2f}%。5年ごとの増え方は2013年をピークに小さく", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：数字は住宅全体の割合の5年ごとの増分（ポイント）。分母は設備が不詳の住宅も含む住宅の総数。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_national.png")

# ---- 図2：建て方 -------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.7))
yrs = list(tk.index); x = np.arange(len(yrs)); w = 0.26
for k, (col, c) in enumerate([("一戸建", C[1]), ("長屋建", C[3]), ("共同住宅", C[0])]):
    ax.bar(x + (k - 1) * (w + 0.02), tk[col], width=w, color=c, label=col)
    for xi, v in zip(x, tk[col]):
        ax.text(xi + (k - 1) * (w + 0.02), v + 0.12, f"{v:.1f}", ha="center", fontsize=8.4, color=INK)
ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in yrs])
ax.set_ylabel("太陽光の発電機器のある住宅の割合（%）"); ax.set_ylim(0, 10)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"2023年は一戸建て{main['tatekata_share_2023']['一戸建']:.2f}%、共同住宅{main['tatekata_share_2023']['共同住宅']:.2f}%（{main['detached_vs_apartment_2023']:.0f}倍）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：全国。建て方の「その他」は省いた。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_building_type.png")

# ---- 図3：建築の時期（持ち家、2023年） -----------------------------------------------------------------
o = jk[(jk.tenure == "持ち家") & (~jk.period.isin(["総数", "不詳"]))].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.8, 4.8))
cols = [C[1] if p in ["2019年", "2020年", "2021年", "2022年", "2023年1月～9月"] else C[0] for p in o.period]
ax.bar(range(len(o)), o.share, color=cols, width=0.7)
for i, v in enumerate(o.share):
    ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=8.4, color=INK)
ax.axhline(main["own_share_all_2023"], color=INK2, lw=0.8, ls=":")
ax.text(-0.4, main["own_share_all_2023"] + 0.4, f"持ち家全体 {main['own_share_all_2023']:.1f}%", fontsize=8.6, color=INK2)
ax.set_xticks(range(len(o))); ax.set_xticklabels([p.replace("2023年1月～9月", "2023年\n1〜9月").replace("～", "〜\n") for p in o.period], fontsize=8)
ax.set_ylabel("太陽光の発電機器のある住宅の割合（%）"); ax.set_ylim(0, 24)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"持ち家は新しいほど多い。2011年以降に建てた家は{main['own_share_built_2011_2023']:.1f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：2023年10月時点の持ち家を、建てた時期で分けた。オレンジは2019年以降に建てた家。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.2)
save(fig, "fig3_built_period.png")

# ---- 図4：都道府県（持ち家率との関係） ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
C7 = {"北海道": "#6250d6", "東北": C[0], "関東": C[1], "中部": C[2], "近畿": C[3], "中国・四国": "#e87ba4", "九州・沖縄": "#008300"}
for rg, col in C7.items():
    g = pref[pref.region == rg]
    ax.scatter(g.own_rate_2023, g.share_2023, s=42, color=col, alpha=0.9, edgecolors="#fcfcfb", linewidths=0.8, label=f"{rg} {main['region_share_2023'][rg]:.1f}%")
ax.legend(loc="upper left", frameon=False, fontsize=8.6, title="地方（地方全体の割合）", title_fontsize=8.6)
b = np.polyfit(pref.own_rate_2023, pref.share_2023, 1)
xx = np.linspace(pref.own_rate_2023.min(), pref.own_rate_2023.max(), 10)
ax.plot(xx, np.polyval(b, xx), color=INK2, lw=1, ls="--")
ax.set_xlabel("持ち家率（%、2023年）"); ax.set_ylabel("太陽光の発電機器のある住宅の割合（%、2023年）")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"都道府県の差は、持ち家率だけでは説明できない（相関 {main['pref_corr_2023']:.2f}）", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：47都道府県。点線は直線の当てはめ。割合は{main['pref_share_2023_min']:.1f}〜{main['pref_share_2023_max']:.1f}%に分かれる。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_prefectures.png")
print("ok")
