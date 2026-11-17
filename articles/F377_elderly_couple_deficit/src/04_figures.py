"""04_figures.py : 図4枚（PNG）。日付などのメタデータは入れない（オフライン）。"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
F = ROOT / "figures"
F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f377"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a63d2"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「家計調査（家計収支編）」二人以上の世帯 第3-12表、「消費者物価指数」（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
ser = pd.read_csv(R / "series.csv")
fill = pd.read_csv(R / "fill.csv")
ic = pd.read_csv(R / "income_class.csv")
rq = pd.read_csv(R / "requestion.csv")
yrs = ser["year"].to_numpy()

# 図1 不足分の推移
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
ax.plot(yrs, ser["deficit"] / 1e4, color=C[0], lw=2.2, marker="o", ms=3.5, label="不足分（名目）")
ax.plot(yrs, ser["deficit_real2025"] / 1e4, color=C[1], lw=1.6, ls="--", label="不足分（2025年の物価で実質）")
ax.axvline(2017.5, color=INK2, lw=0.8, ls=":")
ax.text(2017.6, 7.3, "2018年1月\n家計簿の改正", fontsize=8.8, color=INK2, va="top")
v17 = main["y2017"]["不足分"]
ax.annotate(f"2017年 {v17/1e4:.2f}万円\n（2019年の報告書が使った年）", xy=(2017, v17 / 1e4), xytext=(2009.3, 6.9),
            fontsize=9.2, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
v20 = main["deficit_2020"]
ax.annotate(f"2020年 {v20/1e4:.2f}万円\n（特別定額給付金の年）", xy=(2020, v20 / 1e4), xytext=(2021.0, 0.5),
            fontsize=9.0, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
v25 = main["deficit_2025"]
ax.text(2025.3, v25 / 1e4, f"{v25/1e4:.2f}", fontsize=9, color=C[0], va="center")
ax.set_xlim(1999.5, 2026.6)
ax.set_ylim(0, 7.8)
ax.set_ylabel("1か月あたり（万円）")
ax.set_xlabel("年")
ax.legend(loc="upper left", frameon=False, fontsize=9.5)
ax.set_title("高齢夫婦無職世帯の毎月の不足分は、約5万円の年もあれば2万円台の年もある", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：不足分＝実支出（消費支出＋税・社会保険料）−実収入。夫65歳以上・妻60歳以上の夫婦のみの無職世帯の年平均。\n" + SRC,
         fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig1_deficit_trend.png")

# 図2 収入と支出（名目）と年金の段差
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
ax.plot(yrs, ser["実支出"] / 1e4, color=C[1], lw=2.2, label="実支出（消費支出＋税・社会保険料）")
ax.plot(yrs, ser["消費支出"] / 1e4, color=C[3], lw=1.5, ls="--", label="うち消費支出")
ax.plot(yrs, ser["実収入"] / 1e4, color=C[0], lw=2.2, label="実収入")
ax.plot(yrs, ser["公的年金給付"] / 1e4, color=C[2], lw=1.5, ls="--", label="うち公的年金給付")
ax.axvspan(2017.5, 2019.5, color="#e8eef7", lw=0)
rr = json.load(open(R / "requestion.json", encoding="utf-8"))["couple_6560"]
ax.annotate(f"公的年金給付が2年で+{rr['pension_change_2017_2019_pct']:.1f}%\n（2001〜2017年の前年比は {rr['pension_yoy_2001_2017_min']:.1f}〜+{rr['pension_yoy_2001_2017_max']:.1f}%）",
            xy=(2019, ser.loc[ser.year == 2019, "公的年金給付"].iloc[0] / 1e4), xytext=(2008.2, 18.6), fontsize=9.0,
            color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(1999.5, 2026)
ax.set_ylim(17.5, 31)
ax.set_ylabel("1か月あたり（万円、名目）")
ax.set_xlabel("年")
ax.legend(loc="upper left", frameon=False, fontsize=9.2, ncol=2)
ax.set_title("2018〜2019年に記録された年金が12.7%増え、不足分が縮んだ", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：網かけは家計簿の改正（2018年1月、口座への入金の欄を新設。2018年は約半数の世帯が新しい家計簿）の切り替えの2年。\n" + SRC,
         fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig2_income_spending.png")

# 図3 埋め方の内訳
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
comp = [("fill_deposit", "預貯金の純減（引き出し−預け入れ）", C[0]), ("fill_insurance", "保険の純受取", C[2]),
        ("fill_cash", "手元の現金の減少（繰入金−繰越金）", C[3]), ("fill_other", "有価証券・借入・その他", "#b9b7b0")]
fill["fill_other2"] = fill["fill_other"] + fill["fill_securities"]
pos = np.zeros(len(fill))
neg = np.zeros(len(fill))
for col, lab, colr in comp:
    v = (fill["fill_other2"] if col == "fill_other" else fill[col]).to_numpy() / 1e4
    b = np.where(v >= 0, pos, neg)
    ax.bar(fill["year"], v, bottom=b, color=colr, width=0.75, label=lab)
    pos = pos + np.where(v >= 0, v, 0)
    neg = neg + np.where(v < 0, v, 0)
ax.plot(fill["year"], fill["deficit"] / 1e4, color=INK, lw=1.8, marker="o", ms=3, label="不足分（棒の合計と一致）")
ax.axhline(0, color=INK2, lw=0.8)
ax.axvline(2017.5, color=INK2, lw=0.8, ls=":")
ax.set_xlim(1999.3, 2025.7)
ax.set_ylim(-6.6, 6.8)
ax.set_ylabel("1か月あたり（万円、名目）")
ax.set_xlabel("年")
ax.legend(loc="lower left", frameon=False, fontsize=8.8, ncol=2)
ax.set_title("2017年までは預貯金の取り崩しが中心。2019年からは家計簿の上で預け入れが上回る", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：家計調査の収支は「実収入＋実収入以外の受取＋繰入金＝実支出＋実支出以外の支払＋繰越金」で釣り合う（各年の差は2円以内）。\n" + SRC,
         fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_fill_breakdown.png")

# 図4 年間収入の区分ごとの不足分（2015〜2025年平均）
p = ic[(ic.year >= 2015) & (ic.year <= 2025)].groupby("group", sort=True)[["実収入", "消費支出", "deficit"]].mean()
order = [("elder_inc_lt250", "年間収入\n250万円未満"), ("elder_inc_250_349", "250〜349万円"),
         ("elder_inc_ge350", "350万円以上"), ("elder_nojob", "（無職世帯の全体）")]
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
x = np.arange(len(order))
wd = 0.27
ax.bar(x - wd, [p.loc[k, "実収入"] / 1e4 for k, _ in order], wd, color=C[0], label="実収入")
ax.bar(x, [p.loc[k, "消費支出"] / 1e4 for k, _ in order], wd, color=C[3], label="消費支出")
ax.bar(x + wd, [p.loc[k, "deficit"] / 1e4 for k, _ in order], wd, color=C[1], label="不足分")
for i, (k, _) in enumerate(order):
    ax.text(i + wd, p.loc[k, "deficit"] / 1e4 + 0.4, f"{p.loc[k, 'deficit']/1e4:.1f}", ha="center", fontsize=9.5, color=INK)
ax.set_xticks(x)
ax.set_xticklabels([l for _, l in order])
ax.set_ylabel("1か月あたり（万円、名目、2015〜2025年の平均）")
ax.legend(loc="upper left", frameon=False, fontsize=9.5)
ax.set_title("不足分は、年間収入が350万円以上の世帯で最も大きい", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：男65歳以上・女60歳以上の者のみからなる無職世帯（二人以上）。区分は年間収入（年金などを含む）。\n" + SRC,
         fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig4_income_class.png")
print("figures ok")
