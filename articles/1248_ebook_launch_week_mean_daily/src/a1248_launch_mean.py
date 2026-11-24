"""1248 発売した週の山を含めて平均すると、ふだんの1日の売れ方はどう見えるのか？（架空のデータ）

架空の電子書籍のシリーズ。本ごとに「ふだんの1日の売れ方」（発売の山が終わったあとの1日の冊数の平均）を置き、
発売の日から、ふだんの売れ方の S 倍の上乗せが、1日ごとに 1/e^(1/τ) ずつ減っていく山を足す。
1日の冊数は、その日の売れ方を平均にして、でたらめに数を引く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1248
SRC = "架空の電子書籍のシリーズ（作成者が乱数で作成、seed 1248）"
S0, TAU0 = 8.0, 3.0          # 発売の日の上乗せ（ふだんの8倍）、山の減り方（3日で 1/e）
LAM_EX = 2.0                 # 例の本のふだんの1日の売れ方
DAYS = [14, 30, 60, 90, 180, 365]
EXCL = 7                     # 最初の7日（発売の週）を除く
N_BOOK, MAX_AGE = 40, 720    # 本の数、いちばん古い本の発売からの日数


def rate(lam, n_days, S, tau):
    t = np.arange(n_days)
    return lam * (1 + S * np.exp(-t / tau))


def measures(x):
    """x: (回, 日) の1日の冊数。4つの読み方"""
    D = x.shape[1]
    m_all = x.mean(1)
    m_ex = x[:, EXCL:].mean(1) if D > EXCL else m_all
    med = np.median(x, 1)
    last = x[:, -30:].mean(1)
    return m_all, m_ex, med, last


def formula_all(S, tau, D):
    t = np.arange(D)
    return 1 + S * np.exp(-t / tau).sum() / D


def formula_ex(S, tau, D):
    t = np.arange(EXCL, D)
    return 1 + S * np.exp(-t / tau).sum() / (D - EXCL)


def days_within(S, tau, tol=0.1, excl=False):
    f = formula_ex if excl else formula_all
    for D in range(EXCL + 1 if excl else 1, 20000):
        if f(S, tau, D) - 1 <= tol:
            return D
    return None


def catalog(rng, S, tau, n=N_BOOK):
    lam = np.exp(np.log(1.5) + 0.6 * rng.standard_normal(n))
    age = rng.integers(1, MAX_AGE + 1, n)
    out = {k: np.zeros(n) for k in ["all", "ex7", "median", "last30"]}
    for i in range(n):
        x = rng.poisson(rate(lam[i], age[i], S, tau))[None, :]
        a, e, md, l = measures(x)
        out["all"][i], out["ex7"][i], out["median"][i], out["last30"][i] = a[0], e[0], md[0], l[0]
    return lam, age, out


def top_hits(lam, score, age, k=10, rng=None):
    # 同点は乱数で順を決める（中央値は整数なので同点が多い）
    jitter = rng.random(len(score)) * 1e-9
    top_true = set(np.argsort(-lam)[:k])
    top = np.argsort(-(score + jitter))[:k]
    return len(top_true & set(top)), int((age[top] <= 60).sum())


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 例の本（ふだん2冊/日）：発売から D 日の4つの読み方（4,000回）
    rows = []
    for D in DAYS:
        x = rng.poisson(rate(LAM_EX, D, S0, TAU0), size=(4000, D))
        a, e, md, l = measures(x)
        for name, v, f in [("発売からの平均", a, formula_all(S0, TAU0, D)),
                           ("最初の7日を除いた平均", e, formula_ex(S0, TAU0, D)),
                           ("1日の中央値", md, None),
                           ("直近30日の平均", l, None)]:
            r = v / LAM_EX
            rows.append({"days": D, "measure": name, "ratio_mean": round(float(r.mean()), 3),
                         "ratio_p10": round(float(np.quantile(r, .1)), 3),
                         "ratio_p90": round(float(np.quantile(r, .9)), 3),
                         "formula": None if f is None else round(float(f), 3)})
    by_days = pd.DataFrame(rows)
    by_days.to_csv(RES / "by_days.csv", index=False)

    # 例の1冊（365日）と、発売の週の割合
    x1 = rng.poisson(rate(LAM_EX, 365, S0, TAU0))
    pd.DataFrame({"day": np.arange(1, 366), "sold": x1}).to_csv(DATA / "daily_example.csv", index=False)
    ex_rate = rate(LAM_EX, 365, S0, TAU0)
    share_week = {str(D): round(float(ex_rate[:EXCL].sum() / ex_rate[:D].sum()), 4) for D in [30, 90, 365]}
    one_book = {"day1_rate_ratio": 1 + S0, "launch_extra_total_over_lam": round(float(S0 * np.exp(-np.arange(365) / TAU0).sum()), 3),
                "launch_week_share_of_sales": share_week,
                "example_mean_90": round(float(x1[:90].mean()), 3), "example_ex7_90": round(float(x1[EXCL:90].mean()), 3),
                "example_median_90": float(np.median(x1[:90])),
                "days_to_within_10pct_all": days_within(S0, TAU0), "days_to_within_10pct_ex7": days_within(S0, TAU0, excl=True),
                "days_to_within_25pct_all": days_within(S0, TAU0, 0.25)}

    # 2) ふだんの売れ方が少ない本で、1日の中央値（発売から180日）
    med_rows = []
    for lam in [0.3, 0.7, 1.0, 1.5, 3.0, 6.0]:
        x = rng.poisson(rate(lam, 180, S0, TAU0), size=(4000, 180))
        md = np.median(x, 1)
        med_rows.append({"lam": lam, "median_mean": round(float(md.mean()), 4), "median_ratio": round(float(md.mean() / lam), 4),
                         "share_median_0": round(float((md == 0).mean()), 4),
                         "mean_all_ratio": round(float(x.mean(1).mean() / lam), 4)})
    med_df = pd.DataFrame(med_rows)
    med_df.to_csv(RES / "median_low_sales.csv", index=False)

    # 3) 40冊の並び：発売の日がばらばらの本を、読み方ごとに上から10冊（2,000回）
    cat_rows = []
    for r in range(2000):
        g = np.random.default_rng(SEED * 1000 + r)
        lam, age, out = catalog(g, S0, TAU0)
        h_true, rec_true = top_hits(lam, lam, age, rng=g)
        rec = {"rep": r, "recent_in_true_top10": rec_true, "recent_books": int((age <= 60).sum())}
        for k, v in out.items():
            h, rc = top_hits(lam, v, age, rng=g)
            rec[f"hit_{k}"], rec[f"recent_{k}"] = h, rc
        cat_rows.append(rec)
        if r == 0:
            pd.DataFrame({"book": [f"B{i+1:02d}" for i in range(N_BOOK)], "days_since_launch": age,
                          "true_daily": np.round(lam, 4), "mean_all": np.round(out["all"], 4),
                          "mean_ex7": np.round(out["ex7"], 4), "median": out["median"],
                          "mean_last30": np.round(out["last30"], 4)}).to_csv(DATA / "catalog_example.csv", index=False)
    cat = pd.DataFrame(cat_rows)
    cat_sum = {"recent_books_mean": round(float(cat.recent_books.mean()), 3),
               "recent_in_true_top10": round(float(cat.recent_in_true_top10.mean()), 3)}
    for k in ["all", "ex7", "median", "last30"]:
        cat_sum[k] = {"hit10_mean": round(float(cat[f"hit_{k}"].mean()), 3),
                      "recent_in_top10": round(float(cat[f"recent_{k}"].mean()), 3)}
    pd.DataFrame([{"measure": k, **cat_sum[k]} for k in ["all", "ex7", "median", "last30"]]).to_csv(RES / "catalog_top10.csv", index=False)

    # 4) 確かめ：山の高さ S・減り方 τ・日数 D（27通り）と、並びの当たり（9通り）
    grid = []
    for S in [4.0, 8.0, 16.0]:
        for tau in [1.5, 3.0, 7.0]:
            gg = np.random.default_rng(SEED + int(S * 10) + int(tau * 100))
            hits = {"all": [], "ex7": [], "last30": []}
            rec_all = []
            for r in range(300):
                lam, age, out = catalog(gg, S, tau)
                for k in hits:
                    hits[k].append(top_hits(lam, out[k], age, rng=gg)[0])
                rec_all.append(top_hits(lam, out["all"], age, rng=gg)[1])
            for D in [30, 90, 365]:
                x = gg.poisson(rate(LAM_EX, D, S, tau), size=(2000, D))
                a, e, md, l = measures(x)
                grid.append({"S": S, "tau": tau, "days": D,
                             "all_ratio": round(float(a.mean() / LAM_EX), 4), "all_formula": round(float(formula_all(S, tau, D)), 4),
                             "ex7_ratio": round(float(e.mean() / LAM_EX), 4), "ex7_formula": round(float(formula_ex(S, tau, D)), 4),
                             "days_within_10pct_all": days_within(S, tau), "days_within_10pct_ex7": days_within(S, tau, excl=True),
                             "hit10_all": round(float(np.mean(hits["all"])), 3), "hit10_ex7": round(float(np.mean(hits["ex7"])), 3),
                             "hit10_last30": round(float(np.mean(hits["last30"])), 3),
                             "recent_in_top10_all": round(float(np.mean(rec_all)), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {"all_ratio_D90_range": [float(grid[grid.days == 90].all_ratio.min()), float(grid[grid.days == 90].all_ratio.max())],
              "ex7_ratio_D90_range": [float(grid[grid.days == 90].ex7_ratio.min()), float(grid[grid.days == 90].ex7_ratio.max())],
              "all_ratio_D365_range": [float(grid[grid.days == 365].all_ratio.min()), float(grid[grid.days == 365].all_ratio.max())],
              "days_within_10pct_all_range": [int(grid.days_within_10pct_all.min()), int(grid.days_within_10pct_all.max())],
              "days_within_10pct_ex7_range": [int(grid.days_within_10pct_ex7.min()), int(grid.days_within_10pct_ex7.max())],
              "max_abs_sim_minus_formula_all": round(float((grid.all_ratio - grid.all_formula).abs().max()), 4),
              "hit10_all_range": [float(grid.hit10_all.min()), float(grid.hit10_all.max())],
              "hit10_ex7_range": [float(grid.hit10_ex7.min()), float(grid.hit10_ex7.max())],
              "hit10_last30_range": [float(grid.hit10_last30.min()), float(grid.hit10_last30.max())],
              "combos_ex7_beats_all": int((grid.drop_duplicates(["S", "tau"]).hit10_ex7 > grid.drop_duplicates(["S", "tau"]).hit10_all).sum()),
              "recent_in_top10_all_range": [float(grid.recent_in_top10_all.min()), float(grid.recent_in_top10_all.max())]}

    out = {"setting": {"S": S0, "tau": TAU0, "lam_example": LAM_EX, "excl_days": EXCL, "n_book": N_BOOK, "max_age": MAX_AGE},
           "one_book": one_book, "by_days": by_days.to_dict("records"), "median_low_sales": med_df.to_dict("records"),
           "catalog_2000reps": cat_sum, "robust": robust}
    json.dump(out, open(RES / "a1248_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1冊の90日
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.bar(np.arange(1, 91), x1[:90], color=LIGHT, width=0.9)
    ax.axhline(LAM_EX, color=INK, lw=1.2); ax.text(91, LAM_EX - 0.1, f" ふだん {LAM_EX:g}冊", va="top", fontsize=9)
    m90 = x1[:90].mean()
    ax.axhline(m90, color=ORANGE, lw=1.2, ls="--"); ax.text(91, m90 + 0.1, f" 90日の平均 {m90:.3f}冊", va="bottom", fontsize=9, color=ORANGE)
    ax.set_xlabel("発売からの日（1日目＝発売の日）"); ax.set_ylabel("その日に売れた冊数"); ax.set_ylim(0, None)
    ax.set_title("例の1冊：発売の週の山があると、90日の平均はふだんより上に出る")
    save(fig, "a1248_example.png", SRC)

    # 図2：日数ごとの「ふだんの何倍に見えるか」
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ms = ["発売からの平均", "最初の7日を除いた平均", "直近30日の平均"]
    cols = [ORANGE, BLUE, GREEN]
    w = 0.26
    for j, (m, c) in enumerate(zip(ms, cols)):
        v = by_days[by_days.measure == m].ratio_mean.values
        ax.bar(np.arange(len(DAYS)) + (j - 1) * w, v, w, color=c, label=m)
        for i, vv in enumerate(v):
            ax.text(i + (j - 1) * w, vv + 0.04, f"{vv:.3f}", ha="center", va="bottom", fontsize=7, rotation=90)
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_xticks(range(len(DAYS))); ax.set_xticklabels([f"{d}日" for d in DAYS])
    ax.set_xlabel("発売から数えた日数"); ax.set_ylabel("ふだんの売れ方の何倍に見えるか\n（4,000回の平均）", linespacing=1.5)
    ax.set_ylim(0, 3.5); ax.legend(frameon=False, fontsize=9)
    ax.set_title("発売からの平均は、日数が短いほどふだんより大きく出る")
    save(fig, "a1248_by_days.png", SRC)

    # 図3：40冊の並び
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    names = {"all": "発売からの平均", "ex7": "最初の7日を除いた平均", "median": "1日の中央値", "last30": "直近30日の平均"}
    ks = ["all", "ex7", "median", "last30"]
    hv = [cat_sum[k]["hit10_mean"] for k in ks]
    ax.barh([names[k] for k in ks][::-1], hv[::-1], color=[ORANGE, BLUE, GRAY, GREEN][::-1])
    for i, (v, k) in enumerate(zip(hv[::-1], ks[::-1])):
        ax.text(v + 0.1, i, f"{v:g}冊（うち発売60日以内 {cat_sum[k]['recent_in_top10']:g}冊）", va="center", fontsize=8.5)
    ax.set_xlim(0, 10); ax.set_xlabel("上から10冊のうち、ふだんの売れ方の上位10冊に入っていた冊数（2,000回の平均）")
    ax.set_title(f"発売の日がばらばらの40冊を、読み方ごとに並べたとき（本当の上位10冊のうち発売60日以内は{cat_sum['recent_in_true_top10']:g}冊）", fontsize=11)
    save(fig, "a1248_catalog.png", SRC)
    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
