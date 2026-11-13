"""510 同じ検証データで2つのモデルの成績を比べると、本当は同じ力でも、何%の回で「片方が良い」と出るのか

架空の予測問題。検証データの1件ごとに「難しさ」u があり、2つのモデルはどちらも u に引きずられて当たり外れが決まる
（同じデータで同じ問題を解くので、当たり外れはそろいやすい）。
  モデルA が当たる：u + eA > cA、モデルB が当たる：u + eB > cB（u ~ N(0,1)、eA, eB ~ N(0, 0.6²) で独立）
  cA, cB で正解率を決める（同じ力：どちらも80%、少し差：Aが81%・Bが80%）。
検証データの大きさ n を変え、各2,000回作り直して、
  ・素直に比べたとき、A と B のどちらかが上に出る割合（同点を除く）
  ・差の95%区間（ブートストラップ）が0をまたがない＝「差がある」と出る割合：
      対応のある比べ（同じ1件の当たり外れを組で並べ直す）／対応のない比べ（A と B を別々に並べ直す）
を数える。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 510
SRC = "架空の予測問題（作成者が乱数で作成、seed 510）"
SE = 0.6
NS = [100, 200, 500, 1000, 2000, 5000, 10000, 20000]
REPS, BOOT = 2000, 1000


def cut(acc):
    return -np.sqrt(1 + SE**2) * stats.norm.ppf(acc)


def one(n, acc_a, acc_b, rng):
    u = rng.standard_normal(n)
    a = u + SE * rng.standard_normal(n) > cut(acc_a)
    b = u + SE * rng.standard_normal(n) > cut(acc_b)
    return a, b


def boot_ci(a, b, rng):
    n = len(a)
    cells = np.array([(a & b).sum(), (a & ~b).sum(), (~a & b).sum(), (~a & ~b).sum()])
    m = rng.multinomial(n, cells / n, BOOT)                       # 対応のある並べ直し：1件ごとの組を引き直す
    d_pair = (m[:, 1] - m[:, 2]) / n
    d_unp = rng.binomial(n, a.mean(), BOOT) / n - rng.binomial(n, b.mean(), BOOT) / n   # 対応のない並べ直し
    q = lambda d: np.quantile(d, [0.025, 0.975])
    return q(d_pair), q(d_unp)


def run(acc_a, acc_b, rng):
    rows = []
    for n in NS:
        for r in range(REPS):
            a, b = one(n, acc_a, acc_b, rng)
            diff = a.mean() - b.mean()
            cp, cu = boot_ci(a, b, rng)
            rows.append(dict(n=n, rep=r, acc_a=a.mean(), acc_b=b.mean(), diff=diff,
                             agree=float((a == b).mean()), corr=float(np.corrcoef(a, b)[0, 1]),
                             sig_pair=bool(cp[0] > 0 or cp[1] < 0), sig_unp=bool(cu[0] > 0 or cu[1] < 0),
                             mcnemar_p=float(stats.binomtest(int((a & ~b).sum()), int((a != b).sum())).pvalue) if (a != b).any() else 1.0))
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    eq = run(0.80, 0.80, rng); eq["case"] = "同じ力（80%と80%）"
    sm = run(0.81, 0.80, rng); sm["case"] = "少し差（81%と80%）"
    allr = pd.concat([eq, sm]); allr.round(5).to_csv(RES / "reps.csv", index=False)
    g = allr.groupby(["case", "n"]).agg(a_better=("diff", lambda d: (d > 0).mean()), b_better=("diff", lambda d: (d < 0).mean()),
                                        tie=("diff", lambda d: (d == 0).mean()), gap1pt=("diff", lambda d: (d.abs().round(9) >= 0.01).mean()),
                                        gap2pt=("diff", lambda d: (d.abs().round(9) >= 0.02).mean()),
                                        sig_pair=("sig_pair", "mean"), sig_unp=("sig_unp", "mean"),
                                        mcnemar=("mcnemar_p", lambda p: (p < 0.05).mean()),
                                        agree=("agree", "mean"), corr=("corr", "mean"), sd_diff=("diff", "std")).reset_index()
    g.round(4).to_csv(RES / "summary.csv", index=False)
    print(g.round(3).to_string(index=False))
    # 差を80%の回で見分けるのに要る件数（対応のある比べ、少し差の場合）：線形補間
    s = g[g.case.str.startswith("少し")]
    need = lambda col: float(np.interp(0.8, s[col], s.n)) if s[col].max() >= 0.8 else None
    out = dict(seed=SEED, reps=REPS, boot=BOOT, ns=NS, n_needed_80pct_pair=need("sig_pair"), n_needed_80pct_unp=need("sig_unp"),
               summary=g.round(4).to_dict("records"))
    json.dump(out, open(RES / "a510_main.json", "w"), ensure_ascii=False, indent=1)
    print(out["n_needed_80pct_pair"], out["n_needed_80pct_unp"])

    # 図1：同じ力のモデル、n=1000 の差の分布
    d = eq[eq.n == 1000]["diff"] * 100
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    vc = d.round(1).value_counts().sort_index()                    # 1,000件なので差は0.1ポイント刻み
    big = np.abs(vc.index.to_numpy()) >= 1 - 1e-9
    ax.bar(vc.index[~big], vc[~big], width=0.08, color=LIGHT)
    ax.bar(vc.index[big], vc[big], width=0.08, color=BLUE, label=f"差が1ポイント以上：{(d.round(1).abs() >= 1).mean()*100:.1f}%")
    ax.set_xlabel("正解率の差（A − B、ポイント）"); ax.set_ylabel("回数（2,000回のうち）")
    ax.set_title(f"同じ力の2つのモデルでも、検証1,000件では差が出る（同点 {(d == 0).mean()*100:.1f}%）")
    ax.legend(frameon=False)
    save(fig, "a510_diff_hist.png", SRC + "。どちらも正解率80%、検証データ1,000件を2,000回作り直した")

    # 図2：同じ力なのに「差がある」と出る割合
    e = g[g.case.str.startswith("同じ")]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.plot(e.n, (1 - e.tie) * 100, "o-", color=GRAY, lw=2, label="素直に比べて、どちらかが上に出る")
    ax.plot(e.n, e.gap1pt * 100, "o-", color=LIGHT, lw=2, label="1ポイント以上の差が出る")
    ax.plot(e.n, e.sig_unp * 100, "o-", color=ORANGE, lw=2, label="対応のない区間で「差がある」")
    ax.plot(e.n, e.sig_pair * 100, "o-", color=BLUE, lw=2, label="対応のある区間で「差がある」")
    ax.set_xscale("log"); ax.set_ylim(0, 102); ax.set_xlabel("検証データの件数（対数目盛）"); ax.set_ylabel("2,000回のうちの割合（%）")
    ax.set_title("同じ力のモデル：上下はほぼ必ず付くが、区間で見れば約5%")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a510_false_diff.png", SRC + "。95%区間はブートストラップ（1,000回）")

    # 図3：少し差のあるモデル（81%と80%）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.plot(s.n, s.b_better * 100, "o-", color=GRAY, lw=2, label="弱いほう（B）が上に出る")
    ax.plot(s.n, s.sig_unp * 100, "o-", color=ORANGE, lw=2, label="対応のない区間で差を見分ける")
    ax.plot(s.n, s.sig_pair * 100, "o-", color=BLUE, lw=2, label="対応のある区間で差を見分ける")
    ax.axhline(80, color=GRAY, ls="--", lw=1)
    ax.set_xscale("log"); ax.set_ylim(0, 102); ax.set_xlabel("検証データの件数（対数目盛）"); ax.set_ylabel("2,000回のうちの割合（%）")
    ax.set_title("1ポイントの差を8割の回で見分けるには、組で比べても約1万4千件要る")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a510_small_diff.png", SRC + "。Aの正解率81%、Bの正解率80%")


if __name__ == "__main__":
    main()
