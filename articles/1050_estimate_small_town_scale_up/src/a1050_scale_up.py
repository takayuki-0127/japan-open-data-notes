"""1050 小さな町の数字を大きな町に当てはめると、規模の違いでどれだけずれるのか？（架空のデータ）

架空の町の、架空のサービスの1年の申し込み件数。町の期待件数＝200×(人口÷1万)^β×町ごとの振れ。
β＞1 なら大きな町ほど1人あたりの件数が多い（β＝1 なら人口に比例）。実際の件数はポアソン分布で引く。
小さな町（人口2,000〜1万）の数字から、大きな町（人口10万〜30万）の件数を見込み、
見込み÷実際の件数（何倍か）を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, NullLocator
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1050
SRC = "架空の町と架空のサービスの申し込み（作成者が乱数で作成、seed 1050）"
BETA, SIG = 1.15, 0.30
N_SMALL, N_MID, N_BIG = 30, 10, 20
REPS = 4000
METHODS = ["①小さな町1つの1人あたり", "②小さな町30の合計の1人あたり", "③中くらいの町1つの1人あたり",
           "④小さな町30で規模の傾きを引いて延ばす", "⑤小さな町と中くらいの町40で傾きを引いて延ばす"]


def lam(pop, beta, u):
    return 200.0 * (pop / 1e4) ** beta * np.exp(u)


def towns(rng, reps, n, lo, hi, beta, sig):
    pop = np.round(np.exp(rng.uniform(np.log(lo), np.log(hi), (reps, n))))
    u = rng.normal(-sig ** 2 / 2, sig, (reps, n))
    cnt = rng.poisson(lam(pop, beta, u))
    return pop, cnt


def slope_fit(pop, cnt):
    """各回ごとに log(件数) を log(人口) に当てはめる（件数0は0.5件として扱う）"""
    x = np.log(pop); y = np.log(np.maximum(cnt, 0.5))
    xm, ym = x.mean(1, keepdims=True), y.mean(1, keepdims=True)
    b = ((x - xm) * (y - ym)).sum(1) / ((x - xm) ** 2).sum(1)
    a = ym[:, 0] - b * xm[:, 0]
    return a, b


def run(rng, reps=REPS, beta=BETA, sig=SIG, big_lo=1e5, big_hi=3e5, n_big=N_BIG):
    ps, cs = towns(rng, reps, N_SMALL, 2e3, 1e4, beta, sig)
    pm, cm = towns(rng, reps, N_MID, 2e4, 5e4, beta, sig)
    pb, cb = towns(rng, reps, n_big, big_lo, big_hi, beta, sig)
    pick = rng.integers(0, N_SMALL, (reps, n_big))
    pickm = rng.integers(0, N_MID, (reps, n_big))
    r = np.arange(reps)[:, None]
    est = {}
    est[METHODS[0]] = cs[r, pick] / ps[r, pick] * pb
    est[METHODS[1]] = (cs.sum(1) / ps.sum(1))[:, None] * pb
    est[METHODS[2]] = cm[r, pickm] / pm[r, pickm] * pb
    a, b = slope_fit(ps, cs)
    est[METHODS[3]] = np.exp(a[:, None] + b[:, None] * np.log(pb))
    a2, b2 = slope_fit(np.hstack([ps, pm]), np.hstack([cs, cm]))
    est[METHODS[4]] = np.exp(a2[:, None] + b2[:, None] * np.log(pb))
    # 式の値：② の見込みの期待値 ÷ 大きな町の件数の中央値（町ごとの振れの中央値は exp(−σ²/2)）
    f2 = (lam(ps, beta, 0).sum(1) / ps.sum(1))[:, None] * pb / lam(pb, beta, -sig ** 2 / 2)
    return est, cb, f2, b, b2, (ps, cs, pm, cm, pb, cb)


def summarize(est, truth):
    rows = []
    ok = truth > 0
    for m, e in est.items():
        ratio = e[ok] / truth[ok]
        lr = np.log(np.maximum(ratio, 1e-9))
        rows.append({"method": m, "median_ratio": round(float(np.median(ratio)), 4),
                     "p10_ratio": round(float(np.quantile(ratio, .1)), 4),
                     "p90_ratio": round(float(np.quantile(ratio, .9)), 4),
                     "median_abs_miss_times": round(float(np.exp(np.median(np.abs(lr)))), 4),
                     "share_low_pct": round(float((ratio < 1).mean()) * 100, 2)})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    est, cb, f2, b, b2, raw = run(rng)
    base = summarize(est, cb)
    base.to_csv(RES / "methods_base.csv", index=False)
    slope = {"beta_set": BETA, "small_slope_median": round(float(np.median(b)), 4),
             "small_slope_p10": round(float(np.quantile(b, .1)), 4), "small_slope_p90": round(float(np.quantile(b, .9)), 4),
             "small_mid_slope_median": round(float(np.median(b2)), 4),
             "small_mid_slope_p10": round(float(np.quantile(b2, .1)), 4),
             "small_mid_slope_p90": round(float(np.quantile(b2, .9)), 4)}
    formula2 = round(float(np.median(f2)), 4)
    # 1回分の町（data）
    ps, cs, pm, cm, pb, cbb = raw
    rows = []
    for kind, p, c in [("小さな町", ps[0], cs[0]), ("中くらいの町", pm[0], cm[0]), ("大きな町", pb[0], cbb[0])]:
        for i, (pp, cc) in enumerate(zip(p, c)):
            rows.append({"kind": kind, "town": f"{kind}{i+1}", "population": int(pp), "count": int(cc),
                         "per_10k": round(cc / pp * 1e4, 3)})
    one = pd.DataFrame(rows)
    one.to_csv(DATA / "towns_one_draw.csv", index=False)
    # 例：A町（小さな町の1つ）から B市（大きな町の1つ）
    ia = int(np.argsort(ps[0])[N_SMALL // 2]); ib = int(np.argmax(pb[0]))
    ex = {"A_pop": int(ps[0, ia]), "A_count": int(cs[0, ia]), "B_pop": int(pb[0, ib]), "B_count": int(cbb[0, ib]),
          "B_est_from_A": round(float(cs[0, ia] / ps[0, ia] * pb[0, ib]), 1),
          "B_est_from_A_ratio": round(float(cs[0, ia] / ps[0, ia] * pb[0, ib] / cbb[0, ib]), 4),
          "B_est_from_30": round(float(cs[0].sum() / ps[0].sum() * pb[0, ib]), 1),
          "B_est_from_30_ratio": round(float(cs[0].sum() / ps[0].sum() * pb[0, ib] / cbb[0, ib]), 4),
          "small30_per_10k": round(float(cs[0].sum() / ps[0].sum() * 1e4), 3),
          "big20_per_10k": round(float(cbb[0].sum() / pb[0].sum() * 1e4), 3)}

    # 確かめ：β × 町ごとの振れ × 大きな町の大きさ（36通り、各1,000回×大きな町1つ）
    sens = []
    for beta in [0.85, 1.0, 1.15, 1.3]:
        for sig in [0.15, 0.3, 0.5]:
            for size in [5e4, 1.5e5, 5e5]:
                e, t, ff, bb, bb2, _ = run(np.random.default_rng(SEED * 100 + len(sens)), 1000, beta, sig, size, size, 1)
                s = summarize(e, t).set_index("method")
                row = {"beta": beta, "sigma": sig, "big_pop": int(size), "formula2_ratio": round(float(np.median(ff)), 4)}
                for k, m in enumerate(METHODS):
                    row[f"m{k+1}_median"] = s.loc[m, "median_ratio"]
                    row[f"m{k+1}_p10"] = s.loc[m, "p10_ratio"]
                    row[f"m{k+1}_p90"] = s.loc[m, "p90_ratio"]
                    row[f"m{k+1}_absmiss"] = s.loc[m, "median_abs_miss_times"]
                sens.append(row)
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    s115 = sens[sens.beta == 1.15]; s1 = sens[sens.beta == 1.0]; sne = sens[sens.beta != 1.0]
    best = sens[[f"m{k+1}_absmiss" for k in range(5)]].idxmin(axis=1).str[1].astype(int)
    summary = {
        "m2_median_range_all36": [float(sens.m2_median.min()), float(sens.m2_median.max())],
        "m2_median_range_by_beta": {str(bt): [float(g.m2_median.min()), float(g.m2_median.max())] for bt, g in sens.groupby("beta")},
        "m4_median_range_all36": [float(sens.m4_median.min()), float(sens.m4_median.max())],
        "m4_p10_min_all36": float(sens.m4_p10.min()), "m4_p90_max_all36": float(sens.m4_p90.max()),
        "max_abs_formula2_minus_sim_m2": round(float((sens.m2_median - sens.formula2_ratio).abs().max()), 4),
        "best_absmiss_method_counts": {METHODS[k - 1]: int((best == k).sum()) for k in range(1, 6)},
        "m2_better_than_m4_absmiss_beta1": int((s1.m2_absmiss < s1.m4_absmiss).sum()),
        "m5_better_than_m2_absmiss_beta_ne1": int((sne.m5_absmiss < sne.m2_absmiss).sum()),
        "n_beta_ne1": int(len(sne)), "n_beta1": int(len(s1)),
    }
    out = {"settings": {"beta": BETA, "sigma": SIG, "reps": REPS, "n_small": N_SMALL, "n_mid": N_MID, "n_big": N_BIG,
                        "base_per_10k_at_10k": 200},
           "methods_base": base.to_dict("records"), "formula2_median_ratio": formula2,
           "formula_per_person_ratio_10k_vs_100k": round(10 ** (-0.15), 4),
           "slope": slope, "example": ex, "sensitivity_summary": summary}
    json.dump(out, open(RES / "a1050_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1人あたりの件数と人口（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for kind, col in [("小さな町", ORANGE), ("中くらいの町", GREEN), ("大きな町", BLUE)]:
        d = one[one.kind == kind]
        ax.scatter(d.population, d.per_10k, s=22, color=col, alpha=.8, lw=0, label=kind)
    xx = np.exp(np.linspace(np.log(1.5e3), np.log(3.5e5), 50))
    ax.plot(xx, 200 * (xx / 1e4) ** (BETA - 1), color=GRAY, lw=1, ls="--", label="置いた式（振れなし）")
    ax.axhline(ex["small30_per_10k"], color=ORANGE, lw=1, ls=":", label=f"小さな町30の合計の1人あたり（{ex['small30_per_10k']:.0f}件）")
    ax.set_xscale("log"); ax.set_ylim(0, None)
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticks([2e3, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5]); ax.set_xticklabels(["2千", "5千", "1万", "2万", "5万", "10万", "20万"])
    ax.set_xlabel("町の人口（対数の目盛り）"); ax.set_ylabel("人口1万人あたりの申し込み件数")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("大きな町ほど1人あたりが多い置き方（β＝1.15、1回分の60町）")
    save(fig, "a1050_per_person.png", SRC)

    # 図2：見込みの方法ごとの、見込み÷実際（中央値と10〜90%）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    y = np.arange(len(base))[::-1]
    for yi, (_, rr) in zip(y, base.iterrows()):
        ax.plot([rr.p10_ratio, rr.p90_ratio], [yi, yi], color=LIGHT, lw=6, solid_capstyle="butt")
        ax.plot(rr.median_ratio, yi, "o", color=BLUE)
        ax.text(rr.p90_ratio * 1.04, yi, f"中央値{rr.median_ratio:.2f}倍（{rr.p10_ratio:.2f}〜{rr.p90_ratio:.2f}）",
                va="center", fontsize=8)
    ax.axvline(1, color=INK, lw=.8)
    ax.set_xscale("log"); ax.set_xlim(0.2, 6)
    ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([0.25, 0.5, 1, 2, 4]); ax.set_xticklabels(["0.25", "0.5", "1", "2", "4"])
    ax.set_yticks(y); ax.set_yticklabels(base.method, fontsize=8.5)
    ax.set_xlabel("見込み÷実際の件数（倍、対数の目盛り。帯は10〜90%）")
    ax.set_title(f"小さな町の1人あたりを当てはめると、大きな町を低く見込む（{REPS:,}回）")
    save(fig, "a1050_methods.png", SRC)

    # 図3：β ごとの②の中央値（大きな町の大きさ別、振れ0.3）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for size, col in [(5e4, LIGHT), (1.5e5, BLUE), (5e5, INK)]:
        d = sens[(sens.sigma == 0.3) & (sens.big_pop == int(size))]
        ax.plot(d.beta, d.m2_median, "o-", color=col, label=f"大きな町の人口{int(size/1e4)}万")
        ax.plot(d.beta, d.formula2_ratio, "x", color=GRAY, ms=7)
    ax.plot([], [], "x", color=GRAY, label="式の値")
    ax.axhline(1, color=INK, lw=.8)
    ax.set_yscale("log"); ax.yaxis.set_minor_locator(NullLocator()); ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_yticks([0.25, 0.5, 1, 2]); ax.set_yticklabels(["0.25", "0.5", "1", "2"])
    ax.set_xticks([0.85, 1.0, 1.15, 1.3])
    ax.set_xlabel("規模の傾き β（1なら人口に比例）"); ax.set_ylabel("②の見込み÷実際（中央値、倍）")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("ずれの向きと大きさは β と町の大きさの違いで決まる（町ごとの振れ0.3）")
    save(fig, "a1050_beta.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
