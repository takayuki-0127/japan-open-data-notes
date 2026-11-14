"""700 選択肢を1つ足したとき、多項ロジットは他の選択肢のシェアをどう奪うと見て、本当の動きとどれだけずれるのか

架空の商品 A・B・C。B と C はよく似た商品（同じ種類の色違い）、A は別の種類。
本当の選び方：入れ子ロジット（B と C が同じ入れ子、λ＝0.3。λ が小さいほど B と C は似ている）。
  効用の確定部分 V_j＝定数_j − 1.0×価格_j（定数 A 0、B 0.2、C 0.2）
学習データ：2万人。それぞれ {A,B} か {A,B,C} の棚を見て（半々）、価格は 2〜3 の一様乱数。
多項ロジット（MNL）と入れ子ロジット（NL）を最尤法で当てはめ、
「A・B だけの棚（価格はどれも2.5）に C を足す」ときのシェアを、本当の値と比べる。
λ を 0.1〜1.0 に変えたときのずれも数える。seed 700。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の商品の選択（作成者が乱数で作成、seed 700）"
rng = np.random.default_rng(700)
N = 20000
ASC = np.array([0.0, 0.2, 0.2]); BETA = 1.0
NM = ["A", "B", "C"]


def probs(asc, beta, lam, P, avail):
    """入れ子ロジットの確率（lam=1 なら多項ロジット）。P: 価格 (n,3)、avail: 棚にあるか (n,3)"""
    V = asc[None, :] - beta * P
    eA = np.exp(V[:, 0])
    eN = np.where(avail[:, 1:], np.exp(V[:, 1:] / lam), 0.0)
    S = eN.sum(1); IV = np.exp(lam * np.log(S))
    pN = IV / (eA + IV)
    return np.column_stack([1 - pN, pN * eN[:, 0] / S, pN * eN[:, 1] / S])


def simulate(lam):
    P = rng.uniform(2, 3, (N, 3)); avail = np.ones((N, 3), bool); avail[:, 2] = rng.random(N) < 0.5
    pr = probs(ASC, BETA, lam, P, avail)
    u = rng.random(N); ch = (u[:, None] > np.cumsum(pr, 1)).sum(1)
    return P, avail, np.minimum(ch, 2)


def fit(P, avail, ch, nested):
    def nll(th):
        asc = np.array([0.0, th[0], th[1]]); lam = 1 / (1 + np.exp(-th[3])) if nested else 1.0
        pr = probs(asc, th[2], lam, P, avail)
        return -np.log(np.clip(pr[np.arange(len(ch)), ch], 1e-300, None)).sum()
    r = minimize(nll, np.array([0.0, 0.0, 0.5, 0.0]), method="BFGS")
    th = r.x; lam = 1 / (1 + np.exp(-th[3])) if nested else 1.0
    return np.array([0.0, th[0], th[1]]), th[2], lam, r.fun


Pq = np.full((1, 3), 2.5)
two = np.array([[True, True, False]]); three = np.ones((1, 3), bool)


def scenario(asc, beta, lam):
    return probs(asc, beta, lam, Pq, two)[0], probs(asc, beta, lam, Pq, three)[0]


LAM = 0.3
P, avail, ch = simulate(LAM)
mnl = fit(P, avail, ch, False); nl = fit(P, avail, ch, True)
res = {}
for k, (a, b, l) in {"本当": (ASC, BETA, LAM), "多項ロジット": mnl[:3], "入れ子ロジット": nl[:3]}.items():
    before, after = scenario(a, b, l)
    res[k] = {"before": before, "after": after, "from_A": (before[0] - after[0]) / after[2] * 100 if after[2] > 0 else np.nan}
rows = [{"model": k, "when": w, **{NM[j]: v[w][j] * 100 for j in range(3)}} for k, v in res.items() for w in ["before", "after"]]
T = pd.DataFrame(rows); T.round(3).to_csv(RES / "shares.csv", index=False)

# λ を変える
lrows = []
for lam in [0.1, 0.3, 0.5, 0.7, 1.0]:
    P_, a_, c_ = simulate(lam); m = fit(P_, a_, c_, False); n_ = fit(P_, a_, c_, True)
    tb, ta = scenario(ASC, BETA, lam); mb, ma = scenario(*m[:3]); nb, na = scenario(*n_[:3])
    lrows.append({"lam": lam, "true_A_after": ta[0] * 100, "mnl_A_after": ma[0] * 100, "nl_A_after": na[0] * 100,
                  "true_A_before": tb[0] * 100, "nl_lam_hat": n_[2], "lr_stat": 2 * (m[3] - n_[3])})
L = pd.DataFrame(lrows); L.round(3).to_csv(RES / "by_lambda.csv", index=False)

r1 = lambda x: round(float(x), 1)
out = {"n": N, "lambda_true": LAM,
       "mnl": {"ascB": round(float(mnl[0][1]), 3), "ascC": round(float(mnl[0][2]), 3), "beta": round(float(mnl[1]), 3)},
       "nl": {"ascB": round(float(nl[0][1]), 3), "ascC": round(float(nl[0][2]), 3), "beta": round(float(nl[1]), 3), "lambda": round(float(nl[2]), 3)},
       "lr_stat_nl_vs_mnl": round(float(2 * (mnl[3] - nl[3])), 1),
       "shares": {k: {"before": [r1(x * 100) for x in v["before"]], "after": [r1(x * 100) for x in v["after"]], "C_from_A_pct": r1(v["from_A"])} for k, v in res.items()},
       "by_lambda": [{"lam": r.lam, "true_A_after": r1(r.true_A_after), "mnl_A_after": r1(r.mnl_A_after), "nl_A_after": r1(r.nl_A_after), "nl_lam_hat": round(float(r.nl_lam_hat), 3)} for r in L.itertuples()]}
json.dump(out, open(RES / "a700_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：Cを足す前後のシェア
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharey=True)
cA, cB, cC = GRAY, BLUE, LIGHT
for ax, k in zip(axes, ["本当", "多項ロジット", "入れ子ロジット"]):
    for i, w in enumerate(["before", "after"]):
        s = res[k][w] * 100; bottom = 0
        for j, c in enumerate([cA, cB, cC]):
            if s[j] > 0.05:
                ax.bar(i, s[j], 0.6, bottom=bottom, color=c, label=f"商品{NM[j]}" if i == 1 else None)
                ax.text(i, bottom + s[j] / 2, f"{NM[j]} {s[j]:.1f}%", ha="center", va="center", fontsize=9)
            bottom += s[j]
    ax.set_xticks([0, 1]); ax.set_xticklabels(["A・B だけ", "C を足す"]); ax.set_title(k)
axes[0].set_ylabel("シェア（%）"); axes[2].legend(frameon=False, fontsize=8.5, loc="upper right", bbox_to_anchor=(1.35, 1))
fig.suptitle("よく似た C を足すと、本当は主に B のシェアを分け合う。多項ロジットは A からも同じ割合で奪うと見る", y=1.02)
save(fig, "a700_shares.png", SRC)

# 図2：C のシェアはどこから来たか
fig, ax = plt.subplots(figsize=(8, 3.4))
ks = ["本当", "多項ロジット", "入れ子ロジット"]; fa = [res[k]["from_A"] for k in ks]
ax.barh(ks[::-1], [100] * 3, color=BLUE, label="B から")
ax.barh(ks[::-1], fa[::-1], color=GRAY, label="A から")
for i, v in enumerate(fa[::-1]): ax.text(v + 1, i, f"A から {v:.1f}%", va="center", fontsize=9.5, color=INK)
ax.set_xlim(0, 100); ax.set_xlabel("C が取ったシェアの内訳（%）"); ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1.0, 1.18), ncol=2)
ax.set_title("C のシェアのうち、A から来た分", loc="left")
save(fig, "a700_source.png", SRC)

# 図3：λ ごとの A のシェア（C を足したあと）
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(L.lam, L.true_A_after, marker="o", color=INK, label="本当")
ax.plot(L.lam, L.mnl_A_after, marker="s", color=ORANGE, label="多項ロジットの予測")
ax.plot(L.lam, L.nl_A_after, marker="^", color=GREEN, ls="--", label="入れ子ロジットの予測")
ax.set_xlabel("B と C の似ている度合い λ（小さいほどよく似ている。1は似ていない）"); ax.set_ylabel("C を足したあとの A のシェア（%）")
ax.set_xticks(L.lam); ax.legend(frameon=False, fontsize=9)
ax.set_title("B と C が似ているほど、多項ロジットは A のシェアを小さく見積もる")
save(fig, "a700_by_lambda.png", SRC)
print(json.dumps(out, ensure_ascii=False))
