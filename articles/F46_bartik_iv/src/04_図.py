import json, numpy as np, pandas as pd
import statsmodels.api as sm
from common import RES, FIG, DATA, plt

R = json.load(open(RES / "results.json", encoding="utf-8"))
d = pd.read_csv(RES / "municipal_analysis_2016_2021.csv", dtype={"code": str, "pref": str})
C1, C2, C3 = "#2b6cb0", "#c05621", "#718096"

# 図1 第1段階：バーティクと実際の雇用の伸び
fig, ax = plt.subplots(figsize=(7.2, 5))
ax.scatter(d.bartik, d.empg, s=8, alpha=.35, color=C1)
b = np.polyfit(d.bartik, d.empg, 1); xs = np.linspace(d.bartik.min(), d.bartik.max(), 50)
ax.plot(xs, np.polyval(b, xs), color=C2, lw=2)
ax.set_xlabel("産業構成から予測した雇用の伸び（バーティク、%）"); ax.set_ylabel("実際の雇用の伸び 2016→21（%）")
ax.set_title(f"第1段階：予測した伸びと実際の伸び（{len(d)}市区町村）\n県の固定効果つきの F 値 = {R['main_fe']['F']:.1f}", fontsize=11)
ax.axhline(0, color="#ccc", lw=.8); fig.tight_layout(); fig.savefig(FIG / "f46_first_stage.png"); plt.close()

# 図2 OLS と 2SLS
fig, ax = plt.subplots(figsize=(7.2, 4.2))
labs = ["最小二乗法\n（県FEなし）", "2SLS\n（県FEなし）", "最小二乗法\n（県FEあり）", "2SLS\n（県FEあり）"]
vals = [R["main_nofe"]["ols"], R["main_nofe"]["iv"], R["main_fe"]["ols"], R["main_fe"]["iv"]]
for i, (l, v) in enumerate(zip(labs, vals)):
    c = C3 if "最小" in l else C1
    ax.errorbar(i, v[0], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="o", color=c, capsize=6, ms=8)
    ax.text(i + .08, v[0], f"{v[0]:.3f}", va="center", fontsize=9)
ax.axhline(0, color="#999", lw=.8); ax.set_xticks(range(4)); ax.set_xticklabels(labs, fontsize=9)
ax.set_ylabel("転入超過率の変化（%ポイント）")
ax.set_title("雇用の伸び1%ポイントあたりの5年間の転入超過率（95%区間）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f46_ols_vs_iv.png"); plt.close()

# 図3 Rotemberg 重み
rot = pd.read_csv(RES / "rotemberg.csv").sort_values("alpha")
fig, ax = plt.subplots(figsize=(7.2, 5.4))
cols = [C2 if a < 0 else C1 for a in rot.alpha]
ax.barh(rot.industry, rot.alpha, color=cols)
for y, (a, g) in enumerate(zip(rot.alpha, rot.g_pct)):
    ax.text(max(a, 0) + 0.01, y, f"全国の伸び {g:+.1f}%", va="center", ha="left", fontsize=8)
ax.axvline(0, color="#999", lw=.8); ax.set_xlabel("Rotemberg 重み（2SLS の推定値への寄与の割合）")
ax.set_title("2SLS の答えを決めている産業はどれか", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f46_rotemberg.png"); plt.close()

# 図4 頑健性（期間・基準年・分類を変えた推定）
rb = pd.read_csv(RES / "robustness.csv")
fig, ax = plt.subplots(figsize=(7.2, 5.6))
y = np.arange(len(rb))[::-1]
ax.errorbar(rb.IV, y, xerr=[rb.IV - rb.IV下, rb.IV上 - rb.IV], fmt="o", color=C1, capsize=4, label="2SLS")
ax.scatter(rb.OLS, y + .25, color=C3, s=18, label="最小二乗法")
ax.set_yticks(y); ax.set_yticklabels([f"{s}（F={f:.0f}）" for s, f in zip(rb.設定, rb.第1段階F)], fontsize=8)
ax.axvline(0, color="#999", lw=.8); ax.legend(fontsize=8, loc="upper right")
ax.set_xlabel("雇用の伸び1%ポイントあたりの転入超過率の変化（%ポイント）")
ax.set_title("設定を変えた推定（95%区間）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f46_robustness.png"); plt.close()

# 図5 事前トレンド（誘導形）
pre = R["pretrend"]
fig, ax = plt.subplots(figsize=(7.2, 3.8))
ks = list(pre.keys())
for i, k in enumerate(ks):
    v = pre[k]; c = C1 if "本期" in k else C3
    ax.errorbar(i, v[0], yerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="o", color=c, capsize=6, ms=8)
    ax.text(i + .08, v[0], f"{v[0]:.3f}", va="center", fontsize=9)
ax.axhline(0, color="#999", lw=.8); ax.set_xticks(range(len(ks))); ax.set_xticklabels(ks, fontsize=9)
ax.set_ylabel("転入超過率の変化（%ポイント）")
ax.set_title("2016→21 のバーティク1%ポイントあたりの転入超過率：前の期間でも同じ大きさ", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f46_pretrend.png"); plt.close()
print("ok")
