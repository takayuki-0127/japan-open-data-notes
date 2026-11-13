"""618 起きる割合が1%のとき、ROC の AUC と PR の AUC では、予測の良し悪しの見え方はどれだけ違うのか

正解の分かる架空のスコアで比べる。起きない人のスコアは N(0,1)。
  モデルA：起きる人のスコア N(1.6, 1)（全体をまんべんなく見分ける）
  モデルB：起きる人のスコア N(1.0, 2.0²)（全体の見分けは弱いが、上のほうに起きる人が集まる）
起きる割合 50%・10%・1%・0.1% で、ROC AUC・PR AUC（平均適合率）・上位1割の的中率（適合率）と捕捉率を出す。
さらに 1% で件数 5,000（起きる人は約50人）の小さな検証データを 500 回作り、指標の振れと、A と B の順位がどれだけ入れ替わるかを数える。
数字は置いた分布で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve, precision_recall_curve
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の予測スコア（作成者が乱数で作成、seed 618）"
rng = np.random.default_rng(618)
MODELS = {"A": (1.6, 1.0), "B": (1.0, 2.0)}
PREV = [0.5, 0.1, 0.01, 0.001]
N_BIG = 400_000


def draw(n, p, model, rng):
    y = (rng.random(n) < p).astype(int)
    mu, sd = MODELS[model]
    s = np.where(y == 1, rng.normal(mu, sd, n), rng.normal(0, 1, n))
    return y, s


def top_k(y, s, frac=0.1):
    k = int(len(y) * frac)
    idx = np.argsort(-s, kind="stable")[:k]
    return y[idx].mean(), y[idx].sum() / y.sum()


rows = []
for p in PREV:
    for m in MODELS:
        y, s = draw(N_BIG, p, m, rng)
        prec10, rec10 = top_k(y, s)
        rows.append({"prev": p, "model": m, "pos": int(y.sum()), "roc_auc": roc_auc_score(y, s),
                     "pr_auc": average_precision_score(y, s), "prec_top10": prec10, "recall_top10": rec10})
big = pd.DataFrame(rows)
big.round(4).to_csv(RES / "by_prevalence.csv", index=False)

# 小さな検証データでの振れ（1%、5,000件）
REPS, NS = 500, 5000
sm = []
for r in range(REPS):
    rec = {"rep": r}
    for m in MODELS:
        y, s = draw(NS, 0.01, m, rng)
        rec[f"roc_{m}"] = roc_auc_score(y, s); rec[f"pr_{m}"] = average_precision_score(y, s); rec[f"pos_{m}"] = int(y.sum())
    sm.append(rec)
sm = pd.DataFrame(sm)
sm.round(4).to_csv(RES / "small_sample_reps.csv", index=False)
small = {}
for k in ["roc", "pr"]:
    for m in MODELS:
        v = sm[f"{k}_{m}"]
        small[f"{k}_{m}"] = {"mean": round(float(v.mean()), 4), "sd": round(float(v.std()), 4),
                             "p05": round(float(v.quantile(0.05)), 4), "p95": round(float(v.quantile(0.95)), 4),
                             "cv_pct": round(float(100 * v.std() / v.mean()), 1)}
small["A_beats_B_roc_pct"] = round(float(100 * (sm.roc_A > sm.roc_B).mean()), 1)
small["B_beats_A_pr_pct"] = round(float(100 * (sm.pr_B > sm.pr_A).mean()), 1)

g = big.set_index(["prev", "model"])
out = {"models": {k: {"pos_mean": v[0], "pos_sd": v[1]} for k, v in MODELS.items()}, "n_per_scenario": N_BIG,
       "by_prev": big.round(4).to_dict(orient="records"), "small_sample": small, "reps": REPS, "n_small": NS}
json.dump(out, open(RES / "a618_main.json", "w"), ensure_ascii=False, indent=1)
big.round(4).to_csv(RES / "summary.csv", index=False)

# 図1：起きる割合ごとの ROC AUC と PR AUC（モデルA）
fig, ax = plt.subplots(figsize=(8.5, 4.2))
xs = np.arange(len(PREV)); lab = ["50%", "10%", "1%", "0.1%"]
a = big[big.model == "A"]
ax.plot(xs, a.roc_auc, marker="o", color=BLUE, label="ROC の AUC")
ax.plot(xs, a.pr_auc, marker="s", color=ORANGE, label="PR の AUC（平均適合率）")
ax.plot(xs, PREV, ls=":", color=GRAY, label="でたらめに並べたときの PR の AUC（＝起きる割合）")
for x, v1, v2 in zip(xs, a.roc_auc, a.pr_auc):
    ax.text(x, v1 + 0.03, f"{v1:.2f}", ha="center", color=BLUE, fontsize=9)
    ax.text(x + 0.12, v2 + 0.02, f"{v2:.3f}", ha="center", color=ORANGE, fontsize=9)
ax.set_xticks(xs); ax.set_xticklabels(lab); ax.set_xlabel("起きる割合"); ax.set_ylim(0, 1.05)
ax.set_title("同じ見分ける力のモデルでも、起きる割合が下がると PR の AUC だけが下がる")
ax.legend(frameon=False, fontsize=9, loc="center left")
save(fig, "a618_by_prevalence.png", SRC)

# 図2：1% での ROC 曲線と PR 曲線（A と B）
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"wspace": 0.3})
for m, c in [("A", BLUE), ("B", ORANGE)]:
    y, s = draw(N_BIG, 0.01, m, np.random.default_rng(6180))
    fpr, tpr, _ = roc_curve(y, s); pr, rc, _ = precision_recall_curve(y, s)
    r = g.loc[(0.01, m)]
    ax[0].plot(fpr, tpr, color=c, label=f"モデル{m}（AUC {r.roc_auc:.3f}）")
    ax[1].plot(rc, pr, color=c, label=f"モデル{m}（AUC {r.pr_auc:.3f}）")
ax[0].plot([0, 1], [0, 1], ls=":", color=GRAY); ax[0].set_xlabel("起きない人を誤って選ぶ割合"); ax[0].set_ylabel("起きる人を拾う割合")
ax[0].set_title("ROC 曲線：A のほうが上"); ax[0].legend(frameon=False, fontsize=9)
ax[1].set_xlabel("起きる人を拾う割合（捕捉率）"); ax[1].set_ylabel("選んだ中で本当に起きる割合（適合率）")
ax[1].set_title("PR 曲線：上位では B のほうが上"); ax[1].legend(frameon=False, fontsize=9); ax[1].set_ylim(0, 1)
save(fig, "a618_curves.png", SRC, y=-0.04)

# 図3：小さな検証データでの振れ
fig, ax = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"wspace": 0.3})
for i, k in enumerate(["roc", "pr"]):
    for m, c in [("A", BLUE), ("B", ORANGE)]:
        ax[i].hist(sm[f"{k}_{m}"], bins=30, color=c, alpha=0.55, label=f"モデル{m}（変動係数 {small[f'{k}_{m}']['cv_pct']}%）")
    ax[i].legend(frameon=False, fontsize=9)
ax[0].set_title("ROC の AUC（5,000件・起きる人は約50人）"); ax[1].set_title("PR の AUC（同じデータ）")
ax[0].set_ylabel("500回のうちの回数")
save(fig, "a618_small_sample.png", SRC, y=-0.04)
print(json.dumps(out, ensure_ascii=False, indent=1))
