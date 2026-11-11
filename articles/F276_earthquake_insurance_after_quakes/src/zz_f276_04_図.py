"""04 図：figures/f276_1〜6.png"""
import json, pathlib, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f276_common import EVENTS
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 150})
C1, C2, GR = "#2b6cb0", "#c05621", "#718096"
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG, PRO = ROOT / "results", ROOT / "figures", ROOT / "data" / "processed"
FIG.mkdir(exist_ok=True)
R = json.loads((RES / "main.json").read_text(encoding="utf-8"))
an = pd.read_csv(PRO / "annual_pref.csv"); nat = an[an.code == 0].set_index("year")
A = pd.read_csv(RES / "A_affected_uplift.csv"); D = pd.read_csv(RES / "A_adjacent_uplift.csv")
B = pd.read_csv(RES / "B_monthly_series.csv"); E = pd.read_csv(RES / "E_reask_base_vs_peak.csv")
lab = {e[0]: f"{e[2][:4]} {e[1]}" for e in EVENTS}

# 1 全国の付帯率と世帯加入率
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(nat.index, nat.futai, color=C1, lw=2.2, label="付帯率（その年度の住宅の火災保険のうち地震保険を付けた割合）")
ax.plot(nat.index, nat.kanyu, color=C2, lw=2.2, label="世帯加入率（年末の地震保険の件数 ÷ 世帯数）")
for e in EVENTS:
    if e[0] in ("E1995", "E2004", "E2011", "E2016", "E2018", "E2024"):
        y = int(e[2][:4]); ax.axvline(y, color=GR, lw=.8, ls=":")
        ax.text(y, 76, e[1].replace("（2024）", "").replace("（2007）", ""), rotation=90, fontsize=8, color=GR, va="top", ha="right")
ax.set_ylim(0, 78); ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("地震保険：全国の付帯率（2001〜2025年度）と世帯加入率（1991〜2025年）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f276_1_national.png"); plt.close(fig)

# 2 被災県の上乗せ（年度）
fig, ax = plt.subplots(figsize=(9, 5))
for _, r in A.iterrows():
    ks = [k for k in range(6) if not pd.isna(r.get(f"U{k}"))]
    ax.plot(ks, [r[f"U{k}"] for k in ks], color=C1, alpha=.35, lw=1)
bal = A.dropna(subset=[f"U{k}" for k in range(6)])
med = [bal[f"U{k}"].median() for k in range(6)]
ax.plot(range(6), med, color=C1, lw=3, label=f"中央値（5年後まで見られる{len(bal)}組）")
ax.axhline(R["placebo"]["p95"], color=C2, ls="--", lw=1.2)
ax.text(5.05, R["placebo"]["p95"], f"地震のない県×年度の\n山の95%点 {R['placebo']['p95']:.1f}", color=C2, fontsize=8, va="center")
ax.axhline(0, color="k", lw=.6)
for _, r in A[A.pref.isin(["福島", "熊本", "宮城"]) & A.event.isin(["E2011", "E2016", "E2003"])].iterrows():
    k = max(k for k in range(6) if not pd.isna(r.get(f"U{k}")))
    ax.text(k + .05, r[f"U{k}"], f"{lab[r.event][:4]} {r.pref}", fontsize=8, color=C1, va="center")
ax.set_xticks(range(6)); ax.set_xticklabels(["地震の年度", "1年後", "2年後", "3年後", "4年後", "5年後"])
ax.set_ylabel("付帯率の上乗せ（ポイント）\n地震の前の年度からの変化 − 遠い県の変化"); ax.set_xlim(-.2, 6.3)
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("被災県の付帯率は、上がったあと戻らなかった", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f276_2_event_study.png"); plt.close(fig)

# 3 山と5年後
x = A.dropna(subset=["U5"])
fig, ax = plt.subplots(figsize=(6.5, 6))
ax.scatter(x.peak, x.U5, color=C1, s=40)
lim = [min(x.peak.min(), x.U5.min()) - 1, max(x.peak.max(), x.U5.max()) + 1]
ax.plot(lim, lim, color=GR, lw=1, ls="--"); ax.text(lim[1] - .3, lim[1] - 1.2, "5年後＝山", color=GR, fontsize=9, ha="right")
ax.plot(lim, [l / 2 for l in lim], color=GR, lw=1, ls=":"); ax.text(lim[1] - .3, lim[1] / 2 - 1.2, "山の半分", color=GR, fontsize=9, ha="right")
for _, r in x.iterrows():
    if abs(r.peak) > 6 or r.U5 > 9:
        ax.text(r.peak + .2, r.U5, f"{r.event[1:5]}{r.pref}", fontsize=8)
ax.axhline(0, color="k", lw=.5); ax.axvline(0, color="k", lw=.5)
ax.set_xlabel("山（地震の年度〜2年後の上乗せの最大、ポイント）"); ax.set_ylabel("5年後の上乗せ（ポイント）")
ax.set_title(f"5年後の上乗せ ÷ 山：中央値 {R['base']['h2_retention_median']:.2f}", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f276_3_retention.png"); plt.close(fig)

# 4 被災県と隣の県
ev = [e for e in A[A.full_peak].event.unique()]
a = A[A.full_peak].groupby("event").peak.median().reindex(ev); d = D[D.full_peak].groupby("event").peak.median().reindex(ev)
fig, ax = plt.subplots(figsize=(9, 4.8)); xs = np.arange(len(ev))
ax.bar(xs - .2, a, .4, color=C1, label="被災県（複数なら中央値）"); ax.bar(xs + .2, d, .4, color=C2, label="隣の県（中央値）")
ax.axhline(0, color="k", lw=.6); ax.set_xticks(xs); ax.set_xticklabels([lab[e] for e in ev], rotation=35, ha="right", fontsize=9)
ax.set_ylabel("山の上乗せ（ポイント）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"隣の県の上がり方は被災県の約{R['base']['h3_ratio']:.1f}倍（中央値どうし）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f276_4_adjacent.png"); plt.close(fig)

# 5 月の新契約の倍率
sel = [("E2011", "宮城"), ("E2011", "福島"), ("E2016", "熊本"), ("E2018", "北海道"), ("E2024", "石川"), ("E2025", "青森")]
fig, ax = plt.subplots(figsize=(9, 5))
cols = plt.cm.tab10(np.linspace(0, 1, 10))
for i, (e, p) in enumerate(sel):
    s = B[(B.event == e) & (B.pref == p)].sort_values("k")
    ax.plot(s.k, s.R, lw=1.8, color=cols[i], label=f"{lab[e]}（{p}）")
ax.axhline(1, color="k", lw=.6); ax.axvline(0, color=GR, lw=.8, ls=":")
ax.set_xlabel("地震の月からの月数"); ax.set_ylabel("新契約の倍率\n（被災県の地震前の年の同じ月比 ÷ 遠い県の同じ比）")
ax.legend(frameon=False, fontsize=8, ncol=2); ax.set_title(f"月の新契約：山は数か月で下がるが、2011年の2県は2年後も高いまま", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f276_5_monthly.png"); plt.close(fig)

# 6 問い直し：地震の前の水準と上がり幅
fig, ax = plt.subplots(figsize=(7, 5.5))
ax.scatter(E.base, E.peak, color=C1, s=40)
b = np.polyfit(E.base, E.peak, 1); xx = np.linspace(E.base.min(), E.base.max(), 50)
ax.plot(xx, np.polyval(b, xx), color=C2, lw=1.5)
for _, r in E.iterrows():
    ax.text(r.base + .6, r.peak, f"{r.event[1:5]}{r.pref}", fontsize=8)
ax.axhline(0, color="k", lw=.5)
ax.set_xlabel("地震の前の年度の付帯率（%）"); ax.set_ylabel("山の上乗せ（ポイント）")
ax.set_title(f"前の付帯率が低い県ほど上がる傾向（順位相関 {R['reask']['spearman']:.2f}、p≈0.13）。19組では偶然と区別できない", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f276_6_base_vs_peak.png"); plt.close(fig)
print("ok", sorted(p.name for p in FIG.glob("*.png")))
