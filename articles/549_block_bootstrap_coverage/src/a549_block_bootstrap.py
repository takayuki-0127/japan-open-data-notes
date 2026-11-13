"""549 自己相関のある日次データで、ふつうのブートストラップの95%区間は、正解を何%含むのか（手法の解説・正解の分かるデータで試す）

架空の日次の系列（本当の平均 100、AR(1) の自己相関 φ = 0・0.3・0.6・0.9、長さ 90・365・1,000日）で、平均の95%区間を作る。
区間の作り方：
  t区間（ふつうの標準誤差）、ふつうのブートストラップ（1日ずつ戻して引く、パーセンタイル）、
  ブロックブートストラップ（つながった日をまとめて引く、循環の移動ブロック、長さ 5・20・50日、パーセンタイル）
各場面 500回、ブートストラップは 499回。区間が本当の平均（100）を含む割合と、区間の幅を数える。乱数の種 549。
数字は置いた系列の作り方（AR(1)、正規分布の誤差）で決まる。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
from scipy.signal import lfilter
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "出典：架空の日次の系列（作成者が乱数で作成、seed 549）"
PHIS = [0.0, 0.3, 0.6, 0.9]
NS = [90, 365, 1000]
BLOCKS = [5, 20, 50]
REPS, B = 500, 499
MU, SD = 100.0, 10.0


def ar1(rng, n, phi):
    """定常な AR(1)（平均 MU、標準偏差 SD）"""
    e = rng.standard_normal(n) * SD * np.sqrt(1 - phi ** 2)
    e[0] = rng.standard_normal() * SD
    return MU + lfilter([1.0], [1.0, -phi], e)


def true_se(n, phi):
    k = np.arange(1, n)
    return SD * np.sqrt((1 + 2 * np.sum((1 - k / n) * phi ** k)) / n)


def boot_iid(rng, x):
    n = len(x)
    return x[rng.integers(0, n, (B, n))].mean(1)


def boot_block(rng, x, L):
    """循環の移動ブロック：長さ L のつながった日を、始まりをばらばらに選んで並べる"""
    n = len(x); nb = -(-n // L)
    cs = np.concatenate([[0.0], np.cumsum(np.concatenate([x, x[:L]]))])
    blk = cs[np.arange(n) + L] - cs[np.arange(n)]        # 各始まりからの L 日の合計
    st = rng.integers(0, n, (B, nb))
    tot = blk[st[:, :-1]].sum(1)
    last = n - (nb - 1) * L                                # 最後のブロックは n 日に合わせて切る
    tot += cs[st[:, -1] + last] - cs[st[:, -1]]
    return tot / n


def main():
    rng = np.random.default_rng(549)
    rows = []
    for n in NS:
        for phi in PHIS:
            for r in range(REPS):
                x = ar1(rng, n, phi); m = x.mean(); se = x.std(ddof=1) / np.sqrt(n)
                q = stats.t.ppf(0.975, n - 1)
                res = {"t": (m - q * se, m + q * se)}
                res["iid"] = tuple(np.quantile(boot_iid(rng, x), [0.025, 0.975]))
                for L in BLOCKS:
                    if L < n / 3:
                        res[f"block{L}"] = tuple(np.quantile(boot_block(rng, x, L), [0.025, 0.975]))
                for k, (lo, hi) in res.items():
                    rows.append(dict(n=n, phi=phi, rep=r, method=k, lo=lo, hi=hi, cover=int(lo <= MU <= hi), width=hi - lo))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "reps.csv", index=False, float_format="%.5f")
    sm = df.groupby(["n", "phi", "method"]).agg(coverage=("cover", "mean"), mean_width=("width", "mean")).reset_index()
    sm["true_width"] = [2 * 1.96 * true_se(n, phi) for n, phi in zip(sm.n, sm.phi)]
    sm["width_ratio"] = sm.mean_width / sm.true_width
    sm.to_csv(RES / "summary.csv", index=False, float_format="%.4f")
    print(sm.to_string())
    json.dump({"reps": REPS, "B": B, "summary": sm.round(4).to_dict("records")}, open(RES / "a549_main.json", "w"), ensure_ascii=False, indent=1)

    order = ["t", "iid", "block5", "block20", "block50"]
    lab = {"t": "t区間", "iid": "ふつうの\nブートストラップ", "block5": "ブロック\n5日", "block20": "ブロック\n20日", "block50": "ブロック\n50日"}
    # 図1：365日、方法×φ の当たる割合
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); w = 0.2
    s = sm[sm.n == 365]
    for i, (phi, c) in enumerate(zip(PHIS, [LIGHT, BLUE, GREEN, ORANGE])):
        v = [s[(s.phi == phi) & (s.method == m)].coverage.iloc[0] * 100 for m in order]
        xs = np.arange(len(order)) + (i - 1.5) * w
        ax.bar(xs, v, w, color=c, label=f"自己相関 φ={phi}")
        for xx, vv in zip(xs, v):
            ax.text(xx, vv + 1, f"{vv:.0f}", ha="center", fontsize=7.5)
    ax.axhline(95, color=INK, lw=0.8, ls="--")
    ax.set_xticks(range(len(order))); ax.set_xticklabels([lab[m] for m in order], fontsize=9)
    ax.set_ylim(0, 118); ax.set_ylabel("区間が本当の平均を含んだ割合（%）")
    ax.set_title("365日分の平均の95%区間（点線は95%）")
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="upper center")
    save(fig, "a549_coverage_365.png", SRC)

    # 図2：区間の幅（本当に必要な幅との比）、365日
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for m, c in [("t", INK), ("iid", GRAY), ("block5", LIGHT), ("block20", BLUE), ("block50", ORANGE)]:
        g = s[s.method == m]; ax.plot(g.phi, g.width_ratio, "-o", color=c, label=lab[m].replace("\n", ""))
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xticks(PHIS); ax.set_xlabel("自己相関 φ"); ax.set_ylabel("区間の幅 ÷ 本当に必要な幅")
    ax.set_ylim(0, 1.2)
    ax.set_title("区間の幅は、本当に必要な幅の何倍か（365日）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a549_width_ratio.png", SRC)

    # 図3：日数別、φ=0.6 と 0.9 の当たる割合（ふつう・ブロック20）
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for phi, c in [(0.6, BLUE), (0.9, ORANGE)]:
        for m, ls, mk in [("iid", ":", "s"), ("block20", "-", "o")]:
            g = sm[(sm.phi == phi) & (sm.method == m)].sort_values("n")
            ax.plot(g.n, g.coverage * 100, ls, marker=mk, color=c, label=f"{lab[m].replace(chr(10), '')} φ={phi}")
    ax.axhline(95, color=INK, lw=0.8, ls="--")
    ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n}日" for n in NS]); ax.minorticks_off()
    ax.set_ylim(0, 100); ax.set_ylabel("本当の平均を含んだ割合（%）"); ax.set_xlabel("系列の長さ")
    ax.set_title("日数を増やしても、ふつうのブートストラップは当たるようにならない")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower right")
    save(fig, "a549_by_n.png", SRC)


if __name__ == "__main__":
    main()
