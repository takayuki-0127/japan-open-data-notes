"""03 分析：離島の市町村と、人口の規模（と高齢化）をそろえた本土の市町村で、人口の増減率を比べる。オフライン。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"; RES.mkdir(exist_ok=True)
SEED = 20261116
NBOOT = 2000

def prep():
    m = pd.read_csv(BASE / "data" / "municipalities.csv", dtype={"code": str})
    m = m[m.group != "excluded"].copy()
    m["g15_20"] = m.pop2020 / m.pop2015r
    m["g20_25"] = m.pop2025 / m.pop2020r
    m["chg15_25"] = (m.g15_20 * m.g20_25 - 1) * 100
    m["chg20_25"] = (m.g20_25 - 1) * 100
    m["chg10_25"] = (m.pop2015 / m.pop2010r * m.g15_20 * m.g20_25 - 1) * 100
    known15 = m[["a0_14_2015", "a15_64_2015", "a65_2015"]].sum(axis=1)
    m["share65_2015"] = m.a65_2015 / known15 * 100
    m["wa2015"] = m.a15_64_2015 / known15 * m.pop2015      # 15〜64歳（不詳を割合で配る）
    m["chg_wa15_25"] = (m.a15_64_2025 / m.wa2015 - 1) * 100
    m["logpop"] = np.log(m.pop2015r)
    # 2015年の人口が100人未満（増減率が出せない）と、2015年ファイルとつながらない市町村を除く
    m = m[(m.pop2015r >= 100) & m.share65_2015.notna() & m.chg15_25.notna()].copy()
    # 2010→2015年に人口が半分未満になった市町村（特別な事情で人口が大きく動いた町）は本土の側から除く
    m["disrupted"] = (m.group == "mainland") & (m.pop2015 / m.pop2010r < 0.5)
    print("disrupted:", m[m.disrupted].name.tolist())
    m = m[~m.disrupted].copy()
    m["island"] = (m.group == "island").astype(int)
    return m.sort_values("code", kind="mergesort").reset_index(drop=True)

def match(m, outcome, k=5, covs=("logpop",), same_region=False, pool=None):
    isl = m[m.island == 1]
    main = m[m.island == 0] if pool is None else pool
    X = main[list(covs)].to_numpy(dtype=float)
    sd = m[list(covs)].std().to_numpy()
    rows = []
    for _, r in isl.iterrows():
        cand = main
        Xc = X
        if same_region:
            sel = (main.region == r.region).to_numpy()
            cand, Xc = main[sel], X[sel]
        d = np.sqrt((((Xc - r[list(covs)].to_numpy(dtype=float)) / sd) ** 2).sum(axis=1))
        idx = np.argsort(d, kind="mergesort")[:k]
        ctrl = cand.iloc[idx]
        rows.append(dict(code=r.code, name=r["name"], pref=r.pref, pop2015=int(r.pop2015r), share65_2015=round(r.share65_2015, 2),
                         island=round(float(r[outcome]), 3), matched=round(float(ctrl[outcome].mean()), 3),
                         matched_share65=round(float(ctrl.share65_2015.mean()), 2),
                         matched_pop=int(ctrl.pop2015r.mean()), matched_metro=round(float(ctrl.metro2015.mean()), 2), matched_names="・".join(ctrl["name"].tolist())))
    t = pd.DataFrame(rows)
    t["diff"] = (t.island - t.matched).round(3)
    return t

def boot_median(x, seed=SEED):
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    b = np.median(x[rng.integers(0, len(x), size=(NBOOT, len(x)))], axis=1)
    return float(np.median(x)), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))

def summ(t):
    med, lo, hi = boot_median(t["diff"])
    return dict(n=int(len(t)), median_diff=round(med, 2), ci_lo=round(lo, 2), ci_hi=round(hi, 2),
                mean_diff=round(float(t["diff"].mean()), 2), share_island_lower=round(float((t["diff"] < 0).mean()), 3),
                island_median=round(float(t.island.median()), 2), matched_median=round(float(t.matched.median()), 2))

def main():
    m = prep()
    M = {"n_island": int(m.island.sum()), "n_mainland": int((m.island == 0).sum())}
    t1 = match(m, "chg15_25")
    t2 = match(m, "chg15_25", covs=("logpop", "share65_2015"))
    t4 = match(m, "chg_wa15_25")
    t1.to_csv(RES / "matched_size.csv", index=False, lineterminator="\n")
    t2.to_csv(RES / "matched_size_aging.csv", index=False, lineterminator="\n")
    M["H1_size"] = summ(t1)
    M["H2_size_aging"] = summ(t2)
    M["H2_shrink_ratio"] = round(1 - M["H2_size_aging"]["median_diff"] / M["H1_size"]["median_diff"], 3)
    small = t1.pop2015 < 5000
    M["H3_small"] = summ(t1[small]); M["H3_large"] = summ(t1[~small])
    M["H4_working_age"] = summ(t4)
    t4.to_csv(RES / "matched_working_age.csv", index=False, lineterminator="\n")
    # 規模別の中央値（離島と本土）
    bins = [0, 2000, 5000, 20000, 1e9]
    labels = ["2千人未満", "2千〜5千人", "5千〜2万人", "2万人以上"]
    m["size"] = pd.cut(m.pop2015r, bins, labels=labels, right=False)
    sz = m.groupby(["size", "island"], observed=True).agg(n=("chg15_25", "size"), median_chg=("chg15_25", "median"),
                                                          median_share65=("share65_2015", "median")).reset_index()
    sz["median_chg"] = sz.median_chg.round(2); sz["median_share65"] = sz.median_share65.round(2)
    sz.to_csv(RES / "by_size.csv", index=False, lineterminator="\n")
    M["by_size"] = sz.assign(size=sz["size"].astype(str)).to_dict(orient="records")
    M["island_total"] = {"pop2015": int(m[m.island == 1].pop2015r.sum()), "pop2025": int(m[m.island == 1].pop2025.sum()),
                         "chg15_25": round(float((m[m.island == 1].pop2025.sum() / (m[m.island == 1].pop2015r * 1).sum() - 1) * 100), 2)}
    M["island_share65_2015_median"] = round(float(m[m.island == 1].share65_2015.median()), 2)
    M["matched_share65_2015_median_size_only"] = round(float(t1.matched_share65.median()), 2)

    # 問い直し：本土の側を、2015年の大都市圏・都市圏に入らない市町村に絞る（郊外の町と比べないため）
    nonmetro = m[(m.island == 0) & (m.metro2015 == 0)]
    rq = {}
    for name, covs in [("size", ("logpop",)), ("size_aging", ("logpop", "share65_2015"))]:
        t = match(m, "chg15_25", covs=covs, pool=nonmetro)
        t.to_csv(RES / f"requestion_nonmetro_{name}.csv", index=False, lineterminator="\n")
        rq[name] = summ(t)
        rq[name + "_small"] = summ(t[t.pop2015 < 5000]); rq[name + "_large"] = summ(t[t.pop2015 >= 5000])
    rq["n_nonmetro_mainland"] = int(len(nonmetro))
    rq["n_metro_mainland"] = int(((m.island == 0) & (m.metro2015 == 1)).sum())
    rq["metro_share_size_matched_large"] = round(float(t1[t1.pop2015 >= 5000].matched_metro.mean()), 3)
    rq["metro_share_size_matched_small"] = round(float(t1[t1.pop2015 < 5000].matched_metro.mean()), 3)
    M["requestion_nonmetro"] = rq

    # 頑健性
    rob = []
    def add(name, t):
        s = summ(t); s["check"] = name; rob.append(s)
    add("main_k5_size", t1)
    add("k10_size", match(m, "chg15_25", k=10))
    add("same_region_k5_size", match(m, "chg15_25", same_region=True))
    add("period_2020_2025", match(m, "chg20_25"))
    m10 = m[m.chg10_25.notna()]
    add("period_2010_2025", match(m10, "chg10_25"))
    q = m[m.island == 0].chg15_25.quantile([0.01, 0.99]).to_numpy()
    trimmed = m[(m.island == 1) | m.chg15_25.between(q[0], q[1])]
    add("trim_mainland_1pct", match(trimmed, "chg15_25"))
    add("size_aging_k10", match(m, "chg15_25", k=10, covs=("logpop", "share65_2015")))
    add("exclude_tokyo_islands", t1[~t1.pref.eq("東京都")])
    rob = pd.DataFrame(rob)[["check", "n", "median_diff", "ci_lo", "ci_hi", "mean_diff", "share_island_lower"]]
    # 回帰
    reg = {}
    for name, f in [("size", "chg15_25 ~ island + logpop"), ("size_aging", "chg15_25 ~ island + logpop + share65_2015"),
                    ("size_aging_region", "chg15_25 ~ island + logpop + share65_2015 + C(region)")]:
        fit = smf.ols(f, data=m).fit(cov_type="HC1")
        reg[name] = dict(coef=round(float(fit.params["island"]), 2), se=round(float(fit.bse["island"]), 2),
                         p=round(float(fit.pvalues["island"]), 4), r2=round(float(fit.rsquared), 3), n=int(fit.nobs))
        rob = pd.concat([rob, pd.DataFrame([dict(check=f"ols_{name}", n=int(fit.nobs), median_diff=np.nan,
                                                  ci_lo=round(float(fit.conf_int().loc["island", 0]), 2),
                                                  ci_hi=round(float(fit.conf_int().loc["island", 1]), 2),
                                                  mean_diff=round(float(fit.params["island"]), 2), share_island_lower=np.nan)])],
                        ignore_index=True)
    rob.to_csv(RES / "robustness.csv", index=False, lineterminator="\n")
    M["regression"] = reg
    M["robustness"] = [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()} for r in rob.to_dict(orient="records")]
    M["hypotheses"] = {
        "H1": {"median_diff": M["H1_size"]["median_diff"], "supported": bool(M["H1_size"]["median_diff"] <= -3)},
        "H2": {"median_diff": M["H2_size_aging"]["median_diff"], "shrink": M["H2_shrink_ratio"],
               "supported": (bool(M["H2_shrink_ratio"] >= 0.5) if M["H1_size"]["median_diff"] <= -3 else None),
               "note": "H1 の差（離島の方が速く減る差）が3ポイント未満のため、縮み方は判定できない" if M["H1_size"]["median_diff"] > -3 else ""},
        "H3": {"small": M["H3_small"]["median_diff"], "large": M["H3_large"]["median_diff"],
               "supported": bool(M["H3_small"]["median_diff"] < M["H3_large"]["median_diff"])},
        "H4": {"median_diff": M["H4_working_age"]["median_diff"], "supported": bool(M["H4_working_age"]["median_diff"] <= -3)},
    }
    (RES / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: M[k] for k in ["n_island", "n_mainland", "H1_size", "H2_size_aging", "H2_shrink_ratio", "H3_small", "H3_large",
                                        "H4_working_age", "island_total", "island_share65_2015_median",
                                        "matched_share65_2015_median_size_only", "regression", "hypotheses", "requestion_nonmetro"]}, ensure_ascii=False))
    print(rob.to_string()); print(sz.to_string())
    print(t1[["name", "pop2015", "share65_2015", "island", "matched", "matched_share65", "diff"]].to_string())

if __name__ == "__main__":
    main()
