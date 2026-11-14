"""788 変数選びを交差検証の前に全部のデータでやると、関係のないデータでも正解率はどれだけ高く出るのか

架空のデータ。100件、y は 0/1 を半分ずつ、x は y と無関係な正規乱数（変数の数 p を 50〜2,000 に変える）。
本当の正解率は50%。y との差が大きい変数を k 個（f 検定の上位）選んでからロジスティック回帰を当てはめ、
  先に選ぶ：全部のデータで k 個選んでから、5-fold の交差検証
  中で選ぶ：fold ごとに学習データだけで選ぶ（Pipeline）
の正解率を比べる。各 p で50回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 788）"
rng = np.random.default_rng(788)
N, R = 100, 50
PS = [50, 200, 500, 1000, 2000]
KS = [5, 20, 50]


def run(p, k, seed):
    r = np.random.default_rng(seed)
    X = r.standard_normal((N, p)); y = np.r_[np.zeros(N // 2), np.ones(N // 2)].astype(int)
    cv = StratifiedKFold(5, shuffle=True, random_state=seed % 100000)
    lr = LogisticRegression(max_iter=500)
    Xs = SelectKBest(f_classif, k=k).fit_transform(X, y)
    leak = cross_val_score(lr, Xs, y, cv=cv).mean()
    honest = cross_val_score(make_pipeline(SelectKBest(f_classif, k=k), lr), X, y, cv=cv).mean()
    return leak, honest


rows = []
seeds = rng.integers(0, 2**31, size=(len(PS), len(KS), R))
for i, p in enumerate(PS):
    for j, k in enumerate(KS):
        if k > p: continue
        v = np.array([run(p, k, int(seeds[i, j, t])) for t in range(R)])
        rows.append(dict(p=p, k=k, leak=v[:, 0].mean(), honest=v[:, 1].mean(), leak_p10=np.quantile(v[:, 0], .1),
                         leak_p90=np.quantile(v[:, 0], .9), honest_p10=np.quantile(v[:, 1], .1), honest_p90=np.quantile(v[:, 1], .9),
                         leak_ge70=float((v[:, 0] >= .7).mean())))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
g = lambda p, k, c: float(S[(S.p == p) & (S.k == k)][c].iloc[0])
out = {"n": N, "reps": R, "true_accuracy": 0.5,
       "by": {f"p{p}_k{k}": {"leak": round(g(p, k, "leak"), 3), "honest": round(g(p, k, "honest"), 3)} for p in PS for k in KS if k <= p},
       "p2000_k20_leak": g(2000, 20, "leak"), "p2000_k20_honest": g(2000, 20, "honest"), "p2000_k20_leak_ge70": g(2000, 20, "leak_ge70"),
       "p50_k20_leak": g(50, 20, "leak"), "p2000_k5_leak": g(2000, 5, "leak"), "p2000_k50_leak": g(2000, 50, "leak"),
       "honest_range": [float(S.honest.min()), float(S.honest.max())], "leak_max": float(S.leak.max())}
json.dump(out, open(RES / "a788_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：変数の数と正解率（k=20）
s = S[S.k == 20]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.plot(s.p, s.leak, "o-", color=ORANGE, label="先に全部のデータで選ぶ"); ax.fill_between(s.p, s.leak_p10, s.leak_p90, color=ORANGE, alpha=.15)
ax.plot(s.p, s.honest, "o-", color=BLUE, label="fold の中で選ぶ"); ax.fill_between(s.p, s.honest_p10, s.honest_p90, color=BLUE, alpha=.15)
ax.axhline(.5, color=GRAY, ls="--", lw=.8); ax.text(s.p.max(), .51, "本当の正解率 50%", ha="right", fontsize=9, color=GRAY)
ax.set_xscale("log"); ax.set_xticks(PS); ax.set_xticklabels(PS); ax.set_ylim(.3, 1.0)
ax.set_xlabel("候補の変数の数（どれも y と無関係）"); ax.set_ylabel("交差検証の正解率")
ax.legend(frameon=False, loc="upper left"); ax.set_title("関係のない変数でも、先に選ぶと候補が多いほど正解率が上がって見える（20個選ぶ、帯は80%）")
save(fig, "a788_by_p.png", SRC)

# 図2：選ぶ数 k ごと（p=2000）
fig, ax = plt.subplots(figsize=(8, 4.4)); s = S[S.p == 2000]; x = np.arange(len(s)); w = .38
ax.bar(x - w / 2, s.leak, w, color=ORANGE, label="先に選ぶ"); ax.bar(x + w / 2, s.honest, w, color=BLUE, label="fold の中で選ぶ")
for xi, a, b in zip(x, s.leak, s.honest):
    ax.text(xi - w / 2, a + .01, f"{a:.0%}", ha="center", fontsize=9); ax.text(xi + w / 2, b + .01, f"{b:.0%}", ha="center", fontsize=9)
ax.axhline(.5, color=GRAY, ls="--", lw=.8); ax.set_xticks(x); ax.set_xticklabels([f"{k}個選ぶ" for k in s.k]); ax.set_ylim(0, 1.05)
ax.set_ylabel("交差検証の正解率"); ax.legend(frameon=False); ax.set_title("候補2,000個から選ぶとき：何個選んでも、先に選ぶと大きく見える")
save(fig, "a788_by_k.png", SRC)

# 図3：1回分の、選んだ変数と y の差（学習に使ったデータ vs 新しいデータ）
r = np.random.default_rng(7880); X = r.standard_normal((N, 2000)); y = np.r_[np.zeros(N // 2), np.ones(N // 2)].astype(int)
F, _ = f_classif(X, y); top = np.argsort(F)[::-1][:20]
Xn = r.standard_normal((N, 2000)); Fn, _ = f_classif(Xn, y)
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.hist(F, bins=60, color=LIGHT, label="2,000個すべて（選んだデータで）")
ax.scatter(F[top], np.full(20, 5), color=ORANGE, zorder=3, s=25, label="選んだ20個（選んだデータで）")
ax.scatter(Fn[top], np.full(20, 15), color=BLUE, zorder=3, s=25, label="同じ20個（新しいデータで）")
ax.set_xlabel("y の0と1での差の大きさ（F 値）"); ax.set_ylabel("変数の数"); ax.legend(frameon=False)
ax.set_title("選んだ20個は、選んだデータでだけ差が大きい。新しいデータではふつうに戻る")
save(fig, "a788_selected_f.png", SRC)
print(S.round(3).to_string())
