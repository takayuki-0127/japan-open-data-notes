"""332 免責や支払いの上限で切られたデータから、元の損害の分布は戻せるか（架空のデータ、seed 332）"""
import json
import numpy as np, pandas as pd
from scipy import stats, optimize
from common import *

SEED, REPS = 332, 500
MU, SIG = np.log(30.0), 1.2          # 元の損害（万円）：対数正規、中央値30万円
LIMIT = 500.0                        # 支払いの上限（これを超えた損害は 500 と記録）
DEDS = [0, 5, 10, 20, 50, 100]       # 免責（これ以下の事故は記録されない）
N_GROUND = 2000                      # 起きた事故の数（記録に残るのはその一部）
TRUE_MEAN = float(np.exp(MU + SIG ** 2 / 2)); TRUE_Q99 = float(np.exp(MU + SIG * stats.norm.ppf(.99)))


def record(x, d, u=LIMIT):
    """記録に残る姿：d 以下は消え、u を超えたものは u になる"""
    x = x[x > d]
    return np.minimum(x, u), x >= u


def fit_naive(y):
    ly = np.log(y); return ly.mean(), ly.std()


def fit_proper(y, cens, d, u=LIMIT):
    """切断（免責）と打ち切り（上限）を尤度に入れた最尤法"""
    lo = np.log(y[~cens]); nc = cens.sum(); n = len(y); ld = np.log(d) if d > 0 else None; lu = np.log(u)
    def nll(p):
        mu, s = p[0], np.exp(p[1])
        ll = stats.norm.logpdf(lo, mu, s).sum() + nc * stats.norm.logsf(lu, mu, s)     # 記録された額の密度＋上限に当たった件数
        if ld is not None: ll -= n * stats.norm.logsf(ld, mu, s)                       # 「免責を超えた」という条件で割る
        return -ll
    m0, s0 = fit_naive(y)
    r = optimize.minimize(nll, [m0, np.log(s0)], method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 2000})
    return r.x[0], np.exp(r.x[1])


def one_setting(rng, d, n_ground=N_GROUND, limit=LIMIT):
    rows = []
    for _ in range(REPS):
        x = rng.lognormal(MU, SIG, n_ground)
        y, c = record(x, d, limit)
        for name, (m, s) in (("naive", fit_naive(y)), ("proper", fit_proper(y, c, d, limit))):
            rows.append(dict(method=name, n_rec=len(y), mu=m, sigma=s, mean=np.exp(m + s ** 2 / 2), q99=np.exp(m + s * stats.norm.ppf(.99)),
                             rec_mean=y.mean()))
    return pd.DataFrame(rows)


def summ(df):
    out = {}
    for m, g in df.groupby("method"):
        out[m] = dict(n_rec=float(g.n_rec.mean()),
                      mean_bias_pct=float(100 * (np.median(g["mean"]) / TRUE_MEAN - 1)), sigma_bias_pct=float(100 * (np.median(g.sigma) / SIG - 1)),
                      q99_bias_pct=float(100 * (np.median(g.q99) / TRUE_Q99 - 1)),
                      sigma_p10_pct=float(100 * (g.sigma.quantile(.1) / SIG - 1)), sigma_p90_pct=float(100 * (g.sigma.quantile(.9) / SIG - 1)),
                      mean_p10_pct=float(100 * (g["mean"].quantile(.1) / TRUE_MEAN - 1)), mean_p90_pct=float(100 * (g["mean"].quantile(.9) / TRUE_MEAN - 1)),
                      q99_p10_pct=float(100 * (g.q99.quantile(.1) / TRUE_Q99 - 1)), q99_p90_pct=float(100 * (g.q99.quantile(.9) / TRUE_Q99 - 1)),
                      mean_rmse_pct=float(100 * np.sqrt(((g["mean"] / TRUE_MEAN - 1) ** 2).mean())),
                      q99_rmse_pct=float(100 * np.sqrt(((g.q99 / TRUE_Q99 - 1) ** 2).mean())))
    return out


def main():
    rng = np.random.default_rng(SEED)
    res = dict(settings=dict(seed=SEED, reps=REPS, mu=MU, sigma=SIG, limit=LIMIT, n_ground=N_GROUND, true_mean=TRUE_MEAN, true_q99=TRUE_Q99,
                             share_above_limit=float(stats.norm.sf((np.log(LIMIT) - MU) / SIG))))
    main_tab = {}; rows = []
    for d in DEDS:
        s = summ(one_setting(rng, d)); s["share_below_ded"] = float(stats.norm.cdf((np.log(d) - MU) / SIG)) if d > 0 else 0.0
        main_tab[str(d)] = s
        for m in ("naive", "proper"):
            rows.append(dict(deductible=d, share_below_ded=s["share_below_ded"], method=m, **s[m]))
    res["by_deductible"] = main_tab
    # 切り方を分ける（免責20だけ／上限だけ／両方）
    parts = {}
    for name, d, lim in (("免責20だけ", 20, 1e12), ("上限500だけ", 0, LIMIT), ("両方", 20, LIMIT)):
        parts[name] = summ(one_setting(rng, d, limit=lim))
    res["parts"] = parts
    # 件数を減らす（免責20・50）
    small = {}
    for n in (300, 1000, 2000, 10000):
        for d in (20, 100):
            small[f"n{n}_d{d}"] = summ(one_setting(rng, d, n_ground=n))["proper"]
    res["proper_by_n"] = small
    # 上限を下げる（免責20）
    lim = {}
    for u in (200, 500, 2000):
        res_u = summ(one_setting(rng, 20, limit=u)); lim[str(u)] = dict(share_above=float(stats.norm.sf((np.log(u) - MU) / SIG)), **res_u)
    res["by_limit"] = lim
    pd.DataFrame(rows).round(4).to_csv(RES / "bias_by_deductible.csv", index=False)
    json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    x = np.random.default_rng(SEED).lognormal(MU, SIG, 2000); y, c = record(x, 20)
    pd.DataFrame({"recorded_man_yen": y.round(2), "hit_limit": c.astype(int)}).to_csv(DATA / "example_recorded_d20.csv", index=False)

    T = pd.DataFrame(rows)
    # 図1：免責ごとの偏り（平均・99%点）
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, key, ttl in zip(axes, ("mean", "sigma"), ("1事故の損害の平均", "損害の散らばり（対数正規の σ）")):
        for m, c_, lab in (("naive", ORANGE, "記録をそのまま当てはめ"), ("proper", BLUE, "切られ方を入れて当てはめ")):
            g = T[T.method == m]; x_ = np.arange(len(DEDS))
            ax.plot(x_, g[f"{key}_bias_pct"], "o-", color=c_, label=lab)
            ax.fill_between(x_, g[f"{key}_p10_pct"], g[f"{key}_p90_pct"], color=c_, alpha=.15, lw=0)
        ax.axhline(0, color=GRAY, lw=1); ax.set_xticks(range(len(DEDS))); ax.set_xticklabels([f"{d}万円\n({100*main_tab[str(d)]['share_below_ded']:.0f}%)" for d in DEDS], fontsize=8.5)
        ax.set_title(ttl, fontsize=11); ax.set_xlabel("免責（かっこは記録から消える事故の割合）")
    axes[0].set_ylabel("正解からのずれ（%）"); axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("記録をそのまま使うと、免責が高いほど平均は高く、散らばりは小さく出る", y=1.02)
    save(fig, "a332_bias_by_deductible.png", "架空のデータ（元の損害は対数正規、中央値30万円。上限500万円、起きた事故2,000件、500回。seed 332）。線は中央値、帯は10〜90%", y=-0.1)

    # 図2：1組の例（記録の分布と、当てはめた2本の線）
    fig, ax = plt.subplots(figsize=(8, 4.3))
    bins = np.exp(np.linspace(np.log(1), np.log(3000), 60)); xs = np.exp(np.linspace(np.log(1), np.log(3000), 400))
    ax.hist(x, bins=bins, color="#e3e2dc", label="起きた事故（2,000件、ふつうは見えない）")
    ax.hist(y, bins=bins, color=LIGHT, label=f"記録に残った事故（{len(y):,}件）")
    w = np.diff(np.log(bins))[0]
    mn, sn = fit_naive(y); mp, sp = fit_proper(y, c, 20)
    ax.plot(xs, len(y) * w * stats.norm.pdf(np.log(xs), mn, sn), color=ORANGE, lw=2, label="記録をそのまま当てはめ")
    ax.plot(xs, 2000 * w * stats.norm.pdf(np.log(xs), mp, sp) * len(y) / (2000 * stats.norm.sf((np.log(20) - mp) / sp) ) , color=BLUE, lw=2, label="切られ方を入れて当てはめ")
    ax.axvline(20, color=GRAY, ls=":"); ax.axvline(500, color=GRAY, ls=":"); ax.set_xscale("log")
    ax.set_xticks([1, 5, 20, 100, 500, 2000]); ax.set_xticklabels(["1", "5", "20\n（免責）", "100", "500\n（上限）", "2,000"])
    ax.set_xlabel("損害額（万円、対数の目盛り）"); ax.set_ylabel("件数"); ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("免責より下は消え、上限より上は500万円に積み上がる")
    save(fig, "a332_example.png", "架空のデータ1組（免責20万円、上限500万円）。青い線は、消えた部分も含めた元の分布を戻したもの", y=-0.08)

    # 図3：正しい方法の誤差の大きさ（件数と免責）
    fig, ax = plt.subplots(figsize=(7.6, 4.2)); ns = [300, 1000, 2000, 10000]
    for d, c_ in ((20, BLUE), (100, ORANGE)):
        ax.plot(range(len(ns)), [small[f"n{n}_d{d}"]["q99_rmse_pct"] for n in ns], "o-", color=c_, label=f"免責{d}万円・99%点")
        ax.plot(range(len(ns)), [small[f"n{n}_d{d}"]["mean_rmse_pct"] for n in ns], "o--", color=c_, alpha=.6, label=f"免責{d}万円・平均")
    ax.set_xticks(range(len(ns))); ax.set_xticklabels([f"{n:,}件" for n in ns]); ax.set_xlabel("起きた事故の数"); ax.set_ylabel("誤差の大きさ（RMSE、%）")
    ax.set_ylim(0); ax.legend(frameon=False, fontsize=9); ax.set_title("切られ方を入れれば偏りは消えるが、免責が高いと幅は広がる")
    save(fig, "a332_proper_rmse.png", "架空のデータ（切断と打ち切りを入れた最尤法、500回）。免責100万円では事故の84%が記録に残らない", y=-0.04)
    print(T[["deductible", "share_below_ded", "method", "n_rec", "mean_bias_pct", "sigma_bias_pct", "q99_bias_pct", "mean_rmse_pct", "q99_rmse_pct"]].round(2).to_string())
    print(json.dumps({k: {m: {kk: round(vv, 2) for kk, vv in v[m].items() if "bias" in kk} for m in v} for k, v in parts.items()}, ensure_ascii=False))
    print(json.dumps({k: {kk: round(vv, 2) for kk, vv in v.items() if "rmse" in kk or "bias" in kk} for k, v in small.items()}))
    print(json.dumps({k: {m: {kk: round(vv, 2) for kk, vv in v[m].items() if "bias" in kk} for m in ("naive", "proper")} | {"share_above": round(v["share_above"], 4)} for k, v in lim.items()}))
    print(res["settings"])


if __name__ == "__main__":
    main()
