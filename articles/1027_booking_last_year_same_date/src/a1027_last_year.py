"""1027 前年の同じ日の予約と比べると、何を読み違えるのか？（架空のデータ）

架空の飲食店（予約制、夜1回の営業）。1年目（前年）と2年目（今年）の毎日の予約の組数を作る。
1日の予約の平均は、基本40組×曜日の重み×休日の重み（1.5倍）×今年の伸び（1＋g）。日ごとの振れ（ガンマ分布）と
ポアソン分布の振れを足す。休日は「日付の決まった休日」と「曜日で決まる休日（第2月曜など）」を置いた。
1件の予約は、その日の何日前に入るかを幾何分布（平均 m 日）で置き、L 日前の時点で入っている予約を数える。
今年の日ごとの予約を、3つの比べ方で前年と比べ、置いた伸び g からのずれを数える。
  ① 同じ日付の前年の「最終の予約」と、今年の L 日前の予約
  ② 同じ日付の前年の、同じ L 日前の予約
  ③ 同じ曜日の日（364日前）の、同じ L 日前の予約
取り消しは入れない（1018・1020・1021 で扱う）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1027
SRC = "架空の飲食店の予約（作成者が乱数で作成、seed 1027）"
R = 400                      # 2年分を作り直す回数
BASE_MU = 40.0
WD = {"基本": [0.8, 0.8, 0.9, 1.0, 1.4, 1.6, 1.1],
      "曜日の差が小さい": [0.9, 0.9, 0.95, 1.0, 1.15, 1.25, 1.05],
      "曜日の差が大きい": [0.6, 0.6, 0.75, 0.9, 1.6, 2.0, 1.15]}
WD_NAME = ["月", "火", "水", "木", "金", "土", "日"]
HOL_FACTOR = 1.5
DAY_CV = 0.10
MONTH_LEN = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
FIXED_HOL = [0, 1, 2, 41, 79, 118, 122, 123, 124, 223, 224, 265, 307, 326]   # 日付の決まった休日（年の何日目か）
MOVING = [(0, 2), (6, 3), (8, 3), (9, 2)]   # (何月, 第何月曜)：曜日で決まる休日


def calendar(start_wd, ndays=365):
    """年の初日の曜日 start_wd（0=月）から、曜日と休日の印を作る"""
    wd = (start_wd + np.arange(ndays)) % 7
    hol = np.zeros(ndays, bool)
    hol[[d for d in FIXED_HOL if d < ndays]] = True
    mstart = np.cumsum([0] + MONTH_LEN)[:-1]
    for m, k in MOVING:
        days = [d for d in range(mstart[m], mstart[m] + MONTH_LEN[m]) if wd[d] == 0]
        hol[days[k - 1]] = True
    return wd, hol


def make_two_years(rng, g, wdw, offset_days=365, base=None, cv=None):
    """前年（365日、月曜始まり）と今年の毎日の最終の予約。offset_days=366 は間にうるう日をはさむ場合"""
    wd1, h1 = calendar(0)
    wd2, h2 = calendar(offset_days % 7)
    w = np.array(wdw)
    base = BASE_MU if base is None else base
    cv = DAY_CV if cv is None else cv
    mu1 = base * w[wd1] * np.where(h1, HOL_FACTOR, 1.0)
    mu2 = base * w[wd2] * np.where(h2, HOL_FACTOR, 1.0) * (1 + g)
    k = 1 / cv ** 2
    n1 = rng.poisson(mu1 * rng.gamma(k, 1 / k, (R, 365)))
    n2 = rng.poisson(mu2 * rng.gamma(k, 1 / k, (R, 365)))
    return n1, n2, (wd1, h1, mu1), (wd2, h2, mu2)


def on_books(rng, n, L, m):
    """最終の予約 n のうち、L 日前の時点で入っている数（何日前に入るかは平均 m 日の幾何分布）"""
    if L == 0:
        return n
    share = (m / (m + 1)) ** L
    return rng.binomial(n, share)


def compare(rng, g, wdw, m, L, offset_days=365, base=None, cv=None):
    n1, n2, c1, c2 = make_two_years(rng, g, wdw, offset_days, base, cv)
    x2 = on_books(rng, n2, L, m)
    x1 = on_books(rng, n1, L, m)
    # 今年の d 日目と同じ日付の前年：前年の d 日目。同じ曜日の日（364日前）：前年の d+1 日目（offset 365 のとき）
    shift = offset_days - 364   # 1 or 2
    D = np.arange(0, 365 - shift)  # 前年の d+shift 日目がある日
    out = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        out["①同じ日付・前年の最終"] = x2[:, D] / n1[:, D] - 1
        out["②同じ日付・同じ日数前"] = x2[:, D] / x1[:, D] - 1
        out["③同じ曜日・同じ日数前"] = x2[:, D] / x1[:, D + shift] - 1
    mon = np.repeat(np.arange(12), MONTH_LEN)[D]
    wk = D // 7
    pairs = {"①同じ日付・前年の最終": (x2[:, D], n1[:, D]), "②同じ日付・同じ日数前": (x2[:, D], x1[:, D]),
             "③同じ曜日・同じ日数前": (x2[:, D], x1[:, D + shift])}
    month, week = {}, {}
    for k_, (a, b) in pairs.items():
        sa = np.stack([a[:, mon == i].sum(1) for i in range(12)], 1)
        sb = np.stack([b[:, mon == i].sum(1) for i in range(12)], 1)
        month[k_] = sa / sb - 1
        nw = int((D[-1] + 1) // 7)
        sa = np.stack([a[:, wk == i].sum(1) for i in range(nw)], 1)
        sb = np.stack([b[:, wk == i].sum(1) for i in range(nw)], 1)
        week[k_] = sa / sb - 1
    hol_diff = c2[1][D] != c1[1][D + shift]
    return out, month, week, pairs, D, c1, c2, hol_diff, (n1, n2, x1, x2)


def stats(v, g, pair=None):
    """pair=(今年, 前年) を渡すと、合計どうしの比（ratio_of_sums）も出す。前年が0の日は比から除く"""
    n0 = int((~np.isfinite(v)).sum())
    v = v[np.isfinite(v)]
    r = {}
    if pair is not None:
        r["ratio_of_sums"] = round(float(pair[0].sum() / pair[1].sum() - 1) * 100, 2)
    return {**r, "zero_denominator": n0, "median": round(float(np.median(v)) * 100, 2),
            "p10": round(float(np.quantile(v, .1)) * 100, 2), "p90": round(float(np.quantile(v, .9)) * 100, 2),
            "share_negative": round(float((v < 0).mean()) * 100, 2),
            "share_off_20pt": round(float((np.abs(v - g) > 0.20).mean()) * 100, 2)}


def main():
    t0 = time.time()
    g, m = 0.05, 10
    wdw = WD["基本"]
    res = {"setting": {"base_mu": BASE_MU, "weekday_weights": dict(zip(WD_NAME, wdw)), "holiday_factor": HOL_FACTOR,
                       "day_cv": DAY_CV, "growth": g, "lead_mean_days": m, "reps": R,
                       "fixed_holidays": len(FIXED_HOL), "moving_holidays": len(MOVING)}}
    res["share_on_books_formula"] = {str(L): round((m / (m + 1)) ** L * 100, 2) for L in [0, 7, 14]}
    res["method1_formula"] = {str(L): round(((1 + g) * (m / (m + 1)) ** L - 1) * 100, 2) for L in [0, 7, 14]}
    rows, prow = [], []
    for i, L in enumerate([0, 7, 14]):
        out, month, week, pairs, D, c1, c2, hol_diff, raw = compare(np.random.default_rng(SEED * 10 + i), g, wdw, m, L)
        for k, v in out.items():
            if L == 0 and k.startswith("①"):
                continue
            s = stats(v, g, pairs[k])
            rows.append({"lead_L": L, "method": k, **s,
                         **{f"week_{a}": b for a, b in stats(week[k], g).items() if a != "zero_denominator"},
                         **{f"month_{a}": b for a, b in stats(month[k], g).items() if a != "zero_denominator"}})
            if k.startswith("③"):
                hm = {}
                for nm, hd in [("all", hol_diff), ("this_year_only", hol_diff & c2[1][D]), ("last_year_only", hol_diff & ~c2[1][D])]:
                    s3 = stats(v[:, hd], g, (pairs[k][0][:, hd], pairs[k][1][:, hd]))
                    hm[nm] = {"days": int(hd.sum()), "ratio_of_sums": s3["ratio_of_sums"],
                              "share_negative": s3["share_negative"], "share_off_20pt": s3["share_off_20pt"]}
                hm["formula_this_year_only"] = round(((1 + g) * HOL_FACTOR - 1) * 100, 2)
                hm["formula_last_year_only"] = round(((1 + g) / HOL_FACTOR - 1) * 100, 2)
                res[f"method3_L{L}_holiday_mismatch"] = hm
        if L == 7:
            o7, D7, c1_7, c2_7, raw7 = out, D, c1, c2, raw
            wd2 = c2[0][D]
            plain = (~c2[1][D]) & (~c1[1][D]) & (~c1[1][D + 1])
            byw = []
            for w in range(7):
                sel = (wd2 == w) & plain
                f2 = wdw[w]; f1 = wdw[(w - 1) % 7]
                r2 = stats(out["②同じ日付・同じ日数前"][:, sel], g, tuple(a[:, sel] for a in pairs["②同じ日付・同じ日数前"]))
                r3 = stats(out["③同じ曜日・同じ日数前"][:, sel], g, tuple(a[:, sel] for a in pairs["③同じ曜日・同じ日数前"]))
                byw.append({"weekday_this_year": WD_NAME[w], "weekday_last_year_same_date": WD_NAME[(w - 1) % 7], "days": int(sel.sum()),
                            "method2_ratio_of_sums": r2["ratio_of_sums"], "method2_formula": round(((1 + g) * f2 / f1 - 1) * 100, 2),
                            "method3_ratio_of_sums": r3["ratio_of_sums"], "method3_formula": round(g * 100, 2),
                            "method2_share_negative": r2["share_negative"], "method3_share_negative": r3["share_negative"]})
            bw = pd.DataFrame(byw)
            bw.to_csv(RES / "by_weekday_L7.csv", index=False)
            res["by_weekday_L7"] = bw.set_index("weekday_this_year").to_dict(orient="index")
            res["by_weekday_L7_max_abs_sim_minus_formula_pt"] = round(float(max((bw.method2_ratio_of_sums - bw.method2_formula).abs().max(),
                                                                               (bw.method3_ratio_of_sums - bw.method3_formula).abs().max())), 2)
    tab = pd.DataFrame(rows); tab.to_csv(RES / "by_method.csv", index=False)
    res["by_method"] = {f"L{r['lead_L']}_{r['method']}": {k: v for k, v in r.items() if k not in ("lead_L", "method")} for r in rows}

    # うるう日をはさむとき（同じ日付は曜日が2日ずれる）、L=7
    out366, month366, week366, pairs366, *_ = compare(np.random.default_rng(SEED * 10 + 9), g, wdw, m, 7, offset_days=366)
    res["leap_L7"] = {k: {**stats(v, g, pairs366[k]), "week_share_off_20pt": stats(week366[k], g)["share_off_20pt"],
                          "month_share_off_20pt": stats(month366[k], g)["share_off_20pt"]} for k, v in out366.items()}

    # 1回分のデータ（基本、L=7、1回目の2年分）
    n1, n2, x1, x2 = raw7
    one = pd.DataFrame({"day_this_year": D7 + 1, "weekday_this_year": [WD_NAME[w] for w in c2_7[0][D7]],
                        "holiday_this_year": c2_7[1][D7].astype(int),
                        "weekday_last_year_same_date": [WD_NAME[w] for w in c1_7[0][D7]],
                        "holiday_last_year_same_date": c1_7[1][D7].astype(int),
                        "holiday_last_year_same_weekday": c1_7[1][D7 + 1].astype(int),
                        "final_this_year": n2[0, D7], "on_books_L7_this_year": x2[0, D7],
                        "final_last_year_same_date": n1[0, D7], "on_books_L7_last_year_same_date": x1[0, D7],
                        "on_books_L7_last_year_same_weekday": x1[0, D7 + 1]})
    one.to_csv(DATA / "days_one_run_L7.csv", index=False)

    # 確かめ：伸び×曜日の差×何日前に入るか×うるう日×何日前の時点（108通り）
    grid = []
    j = 0
    for gg in [-0.05, 0.05, 0.15]:
        for wn, ww in WD.items():
            for mm in [5, 10, 20]:
                for off in [365, 366]:
                    for L in [7, 14]:
                        out, month, week, pairs, D, c1, c2, hol_diff, _ = compare(np.random.default_rng(SEED * 1000 + j), gg, ww, mm, L, off); j += 1
                        row = {"growth": gg, "weekday": wn, "lead_mean": mm, "offset": off, "lead_L": L}
                        wd2 = c2[0][D]
                        for k, v in out.items():
                            st = stats(v, gg, pairs[k]); tag = k[0]
                            row[f"{tag}_ratio_of_sums"] = st["ratio_of_sums"]
                            row[f"{tag}_share_negative"] = st["share_negative"]; row[f"{tag}_share_off_20pt"] = st["share_off_20pt"]
                            row[f"{tag}_week_share_off_20pt"] = stats(week[k], gg)["share_off_20pt"]
                            row[f"{tag}_month_share_off_20pt"] = stats(month[k], gg)["share_off_20pt"]
                            byw = [pairs[k][0][:, wd2 == w].sum() / pairs[k][1][:, wd2 == w].sum() - 1 for w in range(7)]
                            row[f"{tag}_weekday_min"] = round(float(min(byw)) * 100, 2); row[f"{tag}_weekday_max"] = round(float(max(byw)) * 100, 2)
                        row["①_formula"] = round(((1 + gg) * (mm / (mm + 1)) ** L - 1) * 100, 2)
                        grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    up = grid[grid.growth > 0]
    rng_ = lambda c, d=grid: [float(d[c].min()), float(d[c].max())]
    res["grid"] = {
        "n_cases": int(len(grid)),
        "method1_ratio_of_sums": rng_("①_ratio_of_sums"),
        "method1_max_abs_minus_formula_pt": round(float((grid["①_ratio_of_sums"] - grid["①_formula"]).abs().max()), 2),
        "method1_month_share_off_20pt": rng_("①_month_share_off_20pt"),
        "method2_weekday_min": rng_("②_weekday_min"), "method2_weekday_max": rng_("②_weekday_max"),
        "method3_weekday_min": rng_("③_weekday_min"), "method3_weekday_max": rng_("③_weekday_max"),
        "method2_weekday_minus_growth_pt": [round(float((grid["②_weekday_min"] - grid.growth * 100).min()), 2),
                                            round(float((grid["②_weekday_max"] - grid.growth * 100).max()), 2)],
        "method3_weekday_minus_growth_pt": [round(float((grid["③_weekday_min"] - grid.growth * 100).min()), 2),
                                            round(float((grid["③_weekday_max"] - grid.growth * 100).max()), 2)],
        "method2_share_off_20pt": rng_("②_share_off_20pt"), "method3_share_off_20pt": rng_("③_share_off_20pt"),
        "method2_minus_method3_share_off_20pt": [round(float((grid["②_share_off_20pt"] - grid["③_share_off_20pt"]).min()), 2),
                                                 round(float((grid["②_share_off_20pt"] - grid["③_share_off_20pt"]).max()), 2)],
        "growth_up_method2_share_negative": rng_("②_share_negative", up), "growth_up_method3_share_negative": rng_("③_share_negative", up),
        "method2_week_share_off_20pt": rng_("②_week_share_off_20pt"), "method3_week_share_off_20pt": rng_("③_week_share_off_20pt"),
        "method2_month_share_off_20pt": rng_("②_month_share_off_20pt"), "method3_month_share_off_20pt": rng_("③_month_share_off_20pt"),
        "ratio_of_sums_method2_minus_growth_pt": [round(float((grid["②_ratio_of_sums"] - grid.growth * 100).min()), 2),
                                                  round(float((grid["②_ratio_of_sums"] - grid.growth * 100).max()), 2)],
        "ratio_of_sums_method3_minus_growth_pt": [round(float((grid["③_ratio_of_sums"] - grid.growth * 100).min()), 2),
                                                  round(float((grid["③_ratio_of_sums"] - grid.growth * 100).max()), 2)],
    }
    # 確かめ：1日の予約の多さ×日ごとの振れ（9通り、③・L=7、伸び+5%）
    nz = []
    for i_, bn in enumerate([20, 40, 100]):
        for j_, cv in enumerate([0.05, 0.10, 0.20]):
            out, month, week, pairs, *_ = compare(np.random.default_rng(SEED * 50000 + i_ * 10 + j_), g, wdw, m, 7, 365, bn, cv)
            k3 = "③同じ曜日・同じ日数前"
            st = stats(out[k3], g, pairs[k3])
            nz.append({"base_groups": bn, "day_cv": cv, "share_negative": st["share_negative"], "share_off_20pt": st["share_off_20pt"],
                       "week_share_off_20pt": stats(week[k3], g)["share_off_20pt"], "month_share_off_20pt": stats(month[k3], g)["share_off_20pt"]})
    nz = pd.DataFrame(nz)
    nz.to_csv(RES / "sensitivity_noise_method3_L7.csv", index=False)
    res["noise_method3_L7"] = {c: [float(nz[c].min()), float(nz[c].max())] for c in ["share_negative", "share_off_20pt", "week_share_off_20pt", "month_share_off_20pt"]}
    with open(RES / "a1027_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：曜日ごとの②と③（L=7、休日でない日、合計どうしの比）
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = np.arange(7); w = 0.38
    ax.bar(x - w / 2, bw.method2_ratio_of_sums, w, color=ORANGE, label="②同じ日付（前年は1つ前の曜日）")
    ax.bar(x + w / 2, bw.method3_ratio_of_sums, w, color=BLUE, label="③同じ曜日の日（364日前）")
    for xi, a, b in zip(x, bw.method2_ratio_of_sums, bw.method3_ratio_of_sums):
        ax.text(xi - w / 2, a + (1.5 if a >= 0 else -4.5), f"{a:+.0f}", ha="center", fontsize=8)
        ax.text(xi + w / 2, b + (1.5 if b >= 0 else -4.5), f"{b:+.0f}", ha="center", fontsize=8)
    ax.axhline(0, color=INK, lw=.8); ax.axhline(g * 100, color=GRAY, lw=1, ls="--", label="置いた伸び +5%")
    ax.set_xticks(x); ax.set_xticklabels([f"今年の{a}\n（前年は{b}）" for a, b in zip(bw.weekday_this_year, bw.weekday_last_year_same_date)], fontsize=9)
    ax.set_ylabel("前年比（%、7日前の予約の合計どうし）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_ylim(min(bw.method2_ratio_of_sums.min(), 0) - 8, bw.method2_ratio_of_sums.max() + 10)
    ax.set_title("同じ日付で比べると、曜日のずれがそのまま前年比に出る（休日でない日）")
    save(fig, "a1027_weekday.png", SRC)

    # 図2：3つの比べ方の日ごとの前年比（L=7、ヒストグラム）
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    bins = np.linspace(-80, 120, 26)
    for (k, v), c in zip(o7.items(), [GRAY, ORANGE, BLUE]):
        vv = v[np.isfinite(v)] * 100
        ax.hist(np.clip(vv, -80, 120), bins=bins, color=c, alpha=.55, density=True,
                label=f"{k}（マイナスの日 {res['by_method']['L7_' + k]['share_negative']:.1f}%）")
    ax.axvline(g * 100, color=INK, lw=1, ls="--", label="置いた伸び +5%")
    ax.set_xlabel("今年の7日前の予約の、前年比（%、日ごと。−80〜120%の外は端に寄せた。8ポイント刻み）"); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("同じ+5%でも、何と比べるかで日ごとの前年比はここまで違う（7日前の時点）")
    save(fig, "a1027_daily.png", SRC)

    # 図3：日ごと・7日の合計・1か月の合計で、置いた伸びから20ポイント以上ずれた割合
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    labs = [(f"{r['lead_L']}日前" if r["lead_L"] else "最終") + "\n" + r["method"][:1] for r in rows]
    x = np.arange(len(rows)); w = 0.27
    for i, (col, lab, c) in enumerate([("share_off_20pt", "日ごと", ORANGE), ("week_share_off_20pt", "7日の合計", LIGHT),
                                       ("month_share_off_20pt", "1か月の合計", BLUE)]):
        v = [r[col] for r in rows]
        ax.bar(x + (i - 1) * w, v, w, color=c, label=lab)
        for xi, vi in zip(x, v):
            ax.text(xi + (i - 1) * w, vi + 1.5, f"{vi:.0f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9); ax.set_ylim(0, 112)
    ax.set_ylabel("置いた伸びから20ポイント以上ずれた割合（%）", fontsize=9.5)
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.17))
    ax.set_title("1か月の合計にすると②③はほとんどずれないが、①は合計でも外れる")
    save(fig, "a1027_offrate.png", SRC, y=-0.1)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
