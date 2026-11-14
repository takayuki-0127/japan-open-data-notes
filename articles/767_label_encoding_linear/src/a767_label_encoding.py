"""767 カテゴリを1・2・3の数にして線形回帰に入れると、ダミー変数と比べて予測はどれだけ悪くなるのか

架空の店の客単価。8つの売り場の種類（順番のない区分）ごとに効き目が違い、ほかに数の変数 x がある。
  y = 効き目[種類] + 0.5・x + 誤差（標準偏差1）
種類を 1〜8 の数（番号の振り方は作った順など、意味のない順番）にして線形回帰に入れる場合と、ダミー変数で入れる場合、
決定木（深さ3・6）に番号のまま入れる場合を、学習2,000件・テスト2,000件で比べる。
番号の振り方を200通り変えて、番号の係数と予測の誤差がどれだけ変わるかも測る。seed 767。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeRegressor
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 767）"
rng = np.random.default_rng(767)
K, N, PERMS = 8, 2000, 200
names = ["食品", "飲料", "日用品", "衣料", "家電", "雑貨", "化粧品", "文具"]
eff = np.array([0.0, -0.8, 0.6, 1.5, -1.2, 0.3, 1.0, -0.4])  # 順番に意味はない
SD = 1.0


def make(n):
    c = rng.integers(0, K, n); x = rng.normal(0, 1, n)
    y = eff[c] + 0.5 * x + rng.normal(0, SD, n)
    return c, x, y


def ols(X, y):
    X1 = np.column_stack([np.ones(len(y)), X]); b, *_ = np.linalg.lstsq(X1, y, rcond=None); return b


c, x, y = make(N); ct, xt, yt = make(N)
pd.DataFrame({"category": np.array(names)[c], "x": x.round(4), "y": y.round(4)}).to_csv(RES / "train_sample.csv", index=False)
rmse = lambda p: float(np.sqrt(np.mean((p - yt) ** 2)))
# ダミー
D = np.eye(K)[c][:, 1:]; Dt = np.eye(K)[ct][:, 1:]
bD = ols(np.column_stack([x, D]), y); pD = bD[0] + bD[1] * xt + Dt @ bD[2:]
# 種類を使わない
b0 = ols(x[:, None], y); p0 = b0[0] + b0[1] * xt
rows = []
for k in range(PERMS):
    code = rng.permutation(K) + 1  # 種類 → 番号（1〜8）
    bL = ols(np.column_stack([x, code[c]]), y); pL = bL[0] + bL[1] * xt + bL[2] * code[ct]
    t3 = DecisionTreeRegressor(max_depth=3, random_state=0).fit(np.column_stack([x, code[c]]), y)
    t6 = DecisionTreeRegressor(max_depth=6, random_state=0).fit(np.column_stack([x, code[c]]), y)
    rows.append((k, bL[2], bL[1], rmse(pL), rmse(t3.predict(np.column_stack([xt, code[ct]]))), rmse(t6.predict(np.column_stack([xt, code[ct]])))))
R = pd.DataFrame(rows, columns=["perm", "coef_code", "coef_x", "rmse_label_lin", "rmse_tree3", "rmse_tree6"])
R.round(4).to_csv(RES / "perms.csv", index=False)
# 決定木にダミー（参考）
t6d = DecisionTreeRegressor(max_depth=6, random_state=0).fit(np.column_stack([x, D]), y)
out = {"categories": K, "n_train": N, "n_test": N, "perms": PERMS, "noise_sd": SD,
       "rmse_dummy_linear": round(rmse(pD), 3), "rmse_no_category": round(rmse(p0), 3),
       "rmse_label_linear_median": round(float(R.rmse_label_lin.median()), 3),
       "rmse_label_linear_range": [round(float(R.rmse_label_lin.min()), 3), round(float(R.rmse_label_lin.max()), 3)],
       "label_linear_worse_than_dummy_pct_median": round(float((R.rmse_label_lin.median() / rmse(pD) - 1) * 100), 1),
       "coef_code_range": [round(float(R.coef_code.min()), 3), round(float(R.coef_code.max()), 3)],
       "coef_code_positive_pct": round(float((R.coef_code > 0).mean() * 100), 1),
       "coef_x_dummy": round(float(bD[1]), 3), "coef_x_label_median": round(float(R.coef_x.median()), 3),
       "rmse_tree3_median": round(float(R.rmse_tree3.median()), 3), "rmse_tree6_median": round(float(R.rmse_tree6.median()), 3),
       "rmse_tree6_dummy": round(rmse(t6d.predict(np.column_stack([xt, Dt]))), 3),
       "dummy_effects_vs_true_max_abs_err": round(float(np.max(np.abs((bD[2:]) - (eff[1:] - eff[0])))), 3)}
json.dump(out, open(RES / "a767_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：ある番号の振り方での当てはめ
code = np.array([1, 2, 3, 4, 5, 6, 7, 8])
bL = ols(np.column_stack([x, code[c]]), y)
fig, ax = plt.subplots(figsize=(8.5, 3.8))
mean_by = pd.Series(y - bD[1] * x).groupby(c).mean()
ax.scatter(code, mean_by.values, s=60, color=BLUE, zorder=3, label="種類ごとの平均（x の分を除く）")
for i in range(K):
    ax.text(code[i], mean_by.values[i] + 0.15, names[i], ha="center", fontsize=9)
xx = np.array([1, 8]); ax.plot(xx, bL[0] + bL[2] * xx, color=ORANGE, lw=2, label=f"番号のまま直線を引く（傾き {bL[2]:+.2f}）")
ax.set_xticks(code); ax.set_xlabel("種類の番号（作った順。順番に意味はない）"); ax.set_ylabel("客単価（基準からの差）")
ax.set_ylim(mean_by.min() - 0.4, mean_by.max() + 0.45); ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_title("番号に直線を引いても、種類ごとの違いはほとんど表せない")
save(fig, "a767_fit.png", SRC)
# 図2：予測の誤差
fig, ax = plt.subplots(figsize=(8, 3.8))
labs = ["種類を使わない", "番号のまま\n線形回帰", "ダミー変数で\n線形回帰", "番号のまま\n決定木（深さ3）", "番号のまま\n決定木（深さ6）"]
vals = [out["rmse_no_category"], out["rmse_label_linear_median"], out["rmse_dummy_linear"], out["rmse_tree3_median"], out["rmse_tree6_median"]]
ax.bar(labs, vals, color=[GRAY, ORANGE, BLUE, LIGHT, LIGHT])
for i, v in enumerate(vals):
    ax.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9.5)
ax.axhline(SD, color=GREEN, ls="--", lw=1); ax.text(4.45, SD - 0.06, "置いた誤差の標準偏差（1.0）", color=GREEN, fontsize=8.5, ha="right")
ax.set_ylim(0.9, max(vals) + 0.12); ax.set_ylabel("テストの予測誤差（RMSE）"); ax.tick_params(axis="x", labelsize=9)
ax.set_title("番号のままの線形回帰は、種類を使わないのとほとんど変わらない")
save(fig, "a767_rmse.png", SRC)
# 図3：番号の振り方で係数が変わる
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.hist(R.coef_code, bins=30, color=ORANGE)
ax.axvline(0, color=GRAY, lw=1)
ax.set_xlabel("番号の係数（番号が1増えると客単価がいくら変わるか）"); ax.set_ylabel("番号の振り方の数（200通り）")
ax.set_title(f"番号の振り方を変えると、係数は{R.coef_code.min():+.2f}〜{R.coef_code.max():+.2f}と向きまで変わる")
save(fig, "a767_coef.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
