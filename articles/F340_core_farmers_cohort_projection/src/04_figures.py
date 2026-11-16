"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：農林水産省「農林業センサス」（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}
AGES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
        "65-69", "70-74", "75-79", "80-84", "85+"]
AGEL = ["15〜19", "20〜24", "25〜29", "30〜34", "35〜39", "40〜44", "45〜49", "50〜54", "55〜59", "60〜64",
        "65〜69", "70〜74", "75〜79", "80〜84", "85〜"]
PER = ["2005-10", "2010-15", "2015-20", "2020-25"]
PERL = {"2005-10": "2005→10年", "2010-15": "2010→15年", "2015-20": "2015→20年", "2020-25": "2020→25年"}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
obs = pd.read_csv(R / "observed_metrics.csv", index_col=0)
proj = pd.read_csv(R / "projection_national.csv")

# ---- 図1：実績と推計 -----------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 5.0))
oy = [2005, 2010, 2015, 2020, 2025]
ov = [obs.loc["2005_販売農家", "total"], obs.loc["2010_販売農家", "total"], obs.loc["2015_個人経営体", "total"],
      obs.loc["2020_個人経営体", "total"], obs.loc["2025_個人経営体", "total"]]
ax.plot(oy, np.array(ov) / 1e4, color=INK, lw=2, marker="o", ms=6, zorder=4)
for y, v in zip(oy, ov):
    ax.text(y, v / 1e4 + 7, f"{v/1e4:.0f}", ha="center", fontsize=9.5, color=INK)
lo = proj[proj.rates.isin(PER)].groupby("year").total.min(); hi = proj[proj.rates.isin(PER)].groupby("year").total.max()
yy = [2025] + list(lo.index)
ax.fill_between(yy, [ov[-1] / 1e4] + list(lo.values / 1e4), [ov[-1] / 1e4] + list(hi.values / 1e4), color=C[0], alpha=0.18, lw=0)
mp = proj[proj.rates == "2020-25"].set_index("year").total
ax.plot([2025] + list(mp.index), [ov[-1] / 1e4] + list(mp.values / 1e4), color=C[0], lw=2, ls="--", marker="o", ms=5)
ax.annotate(f"2035年 {lo[2035]/1e4:.0f}〜{hi[2035]/1e4:.0f}万人", xy=(2035, hi[2035] / 1e4), xytext=(2036.5, hi[2035] / 1e4 + 14), fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(2045.3, mp[2045] / 1e4 - 2, f"2045年\n{lo[2045]/1e4:.0f}〜{hi[2045]/1e4:.0f}万人", fontsize=9.5, color=INK, va="top")
ax.text(2006, 40, "実線：実績（2015年までは販売農家、2015年からは個人経営体）\n破線：2020→25年の変化率が続いたときの推計\n帯：2005→10、2010→15、2015→20、2020→25年の変化率で推計した幅",
        fontsize=8.8, color=INK2)
ax.set_xlim(2003, 2049); ax.set_ylim(0, 250)
ax.set_ylabel("基幹的農業従事者（万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("基幹的農業従事者は、2035年に57万〜68万人（2025年は104万人）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：推計は、5歳ごとの年齢の人数が5年後にどれだけ残る・増えるか（コーホート変化率）が続くと仮定したもの。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig1_total_projection.png")

# ---- 図2：年齢の分布 ---------------------------------------------------------
pa = pd.read_csv(R / "projection_by_age.csv", index_col=0)
d = pd.read_csv(ROOT / "data" / "core_workers_by_age.csv")
def obsvec(y, b):
    src = "2025年センサス" if y == 2025 else "累年統計"
    q = d[(d.year == y) & (d.basis == b) & (d.level == "全国") & (d.sex == "計") & (d.source == src)]
    return q.set_index("age").reindex(AGES)["n"].values
series = [("2005年（実績）", obsvec(2005, "販売農家"), C[3], "-"), ("2025年（実績）", obsvec(2025, "個人経営体"), C[0], "-"),
          ("2035年（推計）", pa["2020-25_2035"].values, C[1], "--")]
fig, ax = plt.subplots(figsize=(8.6, 5.0))
x = np.arange(15)
for lab, v, c, ls in series:
    ax.plot(x, v / 1e4, color=c, lw=2, ls=ls, marker="o", ms=5, label=lab)
    k = int(np.argmax(v)); ax.text(x[k], v[k] / 1e4 + 1.2, lab, color=INK, fontsize=9, ha="center")
ax.set_xticks(x, AGEL, rotation=45, fontsize=8.8)
ax.set_xlabel("年齢（歳）"); ax.set_ylabel("人数（万人）")
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("いちばん多い年齢は、2025年の70〜74歳から、2035年は75〜79歳に移る", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：2035年は2020→25年の変化率が続いたときの推計。2005年は販売農家。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.22)
save(fig, "fig2_age_distribution.png")

# ---- 図3：変化率 --------------------------------------------------------------
rt = pd.read_csv(R / "cohort_change_ratios.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.6, 5.0))
x = np.arange(2, 15)   # 25〜29歳から（20〜24歳は新しく加わる人が多く、値が大きいので除く）
for k, c in zip(PER, C):
    ax.plot(x, rt.loc[AGES[2:], k].values, color=c, lw=2, marker="o", ms=5, label=PERL[k])
ax.axhline(1, color=INK2, lw=1)
ax.text(2, 0.93, "1を超える＝同じ生まれ年の人が5年で増えた（新しく加わった）\n1未満＝減った（抜けた）", fontsize=8.8, color=INK2, va="top")
ax.set_xticks(x, ["5年後の年齢\n" + AGEL[2]] + AGEL[3:], fontsize=8.8, rotation=0)
plt.setp(ax.get_xticklabels()[1:], rotation=45)
ax.set_ylabel("コーホート変化率（5年後の人数 ÷ いまの人数）")
ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("60代で新しく加わる人が減り、75歳から先で抜ける人が増えた", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：横軸は5年後の年齢。85〜は「80〜84歳と85歳以上」から「85歳以上」への比。2015年までは販売農家、2015年からは個人経営体。\n" + SRC,
         fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.2)
save(fig, "fig3_cohort_change_ratios.png")

# ---- 図4：問い直し（出入り） ---------------------------------------------------
fb = pd.read_csv(R / "requestion_flow_bands.csv", index_col=0)
bands = ["20〜49歳", "50〜64歳", "65〜74歳", "75歳以上"]
fig, ax = plt.subplots(figsize=(8.6, 5.0))
w = 0.2
x = np.arange(len(bands))
for i, (k, c) in enumerate(zip(PER, C)):
    v = fb.loc[k, bands].values / 1e4
    ax.bar(x + (i - 1.5) * w, v, width=w - 0.02, color=c, label=PERL[k])
for i, k in enumerate(PER):
    v = fb.loc[k, "50〜64歳"] / 1e4
    ax.text(1 + (i - 1.5) * w, v + (0.8 if v >= 0 else -2.5), f"{v:+.1f}", ha="center", fontsize=8.5, color=INK)
    v = fb.loc[k, "75歳以上"] / 1e4
    ax.text(3 + (i - 1.5) * w, v - 2.6, f"{v:.0f}", ha="center", fontsize=8.5, color=INK)
ax.axhline(0, color=INK2, lw=1)
ax.set_xticks(x, [f"5年後に{b}" for b in bands])
ax.set_ylabel("同じ生まれ年の人数の増減（万人、5年間）")
ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_ylim(-46, 12)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("50〜64歳で加わる人は5年で+8.8万人から+1.5万人に減った", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：5年後の年齢ごとに「5年後の人数 − 5年前の同じ生まれ年の人数」を足したもの。農業をやめた人と始めた人の差で、両方の人数は分からない。\n" + SRC,
         fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_flows_by_age.png")
print("figures done")
