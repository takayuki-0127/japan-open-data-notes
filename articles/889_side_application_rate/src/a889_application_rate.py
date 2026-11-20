"""889 応募の採用率は、何件応募すれば読めるのか？（架空のデータ）

架空の副業・フリーランスの人が、仲介サービスの案件に応募する。1件ごとに本当の採用率 p で採用されると置き、
応募の件数ごとに、見かけの採用率（採用÷応募）がどれだけ振れるか、数え方（最初に採用されたところで数える）で
どれだけずれるか、応募文の2つの書き方の差を何件で見分けられるかを数える。
"""
import json
from math import lgamma, log, exp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 889
SRC = "架空の応募と採用（作成者が乱数で作成、seed 889）"
P_BASE = 0.10
NS = [5, 10, 20, 30, 50, 100, 200, 300, 500]


LG = np.concatenate([[0.0], np.cumsum(np.log(np.arange(1, 5001)))])  # log(k!)


def binom_pmf(n, p):
    k = np.arange(n + 1)
    lc = LG[n] - LG[k] - LG[n - k]
    return np.exp(lc + k * log(p) + (n - k) * log(1 - p))


def quantile_rate(n, p, q):
    c = np.cumsum(binom_pmf(n, p))
    return float(np.searchsorted(c, q - 1e-12) / n)


def p_within(n, p, abs_tol=None, rel_tol=None):
    pm = binom_pmf(n, p); r = np.arange(n + 1) / n
    tol = abs_tol if abs_tol is not None else rel_tol * p
    return float(pm[np.abs(r - p) <= tol + 1e-12].sum())


def need_n(p, abs_tol=None, rel_tol=None, target=0.9, nmax=3000):
    """これ以上のどの件数でも target を下回らない最小の n（離散のでこぼこを避ける）"""
    ok = np.array([p_within(n, p, abs_tol, rel_tol) >= target for n in range(1, nmax + 1)])
    bad = np.where(~ok)[0]
    return int(bad[-1] + 2) if len(bad) else 1


def ab_probs(n, pa, pb):
    a, b = binom_pmf(n, pa), binom_pmf(n, pb)
    ca = np.cumsum(a)
    b_better = float((b[1:] * ca[:-1]).sum())
    tie = float((a * b).sum())
    return b_better, tie, 1 - b_better - tie


def main():
    rng = np.random.default_rng(SEED)

    # 1) 件数ごとの見かけの採用率の幅（式で正確に）
    prec = []
    for p in [0.05, 0.10, 0.20, 0.30]:
        for n in NS:
            prec.append({"p": p, "n": n, "p10": round(quantile_rate(n, p, 0.10), 4), "p90": round(quantile_rate(n, p, 0.90), 4),
                         "p05": round(quantile_rate(n, p, 0.05), 4), "p95": round(quantile_rate(n, p, 0.95), 4),
                         "within_5pt": round(p_within(n, p, abs_tol=0.05), 4),
                         "within_rel30": round(p_within(n, p, rel_tol=0.3), 4),
                         "zero_accept": round(float((1 - p) ** n), 4)})
    prec = pd.DataFrame(prec)
    prec.to_csv(RES / "rate_range_by_n.csv", index=False)
    need = []
    for p in [0.05, 0.10, 0.20, 0.30]:
        need.append({"p": p, "n_within_5pt_90": need_n(p, abs_tol=0.05),
                     "n_within_rel30_90": need_n(p, rel_tol=0.3),
                     "n_within_rel50_90": need_n(p, rel_tol=0.5)})
    need = pd.DataFrame(need)
    need.to_csv(RES / "needed_n.csv", index=False)

    # 2) 最初に採用されたところで数える（20万人）
    first = []
    for p in [0.05, 0.10, 0.20, 0.30]:
        r = np.random.default_rng(SEED * 10 + int(p * 100))
        for k in [1, 3, 5, 10]:
            nk = r.negative_binomial(k, p, 200000) + k  # k件目の採用までの応募の件数
            rate = k / nk
            unb = (k - 1) / (nk - 1) if k > 1 else np.full(len(nk), np.nan)
            first.append({"p": p, "k_accepts": k, "mean_rate": round(float(rate.mean()), 4),
                          "median_rate": round(float(np.median(rate)), 4),
                          "share_above_true": round(float((rate > p).mean()), 4),
                          "mean_unbiased": round(float(np.nanmean(unb)), 4) if k > 1 else None,
                          "median_n": float(np.median(nk))})
    first = pd.DataFrame(first)
    first.to_csv(RES / "stop_at_kth_accept.csv", index=False)
    theo_first = round(-P_BASE * log(P_BASE) / (1 - P_BASE), 4)  # E[1/N]（幾何分布）

    # 決めた件数（10件）で数える場合との比べ（p=0.10）
    fixed10 = np.random.default_rng(SEED + 1).binomial(10, P_BASE, 200000) / 10
    fixed = {"fixed10_mean": round(float(fixed10.mean()), 4), "fixed10_median": round(float(np.median(fixed10)), 4)}

    # 3) 応募文の書き方 A（本当10%）と B（本当15%など）を見分ける
    ab = []
    for pb in [0.12, 0.15, 0.20]:
        for n in [10, 20, 50, 100, 200, 300, 500, 1000]:
            bb, tie, aa = ab_probs(n, 0.10, pb)
            ab.append({"pa": 0.10, "pb": pb, "n_each": n, "b_looks_better": round(bb, 4), "tie": round(tie, 4),
                       "a_looks_better": round(aa, 4)})
    ab = pd.DataFrame(ab)
    ab.to_csv(RES / "ab_compare.csv", index=False)
    ab_need = {}
    for pb in [0.12, 0.15, 0.20]:
        ok = [n for n in range(5, 3001, 5) if ab_probs(n, 0.10, pb)[0] >= 0.8]
        ab_need[str(pb)] = ok[0]

    # 4) 確かめ：月ごとに採用率が上下する（同じ月の応募はまとまって当たり外れ）
    sens = []
    MONTH = 10  # 1か月の応募の件数
    for kappa in [None, 50, 10, 3]:
        r = np.random.default_rng(SEED * 100 + (0 if kappa is None else kappa))
        for p in [0.10, 0.20]:
            for n in [50, 100, 200, 500]:
                m = n // MONTH; R = 40000
                if kappa is None:
                    pm = np.full((R, m), p)
                else:
                    pm = r.beta(p * kappa, (1 - p) * kappa, (R, m))
                acc = r.binomial(MONTH, pm).sum(1) / n
                sens.append({"kappa": "なし" if kappa is None else kappa, "p": p, "n": n,
                             "p10": round(float(np.quantile(acc, .1)), 4), "p90": round(float(np.quantile(acc, .9)), 4),
                             "within_5pt": round(float((np.abs(acc - p) <= 0.05 + 1e-12).mean()), 4)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_month_swing.csv", index=False)
    # 1人分の応募の記録（p=0.10、500件）
    one = (rng.random(500) < P_BASE).astype(int)
    log_df = pd.DataFrame({"application_no": np.arange(1, 501), "month": (np.arange(500) // MONTH) + 1, "accepted": one})
    log_df["running_rate"] = (log_df.accepted.cumsum() / log_df.application_no).round(4)
    log_df.to_csv(DATA / "one_person_applications.csv", index=False)
    # 最初の採用で数えた2,000人（p=0.10）
    n1 = np.random.default_rng(SEED + 2).geometric(P_BASE, 2000)
    pd.DataFrame({"person": np.arange(1, 2001), "applications_until_first": n1,
                  "rate_at_first": (1 / n1).round(4)}).to_csv(DATA / "first_accept_2000.csv", index=False)

    pick = lambda p, n: prec[(prec.p == p) & (prec.n == n)].iloc[0].to_dict()
    out = {"p_base": P_BASE, "rate_range_p10": {str(n): pick(0.10, n) for n in NS}, "needed_n": need.to_dict("records"),
           "stop_at_first_accept_theory_p10": theo_first, "stop_at_kth_accept": first.to_dict("records"),
           "fixed_10_applications": fixed, "ab_need_80pct": ab_need, "ab_compare": ab.to_dict("records"),
           "one_person": {"n100_rate": float(log_df.running_rate.iloc[99]), "n500_rate": float(log_df.running_rate.iloc[499]),
                          "n20_rate": float(log_df.running_rate.iloc[19]),
                          "running_min_after20": float(log_df.running_rate.iloc[19:].min()),
                          "running_max_after20": float(log_df.running_rate.iloc[19:].max())}}
    json.dump(out, open(RES / "a889_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：件数ごとの見かけの採用率の幅（本当10%）と、20人の途中経過
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    nn = np.arange(5, 501)
    lo = [quantile_rate(n, P_BASE, 0.05) for n in nn]; hi = [quantile_rate(n, P_BASE, 0.95) for n in nn]
    ax.fill_between(nn, np.array(lo) * 100, np.array(hi) * 100, color=LIGHT, alpha=.6, step="mid", lw=0,
                    label="9割の人が入る幅（5〜95%）")
    pr = np.random.default_rng(SEED + 3)
    for i in range(20):
        a = (pr.random(500) < P_BASE).cumsum() / np.arange(1, 501)
        ax.plot(np.arange(5, 501), a[4:] * 100, color=GRAY, lw=.7, alpha=.7)
    ax.axhline(P_BASE * 100, color=ORANGE, lw=1.2, ls="--", label="本当の採用率 10%")
    ax.set_xscale("log"); ax.set_xticks([5, 10, 20, 50, 100, 200, 500], ["5", "10", "20", "50", "100", "200", "500"])
    ax.set_xlabel("応募の件数（対数の目盛り）"); ax.set_ylabel("見かけの採用率（%）"); ax.set_ylim(0, 45)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("本当の採用率10%でも、数十件では見かけが大きく振れる（灰色は20人の途中経過）", fontsize=11.5)
    save(fig, "a889_funnel.png", SRC)

    # 図2：最初に採用されたところで数えた採用率
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    f1 = first[(first.p == P_BASE)]
    x = np.arange(len(f1))
    ax.bar(x, f1.mean_rate * 100, 0.55, color=BLUE)
    for i, v in enumerate(f1.mean_rate * 100):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9)
    ax.axhline(P_BASE * 100, color=ORANGE, lw=1.2, ls="--")
    ax.set_xlim(-0.5, len(f1) + 0.6)
    ax.text(len(f1) + 0.55, P_BASE * 100 + 0.5, "本当 10%", color=ORANGE, fontsize=9, ha="right")
    ax.text(len(f1) + 0.55, P_BASE * 100 - 0.7, f"決めた10件で\n数えた平均 {fixed['fixed10_mean']*100:.1f}%", color=GRAY, fontsize=8.5, ha="right", va="top")
    ax.set_xticks(x, [f"{k}件目の採用で\n数える" for k in f1.k_accepts])
    ax.set_ylabel("見かけの採用率の平均（%）"); ax.set_ylim(0, f1.mean_rate.max() * 100 * 1.2)
    ax.set_title("採用されたところで数えると、採用率は高く出る（本当10%、20万人）", fontsize=12)
    save(fig, "a889_stop_at_accept.png", SRC)

    # 図3：応募文の2つの書き方
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for pb, c in [(0.12, GRAY), (0.15, BLUE), (0.20, GREEN)]:
        d = ab[ab.pb == pb]
        ax.plot(d.n_each, d.b_looks_better * 100, marker="o", ms=4, color=c, label=f"A 10% 対 B {int(pb*100)}%")
    ax.axhline(80, color=INK, lw=.8, ls=":"); ax.text(10.5, 81.5, "80%", fontsize=8.5)
    ax.set_xscale("log"); ax.set_xticks([10, 20, 50, 100, 200, 500, 1000], ["10", "20", "50", "100", "200", "500", "1000"])
    ax.set_xlabel("書き方ごとの応募の件数（対数の目盛り）"); ax.set_ylabel("本当に良い B が高く見える確率（%）", fontsize=10)
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("差が小さいほど、見分けるのに要る件数は急に増える（A の採用率10%）", fontsize=12)
    save(fig, "a889_ab.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main()
