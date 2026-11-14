"""760 欠けた値を「-999」で埋めたまま回帰すると、係数はどれだけずれるのか

架空の会員1,000人。y（年間の利用額、万円）= 2 + 0.5・x1（会員歴、年）+ 1.0・x2（月の来店回数）+ 誤差。
x1 の一部（1〜30%、無作為）が欠けていて、システムの決まりで「-999」が入っている。
  A -999 のまま線形回帰、B 平均で埋めて「欠けの印」の列を足す、C 欠けた行を除く
で x1・x2 の係数と、テストデータ（同じ割合で欠ける）での予測の誤差を各300回測る。
参考に、決定木（深さ5）で -999 のまま学習した場合の予測の誤差も出す。seed 760。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeRegressor
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 760）"
rng = np.random.default_rng(760)
N, REPS = 1000, 300
MS = [0.01, 0.05, 0.1, 0.3]
B0, B1, B2, SD = 2.0, 0.5, 1.0, 2.0


def make(n, m):
    x1 = rng.uniform(0, 20, n); x2 = rng.poisson(4, n).astype(float)
    y = B0 + B1 * x1 + B2 * x2 + rng.normal(0, SD, n)
    miss = rng.random(n) < m
    return x1, x2, y, miss


def ols(X, y):
    X1 = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return b


rows = []
for m in MS:
    for r in range(REPS):
        x1, x2, y, miss = make(N, m)
        t1, t2, ty, tmiss = make(N, m)
        # A -999
        a1 = np.where(miss, -999.0, x1); ta1 = np.where(tmiss, -999.0, t1)
        bA = ols(np.column_stack([a1, x2]), y)
        pA = bA[0] + bA[1] * ta1 + bA[2] * t2
        # B 平均で埋めて印
        mu = x1[~miss].mean()
        b1_ = np.where(miss, mu, x1); tb1 = np.where(tmiss, mu, t1)
        bB = ols(np.column_stack([b1_, x2, miss.astype(float)]), y)
        pB = bB[0] + bB[1] * tb1 + bB[2] * t2 + bB[3] * tmiss
        # C 欠けた行を除く（テストの欠けた行は平均で埋めて予測）
        bC = ols(np.column_stack([x1[~miss], x2[~miss]]), y[~miss])
        pC = bC[0] + bC[1] * tb1 + bC[2] * t2
        # 参考：決定木に -999 のまま
        if r < 60:
            tree = DecisionTreeRegressor(max_depth=5, random_state=0).fit(np.column_stack([a1, x2]), y)
            pT = tree.predict(np.column_stack([ta1, t2]))
            treeT = DecisionTreeRegressor(max_depth=5, random_state=0).fit(np.column_stack([np.where(miss, mu, x1), x2, miss]), y)
            pT2 = treeT.predict(np.column_stack([tb1, t2, tmiss]))
            rmT, rmT2 = np.sqrt(np.mean((pT - ty) ** 2)), np.sqrt(np.mean((pT2 - ty) ** 2))
        else:
            rmT = rmT2 = np.nan
        rmse = lambda p: np.sqrt(np.mean((p - ty) ** 2))
        rows.append((m, r, bA[1], bA[2], bB[1], bB[2], bC[1], bC[2], rmse(pA), rmse(pB), rmse(pC), rmT, rmT2))
R = pd.DataFrame(rows, columns=["m", "rep", "A_b1", "A_b2", "B_b1", "B_b2", "C_b1", "C_b2", "A_rmse", "B_rmse", "C_rmse", "tree_999_rmse", "tree_flag_rmse"])
S = R.groupby("m").mean().drop(columns="rep").reset_index()
S.round(4).to_csv(RES / "summary.csv", index=False)
gS = lambda m, c: float(S[S.m == m][c].iloc[0])
# 欠けがないときの誤差（参考）
base = []
for r in range(100):
    x1, x2, y, _ = make(N, 0); t1, t2, ty, _ = make(N, 0)
    b = ols(np.column_stack([x1, x2]), y); base.append(np.sqrt(np.mean((b[0] + b[1] * t1 + b[2] * t2 - ty) ** 2)))
out = {"n": N, "reps": REPS, "true_b1": B1, "true_b2": B2, "noise_sd": SD, "missing_rates": MS,
       "A_b1": {str(m): round(gS(m, "A_b1"), 4) for m in MS}, "A_b2": {str(m): round(gS(m, "A_b2"), 3) for m in MS},
       "B_b1": {str(m): round(gS(m, "B_b1"), 3) for m in MS}, "C_b1": {str(m): round(gS(m, "C_b1"), 3) for m in MS},
       "A_b1_pct_of_true": {str(m): round(gS(m, "A_b1") / B1 * 100, 1) for m in MS},
       "A_rmse": {str(m): round(gS(m, "A_rmse"), 2) for m in MS}, "B_rmse": {str(m): round(gS(m, "B_rmse"), 2) for m in MS},
       "C_rmse": {str(m): round(gS(m, "C_rmse"), 2) for m in MS},
       "tree_999_rmse": {str(m): round(gS(m, "tree_999_rmse"), 2) for m in MS}, "tree_flag_rmse": {str(m): round(gS(m, "tree_flag_rmse"), 2) for m in MS},
       "rmse_no_missing": round(float(np.mean(base)), 2)}
json.dump(out, open(RES / "a760_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1回分のデータの散布図（欠け5%）
rng2 = np.random.default_rng(7600)
x1 = rng2.uniform(0, 20, 400); x2 = rng2.poisson(4, 400); y = B0 + B1 * x1 + B2 * x2 + rng2.normal(0, SD, 400)
miss = rng2.random(400) < 0.05; a1 = np.where(miss, -999, x1)
b = ols(np.column_stack([a1, x2]), y); bt = ols(np.column_stack([x1, x2]), y)
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), gridspec_kw={"width_ratios": [1.6, 1]})
ax = axes[0]
ax.scatter(a1[~miss], y[~miss], s=8, color=BLUE, alpha=0.6, label="値のある会員")
ax.scatter(a1[miss], y[miss], s=14, color=ORANGE, label="欠けて -999 の会員")
xx = np.array([-999, 20]); ax.plot(xx, b[0] + b[1] * xx + b[2] * x2.mean(), color=ORANGE, lw=1.5, label=f"-999 のまま：傾き {b[1]:.4f}")
ax.set_xlabel("会員歴（年、-999 を含む）"); ax.set_ylabel("年間の利用額（万円）"); ax.legend(frameon=False, fontsize=8.5)
ax.set_title("-999 の点が、傾きをほぼ0に引っぱる", fontsize=11.5)
ax = axes[1]
ax.scatter(x1[~miss], y[~miss], s=8, color=BLUE, alpha=0.6)
xx = np.array([0, 20]); ax.plot(xx, bt[0] + bt[1] * xx + bt[2] * x2.mean(), color=GREEN, lw=2, label=f"欠けなし：傾き {bt[1]:.2f}")
ax.plot(xx, b[0] + b[1] * xx + b[2] * x2.mean(), color=ORANGE, lw=2, ls="--", label="-999 のまま")
ax.set_xlabel("会員歴（年）"); ax.legend(frameon=False, fontsize=8.5); ax.set_title("0〜20年の範囲を拡大", fontsize=11.5)
save(fig, "a760_scatter.png", SRC, y=-0.06)
# 図2：x1 の係数
fig, ax = plt.subplots(figsize=(7.8, 3.6))
x = np.arange(len(MS))
for k, (c, col, lab) in enumerate([("A_b1", ORANGE, "A -999 のまま"), ("B_b1", BLUE, "B 平均＋欠けの印"), ("C_b1", GREEN, "C 欠けた行を除く")]):
    v = [gS(m, c) for m in MS]
    ax.bar(x + (k - 1) * 0.26, v, 0.26, color=col, label=lab)
    for xi, val in zip(x, v):
        ax.text(xi + (k - 1) * 0.26, val + 0.01, f"{val:.3f}", ha="center", fontsize=7.5)
ax.axhline(B1, color=GRAY, ls="--"); ax.set_xticks(x); ax.set_xticklabels([f"欠け{int(m * 100)}%" for m in MS])
ax.set_ylabel("会員歴の係数（本当は0.5）"); ax.legend(frameon=False, fontsize=9, loc="center right"); ax.set_ylim(0, 0.62)
ax.set_title("-999 のままだと、欠けが1%でも係数はほぼ0になる")
save(fig, "a760_coef.png", SRC)
# 図3：予測の誤差
fig, ax = plt.subplots(figsize=(7.8, 3.6))
for c, col, lab, mk in [("A_rmse", ORANGE, "線形回帰（-999 のまま）", "o"), ("B_rmse", BLUE, "線形回帰（平均＋欠けの印）", "o"),
                        ("tree_999_rmse", GRAY, "決定木（-999 のまま）", "s"), ("tree_flag_rmse", LIGHT, "決定木（平均＋欠けの印）", "s")]:
    ax.plot([m * 100 for m in MS], [gS(m, c) for m in MS], marker=mk, color=col, label=lab)
ax.axhline(out["rmse_no_missing"], color=GREEN, ls=":", lw=1); ax.text(30, out["rmse_no_missing"] - 0.25, "欠けなしの線形回帰", color=GREEN, fontsize=8.5, ha="right")
ax.set_xlabel("会員歴が欠けた割合（%）"); ax.set_ylabel("テストの予測誤差（RMSE、万円）")
ax.legend(frameon=False, fontsize=8.5, loc="upper left"); ax.set_title("決定木は -999 を「別の区分」として扱えるが、線形回帰は扱えない", fontsize=12)
save(fig, "a760_rmse.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
