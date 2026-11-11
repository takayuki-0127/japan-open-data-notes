# 05 図：6枚（図6はダッシュボードの画面。playwright で撮る）
import json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path
R = Path(__file__).resolve().parents[1]; O = R / "results"; FG = R / "figures"; FG.mkdir(exist_ok=True)
fp = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
fm.fontManager.addfont(fp); plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C = ["#1f4e79", "#2e86c1", "#5dade2", "#e67e22", "#c0392b", "#7d3c98"]

# 図1 必要な人数
A = pd.read_csv(O / "A_n_per_arm.csv")
fig, ax = plt.subplots(figsize=(8, 5))
for i, (p, g) in enumerate(A.groupby("baseline")):
    lab = f"基準 {p*100:.0f}%" if p < .5 else f"基準 {p*100:.1f}%（ネット購入世帯の割合）"
    ax.plot(g.rel_lift * 100, g.n_per_arm, marker="o", color=C[i], label=lab)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks([1, 2, 5, 10, 20, 30]); ax.set_xticklabels(["1%", "2%", "5%", "10%", "20%", "30%"])
ax.set_xlabel("見つけたい差（基準に対する相対的な差）"); ax.set_ylabel("1群に必要な人数（対数）")
ax.set_title("図1 見つけたい差が小さいほど、基準の割合が低いほど、必要な人数は増える", loc="left", fontsize=12)
ax.annotate("基準5%・+10%：1群 31,234人", (10, 31234), xytext=(1.05, 900), fontsize=9, color=C[2], arrowprops=dict(arrowstyle="->", color=C[2]))
ax.legend(fontsize=9, frameon=False); ax.grid(alpha=.3, which="both"); fig.tight_layout(); fig.savefig(FG / "fig1_n_required.png", dpi=150); plt.close()

# 図2 検出力の曲線（式とシミュレーション）
B = pd.read_csv(O / "B_power_curve_p5_l10.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(B.n_per_arm, B.theory_power * 100, color=C[0], label="式（正規近似）")
ax.scatter(B.n_per_arm, B.sim_power * 100, color=C[4], zorder=3, label="シミュレーション（6,000回）")
ax.axhline(80, ls="--", color="gray", lw=1); ax.axvline(31234, ls=":", color="gray", lw=1)
ax.set_xlabel("1群の人数"); ax.set_ylabel("検出力（差を見つけられる確率、%）"); ax.set_ylim(0, 100)
ax.set_title("図2 基準5%・+10%：必要な人数の半分だと、見つけられる確率は約50%", loc="left", fontsize=12)
ax.legend(frameon=False); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(FG / "fig2_power_curve.png", dpi=150); plt.close()

# 図3 4週間で見つけられる最小の差
M = pd.read_csv(O / "C_mde_by_traffic.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
for i, (p, g) in enumerate(M.query("weeks==4").groupby("baseline")):
    ax.plot(g.daily_visitors, g.mde_rel * 100, marker="o", color=C[i * 2], label=f"基準 {p*100:.0f}%")
ax.set_xscale("log"); ax.set_xticks([1000, 5000, 20000, 100000]); ax.set_xticklabels(["1,000", "5,000", "2万", "10万"])
ax.set_xlabel("1日の訪問者数（2群の合計）"); ax.set_ylabel("見つけられる最小の差（相対、%）")
ax.set_title("図3 4週間のテストで見つけられる最小の差（検出力80%）", loc="left", fontsize=12)
for r in M.query("weeks==4 and baseline==0.05").itertuples(): ax.annotate(f"+{r.mde_rel*100:.1f}%", (r.daily_visitors, r.mde_rel * 100), textcoords="offset points", xytext=(5, 6), fontsize=9, color=C[2])
ax.legend(frameon=False); ax.grid(alpha=.3, which="both"); fig.tight_layout(); fig.savefig(FG / "fig3_mde_traffic.png", dpi=150); plt.close()

# 図4 検出力が低いと、有意になった差は大げさになる
D = pd.read_csv(O / "D_winners_curse.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.bar([f"{x*100:.0f}%" for x in D.sim_power], D.exaggeration, color=[C[4] if x < .5 else C[1] for x in D.sim_power])
for i, v in enumerate(D.exaggeration): ax.text(i, v + .05, f"{v:.2f}倍", ha="center", fontsize=10)
ax.axhline(1, color="gray", lw=1); ax.set_xlabel("検出力（シミュレーション）"); ax.set_ylabel("有意になった結果の差 ÷ 本当の差")
ax.set_title("図4 人数が足りないまま「有意」になると、差を大きく見積もりやすい（基準5%・本当の差+10%）", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "fig4_exaggeration.png", dpi=150); plt.close()

# 図5 金額の指標
E = pd.read_csv(O / "E_spend_metric.csv").query("rel_lift==0.05")
lab = {("金額（全員）", "そのまま"): "金額（全員・そのまま）", ("金額（全員）", "上位1%で切る"): "金額（上位1%で切る）",
       ("金額（全員）", "上位5%で切る"): "金額（上位5%で切る）", ("買った割合", "-"): "買ったかどうか（割合）", ("買った人の金額", "そのまま"): "買った人の金額（来訪者数に換算）"}
E["lab"] = [lab[(a, b)] for a, b in zip(E.metric, E.treatment)]
E = E.sort_values("n_per_arm")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.barh(E.lab, E.n_per_arm, color=[C[1] if "金額（" in l else C[3] for l in E.lab])
for i, (v, cv) in enumerate(zip(E.n_per_arm, E.cv)): ax.text(v, i, f"  {v:,}人（CV {cv:.2f}）", va="center", fontsize=9)
ax.set_xlabel("+5% の差を見つけるのに必要な1群の人数"); ax.set_xlim(0, E.n_per_arm.max() * 1.45)
ax.set_title("図5 金額の指標は人数が要る。上位を切ると15〜25%減る", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "fig5_spend_metric.png", dpi=150); plt.close()

# 図6 ダッシュボードの画面
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1000, "height": 440}, device_scale_factor=1.5)
    pg.goto((R / "dashboard" / "index.html").as_uri()); pg.wait_for_timeout(500)
    pg.screenshot(path=str(FG / "fig6_calculator.png"), full_page=True); b.close()
print("ok")
