"""759 正解のラベルが1割まちがっていると、モデルの正解率はどれだけ低く見えるのか

架空の解約予測（解約は約30%）。本当の解約しやすさ η から本当のラベル y を作り、2つのモデルの点数を
  モデル A：η＋雑音（標準偏差0.8）、モデル B：η＋雑音（1.4）
とする（A のほうが強い）。テストデータ5,000件のラベルを、
  対称の誤り（どちらの向きにも確率 r で入れかわる）、片側の誤り（解約した人の一部が「解約していない」と記録される）
で r = 0〜30% まちがえ、正解率・AUC・2つのモデルの差が見かけでどれだけ変わるかを各200回で測る。
対称の誤りでは、見かけの正解率 = 本当の正解率×(1−r) + (1−本当の正解率)×r になることも確かめる。seed 759。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 759）"
rng = np.random.default_rng(759)
N, REPS = 5000, 200
RS = [0.0, 0.05, 0.1, 0.2, 0.3]
rows = []
for rep in range(REPS):
    eta = rng.normal(-1.2, 1.5, N)
    y = (rng.random(N) < 1 / (1 + np.exp(-eta))).astype(int)
    sA = eta + rng.normal(0, 0.8, N); sB = eta + rng.normal(0, 1.4, N)
    pA = (sA > 0).astype(int); pB = (sB > 0).astype(int)
    accA, accB = (pA == y).mean(), (pB == y).mean()
    aucA, aucB = roc_auc_score(y, sA), roc_auc_score(y, sB)
    for r in RS:
        flip = rng.random(N) < r
        ys = np.where(flip, 1 - y, y)                       # 対称の誤り
        miss = (y == 1) & (rng.random(N) < r)
        yo = np.where(miss, 0, y)                           # 片側の誤り（解約した人を「解約していない」と記録）
        rows.append((rep, r, accA, accB, aucA, aucB,
                     (pA == ys).mean(), (pB == ys).mean(), roc_auc_score(ys, sA), roc_auc_score(ys, sB),
                     (pA == yo).mean(), (pB == yo).mean(), roc_auc_score(yo, sA), roc_auc_score(yo, sB),
                     pA[y == 1].mean(), pA[yo == 1].mean(), y[pA == 1].mean(), yo[pA == 1].mean()))
cols = ["rep", "r", "accA", "accB", "aucA", "aucB", "accA_sym", "accB_sym", "aucA_sym", "aucB_sym",
        "accA_one", "accB_one", "aucA_one", "aucB_one", "recallA_true", "recallA_one", "precA_true", "precA_one"]
R = pd.DataFrame(rows, columns=cols)
S = R.groupby("r").mean().drop(columns="rep").reset_index()
S["accA_formula"] = S.accA * (1 - S.r) + (1 - S.accA) * S.r
S["gap_acc_true"] = (S.accA - S.accB) * 100; S["gap_acc_sym"] = (S.accA_sym - S.accB_sym) * 100
S["gap_auc_true"] = S.aucA - S.aucB; S["gap_auc_sym"] = S.aucA_sym - S.aucB_sym
S.round(4).to_csv(RES / "summary.csv", index=False)
assert np.allclose(S.accA_sym, S.accA_formula, atol=0.002)
# 差が見かけで逆転した回の割合（正解率）
flipwin = R.groupby("r").apply(lambda g: float(((g.accB_sym > g.accA_sym).mean()) * 100), include_groups=False)
gS = lambda r, c: float(S[S.r == r][c].iloc[0])
out = {"n_test": N, "reps": REPS, "churn_rate_pct": None, "rs": RS,
       "true_acc_A": round(gS(0, "accA") * 100, 1), "true_acc_B": round(gS(0, "accB") * 100, 1),
       "true_auc_A": round(gS(0, "aucA"), 3), "true_auc_B": round(gS(0, "aucB"), 3),
       "sym_acc_A": {str(r): round(gS(r, "accA_sym") * 100, 1) for r in RS},
       "sym_auc_A": {str(r): round(gS(r, "aucA_sym"), 3) for r in RS},
       "sym_gap_acc_pt": {str(r): round(gS(r, "gap_acc_sym"), 2) for r in RS},
       "sym_gap_auc": {str(r): round(gS(r, "gap_auc_sym"), 3) for r in RS},
       "one_sided_acc_A": {str(r): round(gS(r, "accA_one") * 100, 1) for r in RS},
       "one_sided_recall_A": {str(r): round(gS(r, "recallA_one") * 100, 1) for r in RS},
       "one_sided_precision_A": {str(r): round(gS(r, "precA_one") * 100, 1) for r in RS},
       "true_recall_A": round(gS(0, "recallA_true") * 100, 1), "true_precision_A": round(gS(0, "precA_true") * 100, 1),
       "formula_check_max_abs_diff_pt": round(float((S.accA_sym - S.accA_formula).abs().max() * 100), 3),
       "B_beats_A_on_noisy_labels_pct": {str(r): round(v, 1) for r, v in flipwin.items()}}
# 解約率
eta = np.random.default_rng(1).normal(-1.2, 1.5, 200000)
out["churn_rate_pct"] = round(float(np.mean(1 / (1 + np.exp(-eta)))) * 100, 1)
json.dump(out, open(RES / "a759_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：見かけの正解率（対称の誤り）
fig, ax = plt.subplots(figsize=(7.8, 3.8))
x = np.array(RS) * 100
ax.plot(x, S.accA_sym * 100, marker="o", color=BLUE, label="モデル A（見かけ）")
ax.plot(x, S.accB_sym * 100, marker="o", color=ORANGE, label="モデル B（見かけ）")
ax.axhline(gS(0, "accA") * 100, color=BLUE, ls=":", lw=1); ax.axhline(gS(0, "accB") * 100, color=ORANGE, ls=":", lw=1)
ax.text(30.5, gS(0, "accA") * 100, "A の本当", color=BLUE, fontsize=9, va="center"); ax.text(30.5, gS(0, "accB") * 100, "B の本当", color=ORANGE, fontsize=9, va="center")
for xi, v in zip(x, S.accA_sym * 100):
    ax.text(xi, v + 1, f"{v:.1f}", ha="center", fontsize=9, color=BLUE)
ax.set_xlabel("ラベルをまちがえた割合（%、どちらの向きにも）"); ax.set_ylabel("正解率（%）")
ax.legend(frameon=False, loc="lower left"); ax.set_xlim(-1, 35)
ax.set_title("ラベルが1割まちがっていると、正解率は本当より低く見える")
save(fig, "a759_accuracy.png", SRC)
# 図2：2つのモデルの差
fig, ax = plt.subplots(figsize=(7.8, 3.6))
ax.bar(x - 1, S.gap_acc_sym, 2, color=BLUE, label="正解率の差（ポイント）")
for xi, v in zip(x, S.gap_acc_sym):
    ax.text(xi - 1, v + 0.1, f"{v:.2f}", ha="center", fontsize=9)
ax2 = ax.twinx(); ax2.plot(x, S.gap_auc_sym, marker="s", color=ORANGE, label="AUC の差（右）"); ax2.spines["right"].set_visible(True)
ax2.set_ylim(0, S.gap_auc_sym.max() * 1.3)
ax.set_xlabel("ラベルをまちがえた割合（%）"); ax.set_ylabel("A − B（正解率、ポイント）"); ax2.set_ylabel("A − B（AUC）")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right")
ax.set_title("モデルの差も、まちがいが増えるほど小さく見える")
save(fig, "a759_gap.png", SRC)
# 図3：片側の誤り（再現率と適合率）
fig, ax = plt.subplots(figsize=(7.8, 3.6))
ax.plot(x, S.recallA_one * 100, marker="o", color=GREEN, label="再現率（見かけ）")
ax.plot(x, S.precA_one * 100, marker="o", color=ORANGE, label="適合率（見かけ）")
ax.axhline(gS(0, "recallA_true") * 100, color=GREEN, ls=":", lw=1); ax.axhline(gS(0, "precA_true") * 100, color=ORANGE, ls=":", lw=1)
ax.set_xlabel("解約した人を「解約していない」と記録した割合（%）"); ax.set_ylabel("%（モデル A）")
ax.legend(frameon=False, loc="lower left")
ax.set_title("片側だけのまちがいでは、再現率は変わらず、適合率だけが下がって見える", fontsize=12)
save(fig, "a759_one_sided.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
