"""03 分析：
2008Q1〜2026Q2 の74四半期それぞれについて、F18 と同じ4時点（1か月目末・2か月目末・3か月目末・翌月末）で
その時点に出ているデータだけを使い、GDP 前期比を次の方法で推定する。
  - MIDAS 回帰（1系列ずつ、指数アーモン型の重み、ラグ6か月、GDP の手に入る最新期も入れる）→ 20系列の平均
  - ブリッジ方程式（足りない月を月次 AR(2) で埋めて四半期平均 → 回帰）→ 20系列の平均
  - AR(1)、F18 のダイナミックファクターモデル（結果を再利用）
頑健性：重みの形（beta・制約なし U-MIDAS）、ラグ12か月、GDP の自己ラグなし、平均のとり方（中央値）、一致系列だけ、コロナ期を除く評価"""
import json
from multiprocessing import Pool
import numpy as np
import pandas as pd
from scipy import stats
from common import RES, RAW, ALL, COIN, VNAMES, SEED
from midas import load, vintage, fit_predict_midas, fit_predict_bridge, ar_nowcast

np.random.seed(SEED)
P, G = load()
EVAL_Q = pd.period_range("2008Q1", "2026Q2", freq="Q")
COVID_Q = [str(q) for q in pd.period_range("2020Q1", "2021Q2", freq="Q")]
SPECS = {  # 名前: (重み, K, AR を入れるか)
    "almon6": ("almon", 6, True),
    "beta6": ("beta", 6, True),
    "umidas6": ("umidas", 6, True),
    "almon12": ("almon", 12, True),
    "almon6_noar": ("almon", 6, False),
}


def one(args):
    q, vi = args
    V = q.asfreq("M", how="start") + vi
    z, gv = vintage(P, G, V, ALL)
    ar, gap = ar_nowcast(gv, q)
    end_m = q.asfreq("M", how="end")
    out = []
    for c in ALL:
        x = z[c].dropna()
        if len(x) == 0:
            continue
        d = max(0, (end_m - x.index.max()).n)
        rec = dict(q=str(q), vint=VNAMES[vi], series=c, d=d, gap=gap, ar=ar, actual=float(G.get(q, np.nan)))
        for name, (wt, K, use_ar) in SPECS.items():
            v, info = fit_predict_midas(x, gv, q, d, gap, K=K, weight=wt, use_ar=use_ar)
            rec[name] = v
            if name == "almon6" and info is not None and c == "鉱工業生産":
                rec["w_almon6"] = json.dumps([round(float(t), 4) for t in info["w"]])
        rec["bridge"] = fit_predict_bridge(x, gv, q, gap, use_ar=True)
        out.append(rec)
    return out


def dm(e1, e2):
    d = e1 ** 2 - e2 ** 2
    d = d[~np.isnan(d)]
    n = len(d)
    st = d.mean() / np.sqrt(d.var(ddof=0) / n)
    st *= np.sqrt((n - 1) / n)
    return float(st), float(2 * stats.t.sf(abs(st), n - 1))


def rmse(e):
    return float(np.sqrt(np.nanmean(np.asarray(e) ** 2)))


if __name__ == "__main__":
    RES.mkdir(exist_ok=True)
    f = RES / "by_series.csv"
    if not f.exists():
        jobs = [(q, vi) for q in EVAL_Q for vi in range(4)]
        with Pool(2) as pool:
            res = pool.map(one, jobs, chunksize=4)
        bs = pd.DataFrame([r for rr in res for r in rr])
        bs.to_csv(f, index=False)
    bs = pd.read_csv(f)
    dfm = pd.read_csv(RAW / "f18_nowcast_base.csv")[["q", "vint", "dfm"]]

    # 系列の平均（予測の組み合わせ）
    meths = list(SPECS) + ["bridge"]
    comb = []
    for (q, v), g in bs.groupby(["q", "vint"]):
        r = dict(q=q, vint=v, ar=g.ar.iloc[0], actual=g.actual.iloc[0])
        for m in meths:
            r[m] = g[m].mean()
            r[m + "_med"] = g[m].median()
            r[m + "_coin"] = g[g.series.isin(COIN)][m].mean()
        r["almon6_iip"] = g[g.series == "鉱工業生産"].almon6.mean()
        comb.append(r)
    comb = pd.DataFrame(comb).merge(dfm, on=["q", "vint"], how="left")
    comb.to_csv(RES / "nowcast_combined.csv", index=False)

    def table(d, label):
        rows = []
        for v in VNAMES:
            x = d[d.vint == v]
            e = {k: x[k] - x.actual for k in ["ar", "dfm", "almon6", "bridge"]}
            r = dict(設定=label, 時点=v, n=int(x.actual.notna().sum()),
                     RMSE_AR=rmse(e["ar"]), RMSE_DFM=rmse(e["dfm"]), RMSE_MIDAS=rmse(e["almon6"]), RMSE_ブリッジ=rmse(e["bridge"]))
            r["MIDAS÷AR"] = r["RMSE_MIDAS"] / r["RMSE_AR"]
            r["ブリッジ÷AR"] = r["RMSE_ブリッジ"] / r["RMSE_AR"]
            r["DFM÷AR"] = r["RMSE_DFM"] / r["RMSE_AR"]
            r["DM_p_MIDAS対AR"] = dm(e["almon6"].values, e["ar"].values)[1]
            r["DM_p_MIDAS対DFM"] = dm(e["almon6"].values, e["dfm"].values)[1]
            r["DM_p_ブリッジ対AR"] = dm(e["bridge"].values, e["ar"].values)[1]
            r["符号一致_MIDAS"] = float(np.mean(np.sign(x.almon6) == np.sign(x.actual)))
            r["符号一致_DFM"] = float(np.mean(np.sign(x.dfm) == np.sign(x.actual)))
            r["相関_MIDAS"] = float(np.corrcoef(x.almon6, x.actual)[0, 1])
            r["相関_DFM"] = float(np.corrcoef(x.dfm, x.actual)[0, 1])
            rows.append(r)
        return pd.DataFrame(rows)

    acc = pd.concat([table(comb, "基本"), table(comb[~comb.q.isin(COVID_Q)], "コロナ期を除いて評価")])
    acc.to_csv(RES / "accuracy.csv", index=False)
    print(acc.round(3).to_string())

    # 頑健性：MIDAS の各設定 ÷ AR（4時点）
    rob = []
    variants = [("指数アーモン・ラグ6（基本）", "almon6"), ("beta ラグ・ラグ6", "beta6"), ("制約なし U-MIDAS・ラグ6", "umidas6"),
                ("指数アーモン・ラグ12", "almon12"), ("GDP の自己ラグなし", "almon6_noar"),
                ("20系列の中央値", "almon6_med"), ("一致系列だけの平均", "almon6_coin"), ("鉱工業生産だけ", "almon6_iip"), ("ブリッジ方程式", "bridge"),
                ("F18 の DFM", "dfm")]
    yr = comb.q.str[:4].astype(int)
    for evlab, d in [("全期間", comb), ("コロナ期を除く", comb[~comb.q.isin(COVID_Q)]),
                     ("2008〜2016年", comb[yr <= 2016]), ("2017〜2026年", comb[yr >= 2017])]:
        for lab, col in variants:
            r = dict(評価=evlab, 設定=lab)
            for v in VNAMES:
                x = d[d.vint == v]
                r[v] = rmse(x[col] - x.actual) / rmse(x.ar - x.actual)
            rob.append(r)
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    print(rob.round(3).to_string())

    # 系列ごとの MIDAS（基本）÷ AR
    per = []
    for c in ALL:
        r = dict(series=c)
        for v in VNAMES:
            x = bs[(bs.series == c) & (bs.vint == v)]
            r[v] = rmse(x.almon6 - x.actual) / rmse(x.ar - x.actual)
            r[v + "_n"] = int(x.almon6.notna().sum())
        per.append(r)
    per = pd.DataFrame(per).sort_values("翌月")
    per.to_csv(RES / "per_series.csv", index=False)
    print(per.round(3).to_string())

    # 鉱工業生産の重み（時点ごとの平均）
    ww = bs[(bs.series == "鉱工業生産") & bs.w_almon6.notna()].copy()
    W = {v: np.mean([json.loads(s) for s in ww[ww.vint == v].w_almon6], axis=0).tolist() for v in VNAMES}
    # 組み合わせどうしの相関・2026Q3 は扱わない（F18 と同じ評価期間）
    big = comb[comb.vint == "翌月"].copy()
    big["e_midas"] = big.almon6 - big.actual
    big["e_dfm"] = big.dfm - big.actual
    worst = big.reindex(big.e_midas.abs().sort_values(ascending=False).index).head(5)[["q", "actual", "almon6", "dfm", "bridge"]]
    summ = dict(
        weights_iip=W,
        corr_midas_dfm={v: float(comb[comb.vint == v][["almon6", "dfm"]].corr().iloc[0, 1]) for v in VNAMES},
        worst5=worst.round(3).to_dict(orient="records"),
        neg_quarters=int((big.actual < 0).sum()),
        neg_hit_midas=int(((big.actual < 0) & (big.almon6 < 0)).sum()),
        neg_hit_dfm=int(((big.actual < 0) & (big.dfm < 0)).sum()),
        neg_hit_bridge=int(((big.actual < 0) & (big.bridge < 0)).sum()),
        n_fits=int(bs[list(SPECS)].notna().sum().sum()),
    )
    json.dump(summ, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
