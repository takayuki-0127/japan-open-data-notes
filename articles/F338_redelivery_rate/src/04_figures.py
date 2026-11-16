"""04 図：fig1〜fig3（PNG、日付などのメタデータなし）。"""
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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK2 = "#52514e"
SRC = "出典：国土交通省「宅配便の再配達率サンプル調査」（各回の報道発表）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
S3 = pd.read_csv(RES / "rate_3sha.csv", index_col=0)
S6 = pd.read_csv(RES / "rate_6sha.csv", index_col=0)


def lab(p):
    return f"{p[2:4]}年{int(p[5:])}月"


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# fig1 総計（3社・6社）
allp = sorted(set(S3.index) | set(S6.index))
x = {p: i for i, p in enumerate(allp)}
fig, ax = plt.subplots(figsize=(8, 4.6))
s = S3["総計"].dropna()
ax.plot([x[p] for p in s.index], s.values, color=C[0], lw=2, marker="o", ms=4, label="大手3社の合計")
s6 = S6["総計"].dropna()
ax.plot([x[p] for p in s6.index], s6.values, color=C[1], lw=2, marker="o", ms=4, label="大手6社の合計（2022年10月から）")
for p in [s.index[0], "2020-04", s.index[-1]]:
    ax.annotate(f"{s[p]:.1f}%", (x[p], s[p]), xytext=((-26, -4) if p == "2020-04" else (0, 8)), textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.annotate(f"{s6.iloc[-1]:.1f}%", (x[s6.index[-1]], s6.iloc[-1]), xytext=(0, -15), textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(range(len(allp))[::2], [lab(p) for p in allp][::2], fontsize=8.5)
ax.set_ylim(0, 20)
ax.set_xlabel("調査の月"); ax.set_ylabel("再配達率（%）")
ax.set_title(f"再配達率は8年半で{-M['drop_pt']:.1f}ポイント下がった（大手3社、{M['r_first']:.1f}% → {M['r_last']:.1f}%）", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_total.png", "毎年4月と10月の1か月の調査。2020年4月は感染症による外出自粛の時期。再配達率＝再配達数÷配達総数（総数と再配達数から計算）。6社は2023年4月〜2024年4月の値がない")

# fig2 地域別（3社、2017年10月〜2024年10月）
fig, ax = plt.subplots(figsize=(8, 4.6))
s3 = S3.loc[:"2024-10"]
xx = np.arange(len(s3))
for a, c in [("都市部", C[0]), ("都市部近郊", C[2]), ("地方", C[3])]:
    ax.plot(xx, s3[a], color=c, lw=2, marker="o", ms=4)
    ax.text(len(s3) - 0.6, s3[a].iloc[-1], f"{a} {s3[a].iloc[-1]:.1f}%", fontsize=8.5, va="center")
ax.set_xticks(xx[::2], [lab(p) for p in s3.index][::2], fontsize=8.5)
ax.set_ylim(0, 20); ax.set_xlim(-0.5, len(s3) + 1.8)
ax.set_xlabel("調査の月"); ax.set_ylabel("再配達率（%）")
ax.set_title("どの地域も下がり、割合では地方の下がり方が大きい", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig2_areas.png", "大手3社。都市部＝東京23区の人口密度が高く単身世帯の割合が高い区、都市部近郊＝東京都郊外、地方＝人口の少ない県の市町村（調査の定義）")

# fig3 2019年4月・2020年4月・2021年4月
fig, ax = plt.subplots(figsize=(8, 4.2))
areas = ["都市部", "都市部近郊", "地方"]
y = np.arange(3)[::-1]
for p, c, mk in [("2019-04", C[0], "o"), ("2020-04", C[1], "D"), ("2021-04", C[2], "s")]:
    ax.scatter(S3.loc[p, areas], y, s=80, color=c, marker=mk, edgecolor="white", linewidth=1.2, zorder=3, label=lab(p))
for yi, a in zip(y, areas):
    v = S3.loc[["2019-04", "2020-04", "2021-04"], a]
    ax.plot([v.min(), v.max()], [yi, yi], color="#b9b7b0", lw=2, zorder=1)
    ax.text(v.max() + 0.3, yi, f"{v['2019-04']:.1f} → {v['2020-04']:.1f} → {v['2021-04']:.1f}%", va="center", fontsize=8.5, color=INK2)
ax.set_yticks(y, areas); ax.grid(axis="y", visible=False); ax.set_xlim(0, 25)
ax.set_xlabel("再配達率（%）")
ax.set_title("外出自粛の2020年4月は、都市部ほど大きく下がった", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.subplots_adjust(bottom=0.2, left=0.13, right=0.98, top=0.9)
save(fig, "fig3_covid.png", "大手3社")
