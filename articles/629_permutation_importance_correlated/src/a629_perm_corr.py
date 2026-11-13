"""629 相関の強い2つの列があると、並べ替えの重要度はどれだけ小さく出るのか

架空の店のデータ（学習 1,000件・確かめ 1,000件）。売上に効くのは x1（効き 1.0）と x3（効き 0.5）。
x2 は x1 と相関 ρ を持つが、売上には効かない（x1 の「近い親戚」の列）。x4 は何とも関係ない。
ρ = 0・0.5・0.8・0.95・0.99 で、ランダムフォレスト（150本）について次の重要度を比べる（確かめデータの R² の下がり方）：
  並べ替えの重要度（1列ずつ）、x1 と x2 をまとめて並べ替えた重要度、列を外して学習し直したときの差（x1 を外す）
各 ρ で 12回。数字は置いたデータで決まる。
"""
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の店のデータ（作成者が乱数で作成、seed 629）"
rng = np.random.default_rng(629)
N, REPS, RHOS = 1000, 12, [0.0, 0.5, 0.8, 0.95, 0.99]
COLS = ["x1", "x2", "x3", "x4"]


def make(n, rho, rng):
    x1 = rng.normal(0, 1, n); x2 = rho * x1 + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, n)
    x3 = rng.normal(0, 1, n); x4 = rng.normal(0, 1, n)
    y = 1.0 * x1 + 0.5 * x3 + rng.normal(0, 0.7, n)
    return np.column_stack([x1, x2, x3, x4]), y


def perm_drop(model, X, y, cols, rng, k=5):
    base = r2_score(y, model.predict(X)); d = []
    for _ in range(k):
        Xp = X.copy(); idx = rng.permutation(len(X))
        Xp[:, cols] = X[idx][:, cols]
        d.append(base - r2_score(y, model.predict(Xp)))
    return float(np.mean(d))


rows = []
for rho in RHOS:
    for r in range(REPS):
        Xtr, ytr = make(N, rho, rng); Xte, yte = make(N, rho, rng)
        rf = RandomForestRegressor(n_estimators=150, min_samples_leaf=5, random_state=r, n_jobs=1).fit(Xtr, ytr)
        rec = {"rho": rho, "rep": r, "r2": r2_score(yte, rf.predict(Xte))}
        for j, c in enumerate(COLS):
            rec[f"perm_{c}"] = perm_drop(rf, Xte, yte, [j], rng)
        rec["perm_x1x2"] = perm_drop(rf, Xte, yte, [0, 1], rng)
        rf_d = RandomForestRegressor(n_estimators=150, min_samples_leaf=5, random_state=r, n_jobs=1).fit(Xtr[:, 1:], ytr)
        rec["drop_x1"] = rec["r2"] - r2_score(yte, rf_d.predict(Xte[:, 1:]))
        rows.append(rec)
R = pd.DataFrame(rows); R.round(5).to_csv(RES / "reps.csv", index=False)
S = R.groupby("rho").mean().drop(columns="rep"); S.round(4).to_csv(RES / "summary.csv")
out = {"reps": REPS, "n": N, "summary": S.round(4).to_dict(orient="index"),
       "x1_perm_vs_rho0_pct": {str(k): round(float(100 * (S.loc[k, "perm_x1"] / S.loc[0.0, "perm_x1"] - 1)), 1) for k in RHOS}}
json.dump(out, open(RES / "a629_main.json", "w"), ensure_ascii=False, indent=1)

xs = np.arange(len(RHOS)); xl = [f"ρ={r}" for r in RHOS]
# 図1：1列ずつの並べ替えの重要度
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for c, col, lab in [("perm_x1", BLUE, "x1（効く 1.0）"), ("perm_x2", ORANGE, "x2（効かない、x1 と相関）"), ("perm_x3", GREEN, "x3（効く 0.5）"), ("perm_x4", GRAY, "x4（効かない）")]:
    ax.plot(xs, S[c], marker="o", color=col, label=lab)
for x, v in zip(xs, S.perm_x1):
    ax.text(x, v + 0.02, f"{v:.2f}", ha="center", fontsize=8.5, color=BLUE)
ax.set_xticks(xs); ax.set_xticklabels(xl); ax.set_xlabel("x1 と x2 の相関"); ax.set_ylabel("並べ替えたときの R² の下がり方")
ax.set_title("x1 の重要度は、そっくりな列があるほど小さく出る"); ax.legend(frameon=False, fontsize=9)
save(fig, "a629_perm_by_rho.png", SRC)

# 図2：3通りの x1 の測り方
fig, ax = plt.subplots(figsize=(8.5, 4.2))
w = 0.26
for j, (c, col, lab) in enumerate([("perm_x1", BLUE, "x1 だけ並べ替え"), ("perm_x1x2", ORANGE, "x1 と x2 をまとめて並べ替え"), ("drop_x1", GRAY, "x1 を外して学習し直す")]):
    ax.bar(xs + (j - 1) * w, S[c], w, color=col, label=lab)
ax.set_xticks(xs); ax.set_xticklabels(xl); ax.set_ylabel("確かめデータの R² の下がり方"); ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center")
ax.set_ylim(0, 1.4); ax.set_title("x1 の効き目を3通りで測ると")
save(fig, "a629_three_ways.png", SRC)

# 図3：ρ=0.95 のときのくり返しごとの x1 と x2
s = R[R.rho == 0.95]
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.scatter(s.perm_x1, s.perm_x2, color=BLUE, s=30)
ax.plot([0, 1], [0, 1], ls=":", color=GRAY)
ax.set_xlabel("x1 の並べ替えの重要度"); ax.set_ylabel("x2 の並べ替えの重要度"); ax.set_xlim(0, s.perm_x1.max() * 1.3); ax.set_ylim(0, s.perm_x1.max() * 1.3)
ax.set_title("ρ=0.95：12回の学習ごとの x1 と x2（x2 は効かない列）")
save(fig, "a629_split_reps.png", SRC)
print(S.round(3).to_string())
