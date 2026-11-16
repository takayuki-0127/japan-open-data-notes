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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a63d2"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：観光庁「訪日外国人消費動向調査」「インバウンド消費動向調査」（一般客、暦年）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8")); req = json.load(open(R / "requestion.json", encoding="utf-8"))
tab = pd.read_csv(R / "nation_table.csv", index_col="nation")
ss = pd.read_csv(R / "requestion_ryokan_shift_share.csv", index_col=0)
YRS = [2018, 2019, 2023, 2024, 2025]


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1
fig, axs = plt.subplots(1, 2, figsize=(8.8, 4.8), gridspec_kw={"width_ratios": [1, 1.4]})
o = main["overall"]
ax = axs[0]
for seg in [[2018, 2019], [2023, 2024, 2025]]:
    ax.plot(seg, [o["hotel"][str(y)] for y in seg], color=C[0], lw=2.4, marker="o")
for y in [2018, 2025]:
    ax.text(y, o["hotel"][str(y)] + 1.2, f"{o['hotel'][str(y)]:.1f}", ha="center", fontsize=9, color=C[0])
ax.set_ylim(70, 95); ax.set_xticks(YRS); ax.tick_params(axis="x", labelsize=8.5); ax.set_title("ホテル（洋室中心）", fontsize=10.5)
ax.set_ylabel("利用した人の割合（%、複数回答）"); ax.grid(axis="y", color=GRID, lw=0.8)
ax = axs[1]
for it, c, nm in [("ryokan", C[1], "旅館（和室中心）"), ("minpaku", C[2], "有料での住宅宿泊（民泊）"), ("relatives", C[4], "親族・知人宅"), ("guesthouse", C[3], "ユースホステル・ゲストハウス")]:
    for k, seg in enumerate([[2018, 2019], [2023, 2024, 2025]]):
        ax.plot(seg, [o[it][str(y)] for y in seg], color=c, lw=2.2, marker="o", label=nm if k == 0 else None)
    ax.text(2025.25, o[it]["2025"], f"{o[it]['2025']:.1f}", va="center", fontsize=8.8, color=c)
ax.set_ylim(0, 20); ax.set_xticks(YRS); ax.tick_params(axis="x", labelsize=8.5); ax.set_xlim(2017.5, 2026)
ax.grid(axis="y", color=GRID, lw=0.8); ax.legend(loc="lower left", frameon=False, fontsize=8)
fig.suptitle(f"全体ではホテルが{o['hotel']['2018']:.0f}%→{o['hotel']['2025']:.0f}%、旅館は{o['ryokan']['2018']:.1f}%→{o['ryokan']['2025']:.1f}%、民泊は横ばい", x=0.01, ha="left", fontsize=11.5)
foot(fig, "注：2020〜22年は使わない。")
fig.subplots_adjust(left=0.09, right=0.96, top=0.86, bottom=0.13, wspace=0.25)
save(fig, "fig1_overall_lodging.png")

# 図2：旅館 2019年→2025年（地域のまとまり順）
ORDER = ["韓国", "台湾", "香港", "中国", "タイ", "シンガポール", "マレーシア", "インドネシア", "フィリピン", "ベトナム", "インド", "英国", "ドイツ", "フランス", "イタリア", "スペイン", "ロシア", "米国", "カナダ", "オーストラリア"]
fig, ax = plt.subplots(figsize=(8.8, 6.2))
ys = np.arange(len(ORDER))[::-1]
for y, c in zip(ys, ORDER):
    a, b = tab.loc[c, "ryokan_2019"], tab.loc[c, "ryokan_2025"]
    col = C[1] if b < a else C[0]
    ax.plot([a, b], [y, y], color=col, lw=2); ax.plot(a, y, "o", color="#a9a8a3", ms=6); ax.plot(b, y, "o", color=col, ms=7)
    ax.text(max(a, b) + 0.6, y, f"{b - a:+.1f}", va="center", fontsize=8.3, color=INK2)
ax.set_yticks(ys); ax.set_yticklabels(ORDER, fontsize=9)
for yl in [ys[3] - 0.5, ys[10] - 0.5]: ax.axhline(yl, color=GRID, lw=1)
ax.set_xlim(0, 32); ax.set_xlabel("旅館を利用した人の割合（%）　灰色＝2019年、色＝2025年")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"旅館の利用は東アジアで下がり、欧米豪では上がった（下がったのは{main['n_ryokan_down_19_25']}/{main['n_nations']}）", loc="left", fontsize=11)
foot(fig, "注：並びは地域のまとまり（東アジア、東南アジア・インド、欧米豪・ロシア）の順で、値の順ではない。数字は差（ポイント）。")
fig.subplots_adjust(left=0.15, right=0.97, top=0.93, bottom=0.12)
save(fig, "fig2_ryokan_by_nation.png")

# 図3：滞在7日以上と民泊
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.scatter(tab.stay7p_2025, tab.minpaku_2025, s=40, color=C[2], edgecolor="white", lw=0.6)
OFF = {"シンガポール": (-9.5, -1.2), "英国": (0.8, -1.1), "ドイツ": (0.8, -1.0), "オーストラリア": (-12.5, 0.6), "インドネシア": (-11.5, 0.5)}
for c in tab.index:
    dx, dy = OFF.get(c, (0.8, 0.2))
    ax.text(tab.loc[c, "stay7p_2025"] + dx, tab.loc[c, "minpaku_2025"] + dy, c, fontsize=7.8, color=INK2)
k = np.polyfit(tab.stay7p_2025, tab.minpaku_2025, 1); xs = np.linspace(0, 100, 50)
ax.plot(xs, np.polyval(k, xs), color=INK2, lw=1, ls="--")
ax.set_xlim(0, 100); ax.set_ylim(0, 28)
ax.set_xlabel("7日間以上滞在した人の割合（%、2025年）"); ax.set_ylabel("民泊を利用した人の割合（%、2025年）")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"長く滞在する国・地域ほど、民泊を使う人が多い（相関係数 {main['corr_stay7_minpaku_2025']:.2f}）", loc="left", fontsize=11.5)
foot(fig, "注：1つの点が1つの国籍・地域（20）。点線は最小二乗の直線。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_stay_minpaku.png")

# 図4：全体の旅館の割合の変化の分解
labs = ["中国", "香港", "台湾", "韓国", "そのほかの\n国・地域", "訪日客の\n構成の変化"]
vals = [ss.loc["中国", "within"], ss.loc["香港", "within"], ss.loc["台湾", "within"], ss.loc["韓国", "within"],
        float(ss.drop(["中国", "香港", "台湾", "韓国"]).within.sum()), req["mix"]]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.bar(range(6), vals, color=[C[1]] * 4 + [C[0], C[3]], width=0.6)
for i, v in enumerate(vals):
    ax.text(i, v + (0.06 if v >= 0 else -0.06), f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(range(6)); ax.set_xticklabels(labs, fontsize=9)
ax.set_ylim(-2.8, 0.8); ax.set_ylabel("全体の旅館の割合の変化への寄与（ポイント）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"全体の旅館の割合の下がり（{req['change']:+.2f}）は、ほとんど東アジアの4つで説明できる", loc="left", fontsize=11.5)
foot(fig, f"注：2019→2025年。重みは訪日客の居住地の構成比（集計表の全体の列）。東アジア4つの国・地域の中の変化の分の合計は{req['within_ea']:+.2f}。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig4_ryokan_decomposition.png")
print("ok")
