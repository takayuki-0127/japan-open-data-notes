"""616 ロジスティック回帰で、ある区分の全員が同じ結果だと、係数と区間はどうなるのか

架空の申込みデータ（600件前後）。流入経路5区分（A300件・B150件・C100件・D40件・E は件数 n_E を変える）で成約するかどうかを回帰する。
本当の成約率は A 37.8%（基準）、E 75%（係数の本当の値 1.6）。E の件数が少ないと、E の全員が成約（または全員が不成約）になり、
最尤法の係数は無限大に向かう（完全分離）。
  ML ふつうの最尤法（ニュートン法、50回まで）
  FI Firth の補正（罰則つき尤度、区間はプロファイル尤度ではなく Wald で簡略化）
  MG E を D とまとめる
完全分離の起きた割合・E の係数・95%区間が本当の値を含む割合を、n_E=5〜40 の各2,000回で数える。seed 616。
statsmodels の Logit の結果と、自作の最尤法の結果が（分離のないデータで）一致することを確かめる。
"""
import json
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

warnings.filterwarnings("ignore")
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 616）"
rng = np.random.default_rng(616)
BASE, EFF = -0.5, {"B": 0.3, "C": -0.2, "D": 0.5, "E": 1.6}
SIZES = {"A": 300, "B": 150, "C": 100, "D": 40}
REPS = 2000


def make(nE, rs):
    g = np.concatenate([np.full(n, k) for k, n in {**SIZES, "E": nE}.items()])
    lin = BASE + np.array([EFF.get(k, 0.0) for k in g])
    y = (rs.random(len(g)) < 1 / (1 + np.exp(-lin))).astype(float)
    return g, y


def design(g, levels):
    X = np.column_stack([np.ones(len(g))] + [(g == k).astype(float) for k in levels])
    return X


def newton(X, y, firth=False, iters=50):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        W = p * (1 - p)
        XtWX = X.T @ (X * W[:, None])
        try:
            inv = np.linalg.inv(XtWX)
        except np.linalg.LinAlgError:
            inv = np.linalg.pinv(XtWX)
        if firth:
            h = np.einsum("ij,jk,ik->i", X * np.sqrt(W)[:, None], inv, X * np.sqrt(W)[:, None])
            U = X.T @ (y - p + h * (0.5 - p))
        else:
            U = X.T @ (y - p)
        step = inv @ U
        b = b + step
        if np.max(np.abs(step)) < 1e-8:
            break
    p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
    XtWX = X.T @ (X * (p * (1 - p))[:, None])
    se = np.sqrt(np.diag(np.linalg.pinv(XtWX)))
    return b, se


# 自作の最尤法が statsmodels と一致することを、分離のないデータで確かめる
g0, y0 = make(200, np.random.default_rng(1)); X0 = design(g0, ["B", "C", "D", "E"])
b_sm = sm.Logit(y0, X0).fit(disp=0); b_my, se_my = newton(X0, y0)
assert np.allclose(b_sm.params, b_my, atol=1e-6) and np.allclose(b_sm.bse, se_my, atol=1e-6)

rows = []
for nE in [5, 8, 12, 20, 40]:
    for r in range(REPS):
        g, y = make(nE, rng)
        X = design(g, ["B", "C", "D", "E"])
        sep = bool(y[g == "E"].min() == y[g == "E"].max())
        bm, sm_ = newton(X, y); bf, sf = newton(X, y, firth=True)
        gm = np.where(g == "E", "D", g); Xm = design(gm, ["B", "C", "D"]); bg, sg = newton(Xm, y)
        rows.append({"nE": nE, "rep": r, "sep": sep, "E_all1": bool(y[g == "E"].min() == 1),
                     "ml_b": bm[4], "ml_se": sm_[4], "fi_b": bf[4], "fi_se": sf[4], "mg_b": bg[3], "mg_se": sg[3]})
df = pd.DataFrame(rows)
df.round(5).to_csv(RES / "reps.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
T = EFF["E"]
summ = []
for nE, s in df.groupby("nE"):
    for k in ["ml", "fi"]:
        b, se = s[f"{k}_b"], s[f"{k}_se"]
        cover = ((b - 1.96 * se <= T) & (T <= b + 1.96 * se)).mean()
        summ.append({"nE": nE, "method": k, "sep_pct": round(100 * s.sep.mean(), 1), "median_b": round(float(b.median()), 3),
                     "mean_b_nosep": round(float(b[~s.sep].mean()), 3), "median_b_sep": round(float(b[s.sep].median()), 2) if s.sep.any() else None,
                     "median_se_sep": round(float(se[s.sep].median()), 1) if s.sep.any() else None,
                     "coverage_pct": round(100 * float(cover), 1), "mean_abs_err": round(float((b - T).abs().mean()), 3),
                     "median_abs_err": round(float((b - T).abs().median()), 3)})
    summ.append({"nE": nE, "method": "mg", "sep_pct": round(100 * s.sep.mean(), 1), "median_b": round(float(s.mg_b.median()), 3)})
sm_df = pd.DataFrame(summ); sm_df.to_csv(RES / "summary.csv", index=False)
out = {"reps": REPS, "true_E_coef": T, "true_rate_A": round(1 / (1 + np.exp(0.5)), 4), "true_rate_E": round(1 / (1 + np.exp(-1.1)), 4),
       "summary": summ}
json.dump(out, open(RES / "a616_main.json", "w"), ensure_ascii=False, indent=1, default=float)

ns = [5, 8, 12, 20, 40]
ml, fi = sm_df[sm_df.method == "ml"], sm_df[sm_df.method == "fi"]
# 図1：分離の割合
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar([str(n) for n in ns], ml.sep_pct, color=ORANGE)
for i, v in enumerate(ml.sep_pct):
    ax.text(i, v, f"{v:.1f}%", ha="center", va="bottom")
ax.set_xlabel("区分 E の件数（本当の成約率75%）"); ax.set_ylabel("E が全員成約か全員不成約だった割合（%）")
ax.set_title("件数の少ない区分では、全員が同じ結果になることがよくある")
save(fig, "a616_separation_rate.png", SRC)
# 図2：E=8件の係数の分布（最尤法と Firth）
s8 = df[df.nE == 8]
fig, ax = plt.subplots(figsize=(8.5, 3.8))
bins = np.linspace(-2, 12, 57)
ax.hist(np.clip(s8.ml_b, -2, 12), bins=bins, color=ORANGE, alpha=0.7, label="ふつうの最尤法（12以上は12にまとめた）")
ax.hist(np.clip(s8.fi_b, -2, 12), bins=bins, color=GREEN, alpha=0.6, label="Firth の補正")
ax.axvline(T, color=GRAY, ls=":", lw=1.2)
ax.set_xlabel("区分 E の係数（本当は1.6、点線）"); ax.set_ylabel("回数（2,000回中）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("E が8件のとき：最尤法は分離した回で係数が飛ぶ")
save(fig, "a616_coef_hist_n8.png", SRC)
# 図3：区間の当たり方と誤差
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={"wspace": 0.3})
axs[0].plot([str(n) for n in ns], ml.coverage_pct, marker="o", color=ORANGE, label="最尤法")
axs[0].plot([str(n) for n in ns], fi.coverage_pct, marker="s", color=GREEN, label="Firth")
axs[0].axhline(95, color=GRAY, ls=":"); axs[0].set_ylim(50, 101); axs[0].set_xlabel("区分 E の件数")
axs[0].set_ylabel("%"); axs[0].set_title("95%区間が本当の値を含んだ割合"); axs[0].legend(frameon=False)
axs[1].plot([str(n) for n in ns], ml.mean_abs_err, marker="o", color=ORANGE, label="最尤法")
axs[1].plot([str(n) for n in ns], fi.mean_abs_err, marker="s", color=GREEN, label="Firth")
axs[1].set_yscale("log"); axs[1].set_yticks([0.3, 1, 3, 10]); axs[1].set_yticklabels(["0.3", "1", "3", "10"])
axs[1].set_xlabel("区分 E の件数"); axs[1].set_title("係数の誤差の平均（本当の1.6との差、対数の目盛り）"); axs[1].legend(frameon=False)
save(fig, "a616_coverage_error.png", SRC, y=-0.04)
print(sm_df.to_string())
