"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f449"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：厚生労働省「賃金構造基本統計調査」（一般労働者、企業規模10人以上、各年6月分）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
g = pd.read_csv(R / "gap_by_year.csv")
L = g[g.kind == "large"].set_index("year"); O = g[g.kind == "other"].set_index("year")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：時間あたり所定内給与の差の推移
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for T, c, nm in [(L, C[0], "営業用大型貨物自動車運転者"), (O, C[1], "営業用の大型以外（普通・小型）")]:
    for seg in [range(2009, 2020), range(2020, 2026)]:
        s = T.loc[list(seg), "gap_hourly_sched_vs_total"]
        ax.plot(s.index, s.values, color=c, lw=2.2, marker="o", ms=3.5, label=nm if seg.start == 2009 else None)
ax.axvline(2019.5, color=INK2, lw=0.8, ls=":")
ax.text(2019.6, -9.5, "2020年に職業分類と\n推計方法が変わった", fontsize=8.5, color=INK2, va="top")
ax.axhline(0, color=INK2, lw=0.8)
for y in [2009, 2019, 2023, 2025]:
    v = L.loc[y, "gap_hourly_sched_vs_total"]
    ax.text(y, v + 1.0, f"{v:.1f}", ha="center", fontsize=8.5, color=C[0])
ax.set_ylim(-30, 0); ax.set_xlim(2008.5, 2025.5)
ax.set_ylabel("産業計（男女計）との差（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title("時間あたりの所定内給与は、産業計より大型で15%前後、大型以外で20%前後低い", loc="left", fontsize=11.5)
foot(fig, "注：所定内給与額 ÷ 所定内実労働時間数。運転者は2019年まで男、2020年から男女計（どちらも9割超が男性）。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_hourly_gap_trend.png")

# 図2：年間の総額・総時間・時間あたり（2025年）
fig, ax = plt.subplots(figsize=(8.8, 4.8))
labels = ["年間の賃金総額", "年間の総労働時間", "時間あたり（総額÷総時間）"]
vl = [main["large"]["gap_annual_pay_2025"], (main["large"]["hours_ratio_2025"] - 1) * 100, main["large"]["gap_hourly_total_2025"]]
vo = [main["other"]["gap_annual_pay_2025"], (main["other"]["hours_ratio_2025"] - 1) * 100, main["other"]["gap_hourly_total_2025"]]
import numpy as np
x = np.arange(3); w = 0.36
for xs, vs, c, nm in [(x - w / 2, vl, C[0], "大型"), (x + w / 2, vo, C[1], "大型以外")]:
    ax.bar(xs, vs, width=w, color=c, label=nm)
    for xi, v in zip(xs, vs):
        ax.text(xi, v + (1 if v >= 0 else -1), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylim(-36, 30); ax.set_ylabel("産業計（男女計）との差（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_title("2025年：年間では7%低いだけの大型も、長く働く分を割ると23%低い", loc="left", fontsize=11.5)
foot(fig, "注：年間の賃金総額 = きまって支給する現金給与額×12 + 年間賞与その他特別給与額。総労働時間 =（所定内＋超過）×12。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig2_annual_vs_hourly_2025.png")

# 図3：比べる相手を替えると（2025年、所定内の時間あたり）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
labels = ["産業計の男女計", "産業計の男", "同じ年齢構成の男"]
vl = [main["large"]["gap_hourly_2025"], main["large"]["gap_male_vs_male_2025"], main["large"]["gap_age_matched_2025"]]
vo = [main["other"]["gap_hourly_2025"], main["other"]["gap_male_vs_male_2025"], main["other"]["gap_age_matched_2025"]]
for xs, vs, c, nm in [(x - w / 2, vl, C[0], "大型"), (x + w / 2, vo, C[1], "大型以外")]:
    ax.bar(xs, vs, width=w, color=c, label=nm)
    for xi, v in zip(xs, vs):
        ax.text(xi, v - 0.8, f"{v:.1f}", ha="center", va="top", fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylim(-36, 2); ax.set_ylabel("時間あたり所定内給与の差（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title("比べる相手を男性・同じ年齢にそろえると、差は27〜30%に広がる", loc="left", fontsize=11.5)
foot(fig, f"注：2025年。「同じ年齢構成の男」は年齢階級ごとの比を運転者の人数で重みづけた平均。運転者の平均年齢は大型{main['large']['drv_age_2025']}歳、産業計は{main['large']['all_age_2025']}歳。")
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig3_comparison_groups_2025.png")

# 図4：超過実労働時間
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for T, c, nm in [(L, C[0], "大型"), (O, C[1], "大型以外")]:
    for seg in [range(2009, 2020), range(2020, 2026)]:
        s = T.loc[list(seg), "drv_ot_hours"]
        ax.plot(s.index, s.values, color=c, lw=2.2, marker="o", ms=3.5, label=nm if seg.start == 2009 else None)
s = L["all_ot_hours"]
ax.plot(s.index, s.values, color=INK2, lw=1.6, ls="--", label="産業計（男女計）")
ax.axvline(2019.5, color=INK2, lw=0.8, ls=":")
ax.axvspan(2023.5, 2025.5, color=C[3], alpha=0.12, lw=0)
ax.text(2025.4, 47, "時間外労働の上限\n（2024年4月〜）", fontsize=8.5, color=INK2, va="top", ha="right")
ax.set_ylim(0, 50); ax.set_xlim(2008.5, 2025.5)
ax.set_ylabel("超過実労働時間（時間／月、6月分）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9, ncol=3)
ax.set_title(f"大型の残業は2022〜23年平均{main['large']['ot_2022_23']:.0f}時間から2024〜25年{main['large']['ot_2024_25']:.0f}時間へ", loc="left", fontsize=11.5)
foot(fig)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.12)
save(fig, "fig4_overtime_hours.png")
print("ok")
