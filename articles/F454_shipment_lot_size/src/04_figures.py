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
SRC = "出典：国土交通省「全国貨物純流動調査（物流センサス）」（3日間調査）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
lot = pd.read_csv(R / "lot_by_mode.csv", index_col="year")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


Y = [2000, 2005, 2010, 2015, 2021]
# 図1：ロットと件数・重量（2000年=100）
fig, ax = plt.subplots(figsize=(8.8, 5.0))
cnt = np.array([main["count_million"][str(y)] for y in Y]); ton = np.array([main["ton_million"][str(y)] for y in Y]); lt = np.array([main["lot"][str(y)] for y in Y])
for arr, c, nm in [(cnt, C[1], "件数"), (ton, C[2], "重量"), (lt, C[0], "1件あたりの重さ（流動ロット）")]:
    s = arr / arr[0] * 100
    ax.plot(Y, s, color=c, lw=2.4, marker="o", label=nm)
    ax.text(2021.4, s[-1], f"{s[-1]:.0f}", va="center", fontsize=9, color=c)
ax.axhline(100, color=INK2, lw=0.7)
ax.set_xticks(Y); ax.set_xlim(1999, 2023); ax.set_ylim(30, 175)
ax.set_ylabel("2000年 = 100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title(f"件数は{main['count_pct_2000_2021']:+.0f}%、重量は{main['ton_pct_2000_2021']:+.0f}%、1件あたりの重さは{main['lot_pct_2000_2021']:+.0f}%（2000→2021年）", loc="left", fontsize=11.5)
foot(fig, f"注：流動ロットは2000年{main['lot']['2000']:.3f}トン/件、2021年{main['lot']['2021']:.3f}トン/件。調査した3日間の出荷の推計。")
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, "fig1_lot_count_weight.png")

# 図2：輸送機関別のロット（2000年と2021年、対数）
MS = [("宅配便等混載", "宅配便等混載"), ("自家用トラック", "自家用トラック"), ("フェリー", "フェリー"), ("一車貸切", "一車貸切"), ("鉄道コンテナ", "鉄道コンテナ"), ("トレーラー", "トレーラー")]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
x = np.arange(len(MS)); w = 0.38
a = [lot.loc[2000, k] for k, _ in MS]; b = [lot.loc[2021, k] for k, _ in MS]
ax.bar(x - w / 2, a, width=w, color="#a9a8a3", label="2000年"); ax.bar(x + w / 2, b, width=w, color=C[0], label="2021年")
for xi, v in zip(x + w / 2, b):
    ax.text(xi, v * 1.12, f"{v:.3g}", ha="center", fontsize=8.5, color=C[0])
for xi, v in zip(x - w / 2, a):
    ax.text(xi, v * 1.12, f"{v:.3g}", ha="center", fontsize=8.5, color=INK2)
ax.set_yscale("log"); ax.set_ylim(0.02, 60)
ax.set_xticks(x); ax.set_xticklabels([l for _, l in MS], fontsize=9)
ax.set_ylabel("1件あたりの重さ（トン/件、対数目盛）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title("どの運び方でも1件あたりの重さは小さくなった（一車貸切は4.78→2.17トン）", loc="left", fontsize=11.5)
foot(fig)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.13)
save(fig, "fig2_lot_by_mode.png")

# 図3：ロット階層別の件数と重量の割合（2021年）
L = pd.read_csv(R / "lot_classes_share.csv")
l21 = L[L.year == 2021]
lab = ["10kg未満", "10〜50kg", "50〜100kg", "0.1〜0.5t", "0.5〜1t", "1〜3t", "3〜5t", "5〜7t", "7〜10t", "10〜15t", "15〜20t", "20〜30t", "30〜50t", "50〜100t", "100〜500t", "500〜1000t", "1000t以上"]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
x = np.arange(17)
ax.bar(x - w / 2, l21.count_share, width=w, color=C[1], label="件数の割合")
ax.bar(x + w / 2, l21.ton_share, width=w, color=C[2], label="重量の割合")
ax.set_xticks(x); ax.set_xticklabels(lab, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False, fontsize=9)
u = main["under0.1_2021"]
ax.set_title(f"2021年：0.1トン未満の荷物が件数の{u['count_share']:.1f}%、重量では{u['ton_share']:.1f}%", loc="left", fontsize=11.5)
foot(fig, "注：1件あたりの重さの階層ごとの、件数と重量の割合（全業種・全輸送機関）。")
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.25)
save(fig, "fig3_lot_classes_2021.png")

# 図4：業種別のロットの変化（2005→2021年）
inds = ["製造業", "卸売業", "倉庫業", "鉱業"]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = np.arange(len(inds))
ax.bar(x - w / 2, [req[i]["lot_pct"] for i in inds], width=w, color=C[0], label="1件あたりの重さ")
ax.bar(x + w / 2, [req[i]["count_pct"] for i in inds], width=w, color=C[1], label="件数")
for xi, i in zip(x, inds):
    v = req[i]["lot_pct"]; ax.text(xi - w / 2, v - 3, f"{v:.0f}%", ha="center", va="top", fontsize=8.8)
    v = req[i]["count_pct"]; ax.text(xi + w / 2, v + (2 if v >= 0 else -3), f"{v:+.0f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.8)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{i}\n（件数の{req[i]['count_share_2021']:.1f}%）" for i in inds])
ax.set_ylim(-70, 130); ax.set_ylabel("2005→2021年の変化（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_title("倉庫業は件数が2倍を超え、1件あたりの重さは半分に", loc="left", fontsize=11.5)
foot(fig, "注：出荷した事業所の業種別。かっこ内は2021年の件数全体に占める割合。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig4_industry.png")
print("ok")
