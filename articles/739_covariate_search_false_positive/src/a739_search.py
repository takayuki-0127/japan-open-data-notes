"""739 入れる変数の組み合わせを有意になるまで探すと、効果が0の施策でも何%で「有意」になるのか

架空の店200店。施策は無作為に半分の店へ。施策の本当の効果は0。
売上は、候補の変数 k 個（各店の広さ・客層など、どれも売上に少し効く）とばらつきで決まる。
入れる変数の組み合わせ（2^k 通り）をすべて試し、施策の p 値が最も小さい式を選ぶ。
  決めた式：候補をすべて入れた式1本だけ
  探す：2^k 通りの中で p<0.05 が1つでもあれば「有意」
  分けて確かめる：半分の店で探し、選んだ式を残り半分の店で1回だけ検定
k＝0〜8、各600回。
"""
import json
from itertools import combinations
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 739）"
rng = np.random.default_rng(739)
N, R = 200, 600
KS = [0, 1, 2, 4, 6, 8]


def p_treat(Y, T, Z):
    X = np.column_stack([np.ones(len(Y)), T] + ([Z] if Z.shape[1] else []))
    b, *_ = np.linalg.lstsq(X, Y, rcond=None)
    e = Y - X @ b; df = len(Y) - X.shape[1]
    s2 = e @ e / df
    se = np.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
    return 2 * stats.t.sf(abs(b[1] / se), df)


def subsets(k):
    out = []
    for r in range(k + 1):
        out += [list(c) for c in combinations(range(k), r)]
    return out


rows = []; minp8 = []
for k in KS:
    subs = subsets(k)
    fixed = searched = split = 0
    for rep in range(R):
        T = (rng.random(N) < .5).astype(float)
        Z = rng.standard_normal((N, k))
        Y = Z @ np.full(k, .3) + rng.standard_normal(N) if k else rng.standard_normal(N)
        ps = np.array([p_treat(Y, T, Z[:, s]) for s in subs])
        fixed += ps[-1] < .05
        searched += ps.min() < .05
        if k == 8:
            minp8.append(ps.min())
        h = rng.permutation(N); a, b = h[:N // 2], h[N // 2:]
        pa = [p_treat(Y[a], T[a], Z[a][:, s]) for s in subs]
        best = subs[int(np.argmin(pa))]
        split += p_treat(Y[b], T[b], Z[b][:, best]) < .05
    rows.append(dict(k=k, n_models=len(subs), fixed=fixed / R, searched=searched / R, split=split / R))
    print(rows[-1], flush=True)
S = pd.DataFrame(rows); S.to_csv(RES / "by_k.csv", index=False)
minp8 = np.array(minp8)
out = {"stores": N, "reps": R, "true_effect": 0,
       "by_k": {int(r.k): {"models": int(r.n_models), "fixed": float(r.fixed), "searched": float(r.searched), "split": float(r.split)} for r in S.itertuples()},
       "k8_searched": float(S.searched.iloc[-1]), "k4_searched": float(S[S.k == 4].searched.iloc[0]),
       "k8_fixed": float(S.fixed.iloc[-1]), "k8_split": float(S.split.iloc[-1]),
       "k8_minp_median": float(np.median(minp8))}
json.dump(out, open(RES / "a739_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：候補の数と偽の有意
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(S.k, S.searched * 100, "o-", color=ORANGE, label="組み合わせを探す（どれか1つでも p<0.05）")
ax.plot(S.k, S.fixed * 100, "o-", color=BLUE, label="決めた式1本")
ax.axhline(5, color=GRAY, ls="--", lw=1); ax.text(0, 5.6, "決めた水準 5%", color=GRAY, fontsize=9)
for x, y in zip(S.k, S.searched):
    ax.text(x, y * 100 + 1, f"{y * 100:.1f}%", ha="center", fontsize=9, color=ORANGE)
ax.set_xlabel("候補の変数の数（試す式は 2^k 通り）"); ax.set_ylabel("効果0なのに「有意」の割合（%）")
ax.legend(frameon=False, loc="upper left"); ax.set_ylim(0, max(S.searched) * 100 * 1.3)
ax.set_title("候補の変数が増えるほど、探せば「有意」が見つかる（各600回）")
save(fig, "a739_by_k.png", SRC)

# 図2：最小の p 値の分布（k=8）
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.hist(minp8, bins=np.linspace(0, 1, 41), color=ORANGE)
ax.axvline(.05, color=GRAY, ls="--"); ax.text(.06, ax.get_ylim()[1] * .9, "0.05", color=GRAY)
ax.set_xlabel(f"256通りの式の中で最も小さい p 値"); ax.set_ylabel("回数")
ax.set_title(f"候補8個：最も小さい p 値は0の側に寄る（中央値 {np.median(minp8):.2f}）")
save(fig, "a739_minp.png", SRC)

# 図3：分けて確かめる
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(S)); w = .27
for j, (c, l, colr) in enumerate([("searched", "探す（全店）", ORANGE), ("split", "半分で探し、残り半分で確かめる", GREEN), ("fixed", "決めた式1本", BLUE)]):
    ax.bar(x + (j - 1) * w, S[c] * 100, w, color=colr, label=l)
ax.axhline(5, color=GRAY, ls="--", lw=1)
ax.set_xticks(x); ax.set_xticklabels([f"{k}個" for k in S.k]); ax.set_xlabel("候補の変数の数")
ax.set_ylabel("効果0なのに「有意」の割合（%）"); ax.legend(frameon=False, loc="upper left")
ax.set_title("探した式を別の店で1回だけ確かめると、5%前後に戻る")
save(fig, "a739_split.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
