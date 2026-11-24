"""1267 見込みの良し悪しを、期の合計の外れで見るか、1件ずつの確度の当たりで見るかで、良い付け方は入れかわるのか？（架空のデータ）

架空の会社の法人向けの商談。商談ごとの本当の受注の確率と金額を作成者が置き、取れる・取れないを乱数で決める。
確度の付け方を5つ置き、(1) 期の見込みの合計（確度×金額の合計）と実績の外れ、(2) 1件ずつの確度と結果（1か0）の二乗の外れ、
(3) 金額で重みを付けた1件ずつの二乗の外れ、で良い順に並べて比べる。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1267
SRC = "架空の会社の法人向けの商談（作成者が置いた受注の確率・金額・確度の付け方からの乱数、seed 1267）"
PERIODS = 2000
SHORT = 8           # 2年分（8期）で比べたとき
BASE = dict(n=150, mu=-0.75, spread=1.2, amt_sd=1.0, noise=0.5, opt=0.7, big_share=0.2, stage_noise=0.7)
METHODS = ["本当の確率", "A 全件に同じ確度", "B 段階ごとの確度", "C 全体に強気", "D 見分けがよい（ぶれだけ）", "E 大きい商談だけ強気"]
SHORTNAME = ["本当", "A", "B", "C", "D", "E"]


def sig(x):
    return 1 / (1 + np.exp(-x))


def deals(p, n, rng):
    z = rng.standard_normal(n)
    lq = p["mu"] + p["spread"] * z
    q = sig(lq)
    amt = np.exp(np.log(100) + p["amt_sd"] * rng.standard_normal(n))   # 万円、中央値100万円
    stage_sig = z + p["stage_noise"] * rng.standard_normal(n)
    e = p["noise"] * rng.standard_normal(n)
    y = (rng.random(n) < q).astype(float)
    return dict(lq=lq, q=q, amt=amt, stage_sig=stage_sig, e=e, y=y)


def calibrate(p, rng):
    """過去の記録（20万件）から、全体の受注率・段階の切れ目・段階ごとの受注率・大きい商談の境目を作る"""
    d = deals(p, 200_000, rng)
    cuts = np.quantile(d["stage_sig"], [0.2, 0.4, 0.6, 0.8])
    st = np.searchsorted(cuts, d["stage_sig"])
    stage_rate = np.array([d["y"][st == k].mean() for k in range(5)])
    big_cut = float(np.quantile(d["amt"], 1 - p["big_share"]))
    return dict(overall=float(d["y"].mean()), cuts=cuts, stage_rate=stage_rate, big_cut=big_cut)


def assign(p, d, cal):
    st = np.searchsorted(cal["cuts"], d["stage_sig"])
    big = d["amt"] >= cal["big_cut"]
    return np.vstack([
        d["q"],
        np.full_like(d["q"], cal["overall"]),
        cal["stage_rate"][st],
        sig(d["lq"] + d["e"] + p["opt"]),
        sig(d["lq"] + d["e"]),
        sig(d["lq"] + d["e"] + p["opt"] * big),
    ]), st


def run(p, periods, rng, keep_example=False):
    cal = calibrate(p, rng)
    n = p["n"]
    d = deals(p, n * periods, rng)
    P, st = assign(p, d, cal)
    per = np.repeat(np.arange(periods), n)
    a, y = d["amt"], d["y"]
    actual = np.bincount(per, a * y, periods)
    fc = np.vstack([np.bincount(per, P[m] * a, periods) for m in range(len(METHODS))])
    rel = (fc - actual) / actual.mean()                            # 期ごとの外れ（実績の平均に対する割合）
    sq = (P - y) ** 2
    sq_p = np.vstack([np.bincount(per, sq[m], periods) / n for m in range(len(METHODS))])        # 期ごとの1件ずつの二乗の外れ
    sqw_p = np.vstack([np.bincount(per, sq[m] * a, periods) / np.bincount(per, a, periods) for m in range(len(METHODS))])
    out = dict(cal=cal, rel=rel, sq_p=sq_p, sqw_p=sqw_p, actual=actual)
    if keep_example:
        out["example"] = (d, P, st, per)
    return out


def summarize(r):
    rows = []
    for m, nm in enumerate(METHODS):
        rows.append(dict(method=nm, total_abs_err=np.abs(r["rel"][m]).mean() * 100,
                         total_bias=(r["rel"][m]).mean() * 100,
                         per_deal_sq=r["sq_p"][m].mean(), per_deal_sq_amt=r["sqw_p"][m].mean()))
    s = pd.DataFrame(rows)
    s["total_abs_err"] = s.total_abs_err.round(2)
    s["total_bias"] = s.total_bias.round(2)
    s["per_deal_sq"] = s.per_deal_sq.round(4)
    s["per_deal_sq_amt"] = s.per_deal_sq_amt.round(4)
    for col in ["total_abs_err", "per_deal_sq", "per_deal_sq_amt"]:
        s["rank_" + col] = s[s.method != METHODS[0]][col].rank(method="min")
    return s


def short_pick(r, k=SHORT):
    """k 期だけで比べたとき、どの付け方がいちばん良く見えるか（本当の確率は除く）"""
    nb = r["rel"].shape[1] // k
    res = {}
    for key, mat in [("total_abs_err", np.abs(r["rel"])), ("per_deal_sq", r["sq_p"]), ("per_deal_sq_amt", r["sqw_p"])]:
        blk = mat[1:, :nb * k].reshape(len(METHODS) - 1, nb, k).mean(2)
        best = blk.argmin(0)
        res[key] = {SHORTNAME[1 + m]: round(float((best == m).mean() * 100), 1) for m in range(len(METHODS) - 1)}
        # D が A より良く見えた割合
        res[key]["D_better_than_A"] = round(float((blk[3] < blk[0]).mean() * 100), 1)
    res["n_blocks"] = int(nb)
    return res


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    r = run(BASE, PERIODS, rng, keep_example=True)
    s = summarize(r)
    s.round(5).to_csv(RES / "methods_summary.csv", index=False)
    sp = short_pick(r)

    # 帯ごとの当たり（1件ずつ）
    d, P, st, per = r["example"]
    bins = np.linspace(0, 1, 11)
    cal_rows = []
    for m, nm in enumerate(METHODS):
        b = np.clip(np.digitize(P[m], bins) - 1, 0, 9)
        for k in range(10):
            msk = b == k
            if msk.sum() >= 30:
                cal_rows.append(dict(method=nm, band_low=bins[k], band_high=bins[k + 1], n=int(msk.sum()),
                                     mean_assigned=float(P[m][msk].mean()), won_share=float(d["y"][msk].mean()),
                                     won_share_pct=round(float(d["y"][msk].mean() * 100), 2)))
    calib = pd.DataFrame(cal_rows)
    calib.round(5).to_csv(RES / "calibration_bands.csv", index=False)

    # 期ごとの外れ（はじめの40期）
    pe = pd.DataFrame({"period": np.arange(1, 41), "actual": r["actual"][:40].round(2)})
    for m, nm in enumerate(SHORTNAME):
        pe[f"err_{nm}"] = (r["rel"][m][:40] * 100).round(3)
    pe.to_csv(RES / "period_errors_first40.csv", index=False)

    # 1期分の商談（例）
    msk = per == 0
    ex = pd.DataFrame({"deal_id": np.arange(1, msk.sum() + 1), "amount_man_yen": d["amt"][msk].round(1),
                       "true_prob": d["q"][msk].round(4), "stage": st[msk] + 1, "won": d["y"][msk].astype(int)})
    for m, nm in enumerate(SHORTNAME[1:], start=1):
        ex[f"p_{nm}"] = P[m][msk].round(4)
    ex.to_csv(DATA / "deals_period1.csv", index=False)

    # 確かめ：置き方を変える
    grid_rows = []
    for n, amt_sd, opt, noise in itertools.product([50, 150, 500], [0.5, 1.0, 1.5], [0.3, 0.7, 1.2], [0.3, 0.8]):
        p = {**BASE, "n": n, "amt_sd": amt_sd, "opt": opt, "noise": noise}
        rr = run(p, 400, rng)
        ss = summarize(rr)
        row = dict(n=n, amt_sd=amt_sd, opt=opt, noise=noise)
        for i, nm in enumerate(SHORTNAME):
            row[f"total_{nm}"] = round(float(ss.total_abs_err[i]), 3)
            row[f"sq_{nm}"] = round(float(ss.per_deal_sq[i]), 5)
            row[f"sqw_{nm}"] = round(float(ss.per_deal_sq_amt[i]), 5)
        o = ss[ss.method != METHODS[0]]
        row["best_total"] = SHORTNAME[1 + int(np.argmin(o.total_abs_err.values))]
        row["best_sq"] = SHORTNAME[1 + int(np.argmin(o.per_deal_sq.values))]
        row["best_sqw"] = SHORTNAME[1 + int(np.argmin(o.per_deal_sq_amt.values))]
        row["A_beats_C_total"] = bool(row["total_A"] < row["total_C"])
        row["A_beats_C_sq"] = bool(row["sq_A"] < row["sq_C"])
        row["A_beats_E_total"] = bool(row["total_A"] < row["total_E"])
        row["A_beats_E_sq"] = bool(row["sq_A"] < row["sq_E"])
        row["E_beats_C_sq"] = bool(row["sq_E"] < row["sq_C"])
        row["E_beats_C_total"] = bool(row["total_E"] < row["total_C"])
        grid_rows.append(row)
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False)

    flipAC = grid[grid.A_beats_C_total & ~grid.A_beats_C_sq]
    flipAE = grid[grid.A_beats_E_total & ~grid.A_beats_E_sq]
    robust = {
        "n_grid": int(len(grid)), "periods_per_setting": 400,
        "A_beats_C_total_n": int(grid.A_beats_C_total.sum()), "A_beats_C_sq_n": int(grid.A_beats_C_sq.sum()),
        "flip_A_C_n": int(len(flipAC)),
        "A_beats_E_total_n": int(grid.A_beats_E_total.sum()), "A_beats_E_sq_n": int(grid.A_beats_E_sq.sum()),
        "flip_A_E_n": int(len(flipAE)),
        "best_total_counts": grid.best_total.value_counts().to_dict(),
        "best_sq_counts": grid.best_sq.value_counts().to_dict(),
        "best_sqw_counts": grid.best_sqw.value_counts().to_dict(),
        "best_total_eq_best_sq_n": int((grid.best_total == grid.best_sq).sum()),
        "flip_A_C_by_opt": {str(o): int((flipAC.opt == o).sum()) for o in [0.3, 0.7, 1.2]},
        "flip_A_E_by_amt_sd": {str(a): int((flipAE.amt_sd == a).sum()) for a in [0.5, 1.0, 1.5]},
        "flip_A_E_by_opt": {str(o): int((flipAE.opt == o).sum()) for o in [0.3, 0.7, 1.2]},
        "flip_A_C_by_n": {str(o): int((flipAC.n == o).sum()) for o in [50, 150, 500]},
        "total_A_range": [float(grid.total_A.min()), float(grid.total_A.max())],
        "total_D_range": [float(grid.total_D.min()), float(grid.total_D.max())],
        "total_true_range": [float(grid["total_本当"].min()), float(grid["total_本当"].max())],
    }
    headline = {"methods": s.round(5).to_dict(orient="records"), "short8": sp,
                "calibration_overall": round(r["cal"]["overall"], 4),
                "gap_total_A_vs_true_pt": round(float(s.total_abs_err[1] - s.total_abs_err[0]), 2),
                "stage_rate": [round(float(v), 4) for v in r["cal"]["stage_rate"]],
                "calibration_overall_pct": round(r["cal"]["overall"] * 100, 2),
                "stage_rate_pct": [round(float(v) * 100, 2) for v in r["cal"]["stage_rate"]],
                "big_cut_man_yen": round(r["cal"]["big_cut"], 1),
                "big_deal_share_count": round(float((d["amt"] >= r["cal"]["big_cut"]).mean() * 100), 2),
                "big_deal_share_amount": round(float(d["amt"][d["amt"] >= r["cal"]["big_cut"]].sum() / d["amt"].sum() * 100), 2),
                "mean_actual_per_period_man_yen": round(float(r["actual"].mean()), 1)}
    run_sec = round(time.time() - t0, 1)
    json.dump({"base": BASE, "periods": PERIODS, "headline": headline, "robust": robust},
              open(RES / "a1267_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：3つの物差しでの並び
    cols = [GRAY, ORANGE, LIGHT, GREEN, BLUE, INK]
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.4))
    for a, col, ttl, fmt in [(ax[0], "total_abs_err", "期の合計の外れ（%、実績の平均に対する）", "{:.2f}"),
                             (ax[1], "per_deal_sq", "1件ずつの二乗の外れ", "{:.4f}"),
                             (ax[2], "per_deal_sq_amt", "金額で重みを付けた1件ずつの二乗の外れ", "{:.4f}")]:
        v = s[col].values
        yy = np.arange(len(METHODS))[::-1]
        a.barh(yy, v, color=cols)
        for yi, vi in zip(yy, v):
            a.text(vi, yi, " " + fmt.format(vi), va="center", fontsize=8.5)
        a.set_yticks(yy)
        a.set_yticklabels(METHODS if a is ax[0] else [""] * len(METHODS), fontsize=9)
        a.set_xlim(0, v.max() * 1.3)
        a.set_title(ttl, fontsize=10.5)
    fig.suptitle(f"小さいほど良い。1期{BASE['n']}件・{PERIODS:,}期の平均", fontsize=12, y=1.02)
    save(fig, "a1267_three_scores.png", SRC)

    # 図2：帯ごとの当たり
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.plot([0, 1], [0, 1], color=GRAY, ls=":", lw=1)
    for m, nm in enumerate(METHODS[1:], start=1):
        c = calib[calib.method == nm]
        ax.plot(c.mean_assigned * 100, c.won_share * 100, marker="o", ms=8 if len(c) == 1 else 4, lw=1.5, color=cols[m], label=nm)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("付けた確度（10%ごとの帯の平均、%）")
    ax.set_ylabel("その帯で実際に取れた割合（%）")
    ax.set_title("付けた確度と実際に取れた割合（30件以上の帯。A は1点）")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1267_bands.png", SRC)

    # 図3：8期だけで比べたとき、いちばん良く見えた付け方
    fig, ax = plt.subplots(figsize=(9, 4.2))
    keys = [("total_abs_err", "期の合計の外れ"), ("per_deal_sq", "1件ずつの二乗の外れ"), ("per_deal_sq_amt", "金額で重みを付けた\n1件ずつの二乗の外れ")]
    left = np.zeros(3)
    for m, nm in enumerate(SHORTNAME[1:]):
        v = np.array([sp[k][nm] for k, _ in keys])
        ax.barh(np.arange(3)[::-1], v, left=left, color=cols[m + 1], label=METHODS[m + 1])
        for yi, vi, li in zip(np.arange(3)[::-1], v, left):
            if vi >= 6:
                ax.text(li + vi / 2, yi, f"{vi:.1f}", ha="center", va="center", fontsize=8.5,
                        color="white" if m in (0, 3, 4) else INK)
        left += v
    ax.set_yticks(np.arange(3)[::-1])
    ax.set_yticklabels([k[1] for k in keys], fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel(f"いちばん良く見えた割合（%、8期ずつ{sp['n_blocks']}組）")
    ax.set_title("2年分（8期）だけで比べると、どの付け方がいちばん良く見えるか")
    ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    save(fig, "a1267_short8.png", SRC, y=-0.2)

    print(s.round(4).to_string())
    print(json.dumps(sp, ensure_ascii=False, indent=1))
    print(json.dumps(robust, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in headline.items() if k not in ("methods", "short8")}, ensure_ascii=False))
    print("run_sec", run_sec)


if __name__ == "__main__":
    main()
