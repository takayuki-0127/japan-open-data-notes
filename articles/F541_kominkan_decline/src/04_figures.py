"""図4枚（PNG）。日付などのメタデータは入れない。都道府県は北から南の順に並べる（値の順には並べない）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = pathlib.Path(__file__).resolve().parent.parent
R = BASE / "results"; F = BASE / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cc7", "#e87ba4", "#4fb3c9", "#9a8f7a"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「社会教育調査」をもとに作成者が加工して作成"
META = {"Software": None}
REG = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
nat = pd.read_csv(BASE / "data" / "national.csv", index_col="year")
t = pd.read_csv(R / "pref_changes.csv", index_col="pref")
up = pd.read_csv(R / "users_per_facility.csv")

# 図1 全国の館数と利用者（上下2段）
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.4, 5.8), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
f = nat["facilities_incl_similar"].dropna()
a1.plot(f.index, f.values, color=C[0], lw=2.2, marker="o", ms=3.5)
for y, dy, ha in [(1955, 6, "left"), (1999, 8, "center"), (2024, -14, "right")]:
    a1.annotate(f"{y}年度 {f.loc[y]:,.0f}", (y, f.loc[y]), xytext=(4 if ha == "left" else 0, dy), textcoords="offset points", ha=ha, fontsize=9, color=C[0])
a1.set_ylabel("館数"); a1.set_ylim(0, 40000)
a1.grid(axis="y", color=GRID, lw=0.8)
a2.plot(up.users_fy, up.users_thousand / 1000, color=C[1], lw=2.2, marker="o", ms=3.5)
for y, dy in [(2007, 8), (2020, -14), (2023, 8)]:
    v = up.loc[up.users_fy == y, "users_thousand"].iloc[0] / 1000
    a2.annotate(f"{y}年度 {v:.0f}", (y, v), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=9, color=C[1])
a2.set_ylabel("利用者（百万人、延べ）"); a2.set_ylim(0, 280)
a2.grid(axis="y", color=GRID, lw=0.8); a2.set_xlabel("年度（利用者は年度間）")
a1.set_title("公民館（類似施設を含む）は1999年度から3割減。利用者は2007年度の半分", loc="left", fontsize=12.5, color=INK, pad=12)
fig.text(0.01, 0.045, "注：類似施設は1975年度から調査。2024年度から首長部局の設置する類似施設を調査に加えた。", fontsize=7.8, color=INK2)
fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.98, top=0.91, bottom=0.14, hspace=0.12)
save(fig, "fig1_national_trend.png")

# 図2 本館・分館（類似を除く公民館）と市町村数
h2 = m["H2"]
pref_all = pd.read_csv(BASE / "data" / "pref.csv", index_col="pref").loc["全国"]
yrs = [2002, 2005, 2024]
hon = [pref_all[f"honkan_{y}"] for y in yrs]; bun = [pref_all[f"bunkan_{y}"] for y in yrs]; mun = [pref_all[f"muni_{y}"] for y in yrs]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
x = np.arange(3)
ax.bar(x - 0.2, hon, 0.38, color=C[0], label="本館")
ax.bar(x - 0.2, bun, 0.38, bottom=hon, color=C[6], label="分館")
ax.bar(x + 0.2, mun, 0.38, color="#b9b7b0", label="市（区）町村の数")
for i in range(3):
    ax.text(x[i] - 0.2, hon[i] / 2, f"{hon[i]:,.0f}", ha="center", va="center", color="white", fontsize=9)
    ax.text(x[i] - 0.2, hon[i] + bun[i] / 2, f"{bun[i]:,.0f}", ha="center", va="center", color="white", fontsize=9)
    ax.text(x[i] - 0.2, hon[i] + bun[i] + 250, f"計 {hon[i] + bun[i]:,.0f}", ha="center", fontsize=9.3, color=INK)
    ax.text(x[i] + 0.2, mun[i] + 250, f"{mun[i]:,.0f}", ha="center", fontsize=9.3, color=INK2)
ax.set_xticks(x, [f"{y}年度" for y in yrs]); ax.set_ylim(0, 20000)
ax.set_ylabel("館数・市町村数")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, f"2002→2024年度に本館は{-h2['honkan_pct']:.1f}%減、分館は{-h2['bunkan_pct']:.1f}%減。市町村は{-m['muni']['muni_pct']:.1f}%減")
fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.11)
save(fig, "fig2_honkan_bunkan.png")

# 図3 市町村数の変化と公民館の変化（都道府県、散布図）
fig, ax = plt.subplots(figsize=(8.4, 5.4))
for i, rg in enumerate(REG):
    d = t[t.region == rg]
    ax.scatter(d.muni_chg_pct, d.total_chg_pct, s=34, color=C[i], label=rg, zorder=3)
xs = np.linspace(t.muni_chg_pct.min(), 0, 50)
ys = (np.exp(q["intercept"] + q["slope"] * np.log(1 + xs / 100)) - 1) * 100
ax.plot(xs, ys, color=INK2, lw=1.2, ls="--", label=f"当てはめ（傾き {q['slope']:.2f}）")
ax.plot([-80, 0], [-80, 0], color=GRID, lw=1.2)
ax.text(-62, -66, "市町村と同じ割合で減る線", fontsize=8.5, color=INK2, rotation=33)
ax.set_xlim(-82, 3); ax.set_ylim(-90, 10)  # レビュー：-83.4% の県が枠の外に出ていたので下を広げた
ax.set_xlabel("市（区）町村の数の変化（%、2002→2024年度）"); ax.set_ylabel("公民館の数の変化（%、類似施設を除く）")
ax.grid(color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper left", fontsize=8.5, ncol=3)
finish(fig, ax, f"市町村が大きく減った県ほど公民館も減ったが、関係は弱い（順位相関 {m['H3']['spearman']:.2f}）")
fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.12)
save(fig, "fig3_pref_scatter.png")

# 図4 都道府県別の変化（北から南の順）
fig, ax = plt.subplots(figsize=(8.4, 9.6))
yy = np.arange(len(t))[::-1]
cols = [C[REG.index(r)] for r in t.region]
ax.barh(yy, t.total_chg_pct, color=cols, height=0.7)
ax.scatter(t.muni_chg_pct, yy, marker="|", s=60, color=INK, zorder=3, label="市町村の数の変化")
ax.set_yticks(yy, t.index, fontsize=8.6)
ax.axvline(0, color=INK2, lw=0.8)
ax.axvline(h2["total_pct"], color=INK2, lw=0.8, ls=":")
ax.text(h2["total_pct"] - 0.8, len(t) - 0.3, f"全国 {h2['total_pct']:.1f}%", ha="right", fontsize=8.5, color=INK2)
ax.set_xlabel("2002→2024年度の変化（%）　棒：公民館の数　縦線：市町村の数")
ax.set_xlim(-85, 5); ax.set_ylim(-1, len(t) + 1)
ax.grid(axis="x", color=GRID, lw=0.8)
handles = [plt.Rectangle((0, 0), 1, 1, color=C[i]) for i in range(len(REG))]
ax.legend(handles, REG, frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0), fontsize=8.3, ncol=8, handlelength=1.0, columnspacing=0.8)
finish(fig, ax, "47都道府県のすべてで公民館は減った（北から南の順）")
ax.set_title("47都道府県のすべてで公民館は減った（北から南の順）", loc="left", fontsize=12.5, color=INK, pad=30)
fig.subplots_adjust(left=0.11, right=0.97, top=0.93, bottom=0.07)
save(fig, "fig4_pref_north_south.png")
print("ok")
