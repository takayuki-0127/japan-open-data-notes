"""770 傾向スコアか結果のモデルのどちらかがまちがっているとき、二重に頑健な推定はどれだけずれるのか

架空のデータ。x1・x2 は標準正規。施策を受ける確率は logistic(−0.9 + 0.8·x1 + 0.6·x1²)（x1 の2乗が効く）、
結果は y = 1 + 2·施策 + 1.5·x1 + 1.0·x1² + 0.5·x2 + N(0,1)。本当の効果は2。
「正しいモデル」は x1² を入れたもの、「まちがったモデル」は x1² を入れないもの。
傾向スコアと結果のモデルを、それぞれ正しい・まちがいの4通りにして、
回帰の調整（結果のモデルだけ）・逆確率の重み（傾向スコアだけ、重みは正規化）・二重に頑健な推定（AIPW）を比べる。2,000件、各400回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 770）"
rng = np.random.default_rng(770)
N, R, TAU = 2000, 400, 2.0


def make():
    x1, x2 = rng.standard_normal(N), rng.standard_normal(N)
    p = 1 / (1 + np.exp(-(-0.9 + 0.8 * x1 + 0.6 * x1 ** 2)))
    t = (rng.random(N) < p).astype(float)
    y = 1 + TAU * t + 1.5 * x1 + 1.0 * x1 ** 2 + 0.5 * x2 + rng.standard_normal(N)
    return x1, x2, t, y


def feats(x1, x2, right): return np.c_[x1, x2, x1 ** 2] if right else np.c_[x1, x2]


def estimate(x1, x2, t, y, ps_right, out_right):
    Zp = feats(x1, x2, ps_right)
    e = LogisticRegression(C=1e6, max_iter=500).fit(Zp, t).predict_proba(Zp)[:, 1]
    e = np.clip(e, .01, .99)
    Zo = np.c_[np.ones(N), feats(x1, x2, out_right)]
    m1 = Zo @ np.linalg.lstsq(Zo[t == 1], y[t == 1], rcond=None)[0]
    m0 = Zo @ np.linalg.lstsq(Zo[t == 0], y[t == 0], rcond=None)[0]
    reg = np.mean(m1 - m0)
    w1, w0 = t / e, (1 - t) / (1 - e)
    ipw = np.sum(w1 * y) / np.sum(w1) - np.sum(w0 * y) / np.sum(w0)
    aipw = np.mean(m1 - m0 + t * (y - m1) / e - (1 - t) * (y - m0) / (1 - e))
    return reg, ipw, aipw


CASES = [("両方正しい", True, True), ("傾向スコアがまちがい", False, True), ("結果のモデルがまちがい", True, False), ("両方まちがい", False, False)]
rows = []
naive = []
for r in range(R):
    x1, x2, t, y = make()
    naive.append(y[t == 1].mean() - y[t == 0].mean())
    for name, pr, orr in CASES:
        reg, ipw, aipw = estimate(x1, x2, t, y, pr, orr)
        rows.append(dict(rep=r, case=name, reg=reg, ipw=ipw, aipw=aipw))
D = pd.DataFrame(rows)
D.to_csv(RES / "reps.csv", index=False, float_format="%.5f")
S = D.groupby("case", sort=False)[["reg", "ipw", "aipw"]].agg(["mean", "std"])
S.columns = [f"{a}_{b}" for a, b in S.columns]
S = S.reset_index(); S.to_csv(RES / "summary.csv", index=False)
out = {"n": N, "reps": R, "true_effect": TAU, "naive_mean": float(np.mean(naive)),
       "by_case": {r.case: {k: round(getattr(r, k), 3) for k in S.columns[1:]} for r in S.itertuples()}}
json.dump(out, open(RES / "a770_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：4通りの平均
fig, ax = plt.subplots(figsize=(10, 4.8)); x = np.arange(len(S)); w = .27
for j, (k, l, c) in enumerate([("reg", "回帰の調整", BLUE), ("ipw", "逆確率の重み", ORANGE), ("aipw", "二重に頑健", GREEN)]):
    b = ax.bar(x + (j - 1) * w, S[f"{k}_mean"], w, color=c, label=l)
    for bb, v in zip(b, S[f"{k}_mean"]): ax.text(bb.get_x() + w / 2, v + .03, f"{v:.2f}", ha="center", fontsize=8)
ax.axhline(TAU, color=GRAY, ls="--"); ax.text(len(S) - .5, TAU + .03, "本当の効果 2", ha="right", color=GRAY)
ax.set_xticks(x); ax.set_xticklabels(S.case); ax.set_ylabel("効果の推定（400回の平均）")
ax.set_ylim(0, max(S[["reg_mean", "ipw_mean", "aipw_mean"]].max()) * 1.15)
ax.legend(frameon=False, loc="lower left"); ax.set_title("片方が正しければ、二重に頑健な推定はほぼ2に戻る")
save(fig, "a770_means.png", SRC)

# 図2：ばらつき
fig, ax = plt.subplots(figsize=(10, 4.6))
for j, (k, l, c) in enumerate([("reg", "回帰の調整", BLUE), ("ipw", "逆確率の重み", ORANGE), ("aipw", "二重に頑健", GREEN)]):
    ax.bar(x + (j - 1) * w, S[f"{k}_std"], w, color=c, label=l)
ax.set_xticks(x); ax.set_xticklabels(S.case); ax.set_ylabel("推定の標準偏差（400回）")
ax.legend(frameon=False); ax.set_title("ばらつきは、逆確率の重みがいちばん大きい")
save(fig, "a770_sd.png", SRC)

# 図3：分布（結果のモデルがまちがい）
fig, ax = plt.subplots(figsize=(9, 4.6))
s = D[D.case == "結果のモデルがまちがい"]
bins = np.linspace(min(s[["reg", "ipw", "aipw"]].min()), max(s[["reg", "ipw", "aipw"]].max()), 50)
for k, l, c in [("reg", "回帰の調整", BLUE), ("ipw", "逆確率の重み", ORANGE), ("aipw", "二重に頑健", GREEN)]:
    ax.hist(s[k], bins=bins, color=c, alpha=.5, label=l)
ax.axvline(TAU, color="black", lw=1.2); ax.set_xlabel("効果の推定"); ax.set_ylabel("回数")
ax.legend(frameon=False); ax.set_title("結果のモデルがまちがいのとき：回帰の調整だけが2から離れる")
save(fig, "a770_hist.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
