"""668 1列ずつ3σで見る方法とマハラノビス距離では、相関を崩す異常をどれだけ見つけられるのか

架空の店の2つの指標（例：来店客数と売上、どちらも標準化した値）を、相関 ρ のある2次元の正規分布で 2,000 日分つくる。
そこへ異常を 40 日（2%）混ぜる。異常は2種類：
  A 相関を崩す異常：片方が +a、もう片方が -a（a=1.0。どちらの列も 3σ の内側）
  B 片方の列だけ大きい異常：片方が 3.3、もう片方はふつうの値
見つけ方：
  1列ずつ 3σ（どちらかの列が平均から3標準偏差より離れたら異常）
  マハラノビス距離（2列の平均とばらつき・相関から測る距離。閾値は、正常な日を誤って拾う割合が 3σ と同じ 0.54% になる値）
  マハラノビス距離（頑健版：MinCovDet で平均と共分散を出す）
平均・標準偏差・共分散は、異常を含んだデータから出す（実際と同じく、どれが異常かは分からない）。
ρ を 0〜0.95 で変え、各 200 回（頑健版は 40 回）くり返す。数字は置いた相関・異常の大きさ・割合で決まる。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.covariance import MinCovDet
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の店の日次の指標（作成者が乱数で作成、seed 668）"
rng = np.random.default_rng(668)
N, K, A_SIZE, B_SIZE, REPS = 2000, 40, 1.0, 3.3, 200

p_in = (stats.norm.cdf(3) - stats.norm.cdf(-3))
FP_TARGET = 1 - p_in ** 2              # 独立のとき、1列ずつ3σで正常を拾う割合
CUT = stats.chi2.ppf(1 - FP_TARGET, 2)  # マハラノビス距離²の閾値


def make(rho, kind):
    C = np.array([[1, rho], [rho, 1]])
    X = rng.multivariate_normal([0, 0], C, N)
    lab = np.zeros(N, bool)
    idx = rng.choice(N, K, replace=False)
    lab[idx] = True
    sgn = rng.choice([-1, 1], K)
    if kind == "A":
        X[idx, 0] = sgn * A_SIZE + 0.2 * rng.standard_normal(K)
        X[idx, 1] = -sgn * A_SIZE + 0.2 * rng.standard_normal(K)
    else:
        col = rng.integers(0, 2, K)
        X[idx] = rng.multivariate_normal([0, 0], C, K)
        X[idx, col] = sgn * B_SIZE
    return X, lab


def detect(X, robust=False):
    z = (X - X.mean(0)) / X.std(0, ddof=1)
    f3 = (np.abs(z) > 3).any(1)
    S = np.cov(X.T); mu = X.mean(0)
    d = X - mu
    m2 = np.einsum("ij,jk,ik->i", d, np.linalg.inv(S), d)
    fm = m2 > CUT
    out = {"sigma3": f3, "maha": fm}
    if robust:
        mcd = MinCovDet(random_state=0).fit(X)
        out["maha_robust"] = mcd.mahalanobis(X) > CUT
    return out


rows = []
RHOS = [0.0, 0.5, 0.8, 0.9, 0.95]
for kind in ["A", "B"]:
    for rho in RHOS:
        for r in range(REPS):
            X, lab = make(rho, kind)
            res = detect(X, robust=(r < 40))
            for m, f in res.items():
                rows.append({"kind": kind, "rho": rho, "rep": r, "method": m,
                             "found": f[lab].mean(), "false_pos": f[~lab].mean()})
D = pd.DataFrame(rows)
S = D.groupby(["kind", "rho", "method"]).agg(found=("found", "mean"), false_pos=("false_pos", "mean"), reps=("rep", "count")).reset_index()
S["found_pct"] = (S.found * 100).round(2); S["false_pos_pct"] = (S.false_pos * 100).round(3)
S[["kind", "rho", "method", "reps", "found_pct", "false_pos_pct"]].to_csv(RES / "summary.csv", index=False)


def g(kind, rho, m, col="found_pct"):
    return float(S[(S.kind == kind) & (S.rho == rho) & (S.method == m)][col].iloc[0])


out = {"days": N, "anomalies": K, "reps": REPS, "reps_robust": 40, "A_size": A_SIZE, "B_size": B_SIZE,
       "fp_target_pct": round(FP_TARGET * 100, 3), "maha2_cut": round(float(CUT), 3),
       "A_found_pct": {m: {str(r): g("A", r, m) for r in RHOS} for m in ["sigma3", "maha", "maha_robust"]},
       "B_found_pct": {m: {str(r): g("B", r, m) for r in RHOS} for m in ["sigma3", "maha", "maha_robust"]},
       "false_pos_pct_A": {m: {str(r): g("A", r, m, "false_pos_pct") for r in RHOS} for m in ["sigma3", "maha", "maha_robust"]}}
json.dump(out, open(RES / "a668_main.json", "w"), ensure_ascii=False, indent=1)

LAB = {"sigma3": "1列ずつ3σ", "maha": "マハラノビス距離", "maha_robust": "マハラノビス距離（頑健版）"}
COL = {"sigma3": ORANGE, "maha": BLUE, "maha_robust": GREEN}
# 図1：例
rng_fig = np.random.default_rng(6681)
C = np.array([[1, .9], [.9, 1]]); Xn = rng_fig.multivariate_normal([0, 0], C, N)
sg = rng_fig.choice([-1, 1], K)
Xa = np.column_stack([sg * A_SIZE, -sg * A_SIZE]) + 0.2 * rng_fig.standard_normal((K, 2))
fig, ax = plt.subplots(figsize=(6.5, 6))
ax.scatter(Xn[:, 0], Xn[:, 1], s=5, color=GRAY, alpha=.5, label="ふつうの日（2,000日）")
ax.scatter(Xa[:, 0], Xa[:, 1], s=18, color=ORANGE, label="相関を崩す異常（40日）")
ax.add_patch(Rectangle((-3, -3), 6, 6, fill=False, ls="--", color=INK, lw=1, label="1列ずつ3σの範囲"))
w, v = np.linalg.eigh(C); ang = np.degrees(np.arctan2(v[1, 1], v[0, 1]))
ax.add_patch(Ellipse((0, 0), 2 * np.sqrt(CUT * w[1]), 2 * np.sqrt(CUT * w[0]), angle=ang, fill=False, color=BLUE, lw=1.5, label="マハラノビス距離の閾値"))
ax.set_xlim(-4.5, 4.5); ax.set_ylim(-4.5, 4.5); ax.set_aspect("equal")
ax.set_xlabel("指標1（標準化）"); ax.set_ylabel("指標2（標準化）"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title("相関0.9の2列：異常はどちらの列も3σの内側にある")
save(fig, "a668_example.png", SRC)

# 図2：Aの見つかる割合
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for m in ["sigma3", "maha", "maha_robust"]:
    y = [g("A", r, m) for r in RHOS]
    ax.plot(RHOS, y, marker="o", color=COL[m], label=LAB[m])
    ax.text(RHOS[-1] + .01, y[-1], f"{y[-1]:.0f}%", va="center", fontsize=9, color=COL[m])
ax.set_xlabel("2列の相関 ρ"); ax.set_ylabel("相関を崩す異常のうち見つけた割合（%）"); ax.set_ylim(-3, 105)
ax.legend(frameon=False, fontsize=9); ax.set_title("相関が強いほど、マハラノビス距離だけが相関を崩す異常を見つける")
save(fig, "a668_found_by_rho.png", SRC)

# 図3：B の見つかる割合
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for m in ["sigma3", "maha", "maha_robust"]:
    y = [g("B", r, m) for r in RHOS]
    ax.plot(RHOS, y, marker="o", color=COL[m], label=LAB[m])
    ax.text(RHOS[0] - .02, y[0], f"{y[0]:.0f}%", va="center", ha="right", fontsize=9, color=COL[m])
ax.set_xlim(-.12, 1.0)
ax.set_xlabel("2列の相関 ρ"); ax.set_ylabel("片方の列だけ大きい異常のうち見つけた割合（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("片方の列だけ3.3の異常は、相関が弱いと1列ずつ3σの方がよく見つける")
save(fig, "a668_found_single.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
