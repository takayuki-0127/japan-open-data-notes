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
SRC = "出典：総務省「住民基本台帳人口移動報告」をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
yr = pd.read_csv(R / "season_by_year.csv")
I = yr[yr.kind == "inter"].set_index("year"); N = yr[yr.kind == "intra"].set_index("year")
L = pd.read_csv(ROOT / "data" / "long_monthly.csv")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：長期の3〜4月の割合
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(I.index, I.share_mar_apr, color=C[0], lw=2.2, label="都道府県間の移動")
ax.plot(N.index, N.share_mar_apr, color=C[1], lw=2.0, label="都道府県内の移動")
ax.axhline(main["even_share_2months"], color=INK2, lw=0.9, ls=":")
ax.text(1955, main["even_share_2months"] + 0.5, "どの月も同じなら16.7%", fontsize=8.5, color=INK2)
ax.annotate(f"{main['inter_share_max_year']}年 {main['inter_share_max']:.1f}%", (main["inter_share_max_year"], main["inter_share_max"]),
            xytext=(1996, 41.5), fontsize=8.8, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(2025.5, I.share_mar_apr.loc[2025], f"{I.share_mar_apr.loc[2025]:.1f}", fontsize=8.8, color=C[0], va="center")
ax.text(2025.5, N.share_mar_apr.loc[2025], f"{N.share_mar_apr.loc[2025]:.1f}", fontsize=8.8, color=C[1], va="center")
ax.set_ylim(10, 44); ax.set_xlim(1953, 2029)
ax.set_ylabel("1年の移動者のうち3〜4月の割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.set_title("都道府県をまたぐ引っ越しの3〜4月の割合は、1990年代から37%前後のまま", loc="left", fontsize=11.5)
foot(fig, "注：日本人移動者。1954〜2025年。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.13)
save(fig, "fig1_mar_apr_share_long.png")

# 図2：月ごとの割合（都道府県間）2017〜19年平均と2023〜25年平均
X = L[L.kind == "inter"].copy()
X["share"] = X.movers / X.groupby("year").movers.transform("sum") * 100
p = X[X.year.isin([2017, 2018, 2019])].groupby("month").share.mean()
q = X[X.year.isin([2023, 2024, 2025])].groupby("month").share.mean()
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = np.arange(1, 13); w = 0.38
ax.bar(x - w / 2, p, width=w, color="#a9a8a3", label="2017〜19年平均")
ax.bar(x + w / 2, q, width=w, color=C[0], label="2023〜25年平均")
for m_ in [3, 4]:
    ax.text(m_ - w / 2, p[m_] + 0.3, f"{p[m_]:.1f}", ha="center", fontsize=8.5, color=INK2)
    ax.text(m_ + w / 2, q[m_] + 0.3, f"{q[m_]:.1f}", ha="center", fontsize=8.5, color=C[0])
ax.axhline(100 / 12, color=INK2, lw=0.8, ls=":")
ax.set_xticks(x); ax.set_xticklabels([f"{i}月" for i in x])
ax.set_ylabel("1年の移動者に占める割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_title(f"3月の割合は{main['inter_mar_1719']:.1f}%→{main['inter_mar_2325']:.1f}%と上がり、4月は{main['inter_apr_1719']:.1f}%→{main['inter_apr_2325']:.1f}%に下がった", loc="left", fontsize=11.5)
foot(fig, "注：都道府県間の日本人移動者。点線は均等なときの割合（8.3%）。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.13)
save(fig, "fig2_monthly_profile.png")

# 図3：年齢別の3〜4月の割合
K = ["0-14", "15-19", "20-24", "25-29", "30-39", "40-64", "65+"]
lab = ["0〜14歳", "15〜19歳", "20〜24歳", "25〜29歳", "30〜39歳", "40〜64歳", "65歳以上"]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
x = np.arange(len(K))
a19 = [main["age_share"][k]["2019"] for k in K]; a25 = [main["age_share"][k]["2025"] for k in K]
ax.bar(x - w / 2, a19, width=w, color="#a9a8a3", label="2019年")
ax.bar(x + w / 2, a25, width=w, color=C[0], label="2025年")
for xi, v in zip(x + w / 2, a25):
    ax.text(xi, v + 0.6, f"{v:.1f}", ha="center", fontsize=8.5, color=C[0])
ax.axhline(main["age_share"]["total"]["2025"], color=INK2, lw=0.8, ls="--")
ax.text(6.45, main["age_share"]["total"]["2025"] + 0.8, f"全年齢 {main['age_share']['total']['2025']:.1f}%", fontsize=8.5, color=INK2, ha="right")
ax.set_xticks(x); ax.set_xticklabels(lab)
ax.set_ylim(0, 68); ax.set_ylabel("3〜4月の割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_title("15〜24歳は3〜4月への集中がさらに強まり、30代は少し弱まった", loc="left", fontsize=11.5)
foot(fig, "注：都道府県間の移動者（外国人を含む。月報の表番号3-1の全国の合計）。年齢は移動したときの年齢。")
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_age_share.png")

# 図4：シフトシェア
t = pd.read_csv(R / "requestion_shift_share.csv", index_col="age").loc[K]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.bar(x - w / 2, t.within_contrib, width=w, color=C[2], label="年齢ごとの集中の変化の分")
ax.bar(x + w / 2, t.mix_contrib, width=w, color=C[3], label="年齢の構成の変化の分")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(lab)
ax.set_ylabel("全体の3〜4月の割合への寄与（ポイント）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.set_title(f"2019→2025年の変化{req['total_change']:+.2f}：年齢ごとの変化は打ち消し合い（{req['within']:+.2f}）、構成の分が{req['mix']:+.2f}", loc="left", fontsize=11)
foot(fig, "注：都道府県間の移動者（外国人を含む）。構成の分の主な中身は、0〜14歳の移動の割合が減ったこと（家族での引っ越しが減ったとみられる。推測）。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_shift_share.png")
print("ok")
