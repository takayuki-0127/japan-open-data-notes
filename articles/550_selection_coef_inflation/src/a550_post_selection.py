"""550 回帰に入れる変数を「有意なものだけ残す」で選ぶと、残った係数はどれだけ大きく出るのか（手法の解説・正解の分かるデータで試す）

架空のデータ：説明変数の候補 20個（どの2つも相関 0.3）。本当に効くのは5つ：弱い3つ（係数 0.15）と強い2つ（係数 0.4）。残り15個は効かない（0）。
目的変数 ＝ 効く変数の和 ＋ ばらつき（標準偏差 1）。件数 100・300・1,000。
選び方：
  M1 全部入れる（選ばない）
  M2 全部入れて当て、p<0.05 の変数だけ残して当て直す
  M3 後ろ向きステップワイズ（p が最も大きい変数を1つずつ外し、全部 p<0.05 になるまで）
  M4 データを半分に分け、前半で M2 の選び方をして、後半で当て直す
確かめとして、変数どうしの相関を 0 にした場合も 100・300件で出す。
各件数 1,000回、乱数の種 550。残った係数の平均（本当の値との比）、残る割合、95%区間が本当の値を含む割合を数える。
数字は置いた前提で決まる。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 550）"
P = 20
BETA = np.array([0.15] * 3 + [0.4] * 2 + [0.0] * 15)
KIND = np.array(["弱い"] * 3 + ["強い"] * 2 + ["効かない"] * 15)
RHO = 0.3
NS = [100, 300, 1000]
REPS = 1000


def ols(X, y):
    n, k = X.shape
    Xc = np.column_stack([np.ones(n), X])
    XtX_inv = np.linalg.inv(Xc.T @ Xc)
    b = XtX_inv @ Xc.T @ y
    res = y - Xc @ b
    s2 = res @ res / (n - k - 1)
    se = np.sqrt(np.diag(XtX_inv) * s2)
    t = b / se
    p = 2 * stats.t.sf(np.abs(t), n - k - 1)
    q = stats.t.ppf(0.975, n - k - 1)
    return b[1:], se[1:], p[1:], q


def fit_on(X, y, keep):
    out = np.full(P, np.nan); lo = np.full(P, np.nan); hi = np.full(P, np.nan)
    if keep.sum() == 0:
        return out, lo, hi
    b, se, _, q = ols(X[:, keep], y)
    out[keep] = b; lo[keep] = b - q * se; hi[keep] = b + q * se
    return out, lo, hi


def backward(X, y):
    keep = np.ones(P, bool)
    while keep.sum() > 0:
        _, _, p, _ = ols(X[:, keep], y)
        if p.max() < 0.05:
            break
        idx = np.where(keep)[0][np.argmax(p)]; keep[idx] = False
    return keep


def sim(rng, rho, ns):
    C = np.full((P, P), rho); np.fill_diagonal(C, 1); Lc = np.linalg.cholesky(C)
    rows = []
    for n in ns:
        for r in range(REPS):
            X = rng.standard_normal((n, P)) @ Lc.T
            y = X @ BETA + rng.standard_normal(n)
            res = {}
            res["M1"] = fit_on(X, y, np.ones(P, bool))
            _, _, p, _ = ols(X, y); res["M2"] = fit_on(X, y, p < 0.05)
            res["M3"] = fit_on(X, y, backward(X, y))
            h = n // 2
            _, _, p1, _ = ols(X[:h], y[:h]); res["M4"] = fit_on(X[h:], y[h:], p1 < 0.05)
            for m, (b, lo, hi) in res.items():
                for j in range(P):
                    rows.append((n, r, m, j, KIND[j], BETA[j], b[j], lo[j], hi[j]))
    df = pd.DataFrame(rows, columns=["n", "rep", "method", "var", "kind", "beta", "est", "lo", "hi"])
    df["kept"] = df.est.notna()
    df["cover"] = (df.lo <= df.beta) & (df.beta <= df.hi)
    return df


def main():
    rng = np.random.default_rng(550)
    df = sim(rng, RHO, NS)
    # 確かめ：変数どうしの相関を 0 にした場合（相関があると、外れた効く変数の分を残った変数が肩代わりする）
    d0 = sim(rng, 0.0, [100, 300]); k0 = d0[d0.kept]
    r0 = k0.groupby(["n", "method", "kind"]).agg(mean_est=("est", "mean"), cover=("cover", "mean")).reset_index()
    r0["keep_rate"] = d0.groupby(["n", "method", "kind"]).kept.mean().values
    r0.to_csv(RES / "summary_rho0.csv", index=False, float_format="%.4f"); print(r0.to_string())
    df.to_csv(RES / "reps.csv.gz", index=False, float_format="%.5f", compression="gzip")
    k = df[df.kept]
    sm = k.groupby(["n", "method", "kind"]).agg(mean_est=("est", "mean"), cover=("cover", "mean"), n_kept=("est", "size")).reset_index()
    kr = df.groupby(["n", "method", "kind"]).kept.mean().rename("keep_rate").reset_index()
    sm = sm.merge(kr, on=["n", "method", "kind"])
    sm["true"] = sm.kind.map({"弱い": 0.15, "強い": 0.4, "効かない": 0.0})
    sm["ratio_to_true"] = np.where(sm.true > 0, sm.mean_est / sm.true.replace(0, np.nan), np.nan)
    sm["mean_abs_est"] = k.assign(a=k.est.abs()).groupby(["n", "method", "kind"]).a.mean().values
    anynull = df[df.kind == "効かない"].groupby(["n", "method", "rep"]).kept.any().groupby(["n", "method"]).mean().rename("share_any_null_kept").reset_index()
    sm.to_csv(RES / "summary.csv", index=False, float_format="%.4f"); anynull.to_csv(RES / "any_null_kept.csv", index=False, float_format="%.4f")
    print(sm.to_string()); print(anynull.to_string())
    json.dump({"summary": sm.round(4).to_dict("records"), "summary_rho0": r0.round(4).to_dict("records"), "any_null_kept": anynull.round(4).to_dict("records")},
              open(RES / "a550_main.json", "w"), ensure_ascii=False, indent=1)

    lab = {"M1": "全部入れる", "M2": "p<0.05だけ残す", "M3": "ステップワイズ", "M4": "分けて選ぶ・当てる"}
    ms = ["M1", "M2", "M3", "M4"]; cols = [GRAY, ORANGE, BLUE, GREEN]
    # 図1：弱い変数の、残ったときの係数の平均（本当の値との比）、件数別
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); w = 0.2
    for i, (m, c) in enumerate(zip(ms, cols)):
        v = [sm[(sm.n == n) & (sm.method == m) & (sm.kind == "弱い")].ratio_to_true.iloc[0] for n in NS]
        xs = np.arange(3) + (i - 1.5) * w; ax.bar(xs, v, w, color=c, label=lab[m])
        for xx, vv in zip(xs, v): ax.text(xx, vv + 0.03, f"{vv:.2f}", ha="center", fontsize=8)
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xticks(range(3)); ax.set_xticklabels([f"{n}件" for n in NS])
    ax.set_ylabel("残ったときの係数の平均 ÷ 本当の値"); ax.set_ylim(0, max(2.3, ax.get_ylim()[1]))
    ax.set_title("弱い変数（本当は0.15）：選んで残すと、係数は大きく出る")
    ax.legend(frameon=False, fontsize=9, ncol=2)
    save(fig, "a550_weak_inflation.png", SRC)

    # 図2：残る割合（弱い・効かない）と、効かない変数が1つでも残る割合、300件
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    s = sm[sm.n == 300]; a = anynull[anynull.n == 300]
    grp = [("弱い変数が残る割合", "弱い"), ("効かない変数が残る割合\n（1つあたり）", "効かない"), ("効かない変数が\n1つでも残る割合", None)]
    for i, (m, c) in enumerate(zip(ms[1:], cols[1:])):
        v = [s[(s.method == m) & (s.kind == "弱い")].keep_rate.iloc[0] * 100, s[(s.method == m) & (s.kind == "効かない")].keep_rate.iloc[0] * 100,
             a[a.method == m].share_any_null_kept.iloc[0] * 100]
        xs = np.arange(3) + (i - 1) * 0.26; ax.bar(xs, v, 0.26, color=c, label=lab[m])
        for xx, vv in zip(xs, v): ax.text(xx, vv + 1, f"{vv:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(range(3)); ax.set_xticklabels([g[0] for g in grp], fontsize=9)
    ax.set_ylabel("%（1,000回のうち）"); ax.set_ylim(0, 100)
    ax.set_title("300件で、変数がどれだけ残るか")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a550_keep_rates.png", SRC)

    # 図3：95%区間が本当の値を含む割合（残った変数で）、100件
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); s = sm[sm.n == 100]
    kinds = ["弱い", "強い", "効かない"]
    for i, (m, c) in enumerate(zip(ms, cols)):
        v = [s[(s.method == m) & (s.kind == kd)].cover.iloc[0] * 100 for kd in kinds]
        xs = np.arange(3) + (i - 1.5) * 0.2; ax.bar(xs, v, 0.2, color=c, label=lab[m])
        for xx, vv in zip(xs, v): ax.text(xx, vv + 1, f"{vv:.0f}", ha="center", fontsize=8)
    ax.axhline(95, color=INK, lw=0.8, ls="--")
    ax.set_xticks(range(3)); ax.set_xticklabels(["弱い変数（0.15）", "強い変数（0.4）", "効かない変数（0）"])
    ax.set_ylim(0, 112); ax.set_ylabel("残った変数の95%区間が本当の値を含む割合（%）")
    ax.set_title("100件で、残った係数の95%区間はどれだけ当たるか")
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="upper center")
    save(fig, "a550_coverage.png", SRC)


if __name__ == "__main__":
    main()
