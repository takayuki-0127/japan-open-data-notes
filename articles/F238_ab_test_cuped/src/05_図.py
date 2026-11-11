"""05 図：figures/ に PNG を書く（Noto Sans CJK JP）。ダッシュボードの画面は playwright で撮る。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
R, F, D = ROOT / "results", ROOT / "figures", ROOT / "data"
F.mkdir(exist_ok=True)
for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(p).exists():
        fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
O = json.load(open(R / "main.json"))
A = pd.read_csv(R / "A_geo_methods.csv")
B = pd.read_csv(R / "B_pre_length.csv")
N = pd.read_csv(R / "B_new_users.csv")
C = pd.read_csv(R / "C_post_treatment.csv")
ML = {"naive": "素の差", "diff": "差の差（y−前の値）", "cuped": "CUPED", "regadj": "回帰調整（群ごと）", "strat": "前の値の5分位で層別"}
COL = {"naive": "#9e9e9e", "diff": "#f59f00", "cuped": "#1f6feb", "regadj": "#2b8a3e", "strat": "#ae3ec9"}

# 図1：市区町村の模擬テスト。前の値と今の値（出生率）＋ 推定のばらつき
geo = pd.read_csv(D / "geo_metrics.csv")
dist = np.load(R / "A_geo_dist.npz")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
ax[0].scatter(geo.birth_rate_pre, geo.birth_rate, s=6, alpha=0.4, color="#1f6feb")
ax[0].set_xlabel("前の値（SSDSE 2021年版の出生率、人口千人あたり）"); ax[0].set_ylabel("今の値（2026年版）")
ax[0].set_title(f"1,729市区町村：前の値と今の値（相関 {O['A']['birth_rate']['naive']['rho']:.2f}）", fontsize=11)
for m in ["naive", "diff", "cuped"]:
    v = dist[f"birth_rate__{m}"]
    ax[1].hist(v, bins=60, alpha=0.5, color=COL[m], label=f"{ML[m]}（ばらつき {O['A']['birth_rate'][m]['var_ratio']:.2f}倍）", density=True)
ax[1].axvline(0, color="k", lw=0.8)
ax[1].set_xlabel("効果がないときの推定差（4,000回の割り当て）"); ax[1].set_yticks([])
ax[1].set_title("CUPED は推定のばらつきを約3分の1にした", fontsize=11); ax[1].legend(fontsize=9, frameon=False)
fig.tight_layout(); fig.savefig(F / "fig1_geo_mock.png"); plt.close(fig)

# 図2：指標×手法の分散の比（市区町村）
mets = ["birth_rate", "log_emp_ratio", "aging", "births"]
lab = {"birth_rate": "出生率\n（ρ=0.83）", "log_emp_ratio": "従業者÷人口（対数）\n（ρ=0.97）",
       "aging": "高齢化率\n（ρ=0.98）", "births": "出生数\n（ρ=0.999）"}
fig, ax = plt.subplots(figsize=(10, 4.4))
w = 0.16
for i, m in enumerate(["naive", "diff", "cuped", "strat"]):
    vals = [A.query("metric==@k and method==@m").var_ratio.iloc[0] for k in mets]
    xs = np.arange(len(mets)) + (i - 1.5) * w
    ax.bar(xs, vals, w, color=COL[m], label=ML[m])
    for xx, vv in zip(xs, vals):
        ax.text(xx, vv + 0.02, f"{vv:.2f}" if vv >= 0.01 else f"{vv:.3f}", ha="center", fontsize=8)
ax.set_xticks(range(len(mets))); ax.set_xticklabels([lab[k] for k in mets])
ax.set_ylabel("推定の分散（素の差＝1）"); ax.set_ylim(0, 1.12)
ax.set_title("同じ精度に必要な数の比：低いほど少ない数で済む（市区町村の模擬テスト）", fontsize=11)
ax.legend(fontsize=9, frameon=False, ncol=4, loc="upper left")
fig.tight_layout(); fig.savefig(F / "fig2_geo_methods.png"); plt.close(fig)

# 図3：ユーザー単位。前の期間の長さと相関・必要な人数の比
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
sc_lab = {"visits": "よく来る：訪問回数", "purchase_count": "まれに買う：購入回数", "purchase_revenue": "まれに買う：購入金額"}
sc_col = {"visits": "#1f6feb", "purchase_count": "#f59f00", "purchase_revenue": "#d9480f"}
for sk in ["visits", "purchase_count", "purchase_revenue"]:
    b = B[B.scenario == sk]
    ax[0].plot(b.pre_weeks, b.rho, "o-", color=sc_col[sk], label=sc_lab[sk])
    ax[1].plot(b.pre_weeks, b.var_ratio, "o-", color=sc_col[sk], label=sc_lab[sk])
ax[0].set_xlabel("前の期間の長さ（週）"); ax[0].set_ylabel("テスト2週間の値との相関 ρ"); ax[0].set_ylim(0, 1)
ax[0].set_title("前の期間を長くするほど相関は上がるが、頭打ちになる", fontsize=11); ax[0].legend(fontsize=9, frameon=False)
ax[1].set_xlabel("前の期間の長さ（週）"); ax[1].set_ylabel("必要な人数の比（素の差＝1）"); ax[1].set_ylim(0, 1.05)
ax[1].set_title("訪問回数は3割弱に、購入金額はほぼ変わらない", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig3_user_pre_length.png"); plt.close(fig)

# 図4：新規ユーザーの割合と、金額の指標の手当て
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
ax[0].plot(N.new_share * 100, N.var_ratio, "o-", color="#1f6feb")
for r in N.itertuples():
    ax[0].text(r.new_share * 100, r.var_ratio + 0.03, f"{r.var_ratio:.2f}", ha="center", fontsize=9)
ax[0].set_xlabel("前の期間のデータがない人（新規）の割合（%）"); ax[0].set_ylabel("必要な人数の比（素の差＝1）"); ax[0].set_ylim(0, 1.05)
ax[0].set_title("新規の人が多いほど、CUPED の効き目は薄くなる（訪問回数）", fontsize=11)
rv = O["B_revenue"]
labs = ["素の差", "CUPED\n（前4週の金額）", "前4週の金額\n＋回数", "上位1%を切る\n（ウィンザー化）", "ウィンザー化\n＋CUPED"]
vals = [1.0, rv["vr_cuped_raw"], rv["vr_multi"], rv["vr_wins_only"], rv["vr_wins_cuped"]]
ax[1].bar(range(5), vals, color=["#9e9e9e", "#1f6feb", "#1f6feb", "#f59f00", "#2b8a3e"])
for i, v in enumerate(vals):
    ax[1].text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
ax[1].set_xticks(range(5)); ax[1].set_xticklabels(labs, fontsize=9); ax[1].set_ylim(0, 1.12)
ax[1].set_title("まれな購入の金額では、外れ値を切るほうが効いた", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig4_new_users_revenue.png"); plt.close(fig)

# 図5：落とし穴（テスト中の値で調整）
fig, ax = plt.subplots(figsize=(8, 4.2))
k = ["naive", "cuped_pre", "cuped_during"]
lab5 = ["素の差", "CUPED（テストの前4週の金額）", "CUPED（テスト中の訪問回数）"]
r = [(C[c] / C.true) for c in k]
ax.boxplot(r, showfliers=False, widths=0.5)
ax.axhline(1, color="#d9480f", ls="--", lw=1); ax.text(0.55, 1.05, "本当の効果", color="#d9480f", va="bottom", fontsize=9)
ax.set_xticks([1, 2, 3]); ax.set_xticklabels(lab5, fontsize=10)
ax.set_ylabel("推定した効果 ÷ 本当の効果（800回）")
ax.set_title(f"テスト中に測った値で調整すると、効果の約6割が消えた（平均 {O['C_mean_ratio']['cuped_during']:.2f}）", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig5_post_treatment.png"); plt.close(fig)

# 図6：ダッシュボードの画面
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1100, "height": 620}, device_scale_factor=1)
        pg.goto((ROOT / "dashboard" / "index.html").as_uri())
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(F / "fig6_dashboard.png"), full_page=True)
        b.close()
except Exception as e:
    print("dashboard screenshot skipped:", e)
print(sorted(x.name for x in F.glob("*.png")))
