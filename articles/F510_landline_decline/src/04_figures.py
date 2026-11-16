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
SRC = "出典：総務省「情報通信統計データベース」（加入電話及びISDNの加入数、IP電話利用数、携帯電話・PHSの加入契約数）をもとに作成者が加工して作成"
META = {"Software": None}
fmt = matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
b = pd.read_csv(R / "by_fiscal_year.csv", index_col=0)
b = b.loc[1989:]
comb = b.fixed_total + b.ip_0abj

# ---- 図1 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(b.index, b.fixed_total, color=C[0], lw=2.2, label="加入電話＋ISDN")
ax.plot(b.index, b.ip_0abj, color=C[2], lw=2.2, label="0ABJ-IP電話（市外局番から始まるIP電話）")
ax.plot(comb.index, comb, color=C[1], lw=2.2, ls="--", label="合計（市外局番から始まる固定の番号）")
pk = main["fixed"]["peak_fy"]
ax.annotate(f"{pk}年度末 {main['fixed']['peak']:,.0f}万", (pk, main["fixed"]["peak"]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK)
L = main["last_fy"]
for v, dy in [(b.fixed_total[L], -14), (b.ip_0abj[L], 8), (comb[L], 8)]:
    ax.annotate(f"{v:,.0f}万", (L, v), textcoords="offset points", xytext=(0, dy), ha="center", fontsize=9, color=INK)
ax.set_xlim(1988, 2027.5)
ax.set_ylim(0, 7000)
ax.yaxis.set_major_formatter(fmt)
ax.set_xlabel("年度末（3月末）")
ax.set_ylabel("加入数・番号の数（万）")
ax.legend(frameon=False, loc="lower left", fontsize=9.5)
finish(fig, ax, "加入電話は最高時から8割減。IP電話を足しても25%減")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig1_fixed_lines.png")

# ---- 図2：携帯と固定 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(b.index, b.mobile_phs, color=C[3], lw=2.2, label="携帯電話・PHS")
ax.plot(b.index, b.fixed_total, color=C[0], lw=2.2, label="加入電話＋ISDN")
cy = main["mobile_cross_fy"]
ax.axvline(cy, color=INK2, lw=0.8, ls=":")
ax.text(cy + 0.4, 1500, f"{cy}年度末に携帯が上回る", ha="left", fontsize=9, color=INK2)
ax.annotate(f"{b.mobile_phs[L]:,.0f}万\n（人口の{main['mobile_pen_last_pct']:.0f}%）", (L, b.mobile_phs[L]), textcoords="offset points", xytext=(8, -10), ha="left", va="top", fontsize=9, color=INK)
ax.annotate(f"{b.fixed_total[L]:,.0f}万", (L, b.fixed_total[L]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK)
ax.yaxis.set_major_formatter(fmt)
ax.set_xlim(1988, 2031)
ax.set_xlabel("年度末（3月末）")
ax.set_ylabel("契約数（万）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, f"2025年度末、携帯電話・PHSの契約は加入電話＋ISDNの{main['mobile_over_fixed_last']:.1f}倍")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig2_mobile_vs_fixed.png")

# ---- 図3：前年比 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
yoy_c = (comb / comb.shift(1) - 1) * 100
x = b.loc[2005:]
ax.plot(x.index, x.yoy_fixed_pct, color=C[0], lw=2.2, marker="o", ms=4.5, label="加入電話＋ISDN")
ax.plot(yoy_c.loc[2005:].index, yoy_c.loc[2005:], color=C[1], lw=2.2, marker="o", ms=4.5, label="合計（＋0ABJ-IP電話）")
ax.axhline(0, color=INK2, lw=0.8)
for s_, c_ in [(x.yoy_fixed_pct, C[0]), (yoy_c, C[1])]:
    ax.annotate(f"{s_[L]:.1f}%", (L, s_[L]), textcoords="offset points", xytext=(0, -14 if s_ is x.yoy_fixed_pct else 8), ha="center", fontsize=9, color=INK)
ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(5))
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:.0f}"))
ax.set_xlabel("年度末（3月末）")
ax.set_ylabel("前の年度末からの増減（%）")
ax.set_ylim(-11, 1.5)
ax.legend(frameon=False, loc="center right")
h4 = main["hypotheses"]["H4"]
finish(fig, ax, f"加入電話は2007年度から毎年{-h4['yoy_max']:.1f}〜{-h4['yoy_min']:.1f}%減。番号の合計の減り方は速まった")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig3_yoy_decline.png")

# ---- 図4：期間ごとの置き換わり ----
rp = pd.DataFrame(req["periods"])
fig, ax = plt.subplots(figsize=(8.8, 5.0))
xx = np.arange(len(rp))
wdt = 0.36
ax.bar(xx - wdt / 2 - 0.01, rp.fixed_decrease_per_year, wdt, color=C[0], label="加入電話＋ISDNの減少（年あたり）")
ax.bar(xx + wdt / 2 + 0.01, rp.ip_0abj_increase_per_year, wdt, color=C[2], label="0ABJ-IP電話の増加（年あたり）")
for i, q in rp.iterrows():
    ax.text(i - wdt / 2, q.fixed_decrease_per_year + 6, f"{q.fixed_decrease_per_year:.0f}", ha="center", fontsize=9, color=INK)
    v = q.ip_0abj_increase_per_year
    ax.text(i + wdt / 2, v + (6 if v >= 0 else -18), f"{v:.0f}", ha="center", fontsize=9, color=INK)
    ax.text(i, -60, f"埋めた割合 {q.ratio_pct:.0f}%" if q.ratio_pct >= 0 else "IP電話も減少", ha="center", fontsize=9.2, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xx, [f"{a}→{b_}年度末" for a, b_ in zip(rp.from_fy, rp.to_fy)])
ax.set_ylim(-75, 380)
ax.set_ylabel("年あたりの増減（万）")
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "IP電話による置き換わりは2016年度ごろから細り、2022年度からは止まった")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig4_replacement_by_period.png")
