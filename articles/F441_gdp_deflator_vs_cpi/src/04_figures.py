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
SRC = "出典：内閣府「四半期別GDP速報」（2026年4-6月期2次速報、暦年）、総務省「消費者物価指数」（2025年基準、年平均）をもとに作成者が加工して作成"
META = {"Software": None}
d = pd.read_csv(R / "annual_gap_decomposition.csv", index_col=0)
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
per = pd.read_csv(R / "period_annualized.csv").set_index("period")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.4, color=INK2)


# 図1 前年比の2本の線
fig, ax = plt.subplots(figsize=(9, 5)); fig.subplots_adjust(bottom=0.17, top=0.88, left=0.08, right=0.97)
ax.axhline(0, color=INK2, lw=0.8)
ax.plot(d.index, d.cpi, color=C[0], lw=2, marker="o", ms=4, label="消費者物価指数（総合）")
ax.plot(d.index, d.gdp, color=C[1], lw=2, marker="o", ms=4, label="GDP デフレーター")
for y, off, lo in [(2008, (0, 10), False), (2022, (0, -34), True), (2023, (0, 10), False)]:
    ax.annotate(f"{y}年\n差 {d.loc[y,'gap']:+.1f}", (y, min(d.loc[y, 'cpi'], d.loc[y, 'gdp']) if lo else max(d.loc[y, 'cpi'], d.loc[y, 'gdp'])), xytext=off,
                textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.set_ylabel("前年比（%）"); ax.grid(axis="y", color=GRID, lw=0.7); ax.legend(frameon=False, loc="upper left")
ax.set_ylim(-3, 6)
fig.suptitle("図1 消費者物価と GDP デフレーターの前年比（暦年、1995〜2025年）", x=0.01, ha="left", fontsize=12.5)
foot(fig, "差＝消費者物価の前年比 − GDP デフレーターの前年比（%ポイント）。GDP デフレーターは名目÷実質で計算")
save(fig, "fig1_cpi_vs_gdp_deflator.png")

# 図2 差の4段の積み上げ
lab = {"s1_rent": "1 持家の帰属家賃", "s2_formula": "2 指数の作り方と範囲", "s3_nonconsumption": "3 消費以外の国内需要", "s4_trade": "4 輸出入"}
fig, ax = plt.subplots(figsize=(9.5, 5.4)); fig.subplots_adjust(bottom=0.2, top=0.86, left=0.08, right=0.97)
x = d.index.values; pos = np.zeros(len(x)); neg = np.zeros(len(x))
for i, k in enumerate(lab):
    v = d[k].values
    b = np.where(v >= 0, pos, neg)
    ax.bar(x, v, bottom=b, color=C[i], width=0.78, label=lab[k], edgecolor="#fcfcfb", lw=0.8)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(x, d.gap, color="#1f1e1c", lw=1.6, marker="o", ms=4, label="差（合計）")
ax.axhline(0, color=INK2, lw=0.8); ax.grid(axis="y", color=GRID, lw=0.7)
ax.set_ylabel("%ポイント"); ax.legend(frameon=False, ncol=5, fontsize=8.6, loc="upper center", bbox_to_anchor=(0.5, 1.02))
# 割合の表示は4桁の値から丸める（main.json の3桁の値を丸め直すと 76.5→76 になるため）
vs = pd.read_csv(R / "robustness.csv").iloc[0].to_dict()
fig.suptitle(f"図2 差の年ごとの動きの{vs['s4_trade']*100:.0f}%は「輸出入」の段から（1995〜2025年）", x=0.01, ha="left", fontsize=12.5)
foot(fig, "差＝消費者物価（総合）の前年比 − GDP デフレーターの前年比を4段に分けた。4段の和は差に一致する\n"
          f"差の分散への寄与：輸出入 {vs['s4_trade']*100:.0f}%、作り方と範囲 {vs['s2_formula']*100:.0f}%、帰属家賃 {vs['s1_rent']*100:.0f}%、消費以外 {vs['s3_nonconsumption']*100:.0f}%")
save(fig, "fig2_gap_decomposition.png")

# 図3 期間ごとの年率
ps = ["1994-2012", "2012-2019", "2019-2025"]
names = {"cpi": "消費者物価（総合）", "hh": "家計消費デフレーター\n（帰属家賃除く）", "dd": "国内需要デフレーター", "gdp": "GDP デフレーター"}
fig, ax = plt.subplots(figsize=(9, 5)); fig.subplots_adjust(bottom=0.17, top=0.88, left=0.08, right=0.97)
w = 0.2
for i, k in enumerate(names):
    vals = [per.loc[p, k] for p in ps]
    xs = np.arange(len(ps)) + (i - 1.5) * w
    ax.bar(xs, vals, width=w - 0.02, color=C[i], label=names[k].replace("\n", ""))
    for xx, vv in zip(xs, vals):
        ax.text(xx, vv + (0.05 if vv >= 0 else -0.05), f"{vv:+.2f}", ha="center", va="bottom" if vv >= 0 else "top", fontsize=8.2, color=INK2)
ax.set_xticks(range(len(ps))); ax.set_xticklabels(["1994→2012年", "2012→2019年", "2019→2025年"])
ax.axhline(0, color=INK2, lw=0.8); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_ylabel("年率（%）")
ax.legend(frameon=False, fontsize=8.8, ncol=2, loc="upper left")
ax.set_ylim(-1.4, 3.2)
fig.suptitle("図3 1994→2012年は消費者物価だけが高く、2019→2025年は逆に最も低い", x=0.01, ha="left", fontsize=12.5)
foot(fig, "期間の始めと終わりの年平均どうしの年率（幾何平均）")
save(fig, "fig3_period_annualized.png")

# 図4 問い直し：基準改定からの年数と2段目
fig, ax = plt.subplots(figsize=(9, 5.2)); fig.subplots_adjust(bottom=0.21, top=0.88, left=0.08, right=0.97)
dd = d.loc[:2019]; k = dd.index - (dd.index // 5) * 5
ax.scatter(k + (dd.index % 1), dd.s2_formula, color=C[0], s=36, zorder=3, label="1995〜2019年の各年")
d2 = d.loc[2020:]; k2 = d2.index - (d2.index // 5) * 5
ax.scatter(k2, d2.s2_formula, color=C[1], s=36, marker="D", zorder=3, label="2020〜2025年の各年")
for y in [2021, 2022, 2009]:
    kk = y - (y // 5) * 5
    ax.annotate(f"{y}年", (kk, d.loc[y, "s2_formula"]), xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=INK2, va="center")
m = req["mean_by_k_1995_2019"]
ax.plot(list(range(5)), [m[str(i)] for i in range(5)], color=C[0], lw=2, label="1995〜2019年の平均")
ax.axhline(0, color=INK2, lw=0.8); ax.grid(axis="y", color=GRID, lw=0.7)
ax.set_xticks(range(5)); ax.set_xticklabels(["基準の年（0）", "1年目", "2年目", "3年目", "4年目"])
ax.set_ylabel("2段目の差（%ポイント）")
ax.legend(frameon=False, fontsize=8.8, loc="lower left")
fig.suptitle("図4 2段目は基準の改定から年がたつほど大きい、とまでは言えない", x=0.01, ha="left", fontsize=12.5)
foot(fig, f"2段目＝CPI（持家の帰属家賃を除く総合）の前年比 − 家計消費デフレーター（除く帰属家賃）の前年比。\n基準の年：1995・2000・2005・2010・2015・2020・2025年。1995〜2019年の順位相関 {req['spearman_k_1995_2019']:+.2f}（p={req['spearman_p']:.2f}）")
save(fig, "fig4_formula_gap_years_since_base.png")
print("figures done")
