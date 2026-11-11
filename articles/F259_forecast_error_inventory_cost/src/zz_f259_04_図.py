# F259 04 図（5枚）
import json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f: font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
plt.rcParams["svg.hashsalt"] = "f259"
A = pd.read_csv("results/A_cost_main.csv"); N = pd.read_csv("results/B_needed_ss_by_H.csv")
RHO = pd.read_csv("results/C_rank_corr.csv"); RB = pd.read_csv("results/E_robustness.csv"); m = json.load(open("results/main.json"))
RC = {"なし": "#9e9e9e", "ルートの式": "#1f77b4", "合計の外れの分位点": "#d62728", "偏りだけ直す": "#ff7f0e",
      "分位点（2か月持つ前提）": "#9467bd", "後から見た最良の倍率": "#2ca02c"}
LS = [0, 1, 2, 3]; save = lambda fig, n: (fig.tight_layout(), fig.savefig(f"figures/{n}", dpi=150, metadata={"Software": None}), plt.close(fig))

# 図1 必要な安全在庫の倍率と √(L+R)
g = N[N.H.between(1, 6)].groupby("H")["必要な倍率"]; med, lo, hi = g.median(), g.quantile(0.25), g.quantile(0.75)
fig, ax = plt.subplots(figsize=(9, 4.8)); H = med.index.to_numpy()
ax.fill_between(H, lo, hi, color="#d62728", alpha=0.15, label="実際に要った倍率（真ん中半分）")
ax.plot(H, med, "o-", color="#d62728", lw=2, label="実際に要った倍率（中央値）")
ax.plot(H, np.sqrt(H), "s--", color="#1f77b4", lw=1.5, label="ルートの式の倍率 √(L+R)")
for h in [2, 3, 4, 5]: ax.text(h + 0.08, med[h], f"{med[h]:.2f}", fontsize=9, color="#d62728", va="center")
ax.set_xlabel("何か月分の需要を、1回の発注で守るか（L+R、R=2 なので L=0〜3 が 2〜5）"); ax.set_ylabel("1か月先の外れ×z の何倍の安全在庫が要ったか")
ax.set_title("図1　守る期間が長くなると、要る安全在庫は √ の式より速く増える（6業態×5モデル）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False); save(fig, "fig1_needed_ss.png")

# 図2 カバー率（L+R か月の需要を、予測の合計＋安全在庫で覆えた割合）
q = A[A.p == 9]; cov = q.groupby(["決め方", "L"]).カバー率.mean().unstack()
pool = RB[RB.頑健性 == "6業態まとめて分位点"].groupby(["決め方", "L"]).カバー率.mean().unstack()
fig, ax = plt.subplots(figsize=(9, 4.8))
for r, lab in [("ルートの式", "ルートの式"), ("合計の外れの分位点", "合計の外れの分位点（業態ごと）")]:
    ax.plot(LS, cov.loc[r], "o-", color=RC[r], lw=2, label=lab)
ax.plot(LS, pool.loc["合計の外れの分位点"], "o--", color=RC["合計の外れの分位点"], lw=1.2, alpha=0.7, label="合計の外れの分位点（6業態まとめて）")
ax.plot(LS, cov.loc["なし"], "o:", color=RC["なし"], label="安全在庫なし")
ax.axhline(0.9, color="#333", lw=1); ax.text(3.05, 0.905, "目標 90%", fontsize=9, va="bottom", ha="right")
ax.set_xticks(LS); ax.set_xlabel("リードタイム L（か月）"); ax.set_ylabel("覆えた割合"); ax.set_ylim(0.3, 1.0)
ax.set_title("図2　目標の90%に届いたか（L+R か月の需要を、予測＋安全在庫で覆えた割合）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False, loc="center right"); save(fig, "fig2_coverage.png")

# 図3 費用：決め方×L（左）と、L=2 の内訳（右）
t = q.groupby(["決め方", "L"]).費用.mean().unstack(); part = q[q.L == 2].groupby("決め方")[["在庫費", "欠品費"]].mean()
order = ["なし", "偏りだけ直す", "ルートの式", "合計の外れの分位点", "分位点（2か月持つ前提）", "後から見た最良の倍率"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1, 1.2]})
for r in order: a1.plot(LS, t.loc[r], "o-", color=RC[r], lw=2 if r in ("合計の外れの分位点", "ルートの式") else 1.2, label=r)
a1.set_xticks(LS); a1.set_xlabel("リードタイム L（か月）"); a1.set_ylabel("月あたりの費用（需要の月平均＝100）"); a1.legend(fontsize=8, frameon=False)
y = np.arange(len(order)); a2.barh(y, part.loc[order, "在庫費"], color="#90a4ae", label="在庫を持つ費用")
a2.barh(y, part.loc[order, "欠品費"], left=part.loc[order, "在庫費"], color="#e57373", label="売り逃しの損")
for i, r in enumerate(order): a2.text(part.loc[r].sum() + 0.5, i, f"{part.loc[r].sum():.1f}", va="center", fontsize=9)
a2.set_yticks(y, order, fontsize=9); a2.invert_yaxis(); a2.set_xlabel("L=2 の月あたりの費用"); a2.set_xlim(0, 85); a2.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.09), ncol=2)
fig.suptitle("図3　安全在庫の決め方と費用（p=9：売り逃し1単位の損は、在庫1単位1か月の9倍、と例として置いた）", x=0.01, ha="left", fontsize=12)
save(fig, "fig3_cost_by_rule.png")

# 図4 どの精度指標が費用の順位と合うか
MET = ["MAPE_1か月先", "RMSE_1か月先", "RMSE_合計", "偏り_合計", "ピンボール損失"]
LAB = {"MAPE_1か月先": "1か月先の\nMAPE", "RMSE_1か月先": "1か月先の\nRMSE", "RMSE_合計": "L+R か月の\n合計の外れ（RMSE）", "偏り_合計": "合計の外れの\n偏り（絶対値）", "ピンボール損失": "ピンボール損失\n（90%点）"}
fig, ax = plt.subplots(figsize=(9, 4.8)); w = 0.38
for j, (cr, col, lab) in enumerate([("なし", "#9e9e9e", "安全在庫なしのときの費用"), ("合計の外れの分位点", "#d62728", "分位点で安全在庫を置いたときの費用")]):
    g = RHO[RHO.費用の決め方 == cr].groupby("指標").順位相関.mean().reindex(MET)
    b = ax.bar(np.arange(5) + (j - 0.5) * w, g, w, color=col, label=lab)
    for x_, v in zip(np.arange(5) + (j - 0.5) * w, g): ax.text(x_, v + 0.02 if v >= 0 else 0.02, f"{v:.2f}", ha="center", fontsize=9)
ax.axhline(0, color="#333", lw=0.8); ax.set_xticks(range(5), [LAB[k] for k in MET], fontsize=9); ax.set_ylabel("費用との順位相関（24組の平均）")
ax.set_title("図4　どの「当たり具合」が、お金の順位と合うか（業態×L の中で5モデルを並べる）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False); save(fig, "fig4_metric_vs_cost.png")

# 図5 モデルの差と決め方の差
MO = ["季節ナイーブ", "季節ナイーブ＋伸び", "ETS", "SARIMA", "LightGBM"]
bm = q.groupby(["モデル", "決め方"]).費用.mean().unstack().loc[MO]
fig, ax = plt.subplots(figsize=(9, 4.8))
for r in ["なし", "ルートの式", "合計の外れの分位点", "後から見た最良の倍率"]:
    ax.plot(bm[r], range(5), "o", ms=9, color=RC[r], label=r)
for i, mo in enumerate(MO): ax.plot([bm.loc[mo].min(), bm.loc[mo].max()], [i, i], color="#ccc", zorder=0)
ax.set_yticks(range(5), MO); ax.invert_yaxis(); ax.set_xlabel("月あたりの費用（6業態・L=0〜3 の平均、p=9）")
ax.set_title("図5　モデルの違いと、安全在庫の決め方の違い（横の幅が決め方の差）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False, loc="lower right"); save(fig, "fig5_model_vs_rule.png")

print("ok")
