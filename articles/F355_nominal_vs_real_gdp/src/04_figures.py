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
SRC = "出典：内閣府「四半期別GDP速報」（2026年4-6月期2次速報、暦年）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(R / "annual_indicators.csv").set_index("year")
pr = pd.read_csv(R / "period_rates.csv")

# ---- 図1：名目・実質GDP・実質GDI（1994年＝100） ----------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("nominal_idx", "名目GDP", C[1]), ("real_idx", "実質GDP", C[0]), ("real_gdi_idx", "実質GDI（国内総所得）", C[2])]:
    ax.plot(d.index, d[col], color=c, lw=2.2, label=f"{lab}（2025年 {d[col].iloc[-1]:.0f}）")
ax.legend(loc="lower right", frameon=False, fontsize=9.5)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.axvline(2012, color=GRID, lw=1, zorder=0); ax.axvline(2019, color=GRID, lw=1, zorder=0)
ax.text(2003, 133, "名目は横ばい、実質は増加", ha="center", fontsize=9, color=INK2)
ax.text(2022, 133, "名目が実質より\n速く伸びる", ha="center", fontsize=9, color=INK2)
ax.set_xlim(1994, 2025.5); ax.set_ylim(85, 140)
ax.set_ylabel("1994年＝100")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"1994→2025年、名目も実質も{(main['nominal_ratio_2025_1994']-1)*100:.0f}%増。途中の道すじは大きく違う", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：暦年。実質は2020年連鎖価格。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_nominal_real_index.png")

# ---- 図2：デフレーター ------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c, ls in [("defl_gdp", "GDP", C[0], "-"), ("defl_domestic_demand", "国内需要", C[2], "-"), ("defl_exports", "輸出", C[3], "--"), ("defl_imports", "輸入", C[1], "--")]:
    ax.plot(d.index, d[col], color=c, lw=2.2 if ls == "-" else 1.6, ls=ls)
    off = {"defl_gdp": -3.5, "defl_domestic_demand": 2.5, "defl_exports": -3, "defl_imports": 3}[col]
    ax.text(2025.5, d[col].iloc[-1] + off, f"{lab} {d[col].iloc[-1]:.1f}", fontsize=9, color=INK, va="center")
ax.annotate(f"GDP 2013年 {main['defl_gdp_min']:.1f}", (2013, main["defl_gdp_min"]), xytext=(2005, 78), fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(1994, 2031); ax.set_ylim(70, 160)
ax.set_ylabel("デフレーター（2020年＝100）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"GDPデフレーターは1994年{main['defl_gdp_1994']:.1f}→2013年{main['defl_gdp_min']:.1f}→2025年{main['defl_gdp_2025']:.1f}", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：暦年。輸入デフレーターが上がると、GDPデフレーターは下がる向きに働く（輸入は差し引かれるため）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_deflators.png")

# ---- 図3：期間ごとの年率 ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
q = pr.copy()
x = np.arange(len(q)); w = 0.26
for k, (col, lab, c) in enumerate([("nominal_gdp", "名目GDP", C[1]), ("real_gdp", "実質GDP", C[0]), ("defl_gdp", "GDPデフレーター", C[3])]):
    xs = x + (k - 1) * (w + 0.02)
    ax.bar(xs, q[col], width=w, color=c, label=lab)
    for xx, v in zip(xs, q[col]):
        ax.text(xx, v + (0.06 if v >= 0 else -0.06), f"{v:+.2f}".replace("-0.00", "0.00").replace("+0.00", "0.00"), ha="center", va="bottom" if v >= 0 else "top", fontsize=8.6, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{a}〜{b}年" for a, b in zip(q.start, q.end)])
ax.set_ylim(-1.5, 3.2); ax.set_ylabel("年率（%）")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("1994〜2012年は実質＞名目、2019〜2025年は名目が実質を年2.1ポイント上回る", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：年率は対数の差÷年数。名目の年率 ＝ 実質の年率 ＋ デフレーターの年率（ほぼ）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_period_rates.png")

# ---- 図4：交易利得（GDP比） --------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.bar(d.index, d.trading_gains_pct_gdp, width=0.75, color=[C[0] if v >= 0 else C[1] for v in d.trading_gains_pct_gdp])
ax.axhline(0, color=INK2, lw=0.8)
for y in [1994, 2012, 2022, 2025]:
    v = d.loc[y, "trading_gains_pct_gdp"]
    ax.text(y, v + (0.15 if v >= 0 else -0.15), f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.8, color=INK)
r0 = req["rows"][0]
ax.text(2001, -2.4, f"1994→2012年の交易条件の悪化：\n輸出の値段の下がり {r0['export_share']*100:.0f}%、輸入の値段の上がり {r0['import_share']*100:.0f}%", fontsize=9, color=INK)
ax.set_xlim(1993, 2026); ax.set_ylim(-3.8, 4.2)
ax.set_ylabel("実質GDPに対する交易利得（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"交易利得はGDPの{main['tg_pct_1994']:+.1f}%から{main['tg_pct_2025']:+.1f}%へ（実質GDIが実質GDPより伸びなかった分）", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：交易利得は2020年基準の連鎖価格で、輸出入の値段の比（交易条件）の変化による所得の増減。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_trading_gains.png")
print("figures ok")
