"""03 分析：欠測の埋め方で、6つの「知りたい値」がどれだけ変わるかを比べる。

母集団：SSDSE-A-2026 の 1,740 市区町村（値がそろっている）。真の値はこの母集団で計算する。
くり返しごとに、母集団から同じ数を復元抽出（標本のばらつきを入れるため）→ 3列を欠かす → 埋める → 推定。

  python 03_分析.py           # 本番（2コアで数十分）
  python 03_分析.py --quick   # 短縮版（回数を減らす）
"""
import json
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats

from common import (EST, HAS_SE, IDX, MISS, RES, SEED, available_case, ci_cover, estimates, fill_forest, fill_knn,
                    fill_mean, fill_regression, load, make_missing, mice, mice_strat, rubin)

QUICK = "--quick" in sys.argv
R_MAIN = 30 if QUICK else 250
R_SUB = 15 if QUICK else 120
R_FOREST = 6 if QUICK else 40
M = 10
POP = load()
N = len(POP)
TRUTH, _ = estimates(POP)
TRUTH_LEVEL, _ = estimates(POP, coef_model="level")


def run_methods(D, mech, rate, seed, methods, strength=1.5, mice_kw=None, coef_model="log"):
    rng = np.random.default_rng(seed)
    Dm = make_missing(D, mech, rate, rng, strength)
    rows = []
    truth = TRUTH if coef_model == "log" else TRUTH_LEVEL

    def add(name, q, se, df=np.inf, fmi=np.nan, extra=None):
        for k in EST:
            r = {"method": name, "est": k, "q": q[k], "truth": truth[k]}
            if k in se and np.isfinite(se[k]):
                cov, w = ci_cover(q[k], se[k], df[k] if isinstance(df, dict) else df, truth[k])
                r.update(se=se[k], cover=bool(cov), width=w, fmi=fmi[k] if isinstance(fmi, dict) else fmi)
            if extra:
                r.update(extra)
            rows.append(r)

    for name in methods:
        if name == "full":  # 欠かす前（比べる基準）
            q, se = estimates(D, coef_model)
            add(name, q, se)
        elif name == "avail":
            q, se = available_case(Dm, coef_model)
            add(name, q, se)
        elif name == "mean":
            q, se = estimates(fill_mean(Dm), coef_model)
            add(name, q, se)
        elif name == "reg":
            q, se = estimates(fill_regression(Dm, rng), coef_model)
            add(name, q, se)
        elif name == "knn":
            q, se = estimates(fill_knn(Dm), coef_model)
            add(name, q, se)
        elif name == "forest":
            q, se = estimates(fill_forest(Dm, seed % (2**31)), coef_model)
            add(name, q, se)
        elif name == "sreg":  # 正規分布から1回だけ引く（ばらつきは足すが、SEは1組のまま）
            D1 = mice(Dm, 1, rng, method="norm")[0]
            q, se = estimates(D1, coef_model)
            add(name, q, se)
        elif name.startswith("mi_"):
            kw = dict(mice_kw or {})
            meth = "pmm" if "pmm" in name else "norm"
            if "strata" in kw:
                Ds = mice_strat(Dm, kw.pop("m", M), rng, method=meth, **kw)
            else:
                Ds = mice(Dm, kw.pop("m", M), rng, method=meth, **kw)
            qs, ses = zip(*[estimates(x, coef_model) for x in Ds])
            rb = rubin(list(qs), list(ses))
            q = {k: rb[k][0] for k in EST}
            se = {k: rb[k][1] for k in HAS_SE}
            df = {k: rb[k][2] for k in HAS_SE}
            fmi = {k: rb[k][3] for k in HAS_SE}
            bad = np.nan
            if meth == "norm":
                Mk = np.isnan(Dm)
                bad = np.mean([((x[Mk[:, IDX["unemp"]], IDX["unemp"]] < 0).sum()
                                + (x[Mk[:, IDX["tert"]], IDX["tert"]] > 100).sum()) for x in Ds])
            add(name, q, se, df, fmi, extra={"impossible": bad})
    return rows


def job(args):
    tag, rep, mech, rate, methods, strength, mice_kw, coef_model, resample = args
    seed = _seed(tag, rep)
    rng = np.random.default_rng(seed)
    D = POP[rng.integers(0, N, N)] if resample else POP
    rows = run_methods(D, mech, rate, seed + 1, methods, strength, mice_kw, coef_model)
    for r in rows:
        r.update(tag=tag, rep=rep, mech=mech, rate=rate, strength=strength)
    return rows


def _seed(tag, rep):
    return int(np.random.SeedSequence([SEED, sum(map(ord, tag)) * 1000 + len(tag), rep]).generate_state(1)[0])


def summarize(df, keys):
    g = df.groupby(keys)
    s = g.agg(est_mean=("q", "mean"), truth=("truth", "first"), sd=("q", "std"), n=("q", "size"),
              cover=("cover", "mean"), width=("width", "mean"), fmi=("fmi", "mean"))
    s["bias"] = s["est_mean"] - s["truth"]
    s["rmse"] = np.sqrt(g.apply(lambda x: ((x["q"] - x["truth"]) ** 2).mean()))
    s["std_bias"] = s["bias"] / s["sd"]
    s["mc_se_cover"] = np.sqrt(s["cover"] * (1 - s["cover"]) / s["n"])
    return s.reset_index()


def main():
    t0 = time.time()
    # ---- 0) 真の値と、欠け方の例（母集団そのものに1回欠かす）
    truth_tab = pd.DataFrame({"est": EST, "truth": [TRUTH[k] for k in EST]})
    truth_tab.loc[truth_tab.est == "corr_unemp_tert", "truth_r"] = np.tanh(TRUTH["corr_unemp_tert"])
    truth_tab.to_csv(RES / "truth.csv", index=False)
    pat = []
    dec = pd.qcut(POP[:, IDX["logpop"]], 10, labels=False)
    for mech in ["mcar", "mar", "mnar"]:
        Dm = make_missing(POP, mech, 0.3, np.random.default_rng(SEED))
        for c in MISS:
            miss = np.isnan(Dm[:, IDX[c]])
            for d_ in range(10):
                pat.append({"mech": mech, "var": c, "pop_decile": d_ + 1, "miss_rate": miss[dec == d_].mean()})
            pat.append({"mech": mech, "var": c, "pop_decile": "all", "miss_rate": miss.mean(),
                        "obs_mean": np.nanmean(Dm[:, IDX[c]]), "true_mean": POP[:, IDX[c]].mean()})
    pd.DataFrame(pat).to_csv(RES / "missing_pattern.csv", index=False)

    jobs = []
    main_methods = ["full", "avail", "mean", "reg", "sreg", "knn", "mi_norm", "mi_pmm"]
    for mech in ["mcar", "mar", "mnar"]:
        for rep in range(R_MAIN):
            jobs.append(("main", rep, mech, 0.3, main_methods, 1.5, None, "log", True))
        for rep in range(R_FOREST):
            jobs.append(("forest", rep, mech, 0.3, ["forest"], 1.5, None, "log", True))
    for rate in [0.1, 0.5]:  # 欠測の割合（MAR）
        for rep in range(R_SUB):
            jobs.append((f"rate{rate}", rep, "mar", rate, ["full", "avail", "mean", "mi_pmm"], 1.5, None, "log", True))
    for st in [0.75, 3.0]:  # 欠け方の強さ（MAR・MNAR）
        for mech in ["mar", "mnar"]:
            for rep in range(R_SUB):
                jobs.append((f"str{st}", rep, mech, 0.3, ["avail", "mi_pmm"], st, None, "log", True))
    # 埋めるモデルの設定（MAR 30%）
    variants = {
        "pmm_k1": ("mi_pmm", {"k": 1}), "pmm_k10": ("mi_pmm", {"k": 10}),
        "pmm_iter5": ("mi_pmm", {"iters": 5}), "pmm_iter20": ("mi_pmm", {"iters": 20}),
        "pmm_m5": ("mi_pmm", {"m": 5}), "pmm_m30": ("mi_pmm", {"m": 30}),
        "pmm_no_tax": ("mi_pmm", {"use": ["logpop", "aging", "logdens", "births", "single", "unemp", "tert"]}),
        "pmm_strata5": ("mi_pmm", {"strata": 5}), "norm_strata5": ("mi_norm", {"strata": 5}),
    }
    for vname, (meth, kw) in variants.items():
        for rep in range(R_SUB):
            jobs.append((vname, rep, "mar", 0.3, [meth], 1.5, kw, "log", True))
    for rep in range(R_SUB):  # 分析モデル：地方税を対数にしない
        jobs.append(("level", rep, "mar", 0.3, ["full", "avail", "mean", "mi_pmm"], 1.5, None, "level", True))

    print("ジョブ", len(jobs), flush=True)
    rows = []
    with Pool(2) as pool:
        for i, out in enumerate(pool.imap_unordered(job, jobs, chunksize=4)):
            rows.extend(out)
            if i % 200 == 0:
                print(i, f"{time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df["cover"] = df["cover"].astype(float)
    df.to_csv(RES / "sim_reps.csv.gz", index=False, compression="gzip")
    summ = summarize(df, ["tag", "mech", "rate", "strength", "method", "est"])
    summ.to_csv(RES / "sim_summary.csv", index=False)

    # ---- m（埋める回数）の決め方：母集団に1回だけ欠かしたデータを固定し、埋める乱数だけを変える
    Dm = make_missing(POP, "mar", 0.3, np.random.default_rng(SEED + 7))
    mrows = []
    ms = [2, 5, 10, 20, 50] if not QUICK else [2, 5, 10]
    runs = 30 if not QUICK else 6
    for m in ms:
        for run in range(runs):
            rng = np.random.default_rng([SEED, m, run])
            Ds = mice(Dm, m, rng, method="pmm")
            qs, ses = zip(*[estimates(x) for x in Ds])
            rb = rubin(list(qs), list(ses))
            for k in HAS_SE:
                q, se, dfr, fmi = rb[k]
                t = stats.t.ppf(0.975, dfr)
                mrows.append({"m": m, "run": run, "est": k, "q": q, "se": se, "df": dfr, "fmi": fmi,
                              "lo": q - t * se, "hi": q + t * se})
        print("m", m, f"{time.time() - t0:.0f}s", flush=True)
    mdf = pd.DataFrame(mrows)
    mdf.to_csv(RES / "m_runs.csv", index=False)
    # 基準：m=200 を1回
    rng = np.random.default_rng([SEED, 999])
    Ds = mice(Dm, 200 if not QUICK else 30, rng, method="pmm")
    qs, ses = zip(*[estimates(x) for x in Ds])
    ref = rubin(list(qs), list(ses))
    msum = mdf.groupby(["est", "m"]).agg(q_sd=("q", "std"), hi_sd=("hi", "std"), se_mean=("se", "mean"),
                                         fmi_mean=("fmi", "mean"), df_med=("df", "median")).reset_index()
    msum["ref_q"] = msum.est.map(lambda k: ref[k][0])
    msum["ref_se"] = msum.est.map(lambda k: ref[k][1])
    msum["ref_fmi"] = msum.est.map(lambda k: ref[k][3])
    msum["q_sd_over_se"] = msum.q_sd / msum.ref_se
    msum.to_csv(RES / "m_summary.csv", index=False)

    # ---- 図用：母集団に MAR で欠かしたときの、地方税の埋めた値の分布
    rng = np.random.default_rng(SEED + 11)
    Dm = make_missing(POP, "mar", 0.3, rng)
    mi = np.isnan(Dm[:, IDX["logtax"]])
    dist = {"true_missing": POP[mi, IDX["logtax"]], "observed": Dm[~mi, IDX["logtax"]],
            "mean": fill_mean(Dm)[mi, IDX["logtax"]], "reg": fill_regression(Dm, rng)[mi, IDX["logtax"]],
            "mi_norm": mice(Dm, 1, rng, method="norm")[0][mi, IDX["logtax"]],
            "mi_pmm": mice(Dm, 1, rng, method="pmm")[0][mi, IDX["logtax"]]}
    pd.DataFrame([{"kind": k, "logtax": v} for k, arr in dist.items() for v in arr]).to_csv(
        RES / "imputed_tax_dist.csv", index=False)

    summary = {"n_muni": int(N), "R_main": R_MAIN, "R_sub": R_SUB, "R_forest": R_FOREST, "m": M,
               "truth": {k: float(TRUTH[k]) for k in EST}, "seconds": round(time.time() - t0)}
    json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
    print("done", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
