"""04 図：figures/ に PNG を6枚"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
B = pathlib.Path(__file__).resolve().parents[1]
R, F = B / "results", B / "figures"; F.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f or "NotoSansCJKjp-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "savefig.dpi": 160, "svg.hashsalt": "f262"})
CN, CC, CF, INK, INK2 = "#2a78d6", "#8fbbe8", "#eb6834", "#0b0b0b", "#52514e"
M = json.load(open(R / "main.json")); an = pd.read_csv(R / "annual_decomposition.csv"); st = pd.read_csv(R / "standardized.csv")
rob = pd.read_csv(R / "robustness.csv"); ag = pd.read_csv(R / "age_2015_2025.csv"); h3 = pd.read_csv(R / "robustness_h3.csv")
def save(fig, name): fig.savefig(F / name, bbox_inches="tight", metadata={"Software": None}); plt.close(fig)
man = lambda v: f"{v/1e4:,.1f}万"

# 図1：出生数・15〜49歳の女性・合計特殊出生率（2015年=100）
s = st[st.year >= 1975].set_index("year")
wa = pd.read_csv(B / "data" / "processed" / "women_by_age.csv")
est = wa[wa.source.isin(["estimate", "census2025"])].set_index("year"); imp = wa[wa.source == "implied"].set_index("year")
A44 = ["a15", "a20", "a25", "a30", "a35", "a40"]
w44 = pd.concat([imp.loc[imp.index < 2000, A44].sum(axis=1), est[A44].sum(axis=1)]).sort_index()
s["women15_44"] = w44.reindex(s.index)
fig, ax = plt.subplots(figsize=(8.6, 4.6))
for col, lab, c in [("births", "出生数", INK), ("women15_44", "15〜44歳の女性の数", CN), ("tfr_calc", "合計特殊出生率", CF)]:
    v = s[col] / s.loc[2015, col] * 100
    ax.plot(v.index, v.values, marker="o", ms=3, lw=2, color=c, label=lab)
    ax.annotate(f"{v.loc[2025]:.0f}", (2025, v.loc[2025]), xytext=(5, 0), textcoords="offset points", color=c, fontsize=10, va="center")
ax.axhline(100, color=INK2, lw=.8, ls=":")
ax.set_ylabel("2015年＝100"); ax.set_xlim(1974, 2028)
ax.set_title("出生数・15〜44歳の女性の数・合計特殊出生率（2015年＝100）", loc="left", fontsize=12)
ax.legend(frameon=False, loc="upper right")
fig.text(0.01, -0.03, "2004年以前は5年ごと。女性の数は人口推計（1999年以前は出生数÷出生率で逆算）、2025年は国勢調査にもとづく人口。", fontsize=8.5, color=INK2)
save(fig, "fig1_index_births_women_tfr.png")

# 図2：2つの10年の分解
fig, ax = plt.subplots(figsize=(8.6, 3.6))
rows = [("2005→2015年", M["main"]["2005-2015"]), ("2015→2025年", M["main"]["2015-2025"])]
for i, (lab, d) in enumerate(rows):
    y = len(rows) - 1 - i
    neg, pos = 0, 0
    for k, c, nm in [("N", CN, "女性の数"), ("c", CC, "年齢の並び方"), ("f", CF, "年齢別出生率")]:
        v = d[k] / 1e4
        if v < 0: ax.barh(y, v, left=neg, color=c, height=.55, label=nm if i == 0 else None); ax.text(neg + v / 2, y, f"{v:+.1f}", ha="center", va="center", fontsize=9.5, color="white" if k != "c" else INK); neg += v
        else: ax.barh(y, v, left=pos, color=c, height=.55, label=nm if i == 0 else None); ax.text(pos + v / 2, y, f"{v:+.1f}", ha="center", va="center", fontsize=9.5, color="white"); pos += v
    ax.plot(d["dB"] / 1e4, y + .36, marker="v", color=INK, ms=9, zorder=5, label="出生数の増減（合計）" if i == 0 else None)
    ax.text(d["dB"] / 1e4, y + .48, f"合計 {d['dB']/1e4:+.1f}万人（{d['pct']:+.1f}%）", ha="center", fontsize=9.5)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1]); ax.axvline(0, color=INK2, lw=.8)
ax.set_xlabel("出生数の増減への寄与（万人）"); ax.set_ylim(-.5, 1.85)
ax.set_title("出生数の増減を3つに分ける（Das Gupta の分解）", loc="left", fontsize=12)
ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(.5, -.25), fontsize=9.5)
save(fig, "fig2_decomposition_two_decades.png")

# 図3：各年
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = an.y1.values
pos = np.zeros(len(x)); neg = np.zeros(len(x))
for k, c, nm in [("N", CN, "女性の数"), ("c", CC, "年齢の並び方"), ("f", CF, "年齢別出生率")]:
    v = an[k].values / 1e4
    b = np.where(v < 0, neg, pos)
    ax.bar(x, v, bottom=b, color=c, width=.7, label=nm)
    neg = np.where(v < 0, neg + v, neg); pos = np.where(v >= 0, pos + v, pos)
ax.plot(x, an.dB / 1e4, "D", color=INK, ms=6, label="出生数の前年からの増減")
ax.axvspan(2015.5, 2025.5, color="#f2f1ec", zorder=0)
ax.text(2020.5, 4.6, "10年続けて「過去最少」", ha="center", fontsize=10, color=INK2)
ax.axhline(0, color=INK2, lw=.8); ax.set_xticks(x); ax.set_xticklabels([str(v)[2:] if v % 5 else str(v) for v in x], fontsize=9)
ax.set_ylabel("前年からの増減（万人）"); ax.set_ylim(-6.2, 5.4)
ax.set_title("前の年からの出生数の増減と、その内訳（2006〜2025年）", loc="left", fontsize=12)
ax.legend(frameon=False, ncol=2, loc="lower left", fontsize=9.5)
save(fig, "fig3_annual_decomposition.png")

# 図4：年齢別（2015→2025）
fig, ax = plt.subplots(figsize=(8.6, 4.4))
y = np.arange(len(ag))[::-1]
ax.barh(y + .18, ag.pop_effect / 1e4, height=.34, color=CN, label="女性の数と年齢の並び方")
ax.barh(y - .18, ag.rate_effect / 1e4, height=.34, color=CF, label="年齢別出生率")
for yy, r in zip(y, ag.itertuples()):
    ax.text(0.9, yy, f"出生率 {r.rate2015:.1f}→{r.rate2025:.1f}‰　女性 {r.women2015/1e4:.0f}→{r.women2025/1e4:.0f}万人", va="center", fontsize=8.8, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(ag.age + "歳"); ax.axvline(0, color=INK2, lw=.8)
ax.set_xlim(-8.2, 7.5); ax.set_xlabel("2015→2025年の出生数の増減への寄与（万人）")
ax.set_title("どの年齢で減ったか（2015→2025年）", loc="left", fontsize=12)
ax.legend(frameon=False, loc="lower left", fontsize=9.5)
save(fig, "fig4_by_age_2015_2025.png")

# 図5：頑健性（人口の効果の割合）
fig, ax = plt.subplots(figsize=(8.6, 4.6))
r = rob.copy(); r["share"] = r.share_pop * 100; y = np.arange(len(r))[::-1]
ax.scatter(r.share, y, color=[CN if i == 0 else INK2 for i in range(len(r))], s=[70 if i == 0 else 40 for i in range(len(r))], zorder=3)
for yy, v in zip(y, r.share): ax.text(v + 1, yy, f"{v:.0f}%", va="center", fontsize=9.5)
ax.axvline(50, color=CF, lw=1, ls="--"); ax.text(50.6, len(r) - .4, "半分（仮説H1の外れの基準）", color=CF, fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(r.case.str.replace("（人口推計＋2025国勢調査）", ""), fontsize=9)
ax.set_xlim(30, 62); ax.set_xlabel("出生数の減少のうち、女性の数と年齢の並び方で説明できる割合（%）")
ax.set_title("条件を変えても、女性の数で説明できるのは4割台", loc="left", fontsize=12)
save(fig, "fig5_robustness_share.png")

# 図6：問い直し
s = st[st.year >= 2005].set_index("year"); RA = M["reask"]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(s.index, s.births / 1e4, color=INK, lw=2.2, marker="o", ms=3.5, label="実際の出生数")
ax.plot(s.index[s.index >= 2015], s.births_at_2015_rates[s.index >= 2015] / 1e4, color=CN, lw=2, ls="--", label="年齢別出生率が2015年のままなら（女性の数だけが変わる）")
ax.plot(s.index, s.births_at_2025_women / 1e4, color=CF, lw=2, marker="s", ms=3, label="女性の数と年齢の並びを2025年にそろえたら（率だけが変わる）")
for yr in RA["record_actual_2006_2025"]:
    if yr >= 2016: ax.plot(yr, s.births[yr] / 1e4, "v", color=INK, ms=7)
for yr in RA["record_std_women2025"]:
    ax.plot(yr, s.births_at_2025_women[yr] / 1e4, "v", color=CF, ms=8, mec="white")
ax.axhline(s.births_at_2025_women[2005] / 1e4, color=CF, lw=.8, ls=":")
ax.text(2005.3, s.births_at_2025_women[2005] / 1e4 - 2.2, "2005年の水準（2022年はほぼ同じ、差0.2%）", color=CF, fontsize=9)
ax.text(2016.3, 99.5, "率が2015年のままでも、女性の数の減少だけで\n毎年それまでの最少（2014年の100.4万人）を下回る", color=CN, fontsize=9)
ax.set_xticks(range(2005, 2026, 5))
ax.set_ylabel("出生数（万人）"); ax.set_xlim(2004.5, 2025.8); ax.set_ylim(60, 118)
ax.set_title("▼は「それまでで最少」の年。率だけで見ると最少は2023年から（2022年はほぼ並ぶ）", loc="left", fontsize=12)
ax.legend(frameon=False, loc="upper right", fontsize=9, bbox_to_anchor=(1, 1.02))
save(fig, "fig6_reask_record_lows.png")
print(sorted(p.name for p in F.glob("*.png")))
