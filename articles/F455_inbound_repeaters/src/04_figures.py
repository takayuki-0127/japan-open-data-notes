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
SRC = "出典：観光庁「訪日外国人消費動向調査」「インバウンド消費動向調査」（一般客、暦年）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
sh = pd.read_csv(R / "repeat_by_nation_year.csv")
chg = pd.read_csv(R / "repeat_change_by_nation.csv", index_col="nation")
grp = pd.read_csv(R / "requestion_groups.csv")
YRS = [2014, 2015, 2016, 2017, 2018, 2019, 2023, 2024, 2025]


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


def plot_gap(ax, xs, ys, **kw):
    for seg in [[y for y in xs if y <= 2019], [y for y in xs if y >= 2023]]:
        idx = [xs.index(y) for y in seg]
        ax.plot(seg, [ys[i] for i in idx], **kw); kw.pop("label", None)


# 図1：全体
fig, ax = plt.subplots(figsize=(8.8, 4.8))
r2 = [main["overall_repeat"][str(y)] for y in YRS]; h10 = [main["overall_heavy10"][str(y)] for y in YRS]
plot_gap(ax, YRS, r2, color=C[0], lw=2.4, marker="o", label="2回目以上（リピーター）")
plot_gap(ax, YRS, h10, color=C[1], lw=2.2, marker="o", label="10回以上")
for y, v in zip(YRS, r2):
    ax.text(y, v + 1.5, f"{v:.1f}", ha="center", fontsize=8.5, color=C[0])
ax.axvspan(2019.5, 2022.5, color="#a9a8a3", alpha=0.15, lw=0); ax.text(2021, 40, "2020〜22年は\n使わない", ha="center", fontsize=8.5, color=INK2)
ax.set_ylim(0, 80); ax.set_xticks(YRS); ax.set_ylabel("訪日客に占める割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="center left", frameon=False, fontsize=9)
ax.set_title(f"全体のリピーターの割合は{r2[0]:.1f}%（2014年）→{r2[-1]:.1f}%（2025年）で大きくは変わらない", loc="left", fontsize=11.5)
foot(fig)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.12)
save(fig, "fig1_overall.png")

# 図2：国・地域別 2014年と2025年（地域のまとまり順）
ORDER = ["韓国", "台湾", "香港", "中国", "タイ", "シンガポール", "マレーシア", "インドネシア", "フィリピン", "ベトナム", "インド", "英国", "ドイツ", "フランス", "ロシア", "米国", "カナダ", "オーストラリア"]
fig, ax = plt.subplots(figsize=(8.8, 6.0))
ys = np.arange(len(ORDER))[::-1]
for y, c in zip(ys, ORDER):
    a, b = chg.loc[c, "r2014"], chg.loc[c, "r2025"]
    ax.plot([a, b], [y, y], color=C[0] if b > a else C[1], lw=2)
    ax.plot(a, y, "o", color="#a9a8a3", ms=6); ax.plot(b, y, "o", color=C[0] if b > a else C[1], ms=7)
    ax.text(max(a, b) + 1.5, y, f"{b - a:+.0f}", va="center", fontsize=8.5, color=INK2)
ax.set_yticks(ys); ax.set_yticklabels(ORDER, fontsize=9)
for yline in [ys[3] - 0.5, ys[10] - 0.5]:
    ax.axhline(yline, color=GRID, lw=1)
ax.set_xlim(20, 100); ax.set_xlabel("2回目以上（リピーター）の割合（%）　灰色＝2014年、色＝2025年")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"東アジアと東南アジアの一部で上がり、欧米豪で大きく下がった（上がったのは{main['n_up_2014_2025']}/{main['n_nations']}）", loc="left", fontsize=11)
foot(fig, "注：並びは地域のまとまり（東アジア、東南アジア・インド、欧米豪・ロシア）の順で、値の順ではない。数字は2014→2025年の差（ポイント）。")
fig.subplots_adjust(left=0.15, right=0.97, top=0.93, bottom=0.12)
save(fig, "fig2_by_nation.png")

# 図3：地域のまとまりの初めての割合
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for k, c in zip(["東アジア", "東南アジア・インド", "欧米豪"], [C[0], C[2], C[1]]):
    t = grp[grp.group == k].set_index("year")
    plot_gap(ax, YRS, [t.loc[y, "first"] for y in YRS], color=c, lw=2.3, marker="o", label=k)
    ax.text(2025.3, t.loc[2025, "first"], f"{t.loc[2025, 'first']:.1f}", va="center", fontsize=9, color=c)
ax.axvspan(2019.5, 2022.5, color="#a9a8a3", alpha=0.15, lw=0)
ax.set_xticks(YRS); ax.set_xlim(2013.5, 2026.3); ax.set_ylim(0, 75); ax.set_ylabel("初めて来た人（1回目）の割合（%、単純平均）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title(f"欧米豪では初めての人が{req['欧米豪']['first_2014']:.0f}%→{req['欧米豪']['first_2025']:.0f}%、東アジアでは{req['東アジア']['first_2014']:.0f}%→{req['東アジア']['first_2025']:.0f}%", loc="left", fontsize=11.5)
foot(fig, "注：東アジア＝韓国・台湾・香港・中国、東南アジア・インド＝7か国、欧米豪＝英・独・仏・米・加・豪（2014年に区分のない伊・西は除く）。")
fig.subplots_adjust(left=0.09, right=0.95, top=0.91, bottom=0.14)
save(fig, "fig3_first_time_groups.png")

# 図4：10回以上の割合
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ks = ["東アジア", "東南アジア・インド", "欧米豪"]; x = np.arange(3); w = 0.36
a = [req[k]["heavy10_2014"] for k in ks]; b = [req[k]["heavy10_2025"] for k in ks]
ax.bar(x - w / 2, a, width=w, color="#a9a8a3", label="2014年"); ax.bar(x + w / 2, b, width=w, color=C[0], label="2025年")
for xi, v in zip(x - w / 2, a): ax.text(xi, v + 0.5, f"{v:.1f}", ha="center", fontsize=9, color=INK2)
for xi, v in zip(x + w / 2, b): ax.text(xi, v + 0.5, f"{v:.1f}", ha="center", fontsize=9, color=C[0])
ax.set_xticks(x); ax.set_xticklabels(ks); ax.set_ylim(0, 30)
ax.set_ylabel("10回以上来ている人の割合（%、単純平均）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_title("10回以上の「常連」は東アジアで増え、欧米豪で減った", loc="left", fontsize=11.5)
foot(fig, f"注：香港は{req['hongkong_heavy10']['2014']:.1f}%→{req['hongkong_heavy10']['2025']:.1f}%、台湾は{req['taiwan_heavy10']['2014']:.1f}%→{req['taiwan_heavy10']['2025']:.1f}%、韓国は{req['korea_heavy10']['2014']:.1f}%→{req['korea_heavy10']['2025']:.1f}%。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_heavy_repeaters.png")
print("ok")
