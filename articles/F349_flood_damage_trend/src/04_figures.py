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
SRC = "出典：国土交通省「水害統計調査」（令和5年、参考表 表-44・表-45）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(R / "series.csv")
d = d[d.year >= 1946]
dec = pd.read_csv(R / "decades.csv")
T = {r["col"]: r for r in main["trend"]}

# ---- 図1：名目と実質（億円） -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
old = d[d.year < 1961]; new = d[d.year >= 1961]
ax.bar(old.year, old.damage_real2015_oku / 1e4, width=0.8, color="#c9c7c1", label="実質額（平成27年価格）1946〜60年：別の推計")
ax.bar(new.year, new.damage_real2015_oku / 1e4, width=0.8, color=C[0], label="実質額（平成27年価格）1961年〜：水害統計")
ax.plot(new.year, new.damage_nominal_oku / 1e4, color=C[1], lw=1.8, label="名目額（その年の値段）")
for y in [1961, 2004, 2019]:
    v = float(d.loc[d.year == y, "damage_real2015_oku"].iloc[0]) / 1e4
    ax.text(y, v + 0.05, f"{y}年\n{v:.1f}兆円", ha="center", va="bottom", fontsize=8.6, color=INK)
ax.set_xlim(1944, 2025); ax.set_ylim(0, float(d.damage_real2015_oku.max()) / 1e4 * 1.12)
ax.set_ylabel("水害の被害額（兆円）")
ax.legend(loc="upper left", frameon=False, fontsize=8.8, bbox_to_anchor=(0.2, 1.0))
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"名目は年{T['damage_nominal_oku']['ols_pct_per_year']:+.1f}%で増えたが、実質では{T['damage_real2015_oku']['ols_pct_per_year']:+.1f}%でほぼ横ばい（1961〜2023年）", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：1946年以降。1946〜60年は「戦後水害被害額推計」で、1961年以降の「水害統計」とは別の推計。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_nominal_real.png")

# ---- 図2：国民所得に対する割合（対数目盛り） --------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(old.year, old.ratio_real_pct, color="#a3a19b", lw=1.5)
ax.plot(new.year, new.ratio_real_pct, color=C[0], lw=2, marker="o", ms=3.5)
b, a = np.polyfit(new.year, np.log(new.ratio_real_pct), 1)
ax.plot(new.year, np.exp(a + b * new.year), color=C[1], lw=1.6, ls="--")
ax.text(1962, 0.045, f"点線の傾き 年{T['ratio_real_pct']['ols_pct_per_year']:.1f}%\n（95%区間 {T['ratio_real_pct']['boot_ci_low_pct']:.1f}〜{T['ratio_real_pct']['boot_ci_high_pct']:.1f}%）", fontsize=9, color=INK)
ax.set_yscale("log")
ax.set_yticks([0.05, 0.1, 0.2, 0.5, 1, 2, 5]); ax.set_yticklabels(["0.05", "0.1", "0.2", "0.5", "1", "2", "5"])
for y in [1961, 2019, 2023]:
    v = float(d.loc[d.year == y, "ratio_real_pct"].iloc[0])
    if y == 2023:
        ax.annotate(f"{y}年 {v:.2f}%", (y, v), xytext=(2024.5, 0.055), fontsize=8.8, color=INK, ha="right", arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    else:
        ax.text(y + 0.8, v * 1.12, f"{y}年 {v:.2f}%", fontsize=8.8, color=INK, ha="left")
ax.set_xlim(1944, 2026)
ax.set_ylabel("国民所得に対する被害額の割合（%、対数目盛り）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"経済の大きさに対する被害は、1961年の{main['ratio_1961']:.1f}%から2023年の{main['ratio_2023']:.2f}%に", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：灰色は1946〜60年（別の推計）。点線は1961〜2023年の対数の直線。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig2_ratio_to_income.png")

# ---- 図3：10年ごとの平均と中央値（実質、億円） ------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(dec)); w = 0.38
ax.bar(x - w / 2 - 0.01, dec.real_mean / 1e3, width=w, color=C[0], label="平均")
ax.bar(x + w / 2 + 0.01, dec.real_median / 1e3, width=w, color=C[2], label="中央値")
for i, r in dec.iterrows():
    ax.text(i - w / 2, r.real_mean / 1e3 + 0.1, f"{r.real_mean/1e3:.1f}", ha="center", fontsize=8.4, color=INK)
    ax.text(i + w / 2, r.real_median / 1e3 + 0.1, f"{r.real_median/1e3:.1f}", ha="center", fontsize=8.4, color=INK)
ax.set_xticks(x); ax.set_xticklabels([l.replace("〜", "〜\n") + ("（3年）" if n < 10 else "") for l, n in zip(dec.label, dec.n)], fontsize=9)
ax.set_ylabel("1年あたりの実質被害額（千億円、平成27年価格）")
ax.legend(loc="upper right", frameon=False)
ax.set_ylim(0, 9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2011〜20年の平均は1980年代並みだが、中央値は低い。大きな2年が平均を押し上げる", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：1年あたりの実質被害額の、10年ごとの平均と中央値。2021〜23年は3年分。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_decades_mean_median.png")

# ---- 図4：期間ごとの傾き（実質額、年率%、95%区間） ---------------------------------------
w_ = pd.DataFrame(req["windows"])
rows = [dict(window="1961〜2023（本線）", real_ols_pct=T["damage_real2015_oku"]["ols_pct_per_year"], ci_low_pct=T["damage_real2015_oku"]["boot_ci_low_pct"],
             ci_high_pct=T["damage_real2015_oku"]["boot_ci_high_pct"])] + w_[["window", "real_ols_pct", "ci_low_pct", "ci_high_pct"]].to_dict(orient="records")
q = pd.DataFrame(rows)
order = ["1961〜2023（本線）", "1961〜2023（2018・2019年を除く）", "1991〜2023", "1991〜2023（2018・2019年を除く）", "2001〜2023", "2001〜2023（2018・2019年を除く）"]
q = q.set_index("window").loc[order].reset_index()
fig, ax = plt.subplots(figsize=(8.8, 4.9))
yy = np.arange(len(q))[::-1]
for y_, r in zip(yy, q.itertuples()):
    c = C[0] if "除く" not in r.window else C[1]
    ax.plot([r.ci_low_pct, r.ci_high_pct], [y_, y_], color=c, lw=2.2)
    ax.plot([r.real_ols_pct], [y_], "o", color=c, ms=8, mec="#fcfcfb", mew=2)
    ax.text(r.ci_high_pct + 0.25, y_, f"{r.real_ols_pct:+.1f}%（{r.ci_low_pct:+.1f}〜{r.ci_high_pct:+.1f}）", va="center", fontsize=8.8, color=INK)
ax.axvline(0, color=INK2, lw=0.9)
ax.set_yticks(yy); ax.set_yticklabels(q.window, fontsize=9)
ax.set_xlim(-3, 13.5)
ax.set_xlabel("実質被害額の傾き（年率%、点は推定値、線は95%区間）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2001年からなら上向き。ただし2018・2019年を除くと区間は0をまたぐ", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：区間は5年ブロックのブートストラップ（2,000回、種を固定）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.29, right=0.97, top=0.9, bottom=0.17)
save(fig, "fig4_slopes_by_window.png")
print("figures ok")
