"""667 反応しそうな人に配るのと、配ったら反応が増える人に配るのでは、増える件数はどれだけ違うのか

シミュレーション。架空の顧客（特徴量4つ）。配らなくても買う人、配ると買う人、配ると逆に買わなくなる人が混ざる。
  配らないときの購入確率：logit p0 = -2.2 + 1.3 x1 + 0.6 x2
  配ったときの購入確率：  logit p1 = logit p0 + (0.25 + 0.8 x3 - 0.7 x1)
学習用：無作為に半分に配った2万人。評価：新しい10万人のうち上位から配り、増えた購入（本当の p1−p0 の合計）を数える。
  R 反応率のモデル：配った人だけで P(買う|配った) を当て、高い順に配る
  U 2つのモデルの差（アップリフト）：配った人・配らない人で別に当て、差の大きい順に配る
  参考：無作為、本当の差の順（後から分かる最善）
50回くり返す。seed 667。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 667）"
rng = np.random.default_rng(667)
sig = lambda z: 1 / (1 + np.exp(-z))
def probs(X):
    l0 = -2.2 + 1.3 * X[:, 0] + 0.6 * X[:, 1]
    return sig(l0), sig(l0 + 0.25 + 0.8 * X[:, 2] - 0.7 * X[:, 0])
NTR, NEV, REPS = 20000, 100000, 50
SH = np.array([0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
rows, sel_rows = [], []
for rep in range(REPS):
    X = rng.normal(size=(NTR, 4)); t = rng.random(NTR) < 0.5
    p0, p1 = probs(X); y = rng.random(NTR) < np.where(t, p1, p0)
    mT = LogisticRegression(C=1e6, max_iter=1000).fit(X[t], y[t]); mC = LogisticRegression(C=1e6, max_iter=1000).fit(X[~t], y[~t])
    Z = rng.normal(size=(NEV, 4)); q0, q1 = probs(Z); up = q1 - q0
    sc = {"R": mT.predict_proba(Z)[:, 1], "U": mT.predict_proba(Z)[:, 1] - mC.predict_proba(Z)[:, 1], "best": up, "random": rng.random(NEV)}
    for k, s in sc.items():
        o = np.argsort(-s, kind="stable"); cu = np.cumsum(up[o])
        for f in SH:
            n = int(round(NEV * f)); rows.append({"rep": rep, "method": k, "share": f, "incr": float(cu[n - 1])})
        top = o[:NEV // 5]
        sel_rows.append({"rep": rep, "method": k, "p0_mean": float(q0[top].mean()), "uplift_mean": float(up[top].mean()),
                         "neg_share": float((up[top] < 0).mean()), "sure_share": float((q0[top] > 0.5).mean())})
    if rep == 0:
        pop = {"p0_mean": float(q0.mean()), "uplift_mean": float(up.mean()), "neg_share": float((up < 0).mean()), "sure_share": float((q0 > 0.5).mean())}
D = pd.DataFrame(rows); D.to_csv(RES / "incremental.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
S = pd.DataFrame(sel_rows); S.round(5).to_csv(RES / "selected_top20.csv", index=False)
M = D.groupby(["method", "share"]).incr.agg(["mean", lambda s: s.quantile(0.1), lambda s: s.quantile(0.9)]); M.columns = ["mean", "q10", "q90"]
M.round(2).to_csv(RES / "summary.csv")
g = lambda k, f: float(M.loc[(k, f), "mean"])
out = {"n_train": NTR, "n_eval": NEV, "reps": REPS, "population": {k: round(v, 4) for k, v in pop.items()},
       "incr_all_treated": round(g("best", 1.0), 1),
       "at_share": {f"{int(f * 100)}%": {k: round(g(k, f), 1) for k in ["R", "U", "random", "best"]} for f in [0.1, 0.2, 0.3, 0.5]},
       "top20_selected": {k: {c: round(float(S[S.method == k][c].mean()), 4) for c in ["p0_mean", "uplift_mean", "neg_share", "sure_share"]} for k in ["R", "U", "random", "best"]},
       "U_beats_R_at20_share": round(float((D[(D.method == "U") & (D.share == 0.2)].incr.values > D[(D.method == "R") & (D.share == 0.2)].incr.values).mean()), 3),
       "peak": {k: {"share": float(M.loc[k]["mean"].idxmax()), "incr": round(float(M.loc[k]["mean"].max()), 1)} for k in ["R", "U", "best"]}}
out["at_share"]["20%"]["U_over_R_ratio"] = round(g("U", 0.2) / g("R", 0.2), 2)
json.dump(out, open(RES / "a667_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：配る割合と増えた購入
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.concatenate([[0], SH * 100])
for k, lab, col, ls in [("best", "本当の差の順（後から分かる最善）", GRAY, "--"), ("U", "2つのモデルの差（アップリフト）", BLUE, "-"), ("R", "反応率のモデル", ORANGE, "-"), ("random", "無作為", LIGHT, "-")]:
    ax.plot(x, np.concatenate([[0], M.loc[k]["mean"].values]) / 1000, color=col, ls=ls, marker="o" if ls == "-" else None, ms=3.5, label=lab)
ax.set_xlabel("10万人のうち配った割合（%、上位から）"); ax.set_ylabel("増えた購入（千件）")
ax.legend(frameon=False, fontsize=9); ax.set_title("反応率の高い順に配ると、増える購入はアップリフトの半分以下にとどまる")
save(fig, "a667_curve.png", SRC)
# 図2：上位20%
fig, ax = plt.subplots(figsize=(8.5, 3.2))
lab = ["反応率のモデル", "無作為", "2つのモデルの差", "本当の差の順"]; ks = ["R", "random", "U", "best"]
v = [g(k, 0.2) for k in ks]; lo = [g(k, 0.2) - M.loc[(k, 0.2), "q10"] for k in ks]; hi = [M.loc[(k, 0.2), "q90"] - g(k, 0.2) for k in ks]
ax.barh(lab[::-1], v[::-1], xerr=[lo[::-1], hi[::-1]], color=[ORANGE, LIGHT, BLUE, GRAY][::-1], capsize=3)
for i, xv in enumerate(v[::-1]):
    ax.text(xv + hi[::-1][i], i, f"  {xv:,.0f}件", va="center", fontsize=9)
ax.set_xlim(0, max(v) * 1.3); ax.set_xlabel("上位20%（2万人）に配ったときに増えた購入（件、横線は10〜90%）")
ax.set_title("上位20%に配ると、アップリフトは反応率のモデルの約2倍増やす")
save(fig, "a667_top20.png", SRC, y=-0.06)
# 図3：選ばれた人
fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.4))
for ax, c, t, sc in [(axs[0], "p0_mean", "配らなくても買う確率（平均）", 100), (axs[1], "uplift_mean", "配ると増える確率（平均）", 100)]:
    vv = [out["top20_selected"][k][c] * sc for k in ks] + [out["population"][c] * sc]
    ax.bar(["反応率", "無作為", "差", "最善"], vv[:4], color=[ORANGE, LIGHT, BLUE, GRAY])
    for i, val in enumerate(vv[:4]):
        ax.text(i, val, f"{val:.1f}", ha="center", va="bottom", fontsize=9)
    ax.set_title(t, fontsize=11); ax.set_ylabel("%"); ax.set_ylim(min(0, min(vv)) * 1.2, max(vv) * 1.2)
fig.suptitle("反応率のモデルが選ぶのは、配らなくても買う人", fontsize=13)
fig.tight_layout()
save(fig, "a667_who.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
