"""666 見逃しと空振りのコストが違うとき、確率0.5で切るのと費用で決めた閾値では、損失はどれだけ違うのか

シミュレーション。陽性は全体の10%。特徴量5つのロジスティック回帰を学習用2,000件で当て、評価用5万件で損失を数える。
見逃し（陽性を陰性と判定）1件のコストを、空振り（陰性を陽性と判定）1件の r 倍とする（r＝1〜50）。
  T1 確率0.5で切る
  T2 費用から決めた閾値 1/(1+r)
  T3 学習用の交差検証（5分割）の予測で、損失が最小の閾値を選ぶ
  参考：評価用で損失が最小になる閾値（後から分かる最善）、全員を陰性にする
各 r で200回くり返す。損失は1,000件あたり、空振り1件のコストを1として数える。seed 666。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 666）"
rng = np.random.default_rng(666)
beta = np.array([0.9, -0.7, 0.6, 0.5, -0.4]); b0 = -2.95
def gen(n, r):
    X = r.normal(size=(n, 5)); p = 1 / (1 + np.exp(-(b0 + X @ beta)))
    return X, (r.random(n) < p).astype(int)
R_LIST = [1, 2, 5, 10, 20, 50]; REPS = 200; NTR, NTE = 2000, 50000
grid = np.round(np.arange(0.005, 0.996, 0.005), 3)
def loss_at(p, y, t, r):
    pred = p >= t
    return ((~pred & (y == 1)).sum() * r + (pred & (y == 0)).sum()) / len(y) * 1000
def curve(p, y, r):
    o = np.argsort(-p); ys = y[o]; ps = p[o]
    # 閾値ごとに：陽性と判定する件数 k＝(p>=t) の数
    cum_pos = np.concatenate([[0], np.cumsum(ys)]); cum_neg = np.concatenate([[0], np.cumsum(1 - ys)])
    k = len(p) - np.searchsorted(np.sort(p), grid, side="left")
    fn = ys.sum() - cum_pos[k]; fp = cum_neg[k]
    return (fn * r + fp) / len(y) * 1000
rows, example = [], None
for r in R_LIST:
    for rep in range(REPS):
        Xtr, ytr = gen(NTR, rng); Xte, yte = gen(NTE, rng)
        m = LogisticRegression(C=1e6, max_iter=1000).fit(Xtr, ytr)
        pte = m.predict_proba(Xte)[:, 1]
        oof = np.zeros(NTR)
        for tr, va in StratifiedKFold(5, shuffle=True, random_state=rep).split(Xtr, ytr):
            oof[va] = LogisticRegression(C=1e6, max_iter=1000).fit(Xtr[tr], ytr[tr]).predict_proba(Xtr[va])[:, 1]
        t_cv = grid[np.argmin(curve(oof, ytr, r))]
        c_te = curve(pte, yte, r)
        t_or = grid[np.argmin(c_te)]
        t_th = 1 / (1 + r)
        rows.append({"r": r, "rep": rep, "loss_05": loss_at(pte, yte, 0.5, r), "loss_theory": loss_at(pte, yte, t_th, r),
                     "loss_cv": loss_at(pte, yte, t_cv, r), "loss_oracle": float(c_te.min()), "loss_none": float(yte.sum() * r / NTE * 1000),
                     "t_theory": t_th, "t_cv": float(t_cv), "t_oracle": float(t_or), "pos_rate": float(yte.mean())})
        if r == 10 and rep == 0:
            example = {"grid": grid, "curve": c_te, "t_cv": float(t_cv), "t_th": t_th}
D = pd.DataFrame(rows); D.round(4).to_csv(RES / "reps.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
S = D.groupby("r").agg(loss_05=("loss_05", "mean"), loss_theory=("loss_theory", "mean"), loss_cv=("loss_cv", "mean"),
                       loss_oracle=("loss_oracle", "mean"), loss_none=("loss_none", "mean"),
                       t_cv_med=("t_cv", "median"), t_cv_q10=("t_cv", lambda s: s.quantile(0.1)), t_cv_q90=("t_cv", lambda s: s.quantile(0.9)),
                       t_or_med=("t_oracle", "median"))
for c in ["05", "theory", "cv"]:
    S[f"excess_{c}_pct"] = (S[f"loss_{c}"] / S.loss_oracle - 1) * 100
S.round(3).to_csv(RES / "summary.csv")
out = {"pos_rate": round(float(D.pos_rate.mean()), 4), "n_train": NTR, "n_test": NTE, "reps": REPS,
       "by_r": {int(r): {"loss_05": round(s.loss_05, 1), "loss_theory": round(s.loss_theory, 1), "loss_cv": round(s.loss_cv, 1),
                         "loss_oracle": round(s.loss_oracle, 1), "loss_none": round(s.loss_none, 1),
                         "excess_05_pct": round(s.excess_05_pct, 1), "excess_theory_pct": round(s.excess_theory_pct, 1), "excess_cv_pct": round(s.excess_cv_pct, 1),
                         "t_theory": round(1 / (1 + r), 3), "t_cv_median": round(s.t_cv_med, 3), "t_cv_p10_p90": [round(s.t_cv_q10, 3), round(s.t_cv_q90, 3)],
                         "theory_better_than_cv_share": round(float((D[D.r == r].loss_theory <= D[D.r == r].loss_cv).mean()), 3)}
                for r, s in S.iterrows()}}
json.dump(out, open(RES / "a666_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：損失（後から分かる最善との差）
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(len(R_LIST)); w = 0.27
for i, (c, lab, col) in enumerate([("05", "確率0.5で切る", ORANGE), ("theory", "費用から決めた閾値 1/(1+r)", BLUE), ("cv", "交差検証で選んだ閾値", GREEN)]):
    ax.bar(x + (i - 1) * w, S[f"excess_{c}_pct"], w, color=col, label=lab)
ax.set_xticks(x); ax.set_xticklabels([f"{r}倍" for r in R_LIST]); ax.set_xlabel("見逃し1件のコスト（空振り1件の何倍か）")
ax.set_ylabel("最善の閾値より損失が多い割合（%）"); ax.set_yscale("symlog", linthresh=10)
ax.set_yticks([0, 5, 10, 50, 100, 500]); ax.set_yticklabels(["0", "5", "10", "50", "100", "500"])
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("見逃しが高いほど、0.5で切ると損失がふくらむ")
save(fig, "a666_excess.png", SRC)
# 図2：閾値
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.plot(x, [1 / (1 + r) for r in R_LIST], marker="o", color=BLUE, label="費用から決めた閾値 1/(1+r)")
ax.errorbar(x + 0.08, S.t_cv_med, yerr=[S.t_cv_med - S.t_cv_q10, S.t_cv_q90 - S.t_cv_med], fmt="s", color=GREEN, capsize=3, label="交差検証で選んだ閾値（中央値と10〜90%）")
ax.axhline(0.5, color=ORANGE, ls="--", lw=1, label="0.5")
ax.set_xticks(x); ax.set_xticklabels([f"{r}倍" for r in R_LIST]); ax.set_xlabel("見逃し1件のコスト（空振り1件の何倍か）")
ax.set_ylabel("閾値（この確率以上を陽性に）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("交差検証で選ぶ閾値は、費用の式の値のまわりで大きくぶれる")
save(fig, "a666_thresholds.png", SRC)
# 図3：1回分の損失の曲線
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.plot(example["grid"], example["curve"], color=GRAY)
for t, lab, col in [(0.5, "0.5", ORANGE), (example["t_th"], "1/(1+10)", BLUE), (example["t_cv"], "交差検証", GREEN)]:
    yv = np.interp(t, example["grid"], example["curve"])
    ax.scatter([t], [yv], color=col, s=40, zorder=3, label=f"{lab}：閾値{t:.2f}、損失{yv:.0f}")
ax.set_xlabel("閾値"); ax.set_ylabel("1,000件あたりの損失"); ax.legend(frameon=False, fontsize=9)
ax.set_title("見逃しが10倍のとき、損失の谷は低い閾値のあたりで浅く広い")
save(fig, "a666_curve.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
