"""609 交差検証の K を2・5・10・n と変えると、成績の見積もりの偏りとばらつきはどう変わるのか

本当の予測誤差が分かる架空のデータで、最小二乗の回帰（変数10個）の予測誤差（平均二乗誤差）を交差検証で見積もる。
件数 n=60（変数が件数に比べて多め）と n=300。K=2・5・10・n（1件抜き）で、
  見積もりの偏り（全データで学習したモデルの本当の誤差との差）・ばらつき（データ1,000組での標準偏差）・学習の回数
を比べる。本当の誤差は、そのデータで学習したモデルを大きなテストデータ（2万件）で測って出す。seed 609。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 609）"
rng = np.random.default_rng(609)
P, SIG, REPS = 10, 1.0, 1000
BETA = np.r_[1.0, rng.normal(0, 0.5, P)]


def design(n, rs):
    X = rs.standard_normal((n, P))
    return np.column_stack([np.ones(n), X])


def fit(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


Xt = design(20000, rng); yt = Xt @ BETA + SIG * rng.standard_normal(20000)
rows = []
for n in [60, 300]:
    for r in range(REPS):
        X = design(n, rng); y = X @ BETA + SIG * rng.standard_normal(n)
        b = fit(X, y); true_err = float(np.mean((yt - Xt @ b) ** 2))
        rec = {"n": n, "rep": r, "true_err_full": true_err}
        perm = rng.permutation(n)
        for K in [2, 5, 10]:
            folds = np.array_split(perm, K); sse = 0.0
            for f in folds:
                tr = np.setdiff1d(perm, f)
                bb = fit(X[tr], y[tr]); sse += float(np.sum((y[f] - X[f] @ bb) ** 2))
            rec[f"cv{K}"] = sse / n
        # 1件抜き（最小二乗は「てこ比」で一度に出せる）
        H = X @ np.linalg.pinv(X.T @ X) @ X.T
        res = y - H @ y
        rec["cvn"] = float(np.mean((res / (1 - np.diag(H))) ** 2))
        rows.append(rec)
df = pd.DataFrame(rows); df.to_csv(RES / "reps.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
# 「学習件数が n(K-1)/K のときの本当の誤差」の目安：最小二乗の期待予測誤差 σ²(1 + (p+1)/(m - p - 2))（説明変数が正規のとき）
def expected_err(m):
    return SIG ** 2 * (1 + (P + 1) / (m - P - 2))


summ = []
for n in [60, 300]:
    s = df[df.n == n]
    for K, col in [(2, "cv2"), (5, "cv5"), (10, "cv10"), (n, "cvn")]:
        d = s[col] - s.true_err_full
        summ.append({"n": n, "K": "n" if K == n else K, "fits": K, "cv_mean": round(float(s[col].mean()), 4),
                     "true_err_full_mean": round(float(s.true_err_full.mean()), 4), "bias": round(float(d.mean()), 4),
                     "bias_pct": round(100 * float(d.mean() / s.true_err_full.mean()), 1), "sd": round(float(s[col].std()), 4),
                     "rmse_vs_true": round(float(np.sqrt(np.mean(d ** 2))), 4),
                     "corr_with_true": round(float(np.corrcoef(s[col], s.true_err_full)[0, 1]), 3),
                     "theory_err_train_size": round(expected_err(n * (K - 1) / K), 4)})
sm = pd.DataFrame(summ); sm.to_csv(RES / "summary.csv", index=False)
out = {"reps": REPS, "p": P, "noise_sd": SIG, "summary": summ,
       "theory_full_n60": round(expected_err(60), 4), "theory_full_n300": round(expected_err(300), 4)}
json.dump(out, open(RES / "a609_main.json", "w"), ensure_ascii=False, indent=1)

lab = ["2", "5", "10", "n（1件抜き）"]
# 図1：偏り（n=60, 300）
fig, ax = plt.subplots(figsize=(8, 3.8))
x = np.arange(4)
for i, (n, c) in enumerate([(60, ORANGE), (300, BLUE)]):
    v = sm[sm.n == n].bias_pct.values
    ax.bar(x + (i - 0.5) * 0.38, v, 0.38, color=c, label=f"{n}件")
    for xx, vv in zip(x, v):
        ax.text(xx + (i - 0.5) * 0.38, vv, f"{vv:+.1f}%", ha="center", va="bottom", fontsize=9)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_xlabel("K（データを何分割するか）")
ax.set_ylabel("本当の誤差との差（%、平均）"); ax.legend(frameon=False)
ax.set_title("K が小さいほど、誤差を大きめに見積もる（学習に使う件数が減るため）")
save(fig, "a609_bias.png", SRC)
# 図2：ばらつき（n=60）の分布
s = df[df.n == 60]
fig, ax = plt.subplots(figsize=(8, 3.8))
data = [s.true_err_full] + [s[c] for c in ["cv2", "cv5", "cv10", "cvn"]]
bp = ax.boxplot(data, tick_labels=["本当の誤差"] + [f"K={l}" for l in lab], patch_artist=True, widths=0.5, showfliers=False)
for b, c in zip(bp["boxes"], [GRAY, ORANGE, BLUE, GREEN, LIGHT]):
    b.set_facecolor(c); b.set_alpha(0.7)
ax.set_ylabel("予測の平均二乗誤差"); ax.set_title("60件のデータ1,000組：見積もりの散らばり（外れ値は省略）")
save(fig, "a609_spread_n60.png", SRC)
# 図3：本当の誤差とのずれ（RMSE）と学習の回数
fig, ax = plt.subplots(figsize=(8, 3.6))
for n, c, mk in [(60, ORANGE, "o"), (300, BLUE, "s")]:
    v = sm[sm.n == n]
    ax.plot(lab, v.rmse_vs_true, marker=mk, color=c, label=f"{n}件")
    for xx, (r, f) in enumerate(zip(v.rmse_vs_true, v.fits)):
        ax.text(xx, r, f"  {f}回", fontsize=8, va="bottom", color=c)
ax.set_xlabel("K（右の数字は学習の回数）"); ax.set_ylabel("本当の誤差とのずれ（RMSE）"); ax.legend(frameon=False)
ax.set_title("そのデータで学習したモデルの本当の誤差に、どれだけ近いか")
save(fig, "a609_rmse.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
