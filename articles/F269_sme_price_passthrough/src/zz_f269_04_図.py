"""F269 04 図：figures/ に6枚。業種名は図に出さない（順位づけを避けるため）。"""
import json, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f.replace(" ", "") and "Regular" in f:
        font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); break
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 150})
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(BASE, "data", "processed"); R = os.path.join(BASE, "results"); F = os.path.join(BASE, "figures"); os.makedirs(F, exist_ok=True)
ind = pd.read_csv(os.path.join(P, "industry_passthrough.csv")); tier = pd.read_csv(os.path.join(R, "B_tier.csv"))
m = pd.read_csv(os.path.join(R, "C_industry_negotiation_passthrough.csv")); tk = pd.read_csv(os.path.join(R, "D_tankan_spread.csv"))
main = json.load(open(os.path.join(R, "main.json"), encoding="utf-8"))
C = ["#1f5fa8", "#e07b39", "#3a9d5d", "#b04a8a", "#777777"]
lab = lambda r: r.replace("-03", "年3月").replace("-09", "年9月")

# 図1 全体とコストの種類
tot = ind[ind.industry == "全体"].sort_values("round")
fig, ax = plt.subplots(figsize=(8, 4.6))
for col, name, c in [("total", "コスト全般", C[0]), ("material", "原材料費", C[1]), ("labor", "労務費", C[2]), ("energy", "エネルギー費", C[3])]:
    ax.plot(range(len(tot)), tot[col], marker="o", color=c, lw=2.4 if col == "total" else 1.6, label=name)
    ax.annotate(f"{tot[col].iloc[-1]:.1f}", (len(tot) - 1, tot[col].iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", color=c, fontsize=10)
ax.set_xticks(range(len(tot))); ax.set_xticklabels([lab(r) for r in tot["round"]], rotation=30, ha="right")
ax.set_ylabel("転嫁率（%）"); ax.set_title("図1 価格転嫁率の推移（コスト全般と要素別）"); ax.legend(frameon=False, ncol=4, loc="upper left")
ax.set_ylim(30, 60); fig.tight_layout(); fig.savefig(os.path.join(F, "fig1_overall_by_cost.png")); plt.close()

# 図2 取引段階
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.4, 1]})
d = tier[tier["round"] == "2026-03"].iloc[::-1]
cols = [("full", "10割"), ("p7_9", "9〜7割"), ("p4_6", "6〜4割"), ("p1_3", "3〜1割"), ("zero", "0割"), ("minus", "マイナス")]
cc = ["#1f5fa8", "#5b8fd0", "#a9c4e6", "#f2c9a8", "#e07b39", "#9b2d20"]
left = np.zeros(len(d))
for (k, n), c in zip(cols, cc):
    a1.barh(d.tier, d[k], left=left, color=c, label=n); left += d[k].values
a1.set_xlabel("回答の割合（%、2026年3月）"); a1.legend(frameon=False, ncol=6, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.18))
a1.set_title("図2 取引の段階ごとの転嫁の分布と転嫁率")
for t, c in zip(["1次請け", "2次請け", "3次請け", "4次請け以上"], C):
    x = tier[tier.tier == t].sort_values("round")
    a2.plot([lab(r) for r in x["round"]], x.rate, marker="o", color=c, label=t)
a2.set_ylabel("転嫁率（%）"); a2.legend(frameon=False, fontsize=9); a2.tick_params(axis="x", rotation=30)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig2_tier.png")); plt.close()

# 図3 業種の間の散らばり（名前なし）と取引段階の差
rs = sorted(ind["round"].unique())
fig, ax = plt.subplots(figsize=(8.5, 4.8))
rng = np.random.default_rng(269)
for i, r in enumerate(rs):
    y = ind[(ind["round"] == r) & (ind.industry != "全体")].total
    ax.scatter(i + rng.uniform(-0.12, 0.12, len(y)), y, s=16, color=C[0], alpha=0.55, label="業種（発注企業の業種、1点が1業種）" if i == 0 else None)
    t = tier[tier["round"] == r]
    if len(t):
        ax.plot([i + 0.25] * 2, [t[t.tier == "4次請け以上"].rate.iloc[0], t[t.tier == "1次請け"].rate.iloc[0]], color=C[1], lw=4, label="取引段階の差（4次以上〜1次）" if r == "2024-09" else None)
ax.set_xticks(range(len(rs))); ax.set_xticklabels([lab(r) for r in rs], rotation=30, ha="right")
ax.set_ylabel("転嫁率（%）"); ax.set_title("図3 業種の間の散らばりと、取引の段階の差"); ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(os.path.join(F, "fig3_industry_spread.png")); plt.close()

# 図4 交渉の点と転嫁率（業種単位）
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
d = m[m["round"] == "2026-03"]
a1.scatter(d.score, d.total, color=C[0], s=28)
b = np.polyfit(d.score, d.total, 1); xs = np.linspace(d.score.min(), d.score.max(), 10); a1.plot(xs, np.polyval(b, xs), color=C[1])
h = main["H2"]["industry_level"]["2026-03"]
a1.set_xlabel("価格交渉の平均点（発注企業の業種ごと、−10〜10点）"); a1.set_ylabel("転嫁率（%）")
a1.set_title(f"図4 左：2026年3月の業種（相関 {h['pearson']:.2f}）", fontsize=11)
a = m[m["round"] == "2024-09"].set_index("industry"); bb = m[m["round"] == "2026-03"].set_index("industry"); ci = a.index.intersection(bb.index)
dx, dy = bb.loc[ci, "score"] - a.loc[ci, "score"], bb.loc[ci, "total"] - a.loc[ci, "total"]
a2.scatter(dx, dy, color=C[2], s=28); b = np.polyfit(dx, dy, 1); xs = np.linspace(dx.min(), dx.max(), 10); a2.plot(xs, np.polyval(b, xs), color=C[1])
w = main["H2"]["within_change_2024-09_2026-03"]
a2.set_xlabel("交渉の平均点の変化（2024年9月→2026年3月）"); a2.set_ylabel("転嫁率の変化（ポイント）")
a2.set_title(f"右：同じ業種の変化どうし（相関 {w['pearson']:.2f}）", fontsize=11); a2.axhline(0, color="#bbb", lw=0.8); a2.axvline(0, color="#bbb", lw=0.8)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig4_negotiation.png")); plt.close()

# 図5 短観：販売価格DI − 仕入価格DI
x = tk[tk.industry == "全産業"].copy(); x["t"] = x.year + (x.q - 1) / 4
fig, ax = plt.subplots(figsize=(9, 4.6))
for s, c in [("大企業", C[0]), ("中堅企業", C[3]), ("中小企業", C[1])]:
    y = x[x["size"] == s].sort_values("t"); ax.plot(y.t, y.spread, color=c, label=s, lw=1.8)
ax.axhline(0, color="#999", lw=0.8); ax.axvspan(2021, 2026.75, color="#f3f3f3", zorder=0)
ax.set_ylabel("販売価格DI − 仕入価格DI（ポイント）"); ax.set_title("図5 短観：仕入の値上がりに比べて、売値をどれだけ上げられたか（全産業）")
ax.legend(frameon=False); ax.set_xlim(2010, 2026.9); fig.tight_layout(); fig.savefig(os.path.join(F, "fig5_tankan_spread.png")); plt.close()

# 図6 問い直し：低い業種は追いついたか
w = pd.read_csv(os.path.join(R, "E_industry_wide.csv"), index_col=0)
x0, x1 = w["2023-03"], w["2026-03"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
a1.scatter(x0, x1 - x0, color=C[0], s=28); b = np.polyfit(x0, x1 - x0, 1); xs = np.linspace(x0.min(), x0.max(), 10); a1.plot(xs, np.polyval(b, xs), color=C[1])
a1.set_xlabel("2023年3月の転嫁率（%）"); a1.set_ylabel("2026年3月までの上昇（ポイント）"); a1.set_title("図6 左：最初に低かった業種ほど上がった（共通の27業種）", fontsize=11)
sd = main["reask"]["sd_by_round"]
a2.plot([lab(r) for r in sd], list(sd.values()), marker="o", color=C[2]); a2.set_ylabel("業種の間の標準偏差（ポイント）")
a2.set_title("右：業種の間の散らばり", fontsize=11); a2.tick_params(axis="x", rotation=30); a2.set_ylim(0, 12)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig6_reask_convergence.png")); plt.close()
print(sorted(os.listdir(F)))
