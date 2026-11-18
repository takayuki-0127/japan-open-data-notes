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
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f475"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID, MUTED = "#0b0b0b", "#52514e", "#e4e3df", "#a3a29c"
SRC = "出典：農林水産省「農業物価統計調査」（令和2年基準、暦年・月の指数）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


A = pd.read_csv(R / "annual_tot.csv")
M = pd.read_csv(R / "monthly_tot_2015_2025.csv")
K = pd.read_csv(R / "contributions_2020base.csv")
E = pd.read_csv(R / "requestion_episodes.csv")

# 図1：交易条件（暦年）
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.axhline(100, color=MUTED, lw=1, ls="--")
ax.plot(A.year, A.tot, color=C[0], lw=2, label="交易条件（農産物総合÷資材総合）")
ax.plot(A.year, A.tot_ex_rice, color=C[1], lw=2, label="米を除いた農産物で作った交易条件")
for y in [2020, 2022, 2025]:
    v = A.loc[A.year == y, "tot"].iloc[0]
    ax.annotate(f"{v:.1f}", (y, v), xytext=(0, 8 if y != 2022 else -16), textcoords="offset points",
                ha="center", fontsize=9, color=INK)
v = A.loc[A.year == 2025, "tot_ex_rice"].iloc[0]
ax.annotate(f"{v:.1f}", (2025, v), xytext=(0, -15), textcoords="offset points", ha="center", fontsize=9, color=INK)
ax.set_xlabel("年（暦年）"); ax.set_ylabel("指数（2020年＝100）")
ax.set_xlim(1994, 2026.5)
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "交易条件は2022年に87.7まで下がり、2025年に109.8へ。米を除くと101.2")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig1_terms_of_trade_annual.png")

# 図2：資材総合の上がり方の寄与（2020→各年）
groups = [("飼料", ["飼料"]), ("肥料", ["肥料"]), ("光熱動力", ["光熱動力"]), ("建築資材", ["建築資材"]),
          ("そのほか", None)]
yrs = list(range(2021, 2026))
Ki = K[(K.group == "inputs") & (K["class"] != "（公表の総合−100）")]
named = [c for _, cl in groups if cl for c in cl]
fig, ax = plt.subplots(figsize=(9, 5.2))
pos = [0.0] * len(yrs); neg = [0.0] * len(yrs)
cols = [C[3], C[2], C[1], C[0], MUTED]
for (lab, cl), col in zip(groups, cols):
    vals = []
    for y in yrs:
        s = Ki[Ki.year == y]
        vals.append(s[s["class"].isin(cl)].points.sum() if cl else s[~s["class"].isin(named)].points.sum())
    bot = [p if v >= 0 else n for v, p, n in zip(vals, pos, neg)]
    ax.bar(yrs, vals, bottom=bot, color=col, width=0.62, label=lab, edgecolor="#fcfcfb", linewidth=1.5)
    pos = [p + max(v, 0) for v, p in zip(vals, pos)]; neg = [n + min(v, 0) for v, n in zip(vals, neg)]
tot = [K[(K.group == "inputs") & (K.year == y) & (K["class"] == "（公表の総合−100）")].points.iloc[0] for y in yrs]
for y, t, p in zip(yrs, tot, pos):
    ax.text(y, p + 0.5, f"+{t:.1f}", ha="center", fontsize=9.5, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(yrs, [f"{y}年" for y in yrs])
ax.set_ylabel("資材総合の2020年からの上がり幅（ポイント）")
ax.legend(frameon=False, ncol=5, loc="upper left", fontsize=9.5)
ax.set_ylim(-3, 30)
finish(fig, ax, "資材の値上がりの多くは飼料・肥料・光熱動力（2023年は上がり幅の77%）")
fig.text(0.01, 0.045, "注：「そのほか」は畜産用動物（2023年は −1.3）などを含む。寄与＝ウエイト×（類の指数−100）÷10000。", fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig2_inputs_contributions.png")

# 図3：月の交易条件（2019〜2025年）
m = M[M.year >= 2019].copy()
x = m.year + (m.month - 1) / 12
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.axhline(100, color=MUTED, lw=1, ls="--")
ax.plot(x, m.tot, color=C[0], lw=2, label="交易条件（月）")
ax.plot(x, m.tot_ex_rice, color=C[1], lw=2, label="米を除いた交易条件（月）")
lo = m.loc[m.tot.idxmin()]
ax.annotate(f"{int(lo.year)}年{int(lo.month)}月 {lo.tot:.1f}", (lo.year + (lo.month - 1) / 12, lo.tot),
            xytext=(10, -4), textcoords="offset points", fontsize=9, color=INK)
s = m[(m.year == 2024) & (m.month == 9)].iloc[0]
ax.annotate("2024年9月から100以上が続く\n（米の指数が大きく上がった月）", (2024 + 8 / 12, s.tot), xytext=(2021.3, 108.5),
            textcoords="data", fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlabel("年"); ax.set_ylabel("指数（2020年＝100）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "月で見ると底は2022年7月。100を超えて続くのは2024年9月から")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig3_terms_of_trade_monthly.png")

# 図4：2008年前後と2021年以降の比較（基準の年＝100）
fig, axes = plt.subplots(1, 2, figsize=(9.6, 5.2), sharey=True)
for ax, (ep, g) in zip(axes, E.groupby("episode", sort=False)):
    ax.axhline(100, color=MUTED, lw=1, ls="--")
    ax.plot(g.k, g.products, color=C[2], lw=2, marker="o", ms=5, label="農産物総合")
    ax.plot(g.k, g.inputs, color=C[3], lw=2, marker="o", ms=5, label="資材総合")
    ax.plot(g.k, g.tot, color=C[0], lw=2, marker="o", ms=5, label="交易条件")
    ax.set_xticks(g.k, [f"{int(y)}" for y in g.year])
    ax.set_title(ep, loc="left", fontsize=11, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for col, c in [("tot", C[0]), ("inputs", C[3]), ("products", C[2])]:
        v = g[col].iloc[-1]
        dy = 0
        if ep.startswith("2008"):
            dy = {"inputs": 5, "products": -5}.get(col, 0)
        ax.annotate(f"{v:.1f}", (5, v), xytext=(6, dy), textcoords="offset points", va="center", fontsize=9, color=INK)
    ax.set_xlim(-0.3, 5.8)
axes[0].set_ylabel("基準の年＝100")
axes[0].legend(frameon=False, loc="upper left", fontsize=9.5)
fig.suptitle("2008年前後は資材の上がり幅が小さく、2010年に一度100へ。今回は資材が下がらず、農産物の値上がりで戻った",
             x=0.01, ha="left", fontsize=11.5, color=INK)
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.95, top=0.84, bottom=0.14, wspace=0.12)
save(fig, "fig4_episodes_2008_vs_2021.png")
print("ok")
