"""F112 04 図（5枚）"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 130})
C1, C2, C3, CG = "#2f6db5", "#d1603d", "#3a9a5b", "#8a8f98"
S = json.load(open(RES / "summary.json", encoding="utf-8"))

# ---- 図1 全国の推移と都道府県のばらつき
tr = pd.read_csv(RES / "national_util_trend.csv")
pv = pd.read_csv(RES / "prefecture_values_anonymous.csv")
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw={"width_ratios": [1.25, 1]})
a = ax[0]
a.bar(tr.year, tr.per_team_per_day, color=C1, alpha=0.75, label="1隊あたりの出動件数（1日）")
a.set_ylabel("1隊あたりの出動件数（件／日）"); a.set_ylim(0, 4.8)
a.set_xticks(tr.year); a.set_xticklabels([str(y) for y in tr.year], rotation=0, fontsize=9)
b = a.twinx(); b.grid(False)
b.fill_between(tr.year, tr.util_R10 * 100, tr.util_R30 * 100, color=C2, alpha=0.18, label="稼働率の目安（R=10〜30分）")
b.plot(tr.year, tr.util_R20 * 100, color=C2, marker="o", label="稼働率の目安（R=20分）")
b.set_ylabel("隊がふさがっている時間の割合（%）", color=C2); b.set_ylim(0, 24)
b.spines["right"].set_visible(True)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = b.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8.5, framealpha=0.9)
a.set_title("全国：救急隊1隊あたりの負担（2015〜2024年）", fontsize=11.5)
a = ax[1]
a.scatter(pv.teams_per_100k, pv.util_base * 100, color=C1, s=28, alpha=0.8)
a.set_xlabel("人口10万人あたりの救急隊数"); a.set_ylabel("隊がふさがっている時間の割合（%）")
a.set_title("47都道府県（名前は出さない）", fontsize=11.5)
a.text(0.97, 0.95, f"相関 {S['pref']['corr_teamsper100k_vs_util']:.2f}", transform=a.transAxes, ha="right", va="top", fontsize=10)
fig.text(0.01, 0.005, "出典：総務省消防庁『令和7年版 救急救助の現況』をもとに作成。稼働率は、出動1件で隊がふさがる時間を仮定して計算した目安（本文参照）", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f112_trend_pref.png"); plt.close(fig)

# ---- 図2 時間帯（10万人の地域、4隊・5隊）
hr = pd.read_csv(RES / "allbusy_by_hour_100k.csv")
import sys
sys.path.insert(0, str(ROOT / "src"))
hourly = pd.read_csv(ROOT / "data" / "hourly_transport_2h.csv")
fac = hourly["合計"] / hourly["合計"].mean()
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.2))
x = hourly["from"] + 1
a = ax[0]
a.bar(x, fac, width=1.7, color=C1, alpha=0.75)
a.axhline(1, color=CG, lw=1, ls="--")
a.set_xticks(range(0, 25, 4)); a.set_xlabel("入電した時刻（時）"); a.set_ylabel("1日平均を1としたときの多さ")
a.set_title("救急要請の多さは時間帯で約4倍ちがう", fontsize=11.5)
a = ax[1]
for c, col in [(4, C2), (5, C1), (3, CG)]:
    d = hr[(hr.c == c) & (hr.dS == 0)]
    a.plot(d.hour_from + 1, d.p * 100, marker="o", color=col, label=f"{c}隊")
a.set_xticks(range(0, 25, 4)); a.set_xlabel("入電した時刻（時）"); a.set_ylabel("全隊が出払っている確率（%）")
a.set_title("人口10万人の地域：全隊出払いは日中に集中", fontsize=11.5)
a.legend(fontsize=9)
fig.text(0.01, 0.005, "左：入電時刻別の搬送人員（令和6年）。右：待ち行列モデル（M/M/c、時間帯・月・曜日で到着率を変えた近似）。隊がふさがる平均時間は約60分と仮定", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f112_hourly.png"); plt.close(fig)

# ---- 図3 隊の数と全隊出払いの確率（人口別）
g = pd.read_csv(RES / "allbusy_by_teams.csv")
fig, ax = plt.subplots(figsize=(8.6, 4.8))
for pop, col, lab in [(50000, C3, "5万人"), (100000, C2, "10万人"), (300000, C1, "30万人")]:
    d = g[(g["pop"] == pop) & (g.psa > 1e-5)]
    ax.plot(d.c, d.psa * 100, marker="o", color=col, label=f"人口{lab}")
    r = S["teams_per_100k"] * pop / 1e5
    ax.axvline(r, color=col, lw=1, ls=":", alpha=0.8)
ax.set_yscale("log"); ax.set_xlabel("救急隊の数"); ax.set_ylabel("119番の時点で全隊が出払っている割合（%、対数）")
ax.set_xlim(0.5, 16.5); ax.set_xticks(range(1, 17))
ax.set_title("全国平均並みの隊数の近くでは、1隊増やすと全隊出払いが5〜7分の1になる", fontsize=11.5)
d = g[g["pop"] == 100000].set_index("c")
for c in [3, 4, 5]:
    ax.annotate(f"{d.loc[c, 'psa'] * 100:.2f}%\n（年{d.loc[c, 'per_year_psa']:.0f}件）", (c, d.loc[c, "psa"] * 100), textcoords="offset points",
                xytext=(8, 4), fontsize=8.5, color=C2)
ax.legend(fontsize=9, loc="upper right")
fig.text(0.01, 0.005, "点線：全国平均の割合（人口10万人あたり4.35隊）をあてはめた隊の数。時間帯・月・曜日の変動を入れた近似（隊がふさがる平均約60分）", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f112_teams.png"); plt.close(fig)

# ---- 図4 1隊の増減と、ふさがる時間の延び（10万人・4隊）
eq = pd.read_csv(RES / "team_vs_time_100k.csv").set_index("c")
e = eq.loc[4]
labs = ["1隊減らす（3隊）", "ふさがる時間\n+10分", "病院収容が\n令和4年並み（47.2分）", "基準\n（4隊・令和6年44.6分）", "病院収容が\n令和元年並み（39.5分）", "1隊増やす（5隊）"]
vals = [e.p_minus1, e.p_plus10min, e.p_2022_hosp, e.p_base, e.p_2019_hosp, e.p_plus1]
cols = [C2, C2, C2, CG, C1, C1]
fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.barh(range(len(vals))[::-1], np.array(vals) * 100, color=cols, alpha=0.85)
for i, v in enumerate(vals):
    ax.text(v * 100 + 0.08, len(vals) - 1 - i, f"{v * 100:.2f}%（年{v * S['rate_per_10k'] * 10:.0f}件）", va="center", fontsize=9)
ax.set_yticks(range(len(vals))[::-1]); ax.set_yticklabels(labs, fontsize=9.5)
ax.set_xlabel("全隊が出払っている割合（%）"); ax.set_xlim(0, 8.2)
ax.set_title(f"人口10万人・4隊：1隊減らすのと同じ悪化は、ふさがる時間が約{e.dS_equiv_minus1team:.0f}分延びたとき", fontsize=11)
fig.text(0.01, 0.005, "年あたりの件数は、出動件数（10万人で年約6,100件）に割合をかけたもの。ふさがる時間＝病院収容所要時間＋引継ぎ後20分（仮定）、不搬送は30分（仮定）", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f112_team_vs_time.png"); plt.close(fig)

# ---- 図5 仮定を変える（10万人・4隊、シミュレーション）
sim = pd.read_csv(RES / "simulation.csv")
name_map = {"base": "基準（対数正規・R=20・N=30）", "dist=exp": "ふさがる時間を指数分布に", "dist=gamma": "ガンマ分布に", "dist=const": "病院収容を一定（44.6分）に",
            "R=10": "引継ぎ後 R=10分", "R=30": "R=30分", "R=40": "R=40分", "N=20": "不搬送 N=20分", "N=40": "N=40分",
            "cv_day=0.1": "日ごとの多さのぶれ 10%", "cv_day=0.2": "ぶれ 20%", "policy=loss": "出払い時は応援に回す（待たない）"}
rows = []
for k, lab in name_map.items():
    d = sim[(sim.scenario == k) & (sim.c == 4) & (sim["pop"] == 100000)]
    if len(d): rows.append((lab, d.p_allbusy.iloc[0], d.psa.iloc[0]))
base = sim[(sim.scenario == "base") & (sim.c == 4) & (sim["pop"] == 100000)].iloc[0]
rows.append(("参考：時間の変動を無視した式（定常）", base.stationary, np.nan))
fig, ax = plt.subplots(figsize=(9.5, 5.2))
y = np.arange(len(rows))[::-1]
ax.barh(y, [r[1] * 100 for r in rows], color=[CG if i == 0 else (C3 if "参考" in r[0] else C1) for i, r in enumerate(rows)], alpha=0.85)
ax.scatter([r[2] * 100 for r in rows], y, color=C2, zorder=3, s=22, label="近似式（時間帯ごとの M/M/c）")
for yi, r in zip(y, rows):
    ax.text(max(r[1], 0 if np.isnan(r[2]) else r[2]) * 100 + 0.06, yi, f"{r[1] * 100:.2f}%", va="center", fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=9)
ax.axvline(base.p_allbusy * 100, color=CG, ls="--", lw=1)
ax.set_xlabel("全隊が出払っている割合（%）"); ax.legend(fontsize=8.5, loc="lower right")
ax.set_title("人口10万人・4隊：どの仮定で答えが動くか（10年分のシミュレーション）", fontsize=11.5)
fig.text(0.01, 0.005, "棒：シミュレーション（時間帯・月・曜日で到着率を変えたポアソン到着、10年分・約6.1万件）。R＝引継ぎ後に次の出動ができるまでの時間、N＝不搬送1件の時間（どちらも仮定）", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f112_robustness.png"); plt.close(fig)
print(sorted(p.name for p in FIG.glob("*.png")))
