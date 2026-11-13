"""546 2つの系列のずらし幅を0〜12か月で動かして最も強い相関を選ぶと、関係がなくても相関はどれだけ高く出るのか（手法の解説）

関係のない2つの月次系列（どちらも AR(1)、自己相関 φ = 0・0.5・0.9、長さ 5・10・20年）を作り、
y_t と x_{t-k}（k = 0〜12か月）の相関を出して、絶対値が最も大きいずらし幅を選ぶ。
判定のしかた：
  T1 ずらし幅0だけをふつうの t 検定（選ばない場合の参考）
  T2 選んだずらし幅の相関を、ふつうの t 検定（選んだことを入れない）
  T3 並べ替え検定：x をばらばらに並べ替えて「最大の相関」を出し直す（選び方は入れるが、自己相関は壊れる）
  T4 ブロックの並べ替え：x を12か月ずつのブロックに切ってブロックの順番だけを並べ替え、「最大の相関」を出し直す
  T5 作り直し：x に AR(1) を当てはめ、同じ自己相関の系列を作り直して「最大の相関」を出し直す
各場面 1,000回、T3〜T5 は 199回の出し直し。有意水準 5%。乱数の種 546。数字は置いた前提で決まる。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "出典：架空の月次系列（作成者が乱数で作成、seed 546）"
PHIS = [0.0, 0.5, 0.9]
YEARS = [5, 10, 20]
LAGS = 13
REPS = 1000
B = 199


def ar1(rng, n, phi, m=1):
    e = rng.standard_normal((m, n + 100))
    x = np.empty_like(e); x[:, 0] = e[:, 0]
    for t in range(1, n + 100):
        x[:, t] = phi * x[:, t - 1] + e[:, t]
    return x[:, 100:]


def lag_corrs(y, X):
    """y: (n,), X: (m, n) → (m, LAGS) の相関。y_t と x_{t-k}、t = 12..n-1 にそろえる"""
    n = len(y); m0 = LAGS - 1
    yy = y[m0:]; yy = (yy - yy.mean()) / yy.std()
    out = np.empty((X.shape[0], LAGS))
    for k in range(LAGS):
        xs = X[:, m0 - k:n - k]
        xs = (xs - xs.mean(1, keepdims=True)) / xs.std(1, keepdims=True)
        out[:, k] = xs @ yy / len(yy)
    return out


def tp(r, n):
    t = r * np.sqrt((n - 2) / (1 - r ** 2))
    return 2 * stats.t.sf(np.abs(t), n - 2)


def main():
    rng = np.random.default_rng(546)
    rows = []
    for yrs in YEARS:
        n = yrs * 12
        neff = n - (LAGS - 1)
        for phi in PHIS:
            for r in range(REPS):
                x = ar1(rng, n, phi)[0]; y = ar1(rng, n, phi)[0]
                c = lag_corrs(y, x[None, :])[0]
                k = int(np.argmax(np.abs(c))); mx = abs(c[k])
                perm = np.array([rng.permutation(x) for _ in range(B)])
                p3 = (1 + (np.abs(lag_corrs(y, perm)).max(1) >= mx).sum()) / (B + 1)
                blk = x.reshape(-1, 12)                                        # 12か月ずつのブロック
                bp = np.array([blk[rng.permutation(len(blk))].ravel() for _ in range(B)])
                p4 = (1 + (np.abs(lag_corrs(y, bp)).max(1) >= mx).sum()) / (B + 1)
                xc = x - x.mean(); ph = float(xc[1:] @ xc[:-1] / (xc[:-1] @ xc[:-1]))   # x に AR(1) を当てはめる
                sd = float(np.std(xc[1:] - ph * xc[:-1]))
                p5 = (1 + (np.abs(lag_corrs(y, ar1(rng, n, ph, B) * sd)).max(1) >= mx).sum()) / (B + 1)
                rows.append(dict(years=yrs, phi=phi, rep=r, best_lag=k, max_abs_corr=mx, corr_lag0=c[0],
                                 p_T1=tp(c[0], neff), p_T2=tp(c[k], neff), p_T3=p3, p_T4=p4, p_T5=p5, phi_hat_x=ph))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "reps.csv", index=False, float_format="%.6f")
    g = df.groupby(["years", "phi"])
    sm = g.agg(median_max_abs_corr=("max_abs_corr", "median"), p90_max_abs_corr=("max_abs_corr", lambda v: v.quantile(0.9)),
               median_abs_corr_lag0=("corr_lag0", lambda v: v.abs().median()),
               share_max_over_03=("max_abs_corr", lambda v: (v >= 0.3).mean()),
               **{f"reject_{t}": (f"p_{t}", lambda v: (v < 0.05).mean()) for t in ["T1", "T2", "T3", "T4", "T5"]}).reset_index()
    sm.to_csv(RES / "summary.csv", index=False, float_format="%.4f")
    print(sm.to_string())
    json.dump({"reps": REPS, "B": B, "summary": sm.round(4).to_dict("records")}, open(RES / "a546_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：10年・最大相関の分布（φ=0 と 0.9）、ずらし幅0の分布も
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bins = np.linspace(0, 0.8, 41)
    d0 = df[(df.years == 10) & (df.phi == 0.0)]; d9 = df[(df.years == 10) & (df.phi == 0.9)]
    ax.hist(d0.corr_lag0.abs(), bins=bins, color=LIGHT, label="ずらし幅0だけ（φ=0）", alpha=0.9)
    ax.hist(d0.max_abs_corr, bins=bins, histtype="step", lw=2, color=BLUE, label="13通りから最大を選ぶ（φ=0）")
    ax.hist(d9.max_abs_corr, bins=bins, histtype="step", lw=2, color=ORANGE, label="13通りから最大を選ぶ（φ=0.9）")
    for d, c in [(d0.corr_lag0.abs(), GRAY), (d0.max_abs_corr, BLUE), (d9.max_abs_corr, ORANGE)]:
        ax.axvline(d.median(), color=c, ls="--", lw=1)
    ax.set_xlabel("相関の絶対値（関係のない2系列、10年＝120か月）"); ax.set_ylabel("回数（1,000回のうち）")
    ax.set_title("ずらし幅を選ぶと、関係がなくても相関は高く出る（点線は中央値）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a546_max_corr_hist.png", SRC)

    # 図2：10年、方法×φ の「有意」割合
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    s10 = sm[sm.years == 10]
    labs = ["T1 ずらし幅0\nだけt検定", "T2 選んだ幅\nをt検定", "T3 並べ替え", "T4 ブロックの\n並べ替え", "T5 AR(1)で\n作り直し"]
    w = 0.26
    for i, (phi, c) in enumerate(zip(PHIS, [LIGHT, BLUE, ORANGE])):
        v = s10[s10.phi == phi][[f"reject_T{j}" for j in range(1, 6)]].values[0] * 100
        b = ax.bar(np.arange(5) + (i - 1) * w, v, w, color=c, label=f"自己相関 φ={phi}")
        for xx, vv in zip(np.arange(5) + (i - 1) * w, v):
            ax.text(xx, vv + 1, f"{vv:.0f}", ha="center", fontsize=8.5)
    ax.axhline(5, color=INK, lw=0.8, ls="--"); ax.text(4.45, 6, "5%", fontsize=9)
    ax.set_xticks(range(5)); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylabel("関係がないのに「有意」と出た割合（%）"); ax.set_title("10年分の月次で、判定のしかたごとの「有意」の割合")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a546_false_positive.png", SRC)

    # 図3：年数別、T2 と T5
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for phi, c in zip(PHIS, [GRAY, BLUE, ORANGE]):
        s = sm[sm.phi == phi]
        ax.plot(s.years, s.reject_T2 * 100, "-o", color=c, label=f"T2 選んだ幅をt検定 φ={phi}")
        ax.plot(s.years, s.reject_T5 * 100, ":s", color=c, label=f"T5 AR(1)で作り直し φ={phi}")
    ax.axhline(5, color=INK, lw=0.8, ls="--")
    ax.set_xticks(YEARS); ax.set_xlabel("系列の長さ（年）"); ax.set_ylabel("「有意」と出た割合（%）")
    ax.set_title("データを長くしても、選んだ幅のt検定は5%に戻らない")
    ax.set_ylim(0, 95)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="center", bbox_to_anchor=(0.5, 0.27))
    save(fig, "a546_by_years.png", SRC)


if __name__ == "__main__":
    main()
