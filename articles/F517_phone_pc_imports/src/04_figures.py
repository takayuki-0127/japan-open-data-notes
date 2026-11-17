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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：財務省「貿易統計」（輸入、主要商品別）、日本銀行「外国為替市況」をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
ws = pd.read_csv(R / "world_series.csv")
ph = ws[ws.item == "phones"].set_index("year")

# 図1：電話機の指数
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("value_yen", "輸入額（円）", C[0]), ("unit_yen", "1台あたりの単価（円）", C[1]), ("unit_usd", "1台あたりの単価（ドル）", C[3]), ("qty", "台数", C[2])]:
    v = 100 * ph[col] / ph[col][2017]
    ax.plot(v.index, v, color=c, lw=2.2, marker="o", ms=5, label=lab)
    ax.annotate(f"{v.iloc[-1]:.0f}", (v.index[-1], v.iloc[-1]), textcoords="offset points", xytext=(8, 0), va="center", fontsize=9, color=INK)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(2016.6, 2025.8)
ax.set_xlabel("年")
ax.set_ylabel("指数（2017年＝100）")
ax.legend(frameon=False, loc="upper left")
p = m["phones"]
finish(fig, ax, f"電話機の輸入額は1.91兆円→3.13兆円。台数は{p['2017']['qty_million']:.1f}→{p['2025']['qty_million']:.1f}百万台でほぼ横ばい")
fig.subplots_adjust(left=0.09, right=0.96, top=0.89, bottom=0.15)
save(fig, "fig1_phones_index.png")

# 図2：分け方
dec = m["decomposition"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
labs = [("phones_2017_2025", "電話機"), ("computers_2017_2025", "電算機類\n（含周辺機器）")]
y = np.arange(len(labs))
for i, (k, lab) in enumerate(labs):
    q = dec[k]
    lv = np.log(1 + q["value_change_pct"] / 100)
    parts = [("台数", np.log(1 + q["qty_change_pct"] / 100), C[2]), ("ドル建ての単価", np.log(1 + q["unit_usd_change_pct"] / 100), C[3]),
             ("円安（ドル円）", np.log(1 + q["fx_change_pct"] / 100), C[1])]
    left = 0.0
    for name, v, c in parts:
        sharev = 100 * v / lv
        ax.barh(i, sharev, left=left, color=c, height=0.5, edgecolor="#fcfcfb", lw=2, label=name if i == 0 else None)
        ax.text(left + sharev / 2, i, f"{sharev:.0f}%", ha="center", va="center", fontsize=10, color=INK)
        left += sharev
    ax.text(101, i, f"輸入額 +{q['value_change_pct']:.0f}%", va="center", fontsize=9.5, color=INK)
ax.set_yticks(y, [l for _, l in labs])
ax.set_xlim(0, 122)
ax.invert_yaxis()
ax.set_xlabel("2017→2025年の輸入額の増え方（対数の差）に占める割合（%）")
ax.legend(frameon=False, loc="lower center", ncol=3, bbox_to_anchor=(0.45, 1.0))
ax.set_title(f"増えた分の大半は単価。電話機では円安の分が{dec['phones_2017_2025']['share_fx_in_value_pct']:.0f}%", loc="left", fontsize=12.5, color=INK, pad=30)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.16, right=0.96, top=0.84, bottom=0.15)
save(fig, "fig2_decomposition.png")

# 図3・図4：電算機類 中国と中国以外
q = pd.read_csv(R / "computers_china_vs_other.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(q.index, q.china_qty_share, color=C[0], lw=2.2, marker="o", ms=5, label="台数に占める中国の割合")
ax.plot(q.index, q.china_value_share, color=C[1], lw=2.2, marker="o", ms=5, label="金額に占める中国の割合")
for col in ["china_qty_share", "china_value_share"]:
    for yy in [2017, 2025]:
        ax.annotate(f"{q[col][yy]:.1f}", (yy, q[col][yy]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK)
ax.set_ylim(50, 90)
ax.set_xlabel("年")
ax.set_ylabel("電算機類（含周辺機器）の輸入に占める割合（%）")
ax.legend(frameon=False, loc="lower left")
finish(fig, ax, "電算機類：台数の中国の割合は約77%のまま、金額の割合は2024年から63%に")
fig.subplots_adjust(left=0.09, right=0.96, top=0.89, bottom=0.15)
save(fig, "fig3_computers_china_share.png")

fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(q.index, q.china_unit_yen / 1e4, color=C[0], lw=2.2, marker="o", ms=5, label="中国から")
ax.plot(q.index, q.other_unit_yen / 1e4, color=C[1], lw=2.2, marker="o", ms=5, label="中国以外から")
for col in ["china_unit_yen", "other_unit_yen"]:
    for yy in [2021, 2025]:
        dy = 8 if (col == "china_unit_yen" or yy != 2021) else -16
        ax.annotate(f"{q[col][yy] / 1e4:.1f}万円", (yy, q[col][yy] / 1e4), textcoords="offset points", xytext=(0, dy), ha="center", fontsize=9, color=INK)
ax.set_ylim(0, 7)
ax.set_xlabel("年")
ax.set_ylabel("1台あたりの単価（万円）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, f"中国以外からの電算機類は、1台あたりの単価が2021→2025年に約{q.other_unit_yen[2025] / q.other_unit_yen[2021]:.1f}倍")
fig.subplots_adjust(left=0.09, right=0.96, top=0.89, bottom=0.15)
save(fig, "fig4_computers_unit_price_by_origin.png")
