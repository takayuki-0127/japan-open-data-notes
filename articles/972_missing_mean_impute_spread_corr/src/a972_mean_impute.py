"""972 空欄を平均で埋めると、ばらつきと相関はどうなるのか？（架空のデータ）

架空の店の会員アンケート1,000人。「月の来店回数」（全員が答えた）と「満足度（0〜100点）」の2問。
満足度の一部を空欄にし（でたらめに欠ける／来店の少ない人ほど空欄）、空欄の扱い方5つで、
満足度の平均・標準偏差・来店回数との相関・平均の95%の幅が本当の平均を含む割合を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 972
SRC = "架空の店の会員アンケート（作成者が乱数で作成、seed 972）"
N = 1000
RHO = 0.5           # 来店回数と満足度の元になる2つの数の相関（置いた値）
P_MISS = 0.30       # 満足度の空欄の割合
S_MAR = 1.0         # 来店の少ない人ほど空欄：空欄になりやすさ（ロジット）の、来店回数1標準偏差あたりの差
REPS = 2000
M_IMP = 20          # 多重代入の回数
METHODS = ["空欄を除く", "平均で埋める", "回帰で埋める", "回帰＋ばらつきで埋める", "多重代入（20回）"]
MECH = {"mcar": "でたらめに欠ける", "mar": "来店の少ない人ほど空欄"}


def make_members(rng, n=N, rho=RHO):
    z1, z2 = rng.standard_normal(n), rng.standard_normal(n)
    x = np.clip(np.round(8 + 3 * z1), 0, None)
    y = np.clip(np.round(65 + 15 * (rho * z1 + np.sqrt(1 - rho ** 2) * z2)), 0, 100)
    return x, y


def logit_shift(p, s, zs):
    """空欄の割合の平均が p になる切片（二分法）"""
    lo, hi = -20.0, 20.0
    for _ in range(80):
        a = (lo + hi) / 2
        if (1 / (1 + np.exp(-(a - s * zs)))).mean() < p:
            lo = a
        else:
            hi = a
    return a


def make_missing(rng, x, mech, p, a_cache):
    if mech == "mcar":
        return rng.random(len(x)) < p
    z = (x - 8) / 3
    a = a_cache[p]
    return rng.random(len(x)) < 1 / (1 + np.exp(-(a - S_MAR * z)))


def fit(x, y):
    b = np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)
    a = y.mean() - b * x.mean()
    r = y - a - b * x
    return a, b, np.sqrt((r ** 2).sum() / (len(x) - 2))


def summarize(x, y, ok=None):
    """満足度の平均・標準偏差・相関と、ふつうの式の95%の幅（人数は表の行数）"""
    if ok is not None:
        x, y = x[ok], y[ok]
    n = len(y)
    m, s = y.mean(), y.std(ddof=1)
    return m, s, np.corrcoef(x, y)[0, 1], 1.96 * s / np.sqrt(n)


def run_one(rng, mech, p, a_cache, rho=RHO, with_mi=True):
    x, y = make_members(rng, rho=rho)
    miss = make_missing(rng, x, mech, p, a_cache)
    obs = ~miss
    full = summarize(x, y)
    out = {}
    out["空欄を除く"] = summarize(x, y, obs)
    yi = y.copy(); yi[miss] = y[obs].mean()
    out["平均で埋める"] = summarize(x, yi)
    a, b, se = fit(x[obs], y[obs])
    yr = y.copy(); yr[miss] = a + b * x[miss]
    out["回帰で埋める"] = summarize(x, yr)
    ys = y.copy(); ys[miss] = a + b * x[miss] + rng.normal(0, se, miss.sum())
    out["回帰＋ばらつきで埋める"] = summarize(x, ys)
    if with_mi:
        xo, yo = x[obs], y[obs]
        ms, ws, ss, cs = [], [], [], []
        for _ in range(M_IMP):
            idx = rng.integers(0, len(xo), len(xo))     # 作り直した答えで回帰を当て直す（係数の不確かさを入れる）
            a2, b2, se2 = fit(xo[idx], yo[idx])
            yk = y.copy(); yk[miss] = a2 + b2 * x[miss] + rng.normal(0, se2, miss.sum())
            m_, s_, c_, _ = summarize(x, yk)
            ms.append(m_); ss.append(s_); cs.append(c_); ws.append(s_ ** 2 / N)
        qbar, ubar, bvar = np.mean(ms), np.mean(ws), np.var(ms, ddof=1)
        out["多重代入（20回）"] = (qbar, np.mean(ss), np.mean(cs), 1.96 * np.sqrt(ubar + (1 + 1 / M_IMP) * bvar))
    return full, out, (x, y, miss, yi, yr)


def main():
    rng = np.random.default_rng(SEED)
    zs = rng.standard_normal(2_000_000)
    ps = [0.1, 0.2, 0.3, 0.4, 0.5]
    a_cache = {p: logit_shift(p, S_MAR, zs) for p in ps}
    # 本当の値（同じ作り方で200万人）
    xb, yb = make_members(np.random.default_rng(SEED + 2), 2_000_000)
    TRUE_MEAN, TRUE_SD, TRUE_R = yb.mean(), yb.std(), np.corrcoef(xb, yb)[0, 1]
    _TRUE_BY_RHO[RHO] = TRUE_MEAN

    # 1) 基本の置き方（空欄30%、2つの欠け方、2,000回）
    rows = []
    example = None
    for mech in MECH:
        r2 = np.random.default_rng(SEED * 10 + (mech == "mar"))
        for rep in range(REPS):
            full, out, ex = run_one(r2, mech, P_MISS, a_cache)
            if mech == "mcar" and rep == 0:
                example = ex
            for meth, (m, s, c, h) in out.items():
                rows.append({"mech": MECH[mech], "method": meth, "mean": m, "sd": s, "r": c,
                             "sd_ratio": s / full[1], "r_ratio": c / full[2], "half_width": h,
                             "cover": float(abs(m - TRUE_MEAN) <= h), "full_sd": full[1], "full_r": full[2]})
    sim = pd.DataFrame(rows)
    g = sim.groupby(["mech", "method"], sort=False)
    summ = pd.DataFrame({"満足度の平均": g["mean"].mean(), "平均のずれ（点）": g["mean"].mean() - TRUE_MEAN,
                         "標準偏差": g["sd"].mean(), "標準偏差の比（欠ける前の同じ1,000人＝1）": g["sd_ratio"].mean(),
                         "相関": g["r"].mean(), "相関の比（欠ける前＝1）": g["r_ratio"].mean(),
                         "95%の幅の半分（点）": g["half_width"].mean(),
                         "95%の幅が本当の平均を含んだ割合": g["cover"].mean(),
                         "平均の振れ（標準偏差、点）": g["mean"].std()}).round(4)
    summ.to_csv(RES / "methods_p30.csv")
    full_sd_mean, full_r_mean = float(sim["full_sd"].mean()), float(sim["full_r"].mean())

    # 2) 確かめ：空欄の割合 × 相関の置き方 × 欠け方（30通り、各300回、多重代入なし）
    rob = []
    for mech in MECH:
        for rho in [0.2, 0.5, 0.8]:
            for p in ps:
                r3 = np.random.default_rng(SEED * 1000 + int(rho * 10) * 100 + int(p * 100) + (mech == "mar") * 7)
                acc = {k: [] for k in ["sdr", "rr", "cov", "bias"]}
                accd = {k: [] for k in ["cov", "rr", "sdr"]}
                accr = {k: [] for k in ["rr", "sdr"]}
                for rep in range(300):
                    full, out, _ = run_one(r3, mech, p, a_cache, rho=rho, with_mi=False)
                    m, s, c, h = out["平均で埋める"]
                    acc["sdr"].append(s / full[1]); acc["rr"].append(c / full[2])
                    acc["cov"].append(abs(m - TRUE_MEAN_BY_RHO(rho)) <= h); acc["bias"].append(m - full[0])
                    m2, s2, c2, h2 = out["空欄を除く"]
                    accd["cov"].append(abs(m2 - TRUE_MEAN_BY_RHO(rho)) <= h2); accd["rr"].append(c2 / full[2])
                    accd["sdr"].append(s2 / full[1])
                    m3, s3, c3, h3 = out["回帰で埋める"]
                    accr["rr"].append(c3 / full[2]); accr["sdr"].append(s3 / full[1])
                rob.append({"欠け方": MECH[mech], "置いた相関": rho, "空欄の割合": p,
                            "平均で埋める：標準偏差の比": round(np.mean(acc["sdr"]), 4),
                            "平均で埋める：相関の比": round(np.mean(acc["rr"]), 4),
                            "式の値 √(1−空欄の割合)": round(float(np.sqrt(1 - p)), 4),
                            "平均で埋める：95%の幅が本当の平均を含んだ割合": round(np.mean(acc["cov"]), 4),
                            "式の値（でたらめに欠けるとき）2Φ(1.96(1−空欄の割合))−1": round(cover_formula(p), 4),
                            "平均で埋める：平均のずれ（欠ける前の同じ人との差、点）": round(np.mean(acc["bias"]), 3),
                            "空欄を除く：標準偏差の比": round(np.mean(accd["sdr"]), 4),
                            "空欄を除く：相関の比": round(np.mean(accd["rr"]), 4),
                            "空欄を除く：95%の幅が本当の平均を含んだ割合": round(np.mean(accd["cov"]), 4),
                            "回帰で埋める：標準偏差の比": round(np.mean(accr["sdr"]), 4),
                            "回帰で埋める：相関の比": round(np.mean(accr["rr"]), 4)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    mc = rob[rob["欠け方"] == "でたらめに欠ける"]
    ma = rob[rob["欠け方"] == "来店の少ない人ほど空欄"]

    # 例の1回分（でたらめに欠ける・空欄30%）
    x, y, miss, yi, yr = example
    pd.DataFrame({"member_id": np.arange(1, N + 1), "visits_per_month": x.astype(int),
                  "satisfaction_true": y.astype(int),
                  "satisfaction_answered": np.where(miss, np.nan, y),
                  "missing": miss.astype(int), "filled_mean": np.round(yi, 2),
                  "filled_regression": np.round(yr, 2)}).to_csv(DATA / "members_example.csv", index=False)
    ex_mean_val = float(y[~miss].mean())
    same_val_share = float((yi == ex_mean_val).mean())
    band = float((np.abs(yi - ex_mean_val) <= 2.5).mean()); band_true = float((np.abs(y - ex_mean_val) <= 2.5).mean())

    mi = sim[sim.method == "多重代入（20回）"]
    out = {"true_population": {"mean": round(float(TRUE_MEAN), 3), "sd": round(float(TRUE_SD), 3),
                               "r": round(float(TRUE_R), 4), "note": "同じ作り方で200万人"},
           "base": {"n": N, "p_missing": P_MISS, "reps": REPS, "rho_set": RHO,
                    "full_data_sd_mean": round(full_sd_mean, 3), "full_data_r_mean": round(full_r_mean, 4),
                    "formula_sqrt_1_minus_p": round(float(np.sqrt(1 - P_MISS)), 4),
                    "formula_cover_mean_fill_mcar": round(cover_formula(P_MISS), 4),
                    "formula_sd_ratio_exact": round(float(np.sqrt((N * (1 - P_MISS) - 1) / (N - 1))), 4)},
           "methods_p30": summ.reset_index().to_dict("records"),
           "example_mcar_p30": {"n_missing": int(miss.sum()), "filled_value": round(ex_mean_val, 2),
                                "share_exactly_filled_value": round(same_val_share, 4),
                                "share_within_2_5_of_filled_value_after": round(band, 4),
                                "share_within_2_5_of_filled_value_before": round(band_true, 4)},
           "robustness_range": {
               "mean_fill_sd_ratio_min": float(rob["平均で埋める：標準偏差の比"].min()),
               "mean_fill_sd_ratio_max": float(rob["平均で埋める：標準偏差の比"].max()),
               "mean_fill_r_ratio_min": float(rob["平均で埋める：相関の比"].min()),
               "mean_fill_r_ratio_max": float(rob["平均で埋める：相関の比"].max()),
               "mean_fill_cover_min": float(rob["平均で埋める：95%の幅が本当の平均を含んだ割合"].min()),
               "mean_fill_cover_max": float(rob["平均で埋める：95%の幅が本当の平均を含んだ割合"].max()),
               "mcar_max_abs_diff_from_formula_sd": round(float((rob[rob["欠け方"] == "でたらめに欠ける"]["平均で埋める：標準偏差の比"]
                                                               - rob[rob["欠け方"] == "でたらめに欠ける"]["式の値 √(1−空欄の割合)"]).abs().max()), 4),
               "mcar_max_abs_diff_from_formula_r": round(float((rob[rob["欠け方"] == "でたらめに欠ける"]["平均で埋める：相関の比"]
                                                              - rob[rob["欠け方"] == "でたらめに欠ける"]["式の値 √(1−空欄の割合)"]).abs().max()), 4),
               "mcar_mean_fill_sd_ratio_min": float(mc["平均で埋める：標準偏差の比"].min()),
               "mcar_mean_fill_sd_ratio_max": float(mc["平均で埋める：標準偏差の比"].max()),
               "mcar_mean_fill_r_ratio_min": float(mc["平均で埋める：相関の比"].min()),
               "mcar_mean_fill_r_ratio_max": float(mc["平均で埋める：相関の比"].max()),
               "mcar_mean_fill_cover_min": float(mc["平均で埋める：95%の幅が本当の平均を含んだ割合"].min()),
               "mcar_mean_fill_cover_max": float(mc["平均で埋める：95%の幅が本当の平均を含んだ割合"].max()),
               "mcar_cc_cover_min": float(mc["空欄を除く：95%の幅が本当の平均を含んだ割合"].min()),
               "mcar_cc_cover_max": float(mc["空欄を除く：95%の幅が本当の平均を含んだ割合"].max()),
               "mar_mean_fill_r_ratio_min": float(ma["平均で埋める：相関の比"].min()),
               "mar_mean_fill_r_ratio_max": float(ma["平均で埋める：相関の比"].max()),
               "mar_mean_fill_cover_min": float(ma["平均で埋める：95%の幅が本当の平均を含んだ割合"].min()),
               "mar_mean_fill_cover_max": float(ma["平均で埋める：95%の幅が本当の平均を含んだ割合"].max()),
               "mar_mean_fill_bias_min": float(ma["平均で埋める：平均のずれ（欠ける前の同じ人との差、点）"].min()),
               "mar_mean_fill_bias_max": float(ma["平均で埋める：平均のずれ（欠ける前の同じ人との差、点）"].max()),
               "mar_cc_cover_min": float(ma["空欄を除く：95%の幅が本当の平均を含んだ割合"].min()),
               "mar_cc_cover_max": float(ma["空欄を除く：95%の幅が本当の平均を含んだ割合"].max()),
               "regression_fill_r_ratio_min": float(rob["回帰で埋める：相関の比"].min()),
               "regression_fill_r_ratio_max": float(rob["回帰で埋める：相関の比"].max())}}
    json.dump(out, open(RES / "a972_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1回分。満足度の分布と、来店回数との散らばり（平均で埋める／回帰で埋める）
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 3.9))
    bins = np.arange(-0.5, 101.5, 2)
    axs[0].hist(y, bins=bins, color=GRAY, alpha=.55, label="欠ける前（1,000人）")
    axs[0].hist(yi, bins=bins, color=ORANGE, alpha=.6, label="平均で埋めたあと")
    axs[0].set_xlabel("満足度（点）"); axs[0].set_ylabel("人数"); axs[0].legend(frameon=False, fontsize=8.5)
    axs[0].set_title("平均の1か所に山ができる", fontsize=11.5)
    jit = np.random.default_rng(SEED + 5).uniform(-0.3, 0.3, N)
    for ax, yy, ttl in [(axs[1], yi, "平均で埋める"), (axs[2], yr, "回帰で埋める")]:
        ax.scatter(x[~miss] + jit[~miss], y[~miss], s=6, color=BLUE, alpha=.35, lw=0, label="答えた人")
        ax.scatter(x[miss] + jit[miss], yy[miss], s=7, color=ORANGE, alpha=.8, lw=0, label="埋めた空欄")
        ax.set_xlabel("月の来店回数"); ax.set_ylabel("満足度（点）"); ax.set_ylim(0, 102)
        ax.set_title(f"{ttl}（相関 {np.corrcoef(x, yy)[0, 1]:.2f}）", fontsize=11.5)
        ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle(f"空欄30%（でたらめに欠ける）の例の1回分。欠ける前の相関は {np.corrcoef(x, y)[0, 1]:.2f}", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a972_example.png", SRC)

    # 図2：扱い方ごとの標準偏差の比・相関の比・95%の幅が本当の平均を含んだ割合
    s = summ.reset_index()
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.0), sharey=True)
    ylab = METHODS[::-1]
    yy = np.arange(len(ylab))
    cols = [("標準偏差の比（欠ける前の同じ1,000人＝1）", "標準偏差の比（欠ける前＝1）", 1.0),
            ("相関の比（欠ける前＝1）", "相関の比（欠ける前＝1）", 1.0),
            ("95%の幅が本当の平均を含んだ割合", "95%の幅が本当の平均を\n含んだ割合（2,000回）", 0.95)]
    for ax, (c, lab, ref) in zip(axs, cols):
        for k, (mech, colr) in enumerate([("でたらめに欠ける", BLUE), ("来店の少ない人ほど空欄", ORANGE)]):
            v = [float(s[(s.mech == mech) & (s.method == m)][c].iloc[0]) for m in ylab]
            ax.barh(yy + (0.2 if k == 0 else -0.2), v, height=0.38, color=colr, label=mech)
            for i, vv in enumerate(v):
                ax.text(vv + 0.015, yy[i] + (0.2 if k == 0 else -0.2), f"{vv:.2f}", va="center", fontsize=7.5, zorder=4, bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
        ax.axvline(ref, color=INK, lw=0.8, ls="--")
        ax.set_xlabel(lab, fontsize=9.5); ax.set_xlim(0, 1.35)
    axs[0].set_yticks(yy); axs[0].set_yticklabels(ylab)
    h, l = axs[0].get_legend_handles_labels()
    fig.suptitle("空欄30%：平均で埋めると標準偏差も相関も小さくなり、95%の幅は本当の平均を外しやすくなる", fontsize=12)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.legend(h, l, frameon=False, fontsize=9.5, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0))
    save(fig, "a972_methods.png", SRC)

    # 図3：空欄の割合ごとの、平均で埋めたときの標準偏差の比・相関の比（式の値と並べる）
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.0), sharey=True)
    for ax, mech in zip(axs, MECH.values()):
        d = rob[rob["欠け方"] == mech]
        pp = np.array(ps) * 100
        ax.plot(pp, np.sqrt(1 - np.array(ps)), color=INK, lw=1.2, ls="--", label="式の値 √(1−空欄の割合)")
        dd = d[d["置いた相関"] == 0.5]
        ax.plot(pp, dd["平均で埋める：標準偏差の比"], "o-", color=BLUE, label="標準偏差の比（相関0.5）")
        for rho, mk in [(0.2, "^"), (0.5, "s"), (0.8, "v")]:
            dd = d[d["置いた相関"] == rho]
            ax.plot(pp, dd["平均で埋める：相関の比"], marker=mk, color=ORANGE, lw=1, alpha=.85,
                    label=f"相関の比（置いた相関{rho}）")
        ax.set_xlabel("満足度の空欄の割合（%）"); ax.set_title(mech, fontsize=11.5); ax.set_ylim(0.55, 1.02)
    axs[0].set_ylabel("埋めたあと÷欠ける前（各300回の平均）")
    axs[1].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("平均で埋めると、でたらめに欠けるときは標準偏差も相関も √(1−空欄の割合) 倍に縮む（式どおり）", fontsize=12)
    fig.tight_layout()
    save(fig, "a972_robustness.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


_TRUE_BY_RHO = {}


def cover_formula(p):
    """でたらめに欠けるとき：平均で埋めると幅は (1−p) 倍に縮むので、含む割合は 2Φ(1.96(1−p))−1"""
    from math import erf, sqrt
    return 2 * (0.5 * (1 + erf(1.96 * (1 - p) / sqrt(2)))) - 1


def TRUE_MEAN_BY_RHO(rho):
    """置いた相関ごとの本当の満足度の平均（同じ作り方で200万人）"""
    if rho not in _TRUE_BY_RHO:
        _, yb = make_members(np.random.default_rng(SEED + 2), 2_000_000, rho)
        _TRUE_BY_RHO[rho] = yb.mean()
    return _TRUE_BY_RHO[rho]


if __name__ == "__main__":
    main()
