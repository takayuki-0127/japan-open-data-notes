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
SRC = "出典：国土交通省「道路統計年報」、総務省「人口推計」をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
nat = pd.read_csv(R / "national_road_pop.csv").set_index("t")
pf = pd.read_csv(R / "prefecture_road_pop.csv", index_col="code")
pace = pd.read_csv(R / "requestion_pace.csv")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：指数（2008年度当初=100）
s = nat.loc[1990.25:]
base = nat.loc[2008.25]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, c, nm in [("total_km", C[0], "道路の長さ（高速＋一般道路）"), ("pop_thousand", C[1], "人口"), ("m_per_person", C[2], "1人あたりの道路の長さ")]:
    y = s[col] / base[col] * 100
    ax.plot(y.index, y, color=c, lw=2.3, label=nm)
    ax.text(2024.6, y.iloc[-1], f"{y.iloc[-1]:.1f}", fontsize=9, color=c, va="center")
ax.axvline(2008.25, color=INK2, lw=0.8, ls=":")
ax.text(2008.4, 106.6, "人口のピーク（2008年）", fontsize=8.5, color=INK2)
ax.axhline(100, color=INK2, lw=0.6)
ax.set_xlim(1990, 2026.5); ax.set_ylim(88, 108)
ax.set_ylabel("2008年度当初 = 100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.set_title(f"人口が{-main['pop_thousand_pct']:.1f}%減るあいだに、道路は{main['total_km_pct']:.1f}%延び、1人あたりは{main['m_per_person_pct']:.1f}%長くなった", loc="left", fontsize=11.3)
foot(fig, "注：道路は年度当初（2019年からは年度末）の実延長。人口は各年10月1日の値を道路の時点に合わせて直線でつないだ。")
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, "fig1_index_road_pop.png")

# 図2：種類別の増加
inc = main["increase_by_type_km"]
lab = {"expressway_f": "高速自動車国道", "national": "一般国道", "prefectural": "都道府県道", "municipal": "市町村道"}
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ks = ["expressway_f", "national", "prefectural", "municipal"]
ax.bar(range(4), [inc[k] for k in ks], color=[C[3], C[1], C[2], C[0]], width=0.6)
for i, k in enumerate(ks):
    ax.text(i, inc[k] + 300, f"{inc[k]:,.0f}km\n（{main['increase_share_pct'][k]:.1f}%）", ha="center", fontsize=9)
ax.set_xticks(range(4)); ax.set_xticklabels([lab[k] for k in ks])
ax.set_ylim(0, 28000); ax.set_ylabel("2008年度当初→2024年3月末の増加（km）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"増えた{main['total_km_diff']:,.0f}kmのうち、{main['increase_share_pct']['municipal']:.0f}%が市町村道", loc="left", fontsize=11.5)
foot(fig, "注：高速自動車国道は供用延長、ほかは実延長。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.13)
save(fig, "fig2_increase_by_type.png")

# 図3：1年あたりの増加（期間別）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
labs = [f"{int(a)}〜{int(b)}" for a, b in zip(pace.start, pace.end)]
cols = [C[0] if a >= 2008 else "#a9a8a3" for a in pace.start]
ax.bar(range(len(pace)), pace.km_per_year, color=cols, width=0.65)
for i, v in enumerate(pace.km_per_year):
    ax.text(i, v + (150 if v >= 0 else -150), f"{v:,.0f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(len(pace))); ax.set_xticklabels(labs, fontsize=8, rotation=30, ha="right")
ax.set_ylabel("道路の長さの1年あたりの増加（km/年）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"延び方は遅くなり、2019〜2024年は1年あたり{req['pace']['2019-2024']:,}km", loc="left", fontsize=11.5)
foot(fig, "注：各年4月1日ごろの時点の差を年数で割った。1985〜90年と1993年ごろの段差には、集計の範囲や道路の種類の区分の変更が含まれるとみられる（推測）。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.2)
save(fig, "fig3_pace.png")

# 図4：県ごとの人口と道路の伸び
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.scatter(pf.pop_pct, pf.road_pct, s=36, color=C[0], alpha=0.85, edgecolor="white", lw=0.6)
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("人口の増減（2015年10月→2023年10月、%）")
ax.set_ylabel("道路の実延長の増減（2015年4月→2024年3月末、%）")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.text(-10.8, -0.45, f"人口が減った{main['n_pref_pop_decline']}県のうち{main['n_pref_pop_decline_road_up']}県で道路が延びた", fontsize=9, color=INK2)
ax.text(-10.8, -0.65, f"相関係数 {main['corr_pop_road']:.2f}", fontsize=9, color=INK2)
ax.set_title("人口が減った県でも、道路の長さはほぼ同じように延びている", loc="left", fontsize=11.5)
foot(fig, "注：1つの点が1つの都道府県（政令指定都市の分を含む）。")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_pref_scatter.png")
print("ok")
