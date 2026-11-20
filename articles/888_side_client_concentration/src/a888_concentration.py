"""888 1社に頼る割合が高いと、月の収入はどれだけ振れるのか？（架空のデータ）

架空の副業・フリーランスの人。取引先ごとの月の発注額は、置いた平均のまわりで上下に振れ、
取引先は毎月ある確率で発注が止まる（止まったあと、空いた分は G か月後に新しい取引先で埋まる）。
月の収入は「全部の取引先が続いているときの平均の月＝100」とした指数で数える（金額は扱わない）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 888
SRC = "架空の副業・フリーランスの人と取引先（作成者が乱数で作成、seed 888）"
BASE = {"sigma": 0.2, "hazard": 0.03, "gap": 3, "common": 0.1}
TOP_SHARES = [0.3, 0.5, 0.7, 0.9, 1.0]
N_OTHER = 4
MONTHS = 24


def shares_top(s, m=N_OTHER):
    if s >= 1.0:
        return np.array([1.0])
    return np.array([s] + [(1 - s) / m] * m)


def simulate(rng, shares, n, months=MONTHS, sigma=0.2, hazard=0.03, gap=3, common=0.1):
    """shares: (n, k) の割合（行ごとに合計1）。返り値：(n, months) の月の収入（指数）"""
    shares = np.atleast_2d(shares)
    if shares.shape[0] == 1:
        shares = np.repeat(shares, n, 0)
    k = shares.shape[1]
    wait = np.zeros((n, k), dtype=int)  # 0なら発注あり、>0なら空いている残りの月数
    out = np.zeros((n, months))
    for t in range(months):
        z = rng.normal(size=(n, 1))
        e = rng.normal(size=(n, k))
        x = np.exp(common * z + sigma * e - (common ** 2 + sigma ** 2) / 2)
        # この月に止まるか（発注ありの取引先だけ）
        stop = (wait == 0) & (rng.random((n, k)) < hazard)
        wait = np.where(stop, gap, wait)
        active = wait == 0
        out[:, t] = 100 * (shares * x * active).sum(1)
        wait = np.where(wait > 0, wait - 1, 0)
    return out


def year_stats(inc):
    y1, y2 = inc[:, :12], inc[:, 12:24]
    cv1 = y1.std(1) / y1.mean(1)
    any50_1 = (y1 < 50).any(1)
    any50_2 = (y2 < 50).any(1)
    return {"cv_median": round(float(np.median(cv1)), 3),
            "months_below70_pct": round(float((inc < 70).mean() * 100), 1),
            "year_any_below50_pct": round(float(any50_1.mean() * 100), 1),
            "year_min_median": round(float(np.median(y1.min(1))), 1),
            "year1_no_below50_pct": round(float((~any50_1).mean() * 100), 1),
            "year2_below50_given_year1_none_pct": round(float(any50_2[~any50_1].mean() * 100), 1),
            "mean_month": round(float(inc.mean()), 1)}


def main():
    rng = np.random.default_rng(SEED)
    N = 20000

    # 1) 1社の割合ごと（基本の置き方）
    by_share, store = [], {}
    for i, s in enumerate(TOP_SHARES):
        inc = simulate(np.random.default_rng(SEED * 10 + i), shares_top(s), N, **BASE)
        store[s] = inc
        st = year_stats(inc)
        sh = shares_top(s)
        by_share.append({"top_share": s, "n_clients": len(sh), "effective_n": round(float(1 / (sh ** 2).sum()), 2), **st})
    by_share = pd.DataFrame(by_share)
    by_share.to_csv(RES / "by_top_share.csv", index=False)

    # 2) 取引先の数で数えるか、割合で数えるか（数と割合をばらばらに置いた5,000人）
    n2 = 5000
    r2 = np.random.default_rng(SEED * 100)
    ks = r2.integers(2, 11, n2)
    cv24, eff, min24 = np.zeros(n2), np.zeros(n2), np.zeros(n2)
    for k in range(2, 11):
        idx = np.where(ks == k)[0]
        sh = r2.dirichlet(np.full(k, 0.7), len(idx))
        inc = simulate(np.random.default_rng(SEED * 100 + k), sh, len(idx), **BASE)
        cv24[idx] = inc.std(1) / inc.mean(1)
        min24[idx] = inc.min(1)
        eff[idx] = 1 / (sh ** 2).sum(1)
    cnt = pd.DataFrame({"n_clients": ks, "effective_n": eff, "cv24": cv24, "min24": min24})
    rank_corr = lambda a, b: round(float(pd.Series(a).rank().corr(pd.Series(b).rank())), 3)
    count_vs_share = {"spearman_cv_vs_n_clients": rank_corr(cnt.n_clients, cnt.cv24),
                      "spearman_cv_vs_effective_n": rank_corr(cnt.effective_n, cnt.cv24),
                      "spearman_min_vs_n_clients": rank_corr(cnt.n_clients, cnt.min24),
                      "spearman_min_vs_effective_n": rank_corr(cnt.effective_n, cnt.min24)}
    # 同じ「5社」でも割合で振れが違う例
    five = cnt[cnt.n_clients == 5]
    lo, hi = five.effective_n.quantile(0.1), five.effective_n.quantile(0.9)
    count_vs_share["five_clients_cv_median_low_effective"] = round(float(five[five.effective_n <= lo].cv24.median()), 3)
    count_vs_share["five_clients_cv_median_high_effective"] = round(float(five[five.effective_n >= hi].cv24.median()), 3)
    count_vs_share["five_clients_min_median_low_effective"] = round(float(five[five.effective_n <= lo].min24.median()), 1)
    count_vs_share["five_clients_min_median_high_effective"] = round(float(five[five.effective_n >= hi].min24.median()), 1)
    count_vs_share["five_clients_effective_p10"] = round(float(lo), 2)
    count_vs_share["five_clients_effective_p90"] = round(float(hi), 2)
    # 例：5社でトップ80%（ほか4社5%ずつ）と、3社均等
    ex = {}
    for name, sh in [("5社・1社80%", np.array([0.8, 0.05, 0.05, 0.05, 0.05])), ("3社・均等", np.full(3, 1 / 3))]:
        inc = simulate(np.random.default_rng(SEED * 1000 + len(sh)), sh, N, **BASE)
        ex[name] = {"effective_n": round(float(1 / (sh ** 2).sum()), 2), **year_stats(inc)}
    count_vs_share["examples"] = ex
    cnt.round(4).to_csv(RES / "count_vs_share.csv", index=False)

    # 3) 確かめ：置き方を変えると（1社30%と90%）
    rows = []
    j = 0
    for sg in [0.1, 0.2, 0.35]:
        for hz in [0.0, 0.015, 0.03, 0.05]:
            for cm in [0.0, 0.1, 0.2]:
                pr = {"sigma": sg, "hazard": hz, "gap": 3, "common": cm}
                row = dict(pr)
                for s in [0.3, 0.9]:
                    j += 1
                    st = year_stats(simulate(np.random.default_rng(SEED * 7 + j), shares_top(s), 4000, **pr))
                    row[f"any50_{int(s*100)}"] = st["year_any_below50_pct"]
                    row[f"cv_{int(s*100)}"] = st["cv_median"]
                    row[f"below70_{int(s*100)}"] = st["months_below70_pct"]
                rows.append(row)
    sens = pd.DataFrame(rows)
    sens["cv_ratio"] = (sens.cv_90 / sens.cv_30).round(2)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    s_h = sens[sens.hazard > 0]
    sens_sum = {"n_settings": int(len(sens)),
                "any50_30_range": [float(sens.any50_30.min()), float(sens.any50_30.max())],
                "any50_90_range": [float(sens.any50_90.min()), float(sens.any50_90.max())],
                "any50_90_range_hazard_pos": [float(s_h.any50_90.min()), float(s_h.any50_90.max())],
                "any50_30_range_hazard_pos": [float(s_h.any50_30.min()), float(s_h.any50_30.max())],
                "cv_ratio_range": [float(sens.cv_ratio.min()), float(sens.cv_ratio.max())],
                "always_90_higher_cv": bool((sens.cv_90 > sens.cv_30).all()),
                "always_90_higher_any50": bool((sens.any50_90 >= sens.any50_30).all()),
                "hazard0_any50_90_max": float(sens[sens.hazard == 0].any50_90.max()),
                "n_cv_90_lower": int((sens.cv_90 < sens.cv_30).sum()),
                "any50_ratio_hazard_pos_range": [round(float((s_h.any50_90 / s_h.any50_30).min()), 2),
                                                 round(float((s_h.any50_90 / s_h.any50_30).max()), 2)]}

    # 4) 式の確かめ：止まらない（hazard=0）・共通の振れなしなら CV ≒ sigma×√(割合の2乗の和)
    formula = []
    for i, s in enumerate([0.3, 0.9]):
        sh = shares_top(s)
        inc = simulate(np.random.default_rng(SEED * 3 + i), sh, N, sigma=0.2, hazard=0.0, gap=3, common=0.0)
        sd_month = float((inc.std(1, ddof=1) / inc.mean(1)).mean())
        theo = float(np.sqrt((np.exp(0.2 ** 2) - 1) * (sh ** 2).sum()))
        formula.append({"top_share": s, "cv_sim": round(sd_month, 4), "cv_formula": round(theo, 4)})

    formula_any_stop = round(float((1 - (1 - BASE["hazard"]) ** 12) * 100), 1)
    out = {"base": BASE, "formula_top_client_stops_in_year_pct": formula_any_stop, "n_other_clients": N_OTHER, "people_per_setting": N, "by_top_share": by_share.to_dict("records"),
           "count_vs_share": count_vs_share, "sensitivity_summary": sens_sum, "formula_check": formula}
    json.dump(out, open(RES / "a888_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # データ：1社30%と90%の人を200人ずつ、24か月分
    d = []
    for s in [0.3, 0.9]:
        m = store[s][:200]
        df = pd.DataFrame(m.round(2), columns=[f"m{t+1:02d}" for t in range(MONTHS)])
        df.insert(0, "top_share", s); df.insert(0, "person", np.arange(1, 201) + (0 if s == 0.3 else 1000))
        d.append(df)
    pd.concat(d).to_csv(DATA / "monthly_income_index.csv", index=False)

    # 図1：1社の割合ごと
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.7))
    x = np.arange(len(by_share)); lab = [f"{int(s*100)}%" for s in by_share.top_share]
    for ax, col, c, fmt, tt in [(axes[0], "year_any_below50_pct", BLUE, "{:.1f}%", "1年のうちに平均の5割を下回る\n月がある人の割合"),
                                (axes[1], "cv_median", LIGHT, "{:.2f}", "1年の振れ\n（標準偏差÷平均、中央値）")]:
        bb = ax.bar(x, by_share[col], 0.6, color=c)
        for r in bb:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() * 1.02, fmt.format(r.get_height()), ha="center", fontsize=8.5)
        ax.set_xticks(x, lab); ax.set_title(tt, fontsize=10.5); ax.set_ylim(0, by_share[col].max() * 1.22)
        ax.set_xlabel("いちばん大きい取引先の割合")
    fig.suptitle("1社に頼るほど大きく落ちる月は増えるが、標準偏差ではあまり差が出ない", fontsize=12, y=1.03)
    fig.text(0.01, -0.07, "ほかの取引先は4社で等分（100%は1社だけ）。各2万人", fontsize=8, color=GRAY)
    save(fig, "a888_by_share.png", SRC, y=-0.11)

    # 図2：24か月の例
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6), sharey=True)
    for ax, s, col in [(axes[0], 0.3, GREEN), (axes[1], 0.9, ORANGE)]:
        m = store[s]
        for p in range(6):
            ax.plot(np.arange(1, 25), m[p], color=col, lw=1, alpha=.75)
        ax.axhline(100, color=GRAY, lw=.8, ls=":"); ax.axhline(50, color=INK, lw=.8, ls="--")
        ax.set_title(f"1社の割合 {int(s*100)}%（6人分）", fontsize=11); ax.set_xlabel("月")
        ax.set_xticks([1, 6, 12, 18, 24])
    axes[0].set_ylabel("月の収入（指数。全社が続く月の平均＝100）", fontsize=9.5)
    axes[0].text(24.3, 51, "50", fontsize=8, va="bottom", ha="right")
    fig.suptitle("同じ平均でも、1社に頼ると止まった月に大きく落ちる", fontsize=12.5, y=1.02)
    save(fig, "a888_paths.png", SRC)

    # 図3：数で数えるか、割合で数えるか（24か月でいちばん低い月）
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6), sharey=True)
    jit = np.random.default_rng(SEED + 5).uniform(-0.25, 0.25, n2)
    axes[0].scatter(cnt.n_clients + jit, cnt.min24, s=4, color=GRAY, alpha=.4, lw=0)
    axes[0].set_xlabel("取引先の数"); axes[0].set_ylabel("24か月でいちばん低い月（指数）")
    axes[0].set_title(f"数で数える（順位相関 {count_vs_share['spearman_min_vs_n_clients']:.2f}）", fontsize=10.5)
    axes[1].scatter(cnt.effective_n, cnt.min24, s=4, color=BLUE, alpha=.4, lw=0)
    axes[1].set_xlabel("割合で数えた実質の社数（1÷割合の2乗の和）")
    axes[1].set_title(f"割合で数える（順位相関 {count_vs_share['spearman_min_vs_effective_n']:.2f}）", fontsize=10.5)
    fig.suptitle("いちばん低い月は、取引先の数より割合の偏りに少しよく沿う（5,000人）", fontsize=12.5, y=1.02)
    save(fig, "a888_count_vs_share.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
